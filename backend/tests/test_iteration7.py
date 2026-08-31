"""Gestor360 — iteration 7 backend tests.

Feature under test: Product.cost_price (preço de custo) + preço de tabela (price),
with role-based visibility/write rules (owner/gerente see & set cost_price,
vendedor must not see or set it).

Run: pytest /app/backend/tests/test_iteration7.py -v
"""
import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = base_url.rstrip("/") + "/api"

SUFFIX = uuid.uuid4().hex[:6]
COMPANY_CODE = "gestor360"
COMPANY_PW = "Empresa123"
VEND_USERNAME = f"v7{SUFFIX}"
VEND_PW = "Vend123"
GER_USERNAME = f"g7{SUFFIX}"
GER_PW = "Ger1234"

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


def _mongo():
    from pymongo import MongoClient
    env = dotenv_values("/app/backend/.env")
    return MongoClient(env["MONGO_URL"]), env["DB_NAME"]


@pytest.fixture(scope="module")
def owner():
    s = sess()
    r = s.post(f"{BASE}/auth/owner-login", json={"email": OWNER_EMAIL, "password": OWNER_PW})
    if r.status_code != 200:
        pytest.fail(f"owner login failed {r.status_code}: {r.text[:300]}")
    d = r.json()
    STATE["owner_token"] = d["token"]
    STATE["owner_user_id"] = d["user"]["user_id"]
    STATE["company_id"] = d["user"]["company_id"]
    return sess(d["token"])


def _two_step_token(username, password):
    s = sess()
    r = s.post(f"{BASE}/auth/company-login", json={"code": COMPANY_CODE, "password": COMPANY_PW})
    assert r.status_code == 200, f"company-login failed: {r.status_code} {r.text[:200]}"
    r2 = s.post(f"{BASE}/auth/user-login", json={"username": username, "password": password})
    assert r2.status_code == 200, f"user-login failed: {r2.status_code} {r2.text[:200]}"
    return r2.json()["token"], r2.json().get("must_change_password")


