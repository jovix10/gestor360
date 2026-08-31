"""Gestor360 iteration-3 backend tests.

Scope:
- Client new structured address + IE fields (POST/GET/PUT)
- Company IE field (PUT/GET)
- Document payments persistence (POST/GET)
- PUT /api/documents/{id} partial update
- PDF with payments + structured address
- Convert orcamento -> venda with payments present
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
    raise RuntimeError("REACT_APP_BACKEND_URL is missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def creds():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("Missing /app/memory/test_credentials.md")
    c = p.read_text(encoding="utf-8")
    em = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not em or not pw:
        pytest.skip("No credentials in test_credentials.md")
    return {"email": em.group(1), "password": pw.group(1)}


@pytest.fixture(scope="module")
def api(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("token")
    if not token:
        pytest.fail(f"No token: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def tracker(api):
    t = {"clients": [], "products": [], "documents": []}
    yield t
    for d in t["documents"]:
        api.delete(f"{API}/documents/{d}", timeout=30)
    for p in t["products"]:
        api.delete(f"{API}/products/{p}", timeout=30)
    for c in t["clients"]:
        api.delete(f"{API}/clients/{c}", timeout=30)


ADDR = {
    "cep": "01001-000",
    "street": "Praça da Sé",
    "number": "100",
    "complement": "Sala 12",
    "district": "Sé",
    "city": "São Paulo",
    "state": "SP",
}


@pytest.fixture(scope="module")
def structured_client(api, tracker):
    payload = {"name": "TEST_ Cliente Estruturado", "document": "12345678000199",
               "ie": "110042490114", "email": "test_it3@example.test",
               "phone": "11988887777", "notes": "TEST_", **ADDR}
    r = api.post(f"{API}/clients", json=payload, timeout=30)
    assert r.status_code in (200, 201), r.text[:300]
    c = r.json()
    tracker["clients"].append(c["id"])
    return c


# ---------- Client new fields ----------
class TestClientNewFields:
    def test_create_persists_structured_fields(self, api, structured_client):
        c = structured_client
        assert "_id" not in c
        assert c["ie"] == "110042490114"
        for k, v in ADDR.items():
            assert c[k] == v, f"create response {k}={c.get(k)!r} expected {v!r}"

        rows = api.get(f"{API}/clients", timeout=30).json()
        got = [x for x in rows if x["id"] == c["id"]]
        assert got, "client not persisted"
        got = got[0]
        assert got["ie"] == "110042490114"
        for k, v in ADDR.items():
            assert got[k] == v, f"GET {k}={got.get(k)!r} expected {v!r}"

    def test_update_preserves_new_fields(self, api, structured_client):
        cid = structured_client["id"]
        body = {**structured_client, "name": "TEST_ Cliente Estruturado 2", "complement": "Sala 99"}
        r = api.put(f"{API}/clients/{cid}", json=body, timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["name"] == "TEST_ Cliente Estruturado 2"
        assert data["complement"] == "Sala 99"

        rows = api.get(f"{API}/clients", timeout=30).json()
        got = [x for x in rows if x["id"] == cid][0]
        assert got["name"] == "TEST_ Cliente Estruturado 2"
        assert got["complement"] == "Sala 99"
        assert got["cep"] == ADDR["cep"]
        assert got["city"] == ADDR["city"]
        assert got["ie"] == "110042490114"


# ---------- Company IE ----------
class TestCompanyIE:
    def test_put_and_get_ie(self, api):
        original = api.get(f"{API}/company", timeout=30)
        assert original.status_code == 200, original.text[:300]
        base = original.json()
        base.pop("user_id", None)
        base.pop("_id", None)
        body = {**base, "ie": "TEST_IE_998877"}
        r = api.put(f"{API}/company", json=body, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["ie"] == "TEST_IE_998877"

        g = api.get(f"{API}/company", timeout=30)
        assert g.status_code == 200
        assert g.json()["ie"] == "TEST_IE_998877"
        assert "_id" not in g.json()

        # restore
        api.put(f"{API}/company", json={**base, "ie": base.get("ie", "")}, timeout=30)


# ---------- Document payments ----------
PAYMENTS = [
    {"method": "pix", "amount": 60, "installments": 1},
    {"method": "credito", "amount": 120, "installments": 3},
]


@pytest.fixture(scope="module")
def doc_with_payments(api, tracker, structured_client):
    code = f"TEST_IT3_P1_{uuid.uuid4().hex[:6]}"
    rp = api.post(f"{API}/products", json={"code": code, "description": "TEST_ Produto It3",
                                           "price": 90, "stock": 10, "unit": "UN"}, timeout=30)
    assert rp.status_code in (200, 201), rp.text[:300]
    prod = rp.json()
    tracker["products"].append(prod["id"])

    r = api.post(f"{API}/documents", json={
        "doc_type": "orcamento",
        "client_id": structured_client["id"],
        "lines": [{"product_id": prod["id"], "code": prod["code"], "description": prod["description"],
                   "quantity": 2, "unit_price": 90, "discount_pct": 0}],
        "payments": PAYMENTS,
        "notes": "TEST_ pagamento dividido",
    }, timeout=30)
    assert r.status_code in (200, 201), r.text[:300]
    doc = r.json()
    tracker["documents"].append(doc["id"])
    return doc


class TestDocumentPayments:
    def test_create_persists_payments(self, api, doc_with_payments):
        doc = doc_with_payments
        assert "_id" not in doc
        assert len(doc["payments"]) == 2, doc.get("payments")
        assert doc["payments"][0]["method"] == "pix"
        assert doc["payments"][0]["amount"] == 60
        assert doc["payments"][1]["method"] == "credito"
        assert doc["payments"][1]["installments"] == 3

        g = api.get(f"{API}/documents/{doc['id']}", timeout=30)
        assert g.status_code == 200, g.text[:300]
        gd = g.json()
        assert "_id" not in gd
        assert len(gd["payments"]) == 2
        assert gd["payments"][1]["amount"] == 120
        assert gd["payments"][1]["installments"] == 3

    @pytest.mark.parametrize("method", ["pix", "dinheiro", "credito", "debito", "boleto", "transferencia"])
    def test_all_payment_methods_accepted(self, api, tracker, structured_client, method):
        r = api.post(f"{API}/documents", json={
            "doc_type": "orcamento", "client_id": structured_client["id"],
            "lines": [{"code": "X", "description": "TEST_ m", "quantity": 1, "unit_price": 10}],
            "payments": [{"method": method, "amount": 10, "installments": 12 if method == "credito" else 1}],
        }, timeout=30)
        assert r.status_code in (200, 201), f"{method} -> {r.status_code} {r.text[:200]}"
        d = r.json()
        tracker["documents"].append(d["id"])
        assert d["payments"][0]["method"] == method

    def test_empty_description_line_allowed(self, api, tracker, structured_client):
        r = api.post(f"{API}/documents", json={
            "doc_type": "orcamento", "client_id": structured_client["id"],
            "lines": [{"code": "TEST_NODESC", "quantity": 1, "unit_price": 5}],
        }, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        d = r.json()
        tracker["documents"].append(d["id"])
        assert d["lines"][0]["description"] == ""


# ---------- PUT /documents/{id} ----------
class TestDocumentUpdate:
    def test_update_lines_preserves_metadata(self, api, doc_with_payments):
        doc = doc_with_payments
        new_lines = [
            {"product_id": None, "code": "TEST_EDIT", "description": "TEST_ linha editada",
             "quantity": 3, "unit_price": 50, "discount_pct": 10},
        ]
        r = api.put(f"{API}/documents/{doc['id']}", json={"lines": new_lines}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        up = r.json()
        assert "_id" not in up
        assert len(up["lines"]) == 1
        assert up["lines"][0]["code"] == "TEST_EDIT"
        assert up["lines"][0]["quantity"] == 3
        # metadata preserved
        assert up["number"] == doc["number"]
        assert up["created_at"] == doc["created_at"]
        assert up["valid_until"] == doc["valid_until"]
        assert up["doc_type"] == doc["doc_type"]
        # untouched fields preserved
        assert len(up["payments"]) == 2
        assert up["notes"] == "TEST_ pagamento dividido"

        g = api.get(f"{API}/documents/{doc['id']}", timeout=30).json()
        assert g["lines"][0]["code"] == "TEST_EDIT"

        # list total recomputed: 3 * 50 * 0.9 = 135
        rows = api.get(f"{API}/documents", timeout=30).json()
        row = [x for x in rows if x["id"] == doc["id"]]
        assert row, "doc missing from list"
        assert row[0]["total"] == 135.0, row[0]["total"]

    def test_update_payments_and_notes(self, api, doc_with_payments):
        doc = doc_with_payments
        new_pay = [{"method": "boleto", "amount": 135, "installments": 1}]
        r = api.put(f"{API}/documents/{doc['id']}", json={"payments": new_pay, "notes": "TEST_ nota nova"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        up = r.json()
        assert len(up["payments"]) == 1
        assert up["payments"][0]["method"] == "boleto"
        assert up["payments"][0]["amount"] == 135
        assert up["notes"] == "TEST_ nota nova"

        g = api.get(f"{API}/documents/{doc['id']}", timeout=30).json()
        assert g["payments"][0]["method"] == "boleto"
        assert g["notes"] == "TEST_ nota nova"

    def test_update_client_id_valid(self, api, tracker, doc_with_payments):
        rc = api.post(f"{API}/clients", json={"name": "TEST_ Cliente Alvo Edit"}, timeout=30)
        assert rc.status_code in (200, 201), rc.text[:300]
        cid = rc.json()["id"]
        tracker["clients"].append(cid)
        r = api.put(f"{API}/documents/{doc_with_payments['id']}", json={"client_id": cid}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["client_id"] == cid
        # restore original client for PDF test
        api.put(f"{API}/documents/{doc_with_payments['id']}",
                json={"client_id": doc_with_payments["client_id"]}, timeout=30)

    def test_update_invalid_client_400(self, api, doc_with_payments):
        r = api.put(f"{API}/documents/{doc_with_payments['id']}",
                    json={"client_id": "not-a-real-client"}, timeout=30)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text[:200]}"

    def test_update_unknown_doc_404(self, api):
        r = api.put(f"{API}/documents/does-not-exist-xyz", json={"notes": "x"}, timeout=30)
        assert r.status_code == 404, f"expected 404 got {r.status_code} {r.text[:200]}"

    def test_update_requires_auth(self, api, doc_with_payments):
        r = requests.put(f"{API}/documents/{doc_with_payments['id']}", json={"notes": "hack"}, timeout=30)
        assert r.status_code == 401, f"expected 401 got {r.status_code}"

    def test_empty_body_is_noop(self, api, doc_with_payments):
        before = api.get(f"{API}/documents/{doc_with_payments['id']}", timeout=30).json()
        r = api.put(f"{API}/documents/{doc_with_payments['id']}", json={}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        after = r.json()
        assert after == before


# ---------- PDF ----------
class TestPdfWithPayments:
    def test_pdf_renders(self, api, doc_with_payments):
        r = api.get(f"{API}/documents/{doc_with_payments['id']}/pdf", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert "application/pdf" in r.headers.get("content-type", "").lower()
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000


# ---------- Convert ----------
class TestConvertWithPayments:
    def test_convert_copies_lines(self, api, tracker, doc_with_payments):
        r = api.post(f"{API}/documents/{doc_with_payments['id']}/convert", timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        v = r.json()
        tracker["documents"].append(v["id"])
        assert v["doc_type"] == "venda"
        assert v["converted_from"] == doc_with_payments["id"]
        src = api.get(f"{API}/documents/{doc_with_payments['id']}", timeout=30).json()
        assert len(v["lines"]) == len(src["lines"])
        assert v["lines"][0]["code"] == src["lines"][0]["code"]

        g = api.get(f"{API}/documents/{v['id']}", timeout=30)
        assert g.status_code == 200

        rpdf = api.get(f"{API}/documents/{v['id']}/pdf", timeout=60)
        assert rpdf.status_code == 200
        assert rpdf.content[:4] == b"%PDF"

    def test_converted_venda_has_payments_key(self, api, tracker, doc_with_payments):
        """BUG: convert_document builds new_doc without a 'payments' key, so the
        converted venda has no payments field at all (frontend edit-mode reads it)."""
        r = api.post(f"{API}/documents/{doc_with_payments['id']}/convert", timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        v = r.json()
        tracker["documents"].append(v["id"])
        g = api.get(f"{API}/documents/{v['id']}", timeout=30).json()
        assert "payments" in g, "converted venda missing 'payments' key"


# ---------- Regression ----------
class TestRegressionIt3:
    @pytest.mark.parametrize("path", ["/clients", "/products", "/documents", "/stats", "/company", "/"])
    def test_endpoints_200(self, api, path):
        r = api.get(f"{API}{path}", timeout=30)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
        data = r.json()
        if isinstance(data, list):
            for item in data[:10]:
                assert "_id" not in item, f"{path} leaks _id"
        else:
            assert "_id" not in data

    def test_bad_token_401(self):
        r = requests.get(f"{API}/clients", headers={"Authorization": "Bearer garbage.token.value"}, timeout=30)
        assert r.status_code == 401, f"expected 401 got {r.status_code}"
