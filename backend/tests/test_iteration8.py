"""Gestor360 — iteration 8 backend tests.

Feature under test: PDF timezone localization.
GET /api/documents/{id}/pdf?tz=<IANA> renders Emissão/Validade/boleto dates and
footer in the requested timezone (default America/Sao_Paulo, invalid falls back).

Run: pytest /app/backend/tests/test_iteration8.py -v
"""
import io
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import requests
from dotenv import dotenv_values
from pypdf import PdfReader

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = base_url.rstrip("/") + "/api"

SUFFIX = uuid.uuid4().hex[:6]
COMPANY_CODE = "gestor360"
COMPANY_PW = "Empresa123"
ACRE = "America/Rio_Branco"
SP = "America/Sao_Paulo"

STATE = {}


def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:password|senha)(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    if not email or not pw:
        pytest.skip("credentials not parseable in /app/memory/test_credentials.md")
    return email.group(1), pw.group(1)


OWNER_EMAIL, OWNER_PW = creds()


def sess(token=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


@pytest.fixture(scope="module")
def owner():
    s = sess()
    r = s.post(f"{BASE}/auth/owner-login", json={"email": OWNER_EMAIL, "password": OWNER_PW})
    if r.status_code != 200:
        pytest.fail(f"owner login failed {r.status_code}: {r.text[:300]}")
    d = r.json()
    STATE["owner_token"] = d["token"]
    return sess(d["token"])


@pytest.fixture(scope="module")
def doc_ctx(owner):
    """Create client + product + orcamento (with boleto 30/60/90) for PDF tests."""
    c = owner.post(f"{BASE}/clients", json={
        "name": f"TEST_cli8 {SUFFIX}", "document": "12345678909",
        "phone": "68999990000", "city": "Rio Branco", "state": "AC"})
    assert c.status_code == 200, c.text[:300]
    cid = c.json()["id"]

    p = owner.post(f"{BASE}/products", json={
        "code": f"TESTP8{SUFFIX}", "description": f"TEST_prod8 {SUFFIX}",
        "price": 100.0, "stock": 50, "unit": "UN"})
    assert p.status_code == 200, p.text[:300]
    pid = p.json()["id"]

    d = owner.post(f"{BASE}/documents", json={
        "doc_type": "orcamento", "client_id": cid,
        "lines": [{"product_id": pid, "code": f"TESTP8{SUFFIX}", "description": "TEST_prod8",
                   "quantity": 3, "unit_price": 100.0, "discount_pct": 0}],
        "payments": [{"method": "boleto", "amount": 300.0, "installments": 1,
                      "boleto_days": [30, 60, 90]}],
        "notes": "TEST iteration8 tz"})
    assert d.status_code == 200, d.text[:400]
    body = d.json()
    STATE["doc_id"] = body["id"]
    STATE["client_id"] = cid
    STATE["product_id"] = pid
    # created_at as UTC aware datetime
    created_raw = body["created_at"]
    ca = datetime.fromisoformat(created_raw) if isinstance(created_raw, str) else created_raw
    if ca.tzinfo is None:
        ca = ca.replace(tzinfo=timezone.utc)
    STATE["created_utc"] = ca
    STATE["valid_until"] = body.get("valid_until")
    return body


@pytest.fixture(scope="module", autouse=True)
def cleanup(owner):
    yield
    if STATE.get("doc_id"):
        owner.delete(f"{BASE}/documents/{STATE['doc_id']}")
    if STATE.get("client_id"):
        owner.delete(f"{BASE}/clients/{STATE['client_id']}")
    if STATE.get("product_id"):
        owner.delete(f"{BASE}/products/{STATE['product_id']}")


def get_pdf(owner, tz=None):
    url = f"{BASE}/documents/{STATE['doc_id']}/pdf"
    if tz is not None:
        r = owner.get(url, params={"tz": tz})
    else:
        r = owner.get(url)
    return r


EMISSAO_RE = re.compile(r"Emiss[aã]o:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})")
VALIDADE_RE = re.compile(r"Validade:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})")


class TestPdfTimezone:
    def test_01_pdf_acre_tz(self, owner, doc_ctx):
        r = get_pdf(owner, ACRE)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        text = pdf_text(r.content)
        STATE["text_acre"] = text
        m = EMISSAO_RE.search(text)
        assert m, f"Emissão not found in PDF text: {text[:600]!r}"
        got = m.group(1)
        expected = STATE["created_utc"].astimezone(ZoneInfo(ACRE)).strftime("%d/%m/%Y %H:%M")
        assert got == expected, f"Acre Emissão mismatch: pdf={got} expected={expected}"

        v = VALIDADE_RE.search(text)
        assert v, "Validade not found for orçamento"
        vu = datetime.fromisoformat(STATE["valid_until"])
        if vu.tzinfo is None:
            vu = vu.replace(tzinfo=timezone.utc)
        exp_v = vu.astimezone(ZoneInfo(ACRE)).strftime("%d/%m/%Y %H:%M")
        assert v.group(1) == exp_v, f"Acre Validade mismatch: pdf={v.group(1)} expected={exp_v}"

    def test_02_pdf_sao_paulo_tz(self, owner, doc_ctx):
        r = get_pdf(owner, SP)
        assert r.status_code == 200
        text = pdf_text(r.content)
        STATE["text_sp"] = text
        m = EMISSAO_RE.search(text)
        assert m, "Emissão not found"
        expected = STATE["created_utc"].astimezone(ZoneInfo(SP)).strftime("%d/%m/%Y %H:%M")
        assert m.group(1) == expected, f"SP Emissão mismatch: pdf={m.group(1)} expected={expected}"

    def test_03_shift_between_tz_is_2h(self, owner, doc_ctx):
        acre = datetime.strptime(EMISSAO_RE.search(STATE["text_acre"]).group(1), "%d/%m/%Y %H:%M")
        sp = datetime.strptime(EMISSAO_RE.search(STATE["text_sp"]).group(1), "%d/%m/%Y %H:%M")
        assert (sp - acre) == timedelta(hours=2), f"expected 2h shift SP-Acre, got {sp - acre}"

    def test_04_pdf_utc_tz(self, owner, doc_ctx):
        r = get_pdf(owner, "UTC")
        assert r.status_code == 200
        text = pdf_text(r.content)
        m = EMISSAO_RE.search(text)
        assert m
        expected = STATE["created_utc"].astimezone(ZoneInfo("UTC")).strftime("%d/%m/%Y %H:%M")
        assert m.group(1) == expected, f"UTC Emissão mismatch: pdf={m.group(1)} expected={expected}"

    def test_05_no_tz_param_defaults_to_sao_paulo(self, owner, doc_ctx):
        r = get_pdf(owner, None)
        assert r.status_code == 200, r.text[:300]
        m = EMISSAO_RE.search(pdf_text(r.content))
        assert m
        expected = STATE["created_utc"].astimezone(ZoneInfo(SP)).strftime("%d/%m/%Y %H:%M")
        assert m.group(1) == expected, f"default tz not SP: pdf={m.group(1)} expected={expected}"

    def test_06_invalid_tz_falls_back_silently(self, owner, doc_ctx):
        r = get_pdf(owner, "Not/AValidZone")
        assert r.status_code == 200, f"invalid tz should not error: {r.status_code} {r.text[:300]}"
        m = EMISSAO_RE.search(pdf_text(r.content))
        assert m
        expected = STATE["created_utc"].astimezone(ZoneInfo(SP)).strftime("%d/%m/%Y %H:%M")
        assert m.group(1) == expected, f"fallback tz not SP: pdf={m.group(1)} expected={expected}"

    def test_07_empty_tz_param(self, owner, doc_ctx):
        r = get_pdf(owner, "")
        assert r.status_code == 200, f"empty tz should not error: {r.status_code} {r.text[:200]}"

    def test_08_boleto_installment_dates_local_tz(self, owner, doc_ctx):
        text = STATE.get("text_acre") or pdf_text(get_pdf(owner, ACRE).content)
        created_local = STATE["created_utc"].astimezone(ZoneInfo(ACRE))
        found = 0
        for i, days in enumerate([30, 60, 90], 1):
            due = (created_local + timedelta(days=days)).strftime("%d/%m/%Y")
            pat = f"{i}ª/{due}"
            assert pat in text.replace("\n", ""), f"parcela '{pat}' missing. text={text[-900:]!r}"
            found += 1
        assert found == 3
        assert "3x de" in text.replace("\n", ""), "expected '3x de' boleto split"

    def test_09_boleto_dates_shift_with_tz(self, owner, doc_ctx):
        """Boleto due dates must be based on the local-tz created date."""
        text_acre = STATE["text_acre"].replace("\n", "")
        text_utc = pdf_text(get_pdf(owner, "UTC").content).replace("\n", "")
        ca = STATE["created_utc"]
        for i, days in enumerate([30, 60, 90], 1):
            exp_acre = (ca.astimezone(ZoneInfo(ACRE)) + timedelta(days=days)).strftime("%d/%m/%Y")
            exp_utc = (ca.astimezone(ZoneInfo("UTC")) + timedelta(days=days)).strftime("%d/%m/%Y")
            assert f"{i}ª/{exp_acre}" in text_acre
            assert f"{i}ª/{exp_utc}" in text_utc

    def test_10_footer_date_in_requested_tz(self, owner, doc_ctx):
        text = STATE["text_acre"].replace("\n", "")
        expected = datetime.now(ZoneInfo(ACRE)).strftime("%d/%m/%Y")
        assert "Gestor360" in text
        assert expected in text, f"footer date {expected} not in PDF"


# Regression: core endpoints still healthy
class TestRegression:
    def test_11_documents_list_and_stats(self, owner, doc_ctx):
        assert owner.get(f"{BASE}/documents").status_code == 200
        st = owner.get(f"{BASE}/stats")
        assert st.status_code == 200 and isinstance(st.json(), dict)
        one = owner.get(f"{BASE}/documents/{STATE['doc_id']}")
        assert one.status_code == 200 and "_id" not in one.json()

    def test_12_venda_pdf_no_validade(self, owner, doc_ctx):
        d = owner.post(f"{BASE}/documents", json={
            "doc_type": "venda", "client_id": STATE["client_id"],
            "lines": [{"product_id": STATE["product_id"], "code": f"TESTP8{SUFFIX}",
                       "description": "TEST_prod8", "quantity": 1, "unit_price": 100.0,
                       "discount_pct": 0}],
            "payments": [{"method": "pix", "amount": 100.0, "installments": 1}],
            "notes": "TEST iteration8 venda"})
        assert d.status_code == 200, d.text[:300]
        vid = d.json()["id"]
        try:
            r = owner.get(f"{BASE}/documents/{vid}/pdf", params={"tz": ACRE})
            assert r.status_code == 200
            text = pdf_text(r.content)
            m = EMISSAO_RE.search(text)
            assert m
            ca = datetime.fromisoformat(d.json()["created_at"])
            if ca.tzinfo is None:
                ca = ca.replace(tzinfo=timezone.utc)
            assert m.group(1) == ca.astimezone(ZoneInfo(ACRE)).strftime("%d/%m/%Y %H:%M")
            assert "VENDA" in text
        finally:
            owner.delete(f"{BASE}/documents/{vid}")
