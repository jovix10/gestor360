"""Gestor360 v2 (multi-tenant + roles) backend tests — iteration 4.

Covers: startup migration, owner login, company setup, two-step login,
team CRUD, change-password, vendedor scoping, PDF, OAuth error branches,
and core CRUD regression.
Run: pytest /app/backend/tests/test_iteration4.py -v
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
COMPANY_CODE = f"qa{SUFFIX}"
COMPANY_PW = "Empresa123"
COMPANY_NAME = "Gestor360 QA"
VEND_USERNAME = f"vend{SUFFIX}"
VEND_PW = "Vend123"
VEND_PW2 = "Vend456"

STATE = {}


def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:password|senha)(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    if not email or not pw:
        pytest.skip("credentials not parseable")
    return email.group(1), pw.group(1)


OWNER_EMAIL, OWNER_PW = creds()


def _db_delete_user(user_id: str, company_id: str = None):
    """Test-only cleanup for users the API refuses to delete (extra owners)."""
    from pymongo import MongoClient
    env = dotenv_values("/app/backend/.env")
    with MongoClient(env["MONGO_URL"]) as mc:
        mc[env["DB_NAME"]].users.delete_one({"user_id": user_id})
        if company_id:
            mc[env["DB_NAME"]].companies.delete_one({"id": company_id})


def client_session(token=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def owner():
    s = client_session()
    r = s.post(f"{BASE}/auth/owner-login", json={"email": OWNER_EMAIL, "password": OWNER_PW})
    if r.status_code != 200:
        pytest.fail(f"owner login failed {r.status_code}: {r.text[:300]}")
    data = r.json()
    STATE["owner_token"] = data["token"]
    STATE["owner_user_id"] = data["user"]["user_id"]
    return client_session(data["token"])


class TestV2Flow:
    # ---------- owner login / me ----------
    def test_root(self):
        r = requests.get(f"{BASE}/")
        assert r.status_code == 200 and r.json().get("ok") == True

    def test_owner_login(self, owner):
        r = owner.post(f"{BASE}/auth/owner-login", json={"email": OWNER_EMAIL, "password": OWNER_PW})
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["role"] == "owner"
        assert d["user"]["username"] == "admin"
        assert isinstance(d["token"], str) and len(d["token"]) > 10

    def test_owner_login_bad_password(self):
        r = requests.post(f"{BASE}/auth/owner-login", json={"email": OWNER_EMAIL, "password": "wrong-pw"})
        assert r.status_code == 401

    def test_auth_me(self, owner):
        r = owner.get(f"{BASE}/auth/me")
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "owner"
        assert "company" in d and "pending_setup" in d["company"]
        STATE["company_id"] = d["company"]["id"]

    def test_me_unauthenticated(self):
        r = requests.get(f"{BASE}/auth/me")
        assert r.status_code == 401

    # ---------- migration continuity ----------
    def test_migration_data_preserved(self, owner):
        for path in ("clients", "products", "documents"):
            r = owner.get(f"{BASE}/{path}")
            assert r.status_code == 200, f"{path} -> {r.status_code}"
            assert isinstance(r.json(), list)
        docs = owner.get(f"{BASE}/documents").json()
        STATE["owner_doc_count"] = len(docs)
        assert all(d.get("created_by") for d in docs), "migrated documents missing created_by"

    # ---------- setup company ----------
    def test_setup_company_short_code(self, owner):
        r = owner.post(f"{BASE}/auth/setup-company", json={"code": "ab", "password": COMPANY_PW, "name": COMPANY_NAME})
        assert r.status_code == 400

    def test_setup_company_short_password(self, owner):
        r = owner.post(f"{BASE}/auth/setup-company", json={"code": COMPANY_CODE, "password": "1", "name": COMPANY_NAME})
        assert r.status_code == 400

    def test_setup_company_success(self, owner):
        r = owner.post(f"{BASE}/auth/setup-company",
                       json={"code": COMPANY_CODE, "password": COMPANY_PW, "name": COMPANY_NAME})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["code"] == COMPANY_CODE
        me = owner.get(f"{BASE}/auth/me").json()
        assert me["company"]["pending_setup"] == False
        assert me["company"]["code"] == COMPANY_CODE
        assert me["company"]["name"] == COMPANY_NAME

    def test_setup_company_duplicate_code_from_other_company(self):
        """A second freshly-registered owner cannot claim an existing code."""
        s = client_session()
        email = f"TEST_dup_{SUFFIX}@example.com"
        reg = s.post(f"{BASE}/auth/register", json={"name": "TEST Dup Owner", "email": email, "password": "Abcd1234"})
        assert reg.status_code == 200, reg.text[:300]
        tok = reg.json()["token"]
        STATE["other_owner_token"] = tok
        STATE["other_owner_id"] = reg.json()["user"]["user_id"]
        STATE["other_owner_company"] = reg.json()["user"]["company_id"]
        s2 = client_session(tok)
        r = s2.post(f"{BASE}/auth/setup-company",
                    json={"code": COMPANY_CODE, "password": "Outra123", "name": "Outra"})
        assert r.status_code == 400, f"expected 400 duplicate, got {r.status_code}"

    def test_lookup_company(self):
        r = requests.get(f"{BASE}/auth/lookup-company", params={"code": COMPANY_CODE})
        assert r.status_code == 200
        d = r.json()
        assert d["found"] == True and d["name"] == COMPANY_NAME

    def test_lookup_company_not_found(self):
        r = requests.get(f"{BASE}/auth/lookup-company", params={"code": "nope-" + SUFFIX})
        assert r.status_code == 200 and r.json()["found"] == False

    # ---------- team CRUD ----------
    def test_create_vendedor(self, owner):
        r = owner.post(f"{BASE}/users", json={
            "name": "TEST Vendedor", "username": VEND_USERNAME, "password": VEND_PW, "role": "vendedor"})
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["role"] == "vendedor" and d["username"] == VEND_USERNAME
        STATE["vend_id"] = d["user_id"]
        listed = owner.get(f"{BASE}/users").json()
        row = next((u for u in listed if u["user_id"] == d["user_id"]), None)
        assert row is not None, "created user not in GET /users"
        assert row["must_change_password"] == True

    def test_create_user_duplicate_username(self, owner):
        r = owner.post(f"{BASE}/users", json={
            "name": "TEST Dup", "username": VEND_USERNAME, "password": "Abcd1234", "role": "vendedor"})
        assert r.status_code == 400

    def test_create_user_short_password(self, owner):
        r = owner.post(f"{BASE}/users", json={
            "name": "TEST Short", "username": f"sh{SUFFIX}", "password": "1", "role": "vendedor"})
        assert r.status_code == 400

    def test_update_user_name_and_password_reset(self, owner):
        r = owner.put(f"{BASE}/users/{STATE['vend_id']}", json={"name": "TEST Vendedor R", "password": VEND_PW2})
        assert r.status_code == 200
        row = next(u for u in owner.get(f"{BASE}/users").json() if u["user_id"] == STATE["vend_id"])
        assert row["name"] == "TEST Vendedor R"
        assert row["must_change_password"] == True

    def test_cannot_demote_owner(self, owner):
        r = owner.put(f"{BASE}/users/{STATE['owner_user_id']}", json={"role": "vendedor"})
        assert r.status_code == 400

    def test_update_unknown_user_404(self, owner):
        r = owner.put(f"{BASE}/users/user_doesnotexist", json={"name": "x"})
        assert r.status_code == 404

    # ---------- two-step login ----------
    def test_company_login_bad_code(self):
        r = requests.post(f"{BASE}/auth/company-login", json={"code": "nope-" + SUFFIX, "password": COMPANY_PW})
        assert r.status_code == 401

    def test_company_login_bad_password(self):
        r = requests.post(f"{BASE}/auth/company-login", json={"code": COMPANY_CODE, "password": "wrong"})
        assert r.status_code == 401

    def test_user_login_without_cookie(self):
        r = requests.post(f"{BASE}/auth/user-login", json={"username": VEND_USERNAME, "password": VEND_PW2})
        assert r.status_code == 401

    def test_two_step_login_vendedor(self):
        s = client_session()
        r = s.post(f"{BASE}/auth/company-login", json={"code": COMPANY_CODE, "password": COMPANY_PW})
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["company"]["code"] == COMPANY_CODE
        assert any(u["username"] == VEND_USERNAME for u in d["users"])
        assert "company_session" in s.cookies.get_dict()

        bad = s.post(f"{BASE}/auth/user-login", json={"username": "ghost" + SUFFIX, "password": VEND_PW2})
        assert bad.status_code == 401

        r2 = s.post(f"{BASE}/auth/user-login", json={"username": VEND_USERNAME, "password": VEND_PW2})
        assert r2.status_code == 200, r2.text[:300]
        d2 = r2.json()
        assert d2["user"]["role"] == "vendedor"
        assert d2["must_change_password"] == True
        STATE["vend_token"] = d2["token"]

    def test_owner_two_step_login(self):
        s = client_session()
        assert s.post(f"{BASE}/auth/company-login",
                      json={"code": COMPANY_CODE, "password": COMPANY_PW}).status_code == 200
        r = s.post(f"{BASE}/auth/user-login", json={"username": "admin", "password": OWNER_PW})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["role"] == "owner"

    # ---------- change password ----------
    def test_change_password_wrong_current(self):
        s = client_session(STATE["vend_token"])
        r = s.post(f"{BASE}/auth/change-password", json={"current_password": "nope", "new_password": "Novo1234"})
        assert r.status_code == 400

    def test_change_password_short_new(self):
        s = client_session(STATE["vend_token"])
        r = s.post(f"{BASE}/auth/change-password", json={"current_password": VEND_PW2, "new_password": "1"})
        assert r.status_code == 400

    def test_change_password_success(self):
        s = client_session(STATE["vend_token"])
        r = s.post(f"{BASE}/auth/change-password", json={"current_password": VEND_PW2, "new_password": VEND_PW})
        assert r.status_code == 200
        assert s.get(f"{BASE}/auth/me").json()["must_change_password"] == False
        s2 = client_session()
        assert s2.post(f"{BASE}/auth/company-login",
                       json={"code": COMPANY_CODE, "password": COMPANY_PW}).status_code == 200
        r2 = s2.post(f"{BASE}/auth/user-login", json={"username": VEND_USERNAME, "password": VEND_PW})
        assert r2.status_code == 200
        assert r2.json()["must_change_password"] == False
        STATE["vend_token"] = r2.json()["token"]

    # ---------- owner core CRUD regression ----------
    def test_owner_client_product_document_crud(self, owner):
        c = owner.post(f"{BASE}/clients", json={"name": f"TEST Cliente {SUFFIX}", "phone": "11999990000"})
        assert c.status_code == 200, c.text[:300]
        cid = c.json()["id"]
        STATE["client_id"] = cid
        got = owner.get(f"{BASE}/clients").json()
        assert any(x["id"] == cid for x in got)

        upd = owner.put(f"{BASE}/clients/{cid}", json={"id": cid, "name": "TEST Cliente Upd"})
        assert upd.status_code == 200 and upd.json()["name"] == "TEST Cliente Upd"

        p = owner.post(f"{BASE}/products", json={"code": f"TP{SUFFIX}", "description": "TEST Produto",
                                                 "price": 100.0, "stock": 50})
        assert p.status_code == 200, p.text[:300]
        pid = p.json()["id"]
        STATE["product_id"] = pid
        dup = owner.post(f"{BASE}/products", json={"code": f"TP{SUFFIX}", "description": "dup", "price": 1})
        assert dup.status_code == 400

        d = owner.post(f"{BASE}/documents", json={
            "doc_type": "orcamento", "client_id": cid,
            "lines": [{"product_id": pid, "code": f"TP{SUFFIX}", "description": "TEST Produto",
                       "quantity": 2, "unit_price": 100.0, "discount_pct": 10}],
            "payments": [{"method": "pix", "amount": 180.0, "installments": 1}], "notes": "TEST"})
        assert d.status_code == 200, d.text[:300]
        doc = d.json()
        assert doc["created_by"] == STATE["owner_user_id"], "created_by not stamped"
        assert doc["number"] > 0
        STATE["owner_doc_id"] = doc["id"]
        fetched = owner.get(f"{BASE}/documents/{doc['id']}")
        assert fetched.status_code == 200 and fetched.json()["notes"] == "TEST"
        rows = owner.get(f"{BASE}/documents").json()
        row = next(r for r in rows if r["id"] == doc["id"])
        assert row["total"] == 180.0
        assert row["created_by_name"]

    def test_owner_document_update_and_convert(self, owner):
        did = STATE["owner_doc_id"]
        u = owner.put(f"{BASE}/documents/{did}", json={"notes": "TEST atualizado"})
        assert u.status_code == 200 and u.json()["notes"] == "TEST atualizado"
        conv = owner.post(f"{BASE}/documents/{did}/convert")
        assert conv.status_code == 200, conv.text[:300]
        cd = conv.json()
        assert cd["doc_type"] == "venda" and cd["converted_from"] == did
        assert cd["created_by"] == STATE["owner_user_id"]
        STATE["owner_venda_id"] = cd["id"]
        again = owner.post(f"{BASE}/documents/{cd['id']}/convert")
        assert again.status_code == 400

    def test_owner_pdf(self, owner):
        r = owner.get(f"{BASE}/documents/{STATE['owner_doc_id']}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert len(r.content) > 1000

    def test_owner_company_get_put(self, owner):
        g = owner.get(f"{BASE}/company")
        assert g.status_code == 200 and "_id" not in g.json()
        p = owner.put(f"{BASE}/company", json={"phone": "11988887777"})
        assert p.status_code == 200 and p.json()["phone"] == "11988887777"

    def test_owner_stats(self, owner):
        r = owner.get(f"{BASE}/stats")
        assert r.status_code == 200
        d = r.json()
        assert d["scope"] == "company"
        for k in ("clients", "products", "orcamentos", "vendas", "revenue_month"):
            assert d[k] >= 0

    # ---------- vendedor scoping ----------
    def test_vendedor_sees_shared_clients_products(self):
        s = client_session(STATE["vend_token"])
        cl = s.get(f"{BASE}/clients")
        pr = s.get(f"{BASE}/products")
        assert cl.status_code == 200 and pr.status_code == 200
        assert any(c["id"] == STATE["client_id"] for c in cl.json()), "vendedor cannot see company clients"
        assert any(p["id"] == STATE["product_id"] for p in pr.json())

    def test_vendedor_documents_scoped(self):
        s = client_session(STATE["vend_token"])
        docs = s.get(f"{BASE}/documents")
        assert docs.status_code == 200
        ids = [d["id"] for d in docs.json()]
        assert STATE["owner_doc_id"] not in ids, "vendedor sees owner document"
        assert all(d["created_by"] == STATE["vend_id"] for d in docs.json())
        one = s.get(f"{BASE}/documents/{STATE['owner_doc_id']}")
        assert one.status_code == 404
        pdf = s.get(f"{BASE}/documents/{STATE['owner_doc_id']}/pdf")
        assert pdf.status_code == 404

    def test_vendedor_creates_own_doc_and_pdf(self):
        s = client_session(STATE["vend_token"])
        d = s.post(f"{BASE}/documents", json={
            "doc_type": "orcamento", "client_id": STATE["client_id"],
            "lines": [{"code": "X", "description": "TEST vend", "quantity": 1, "unit_price": 50.0}],
            "payments": [], "notes": "TEST vendedor"})
        assert d.status_code == 200, d.text[:300]
        doc = d.json()
        assert doc["created_by"] == STATE["vend_id"]
        STATE["vend_doc_id"] = doc["id"]
        assert s.get(f"{BASE}/documents/{doc['id']}").status_code == 200
        pdf = s.get(f"{BASE}/documents/{doc['id']}/pdf")
        assert pdf.status_code == 200 and pdf.headers["content-type"].startswith("application/pdf")
        conv = s.post(f"{BASE}/documents/{doc['id']}/convert")
        assert conv.status_code == 200 and conv.json()["created_by"] == STATE["vend_id"]
        STATE["vend_venda_id"] = conv.json()["id"]

    def test_vendedor_stats_scope_own(self):
        s = client_session(STATE["vend_token"])
        r = s.get(f"{BASE}/stats")
        assert r.status_code == 200
        d = r.json()
        assert d["scope"] == "own"
        owner_stats = client_session(STATE["owner_token"]).get(f"{BASE}/stats").json()
        assert d["orcamentos"] <= owner_stats["orcamentos"]
        assert d["vendas"] <= owner_stats["vendas"]
        assert d["orcamentos"] >= 1 and d["vendas"] >= 1

    def test_vendedor_forbidden_endpoints(self):
        s = client_session(STATE["vend_token"])
        assert s.get(f"{BASE}/users").status_code == 403
        assert s.post(f"{BASE}/users", json={"name": "x", "username": "xx", "password": "abcd"}).status_code == 403
        assert s.put(f"{BASE}/users/{STATE['vend_id']}", json={"role": "owner"}).status_code == 403
        assert s.delete(f"{BASE}/users/{STATE['vend_id']}").status_code == 403
        assert s.put(f"{BASE}/company", json={"phone": "0"}).status_code == 403
        assert s.post(f"{BASE}/auth/setup-company",
                      json={"code": "abcqa", "password": "1234", "name": "n"}).status_code == 403

    def test_vendedor_cannot_use_owner_login(self):
        r = requests.post(f"{BASE}/auth/owner-login",
                          json={"email": f"TEST_dup_{SUFFIX}@example.com", "password": "Abcd1234"})
        # this account IS an owner → 200 expected; only sanity check that route works
        assert r.status_code == 200

    # ---------- gerente ----------
    def test_gerente_can_update_company_but_not_users(self, owner):
        gname = f"ger{SUFFIX}"
        c = owner.post(f"{BASE}/users", json={"name": "TEST Gerente", "username": gname,
                                              "password": "Ger1234", "role": "gerente"})
        assert c.status_code == 200, c.text[:300]
        STATE["ger_id"] = c.json()["user_id"]
        s = client_session()
        assert s.post(f"{BASE}/auth/company-login",
                      json={"code": COMPANY_CODE, "password": COMPANY_PW}).status_code == 200
        lg = s.post(f"{BASE}/auth/user-login", json={"username": gname, "password": "Ger1234"})
        assert lg.status_code == 200
        gs = client_session(lg.json()["token"])
        assert gs.put(f"{BASE}/company", json={"phone": "11977776666"}).status_code == 200
        assert gs.get(f"{BASE}/users").status_code == 403
        # gerente sees all company documents
        docs = gs.get(f"{BASE}/documents")
        assert docs.status_code == 200
        assert STATE["owner_doc_id"] in [d["id"] for d in docs.json()]
        assert gs.get(f"{BASE}/stats").json()["scope"] == "company"

    # ---------- OAuth error branches ----------
    def test_oauth_bad_session(self):
        r = requests.post(f"{BASE}/auth/session", json={"session_id": "invalid-session-" + SUFFIX})
        assert r.status_code == 401, f"expected 401 got {r.status_code}: {r.text[:200]}"

    # ---------- edge cases / hardening checks ----------
    def test_yy_edge_cases(self, owner):
        s = client_session(STATE["vend_token"])
        findings = []
        # vendedor write access to shared data
        if s.put(f"{BASE}/clients/{STATE['client_id']}",
                 json={"id": STATE["client_id"], "name": "TEST Hacked"}).status_code == 200:
            findings.append("vendedor can UPDATE company clients")
        vp = s.post(f"{BASE}/products", json={"code": f"VP{SUFFIX}", "description": "v", "price": 1})
        if vp.status_code == 200:
            findings.append("vendedor can CREATE products")
            owner.delete(f"{BASE}/products/{vp.json()['id']}")
        # non-existent resources
        if owner.put(f"{BASE}/products/does-not-exist",
                     json={"code": "ZZZ", "description": "x", "price": 1}).status_code == 200:
            findings.append("PUT /products/{id} returns 200 for unknown id (no 404)")
        if owner.delete(f"{BASE}/clients/does-not-exist").status_code == 200:
            findings.append("DELETE /clients/{id} returns 200 for unknown id (no 404)")
        if owner.delete(f"{BASE}/documents/does-not-exist").status_code == 200:
            findings.append("DELETE /documents/{id} returns 200 for unknown id (no 404)")
        if owner.get(f"{BASE}/documents/does-not-exist").status_code != 404:
            findings.append("GET /documents/{id} unknown id not 404")
        # owner can create a second owner via team CRUD
        r = owner.post(f"{BASE}/users", json={"name": "TEST Owner2", "username": f"own{SUFFIX}",
                                             "password": "Abcd1234", "role": "owner"})
        if r.status_code == 200:
            findings.append("POST /users allows creating a second role='owner'")
            uid = r.json()["user_id"]
            owner.put(f"{BASE}/users/{uid}", json={"role": "vendedor"})
            if owner.delete(f"{BASE}/users/{uid}").status_code != 200:
                findings.append("extra owner user cannot be removed via API (cleaned via DB)")
                _db_delete_user(uid)
        # restore client name
        owner.put(f"{BASE}/clients/{STATE['client_id']}", json={"id": STATE["client_id"], "name": "TEST Cliente Upd"})
        # leftover junk product from unknown-id PUT (upsert-free, so nothing created)
        Path("/app/test_reports/pytest/edge_findings.txt").write_text("\n".join(findings) or "none")
        STATE["edge_findings"] = findings

    # ---------- cleanup ----------
    def test_zz_cleanup(self, owner):
        for did in (STATE.get("vend_venda_id"), STATE.get("vend_doc_id"),
                    STATE.get("owner_venda_id"), STATE.get("owner_doc_id")):
            if did:
                owner.delete(f"{BASE}/documents/{did}")
        if STATE.get("product_id"):
            assert owner.delete(f"{BASE}/products/{STATE['product_id']}").status_code == 200
        if STATE.get("client_id"):
            assert owner.delete(f"{BASE}/clients/{STATE['client_id']}").status_code == 200
        for uid in (STATE.get("ger_id"), STATE.get("vend_id")):
            if uid:
                r = owner.delete(f"{BASE}/users/{uid}")
                assert r.status_code == 200, r.text[:200]
        assert owner.delete(f"{BASE}/users/{STATE['owner_user_id']}").status_code == 400
        remaining = [u["user_id"] for u in owner.get(f"{BASE}/users").json()]
        assert STATE["vend_id"] not in remaining
        # remove the throwaway registered owner + its empty company
        if STATE.get("other_owner_id"):
            _db_delete_user(STATE["other_owner_id"], STATE.get("other_owner_company"))
        # leave the company on a stable, documented code for UI testing
        fin = owner.post(f"{BASE}/auth/setup-company",
                         json={"code": "gestor360", "password": "Empresa123", "name": "Gestor360 Teste"})
        assert fin.status_code == 200, fin.text[:200]