class TestCostPrice:
    # ---------- baseline ----------
    def test_health(self):
        r = requests.get(f"{BASE}/")
        assert r.status_code == 200 and r.json().get("ok") is True

    # ---------- owner: create with cost_price ----------
    def test_owner_create_product_with_cost_price(self, owner):
        payload = {"code": f"TEST_C7{SUFFIX}", "description": "TEST Produto Custo",
                   "price": 100.0, "cost_price": 60.0, "stock": 5, "unit": "UN"}
        r = owner.post(f"{BASE}/products", json=payload)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["price"] == 100.0
        assert d["cost_price"] == 60.0
        assert isinstance(d["id"], str) and d["id"]
        assert "_id" not in d
        STATE["prod_id"] = d["id"]

        # GET verifies persistence
        rows = owner.get(f"{BASE}/products").json()
        row = next((p for p in rows if p["id"] == STATE["prod_id"]), None)
        assert row is not None, "created product missing from GET /products"
        assert row["cost_price"] == 60.0
        assert row["price"] == 100.0

    def test_owner_update_cost_price_persists(self, owner):
        r = owner.put(f"{BASE}/products/{STATE['prod_id']}", json={
            "code": f"TEST_C7{SUFFIX}", "description": "TEST Produto Custo",
            "price": 120.0, "cost_price": 75.5, "stock": 5, "unit": "UN"})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["cost_price"] == 75.5
        row = next(p for p in owner.get(f"{BASE}/products").json() if p["id"] == STATE["prod_id"])
        assert row["cost_price"] == 75.5 and row["price"] == 120.0
        # restore baseline for later vendedor tests
        owner.put(f"{BASE}/products/{STATE['prod_id']}", json={
            "code": f"TEST_C7{SUFFIX}", "description": "TEST Produto Custo",
            "price": 100.0, "cost_price": 60.0, "stock": 5, "unit": "UN"})

    def test_update_nonexistent_product_404(self, owner):
        r = owner.put(f"{BASE}/products/does-not-exist-{SUFFIX}", json={
            "code": "ZZZ", "description": "x", "price": 1, "cost_price": 1})
        assert r.status_code == 404, f"expected 404 got {r.status_code}"

    # ---------- legacy docs without cost_price ----------
    def test_legacy_product_without_cost_price_key(self, owner):
        mc, dbname = _mongo()
        legacy_id = f"legacy-{SUFFIX}"
        try:
            mc[dbname].products.insert_one({
                "id": legacy_id, "code": f"TEST_L7{SUFFIX}", "description": "TEST Legacy",
                "price": 10.0, "stock": 1, "unit": "UN", "company_id": STATE["company_id"]})
            STATE["legacy_id"] = legacy_id
            r = owner.get(f"{BASE}/products")
            assert r.status_code == 200, r.text[:300]
            row = next(p for p in r.json() if p["id"] == legacy_id)
            assert row.get("cost_price", 0.0) in (0, 0.0, None), row
            # updating a legacy doc works and adds cost_price
            u = owner.put(f"{BASE}/products/{legacy_id}", json={
                "code": f"TEST_L7{SUFFIX}", "description": "TEST Legacy", "price": 10.0,
                "cost_price": 4.0, "stock": 1, "unit": "UN"})
            assert u.status_code == 200 and u.json()["cost_price"] == 4.0
        finally:
            mc.close()

    # ---------- create vendedor + gerente ----------
    def test_create_temp_users(self, owner):
        v = owner.post(f"{BASE}/users", json={"name": "TEST Vend7", "username": VEND_USERNAME,
                                              "password": VEND_PW, "role": "vendedor"})
        assert v.status_code == 200, v.text[:300]
        STATE["vend_id"] = v.json()["user_id"]
        g = owner.post(f"{BASE}/users", json={"name": "TEST Ger7", "username": GER_USERNAME,
                                              "password": GER_PW, "role": "gerente"})
        assert g.status_code == 200, g.text[:300]
        STATE["ger_id"] = g.json()["user_id"]

        tok, must = _two_step_token(VEND_USERNAME, VEND_PW)
        assert must is True
        cp = sess(tok).post(f"{BASE}/auth/change-password",
                            json={"current_password": VEND_PW, "new_password": VEND_PW})
        # same password may be accepted; re-login to get a clean token
        assert cp.status_code in (200, 400), cp.text[:200]
        STATE["vend_token"] = tok

        gtok, _ = _two_step_token(GER_USERNAME, GER_PW)
        STATE["ger_token"] = gtok

    # ---------- vendedor visibility ----------
    def test_vendedor_cannot_see_cost_price(self):
        s = sess(STATE["vend_token"])
        r = s.get(f"{BASE}/products")
        assert r.status_code == 200, r.text[:300]
        rows = r.json()
        assert rows, "vendedor sees no products"
        leaked = [p["id"] for p in rows if "cost_price" in p and p.get("cost_price")]
        assert not leaked, f"cost_price leaked to vendedor for {leaked}"
        row = next(p for p in rows if p["id"] == STATE["prod_id"])
        assert "cost_price" not in row, row
        assert row["price"] == 100.0, "vendedor must still see table price"

    def test_vendedor_create_ignores_cost_price(self, owner):
        s = sess(STATE["vend_token"])
        r = s.post(f"{BASE}/products", json={"code": f"TEST_V7{SUFFIX}", "description": "TEST Vend Prod",
                                             "price": 50.0, "cost_price": 99.0})
        assert r.status_code == 200, r.text[:300]
        vid = r.json()["id"]
        STATE["vend_prod_id"] = vid
        assert "cost_price" not in r.json(), "response echoes cost_price to vendedor"
        row = next(p for p in owner.get(f"{BASE}/products").json() if p["id"] == vid)
        assert row["cost_price"] == 0.0, f"vendedor managed to set cost_price={row['cost_price']}"
        assert row["price"] == 50.0

    def test_vendedor_update_preserves_owner_cost_price(self, owner):
        s = sess(STATE["vend_token"])
        r = s.put(f"{BASE}/products/{STATE['prod_id']}", json={
            "code": f"TEST_C7{SUFFIX}", "description": "TEST Produto Custo v2",
            "price": 110.0, "cost_price": 1.0, "stock": 5, "unit": "UN"})
        assert r.status_code == 200, r.text[:300]
        assert "cost_price" not in r.json()
        row = next(p for p in owner.get(f"{BASE}/products").json() if p["id"] == STATE["prod_id"])
        assert row["cost_price"] == 60.0, f"vendedor overwrote cost_price -> {row['cost_price']}"
        assert row["price"] == 110.0, "vendedor price update not persisted"

    # ---------- gerente visibility ----------
    def test_gerente_sees_cost_price(self):
        s = sess(STATE["ger_token"])
        r = s.get(f"{BASE}/products")
        assert r.status_code == 200, r.text[:300]
        row = next(p for p in r.json() if p["id"] == STATE["prod_id"])
        assert row["cost_price"] == 60.0

    def test_gerente_can_set_cost_price(self, owner):
        s = sess(STATE["ger_token"])
        r = s.put(f"{BASE}/products/{STATE['prod_id']}", json={
            "code": f"TEST_C7{SUFFIX}", "description": "TEST Produto Custo",
            "price": 100.0, "cost_price": 65.0, "stock": 5, "unit": "UN"})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["cost_price"] == 65.0
        row = next(p for p in owner.get(f"{BASE}/products").json() if p["id"] == STATE["prod_id"])
        assert row["cost_price"] == 65.0

    # ---------- regression: documents / orcamento / pdf ----------
    def test_orcamento_flow_and_pdf(self, owner):
        c = owner.post(f"{BASE}/clients", json={"name": f"TEST Cliente7 {SUFFIX}", "phone": "11999990000"})
        assert c.status_code == 200, c.text[:300]
        STATE["client_id"] = c.json()["id"]
        d = owner.post(f"{BASE}/documents", json={
            "doc_type": "orcamento", "client_id": STATE["client_id"],
            "lines": [{"product_id": STATE["prod_id"], "code": f"TEST_C7{SUFFIX}",
                       "description": "TEST Produto Custo", "quantity": 2,
                       "unit_price": 100.0, "discount_pct": 0}],
            "payments": [{"method": "pix", "amount": 200.0, "installments": 1}], "notes": "TEST it7"})
        assert d.status_code == 200, d.text[:300]
        doc = d.json()
        STATE["doc_id"] = doc["id"]
        assert doc["lines"][0]["unit_price"] == 100.0
        assert "cost_price" not in doc["lines"][0], "cost_price leaked into document line"
        pdf = owner.get(f"{BASE}/documents/{STATE['doc_id']}/pdf")
        assert pdf.status_code == 200, pdf.text[:200]
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert len(pdf.content) > 1000
        conv = owner.post(f"{BASE}/documents/{STATE['doc_id']}/convert")
        assert conv.status_code == 200, conv.text[:300]
        STATE["venda_id"] = conv.json()["id"]
        # stock decremented on venda, cost_price untouched
        row = next(p for p in owner.get(f"{BASE}/products").json() if p["id"] == STATE["prod_id"])
        assert row["cost_price"] == 65.0, "cost_price mutated by stock update"

    def test_vendedor_pdf_of_own_doc_with_new_field(self):
        s = sess(STATE["vend_token"])
        d = s.post(f"{BASE}/documents", json={
            "doc_type": "orcamento", "client_id": STATE["client_id"],
            "lines": [{"product_id": STATE["vend_prod_id"], "code": f"TEST_V7{SUFFIX}",
                       "description": "TEST Vend Prod", "quantity": 1, "unit_price": 50.0}],
            "payments": [], "notes": "TEST it7 vend"})
        assert d.status_code == 200, d.text[:300]
        STATE["vend_doc_id"] = d.json()["id"]
        pdf = s.get(f"{BASE}/documents/{STATE['vend_doc_id']}/pdf")
        assert pdf.status_code == 200 and pdf.headers["content-type"].startswith("application/pdf")

    def test_stats_still_ok(self, owner):
        r = owner.get(f"{BASE}/stats")
        assert r.status_code == 200
        assert r.json()["products"] >= 1

    # ---------- extra hardening observations ----------
    def test_yy_edge_findings(self, owner):
        findings = []
        neg = owner.post(f"{BASE}/products", json={"code": f"TEST_N7{SUFFIX}", "description": "neg",
                                                   "price": 10, "cost_price": -5})
        if neg.status_code == 200:
            findings.append("POST /products accepts negative cost_price (-5)")
            STATE["neg_prod_id"] = neg.json()["id"]
        bad = owner.post(f"{BASE}/products", json={"code": f"TEST_S7{SUFFIX}", "description": "str",
                                                   "price": 10, "cost_price": "abc"})
        if bad.status_code not in (400, 422):
            findings.append(f"POST /products non-numeric cost_price -> {bad.status_code}")
        Path("/app/test_reports/pytest").mkdir(parents=True, exist_ok=True)
        Path("/app/test_reports/pytest/it7_edge_findings.txt").write_text("\n".join(findings) or "none")
        STATE["findings"] = findings

    # ---------- cleanup ----------
    def test_zz_cleanup(self, owner):
        for did in (STATE.get("vend_doc_id"), STATE.get("venda_id"), STATE.get("doc_id")):
            if did:
                owner.delete(f"{BASE}/documents/{did}")
        for pid in (STATE.get("prod_id"), STATE.get("vend_prod_id"),
                    STATE.get("legacy_id"), STATE.get("neg_prod_id")):
            if pid:
                assert owner.delete(f"{BASE}/products/{pid}").status_code == 200
        if STATE.get("client_id"):
            owner.delete(f"{BASE}/clients/{STATE['client_id']}")
        for uid in (STATE.get("vend_id"), STATE.get("ger_id")):
            if uid:
                r = owner.delete(f"{BASE}/users/{uid}")
                assert r.status_code == 200, r.text[:200]
        remaining = [p["code"] for p in owner.get(f"{BASE}/products").json()]
        assert not [c for c in remaining if c.startswith("TEST_")], f"leftover TEST_ products: {remaining}"
        users = [u["username"] for u in owner.get(f"{BASE}/users").json()]
        assert VEND_USERNAME not in users and GER_USERNAME not in users
