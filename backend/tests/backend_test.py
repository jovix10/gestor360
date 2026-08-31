"""Gestor360 backend regression tests (iteration 2).

Scope: auth, clients, products (unit values), documents, convert, PDF, stats.
"""
import os
import re
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

UNITS = ["UN", "PC", "PAR", "KG", "G", "LT", "ML", "MT", "CM", "M2", "M3", "PCT", "CX", "DZ", "RL", "SC"]


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def test_credentials():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("Missing /app/memory/test_credentials.md")
    c = p.read_text(encoding="utf-8")
    em = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not em or not pw:
        pytest.skip("No credentials found in test_credentials.md")
    return {"email": em.group(1), "password": pw.group(1)}


@pytest.fixture(scope="session")
def client(test_credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=test_credentials, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("token") or r.json().get("access_token")
    if not token:
        pytest.fail(f"No token in login response: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def created(client):
    tracker = {"clients": [], "products": [], "documents": []}
    yield tracker
    for pid in tracker["products"]:
        client.delete(f"{API}/products/{pid}", timeout=30)
    for cid in tracker["clients"]:
        client.delete(f"{API}/clients/{cid}", timeout=30)


# ---------- auth ----------
class TestAuth:
    def test_login_returns_token(self, client):
        r = client.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "email" in data
        assert "_id" not in data

    def test_unauthenticated_401(self):
        r = requests.get(f"{API}/clients", timeout=30)
        assert r.status_code == 401, f"expected 401 got {r.status_code}"


# ---------- products / units ----------
class TestProductUnits:
    @pytest.mark.parametrize("unit", ["KG", "CX", "PCT", "PAR"])
    def test_create_product_with_unit_persists(self, client, created, unit):
        payload = {
            "code": f"TEST_U_{unit}",
            "description": f"TEST_ produto {unit}",
            "price": 12.5,
            "stock": 20,
            "unit": unit,
        }
        r = client.post(f"{API}/products", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        prod = r.json()
        assert "_id" not in prod
        assert prod["unit"] == unit
        assert prod["code"] == payload["code"]
        created["products"].append(prod["id"])

        lst = client.get(f"{API}/products", timeout=30)
        assert lst.status_code == 200
        found = [p for p in lst.json() if p["id"] == prod["id"]]
        assert found, "product not persisted"
        assert found[0]["unit"] == unit
        assert found[0]["price"] == 12.5

    def test_all_units_accepted(self, client, created):
        for unit in UNITS:
            payload = {"code": f"TEST_ALLU_{unit}", "description": f"TEST_ {unit}", "price": 1, "stock": 1, "unit": unit}
            r = client.post(f"{API}/products", json=payload, timeout=30)
            assert r.status_code in (200, 201), f"{unit} -> {r.status_code} {r.text[:200]}"
            created["products"].append(r.json()["id"])
            assert r.json()["unit"] == unit

    def test_duplicate_code_rejected(self, client, created):
        payload = {"code": "TEST_DUP_1", "description": "TEST_ dup", "price": 5, "stock": 1, "unit": "UN"}
        r1 = client.post(f"{API}/products", json=payload, timeout=30)
        assert r1.status_code in (200, 201), r1.text[:300]
        created["products"].append(r1.json()["id"])
        r2 = client.post(f"{API}/products", json=payload, timeout=30)
        assert r2.status_code == 400, f"expected 400 got {r2.status_code}"


# ---------- end to end PDF flow ----------
class TestEndToEndPdf:
    def test_full_flow_client_product_orcamento_pdf(self, client, created):
        # client
        rc = client.post(f"{API}/clients", json={
            "name": "TEST_ Cliente PDF", "document": "12345678900",
            "email": "test_pdf@example.test", "phone": "11999990000",
        }, timeout=30)
        assert rc.status_code in (200, 201), rc.text[:300]
        cli = rc.json()
        assert cli["name"] == "TEST_ Cliente PDF"
        assert "_id" not in cli
        created["clients"].append(cli["id"])

        # product with new unit CX
        rp = client.post(f"{API}/products", json={
            "code": "TEST_PDF_CX", "description": "TEST_ Caixa de parafusos",
            "price": 99.9, "stock": 50, "unit": "CX",
        }, timeout=30)
        assert rp.status_code in (200, 201), rp.text[:300]
        prod = rp.json()
        created["products"].append(prod["id"])

        # orcamento
        rd = client.post(f"{API}/documents", json={
            "doc_type": "orcamento",
            "client_id": cli["id"],
            "lines": [{
                "product_id": prod["id"], "code": prod["code"], "description": prod["description"],
                "quantity": 2, "unit_price": 99.9, "discount_pct": 10,
            }],
            "notes": "TEST_ orcamento pdf",
        }, timeout=30)
        assert rd.status_code in (200, 201), rd.text[:300]
        doc = rd.json()
        assert "_id" not in doc
        assert doc["number"] > 0
        assert doc["valid_until"] is not None
        assert len(doc["lines"]) == 1
        assert doc["lines"][0]["unit_price"] == 99.9
        created["documents"].append(doc["id"])

        # PDF
        rpdf = client.get(f"{API}/documents/{doc['id']}/pdf", timeout=60)
        assert rpdf.status_code == 200, rpdf.text[:300]
        assert "application/pdf" in rpdf.headers.get("content-type", "").lower(), rpdf.headers
        assert len(rpdf.content) > 800, f"pdf too small: {len(rpdf.content)}"
        assert rpdf.content[:4] == b"%PDF", rpdf.content[:20]

        # convert to venda then PDF of the venda
        rconv = client.post(f"{API}/documents/{doc['id']}/convert", timeout=30)
        assert rconv.status_code in (200, 201), rconv.text[:300]
        venda = rconv.json()
        assert venda["doc_type"] == "venda"
        assert venda["converted_from"] == doc["id"]
        created["documents"].append(venda["id"])

        rpdf2 = client.get(f"{API}/documents/{venda['id']}/pdf", timeout=60)
        assert rpdf2.status_code == 200, rpdf2.text[:300]
        assert "application/pdf" in rpdf2.headers.get("content-type", "").lower()
        assert rpdf2.content[:4] == b"%PDF"

    def test_pdf_unknown_doc_404(self, client):
        r = client.get(f"{API}/documents/does-not-exist-123/pdf", timeout=30)
        assert r.status_code == 404, f"expected 404 got {r.status_code}"

    def test_pdf_requires_auth(self, client, created):
        assert created["documents"], "no document created by previous test"
        r = requests.get(f"{API}/documents/{created['documents'][0]}/pdf", timeout=30)
        assert r.status_code == 401, f"expected 401 got {r.status_code}"


# ---------- regression on other endpoints ----------
class TestRegression:
    @pytest.mark.parametrize("path", ["/clients", "/products", "/documents", "/stats", "/company"])
    def test_get_endpoints_200(self, client, path):
        r = client.get(f"{API}{path}", timeout=30)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
        data = r.json()
        if isinstance(data, list):
            for item in data[:5]:
                assert "_id" not in item, f"{path} leaks mongo _id"
        else:
            assert "_id" not in data, f"{path} leaks mongo _id"

    def test_stats_shape(self, client):
        r = client.get(f"{API}/stats", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ["clients", "products", "orcamentos", "vendas"]:
            assert k in d, f"missing {k} in stats: {d}"

    def test_client_update_persists(self, client, created):
        rc = client.post(f"{API}/clients", json={"name": "TEST_ Update Cli"}, timeout=30)
        assert rc.status_code in (200, 201), rc.text[:300]
        cid = rc.json()["id"]
        created["clients"].append(cid)
        ru = client.put(f"{API}/clients/{cid}", json={
            "id": cid, "name": "TEST_ Updated Name", "document": "", "email": "", "phone": "", "address": "", "notes": ""
        }, timeout=30)
        assert ru.status_code == 200, ru.text[:300]
        lst = client.get(f"{API}/clients", timeout=30).json()
        got = [c for c in lst if c["id"] == cid]
        assert got and got[0]["name"] == "TEST_ Updated Name"

    def test_product_search_by_description_data_available(self, client, created):
        """Frontend QuoteBuilder falls back to description search; verify list payload
        exposes description so client-side matching is possible."""
        r = client.get(f"{API}/products", timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert items, "no products returned"
        assert all("description" in p and "code" in p for p in items)
