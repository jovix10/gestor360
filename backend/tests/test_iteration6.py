"""Iteration 6 — POST /api/company/change-credentials + slugify hardening.

Covers: role guard (403), wrong current password, empty payload, short/ASCII-folded
code, duplicate code, code change round-trip on company-login, password change
round-trip, lookup-company / company-login empty-slug guards, and a regression
sweep over clients/products/documents/users/PDF/stats for owner+gerente+vendedor.

Teardown restores company code='gestor360', password='Empresa123',
name='Gestor360 Teste' and deletes TEST_ users created here.

Run: pytest /app/backend/tests/test_iteration6.py -v
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
STABLE_CODE = "gestor360"
STABLE_PW = "Empresa123"
STABLE_NAME = "Gestor360 Teste"
OTHER_COMPANY_CODE = "equipe-kirius"   # different company, used for duplicate-code test

VEND_USERNAME = f"v6vend{SUFFIX}"
GER_USERNAME = f"v6ger{SUFFIX}"
USER_PW = "Abcd1234"

STATE = {"current_company_pw": STABLE_PW, "created_users": []}


def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:password|senha)(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    if not email or not pw:
        pytest.skip("credentials not parseable in /app/memory/test_credentials.md")
    return email.group(1), pw.group(1)


OWNER_EMAIL, OWNER_PW = creds()


def session(token=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


def owner_session():
    s = session()
    r = s.post(f"{BASE}/auth/owner-login", json={"email": OWNER_EMAIL, "password": OWNER_PW})
    if r.status_code != 200:
        pytest.fail(f"owner-login failed {r.status_code}: {r.text[:300]}")
    STATE["owner_token"] = r.json()["token"]
    STATE["owner_user_id"] = r.json()["user"]["user_id"]
    return session(r.json()["token"])


@pytest.fixture(scope="module")
def owner():
    return owner_session()


def user_token(company_code, company_pw, username, password):
    """Full two-step login → bearer token."""
    s = session()
    c = s.post(f"{BASE}/auth/company-login", json={"code": company_code, "password": company_pw})
    assert c.status_code == 200, f"company-login failed: {c.status_code} {c.text[:200]}"
    u = s.post(f"{BASE}/auth/user-login", json={"username": username, "password": password})
    assert u.status_code == 200, f"user-login failed: {u.status_code} {u.text[:200]}"
    return u.json()["token"]


@pytest.fixture(scope="module", autouse=True)
def restore_company():
    """Teardown: force the stable company back to a known good state."""
    yield
    o = owner_session()
    r = o.post(f"{BASE}/auth/setup-company",
               json={"code": STABLE_CODE, "password": STABLE_PW, "name": STABLE_NAME})
    assert r.status_code == 200, f"RESTORE FAILED {r.status_code}: {r.text[:300]}"
    assert r.json()["code"] == STABLE_CODE
    for uid in STATE["created_users"]:
        o.delete(f"{BASE}/users/{uid}")
    # sanity: stable login works again
    lg = requests.post(f"{BASE}/auth/company-login", json={"code": STABLE_CODE, "password": STABLE_PW})
    assert lg.status_code == 200, f"post-restore company-login broken: {lg.status_code}"


class TestChangeCompanyCredentials:
    # ---------- basics ----------
    def test_00_health(self):
        r = requests.get(f"{BASE}/")
        assert r.status_code == 200 and r.json().get("ok") is True

    def test_01_baseline_state(self, owner):
        """Make sure we start from code=gestor360 / password=Empresa123."""
        r = owner.post(f"{BASE}/auth/setup-company",
                       json={"code": STABLE_CODE, "password": STABLE_PW, "name": STABLE_NAME})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["code"] == STABLE_CODE
        STATE["current_company_pw"] = STABLE_PW
        me = owner.get(f"{BASE}/auth/me")
        assert me.status_code == 200
        assert me.json()["company"]["code"] == STABLE_CODE

    def test_02_create_team_users(self, owner):
        for uname, role in ((VEND_USERNAME, "vendedor"), (GER_USERNAME, "gerente")):
            r = owner.post(f"{BASE}/users",
                           json={"name": f"TEST_{role}", "username": uname,
                                 "password": USER_PW, "role": role})
            assert r.status_code == 200, f"{role} create -> {r.status_code}: {r.text[:200]}"
            d = r.json()
            assert d["role"] == role and d["username"] == uname
            assert "password_hash" not in d and "_id" not in d
            STATE["created_users"].append(d["user_id"])
            STATE[f"{role}_id"] = d["user_id"]
        listed = owner.get(f"{BASE}/users").json()
        ids = [u["user_id"] for u in listed]
        for uid in STATE["created_users"]:
            assert uid in ids, "created user not persisted in GET /users"

    def test_03_unauthenticated_is_401(self):
        r = requests.post(f"{BASE}/company/change-credentials",
                          json={"current_password": STABLE_PW, "new_password": "Zzz1234"})
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text[:200]}"

    # ---------- (a) role guard ----------
    @pytest.mark.parametrize("role", ["vendedor", "gerente"])
    def test_04_non_owner_forbidden(self, role):
        uname = VEND_USERNAME if role == "vendedor" else GER_USERNAME
        tok = user_token(STABLE_CODE, STATE["current_company_pw"], uname, USER_PW)
        s = session(tok)
        r = s.post(f"{BASE}/company/change-credentials",
                   json={"current_password": STATE["current_company_pw"], "new_code": f"hack{SUFFIX}"})
        assert r.status_code == 403, f"{role} -> {r.status_code}: {r.text[:200]}"
        # nothing changed
        chk = requests.get(f"{BASE}/auth/lookup-company", params={"code": STABLE_CODE})
        assert chk.json()["found"] is True

    # ---------- (b) wrong current password ----------
    def test_05_wrong_current_password(self, owner):
        r = owner.post(f"{BASE}/company/change-credentials",
                       json={"current_password": f"wrong{SUFFIX}", "new_password": "Zzz1234"})
        assert r.status_code == 400, f"got {r.status_code}: {r.text[:200]}"
        assert "detail" in r.json()
        # old password must still work
        lg = requests.post(f"{BASE}/auth/company-login",
                           json={"code": STABLE_CODE, "password": STATE["current_company_pw"]})
        assert lg.status_code == 200

    # ---------- (c) both empty ----------
    @pytest.mark.parametrize("payload_extra", [
        {},
        {"new_code": "", "new_password": ""},
        {"new_code": None, "new_password": None},
    ])
    def test_06_empty_payload_400(self, owner, payload_extra):
        body = {"current_password": STATE["current_company_pw"], **payload_extra}
        r = owner.post(f"{BASE}/company/change-credentials", json=body)
        assert r.status_code == 400, f"{payload_extra} -> {r.status_code}: {r.text[:200]}"

    # ---------- (d) code too short / slugifies to <3 ----------
    @pytest.mark.parametrize("bad_code", ["ab", "!!!", "@@@", "---", "   ", "-a-"])
    def test_07_short_code_400(self, owner, bad_code):
        r = owner.post(f"{BASE}/company/change-credentials",
                       json={"current_password": STATE["current_company_pw"], "new_code": bad_code})
        assert r.status_code == 400, f"{bad_code!r} -> {r.status_code}: {r.text[:200]}"

    def test_08_short_new_password_400(self, owner):
        r = owner.post(f"{BASE}/company/change-credentials",
                       json={"current_password": STATE["current_company_pw"], "new_password": "1"})
        assert r.status_code == 400, f"got {r.status_code}: {r.text[:200]}"

    # ---------- (e) duplicate code ----------
    @pytest.mark.parametrize("dup", [OTHER_COMPANY_CODE, "Equipe Kirius", "EQUIPE  KIRIUS"])
    def test_09_duplicate_code_400(self, owner, dup):
        lk = requests.get(f"{BASE}/auth/lookup-company", params={"code": OTHER_COMPANY_CODE})
        if lk.json().get("found") is not True:
            pytest.skip(f"reference company {OTHER_COMPANY_CODE} not present")
        r = owner.post(f"{BASE}/company/change-credentials",
                       json={"current_password": STATE["current_company_pw"], "new_code": dup})
        assert r.status_code == 400, f"{dup!r} -> {r.status_code}: {r.text[:250]}"

    # ---------- (2) slugify ASCII-fold ----------
    def test_10_accent_code_ascii_folds(self, owner):
        r = owner.post(f"{BASE}/company/change-credentials",
                       json={"current_password": STATE["current_company_pw"], "new_code": "Néto Açaí"})
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("ok") is True
        assert d.get("code") == "neto-acai", f"expected 'neto-acai', got {d.get('code')!r}"
        STATE["code"] = "neto-acai"

    # ---------- (h) code change round-trip ----------
    def test_11_new_code_logs_in_old_code_401(self):
        pw = STATE["current_company_pw"]
        for variant in ("neto-acai", "Néto Açaí", "NETO ACAI", " neto acai "):
            s = session()
            lg = s.post(f"{BASE}/auth/company-login", json={"code": variant, "password": pw})
            assert lg.status_code == 200, f"{variant!r} -> {lg.status_code}: {lg.text[:200]}"
            assert lg.json()["company"]["code"] == "neto-acai"
            assert "company_session" in s.cookies.get_dict()
        old = requests.post(f"{BASE}/auth/company-login", json={"code": STABLE_CODE, "password": pw})
        assert old.status_code == 401, f"old code still works: {old.status_code}"
        lk = requests.get(f"{BASE}/auth/lookup-company", params={"code": STABLE_CODE})
        assert lk.status_code == 200 and lk.json()["found"] is False
        lk2 = requests.get(f"{BASE}/auth/lookup-company", params={"code": "Néto Açaí"})
        assert lk2.json()["found"] is True and lk2.json()["code"] == "neto-acai"

    def test_12_auth_me_reflects_new_code(self, owner):
        me = owner.get(f"{BASE}/auth/me")
        assert me.status_code == 200
        assert me.json()["company"]["code"] == "neto-acai"

    # ---------- (g) password change round-trip ----------
    def test_13_change_password_only(self, owner):
        new_pw = f"NewPw{SUFFIX}"
        r = owner.post(f"{BASE}/company/change-credentials",
                       json={"current_password": STATE["current_company_pw"], "new_password": new_pw})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["ok"] is True
        assert r.json()["code"] == "neto-acai", "code must be unchanged when only password sent"
        old = requests.post(f"{BASE}/auth/company-login",
                            json={"code": "neto-acai", "password": STATE["current_company_pw"]})
        assert old.status_code == 401, f"old password still accepted: {old.status_code}"
        new = requests.post(f"{BASE}/auth/company-login", json={"code": "neto-acai", "password": new_pw})
        assert new.status_code == 200, f"new password rejected: {new.status_code} {new.text[:200]}"
        STATE["current_company_pw"] = new_pw

    def test_14_change_code_and_password_together(self, owner):
        code_raw = f"TEST Empresa {SUFFIX}"
        pw = f"Both{SUFFIX}"
        r = owner.post(f"{BASE}/company/change-credentials",
                       json={"current_password": STATE["current_company_pw"],
                             "new_code": code_raw, "new_password": pw})
        assert r.status_code == 200, r.text[:300]
        expected = f"test-empresa-{SUFFIX}"
        assert r.json()["code"] == expected, f"got {r.json()['code']!r}"
        STATE["current_company_pw"] = pw
        s = session()
        lg = s.post(f"{BASE}/auth/company-login", json={"code": code_raw, "password": pw})
        assert lg.status_code == 200, f"{lg.status_code} {lg.text[:200]}"
        u = s.post(f"{BASE}/auth/user-login", json={"username": "admin", "password": OWNER_PW})
        assert u.status_code == 200, u.text[:250]
        assert u.json()["user"]["role"] == "owner"
        STATE["code"] = expected

    # ---------- (3)/(4) empty-slug guards ----------
    @pytest.mark.parametrize("bad", ["   ", "!!!", "@@@", "---", ""])
    def test_15_lookup_company_empty_slug(self, bad):
        r = requests.get(f"{BASE}/auth/lookup-company", params={"code": bad})
        assert r.status_code == 200, f"{bad!r} -> {r.status_code}: {r.text[:150]}"
        assert r.json().get("found") is False, f"{bad!r} leaked: {r.json()}"

    @pytest.mark.parametrize("bad", ["   ", "!!!", "@@@", "---", ""])
    def test_16_company_login_empty_slug(self, bad):
        r = requests.post(f"{BASE}/auth/company-login", json={"code": bad, "password": ""})
        assert r.status_code == 401, f"{bad!r} -> {r.status_code}: {r.text[:200]}"

    # ---------- (5) restore stable code + full two-step ----------
    def test_17_restore_stable_and_two_step(self, owner):
        r = owner.post(f"{BASE}/company/change-credentials",
                       json={"current_password": STATE["current_company_pw"],
                             "new_code": STABLE_CODE, "new_password": STABLE_PW})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["code"] == STABLE_CODE
        STATE["current_company_pw"] = STABLE_PW
        # name untouched by change-credentials
        comp = owner.get(f"{BASE}/company")
        assert comp.status_code == 200
        assert comp.json()["name"] == STABLE_NAME, f"name changed to {comp.json()['name']!r}"
        assert "_id" not in comp.json()
        s = session()
        c = s.post(f"{BASE}/auth/company-login", json={"code": STABLE_CODE, "password": STABLE_PW})
        assert c.status_code == 200
        u = s.post(f"{BASE}/auth/user-login", json={"username": "admin", "password": OWNER_PW})
        assert u.status_code == 200 and u.json()["user"]["role"] == "owner"

    # ---------- (6) regression sweep ----------
    def test_18_regression_owner_crud(self, owner):
        # clients
        c = owner.post(f"{BASE}/clients", json={"name": f"TEST_cli6 {SUFFIX}", "document": "12345678901"})
        assert c.status_code == 200, c.text[:250]
        cid = c.json()["id"]
        STATE["client_id"] = cid
        assert "_id" not in c.json()
        upd = owner.put(f"{BASE}/clients/{cid}", json={"name": "TEST_cli6 upd", "document": "12345678901"})
        assert upd.status_code == 200 and upd.json()["name"] == "TEST_cli6 upd"
        got = [x for x in owner.get(f"{BASE}/clients").json() if x["id"] == cid]
        assert got and got[0]["name"] == "TEST_cli6 upd", "client update not persisted"

        # products
        p = owner.post(f"{BASE}/products", json={
            "code": f"TESTP{SUFFIX}", "description": f"TEST_prod6 {SUFFIX}",
            "price": 25.5, "stock": 10, "unit": "UN"})
        assert p.status_code == 200, p.text[:250]
        pid = p.json()["id"]
        STATE["product_id"] = pid
        assert p.json()["price"] == 25.5
        assert p.json()["description"] == f"TEST_prod6 {SUFFIX}"
        pl = owner.get(f"{BASE}/products")
        assert pl.status_code == 200 and any(x["id"] == pid for x in pl.json())

        # documents
        d = owner.post(f"{BASE}/documents", json={
            "doc_type": "orcamento", "client_id": cid,
            "lines": [{"product_id": pid, "code": f"TESTP{SUFFIX}", "description": "TEST_prod6",
                       "quantity": 2, "unit_price": 25.5, "discount_pct": 0}],
            "payments": [], "notes": "TEST iteration6"})
        assert d.status_code == 200, d.text[:300]
        did = d.json()["id"]
        STATE["doc_id"] = did
        assert "_id" not in d.json()
        one = owner.get(f"{BASE}/documents/{did}")
        assert one.status_code == 200 and one.json()["id"] == did
        assert owner.get(f"{BASE}/documents").status_code == 200

        # PDF
        pdf = owner.get(f"{BASE}/documents/{did}/pdf")
        assert pdf.status_code == 200, pdf.text[:200]
        assert pdf.content[:4] == b"%PDF", f"not a PDF: {pdf.content[:20]!r}"

        # stats
        st = owner.get(f"{BASE}/stats")
        assert st.status_code == 200 and isinstance(st.json(), dict)

    def test_19_regression_gerente_vendedor(self):
        gtok = user_token(STABLE_CODE, STABLE_PW, GER_USERNAME, USER_PW)
        gs = session(gtok)
        assert gs.get(f"{BASE}/clients").status_code == 200
        assert gs.get(f"{BASE}/products").status_code == 200
        assert gs.get(f"{BASE}/documents").status_code == 200
        assert gs.get(f"{BASE}/stats").status_code == 200
        assert gs.get(f"{BASE}/company").status_code == 200
        assert gs.get(f"{BASE}/users").status_code == 403
        assert gs.get(f"{BASE}/documents/{STATE['doc_id']}").status_code == 200, "gerente must see all docs"

        vtok = user_token(STABLE_CODE, STABLE_PW, VEND_USERNAME, USER_PW)
        vs = session(vtok)
        assert vs.get(f"{BASE}/clients").status_code == 200
        assert vs.get(f"{BASE}/products").status_code == 200
        assert vs.get(f"{BASE}/stats").status_code == 200
        docs = vs.get(f"{BASE}/documents")
        assert docs.status_code == 200
        assert STATE["doc_id"] not in [x["id"] for x in docs.json()], "vendedor sees owner doc"
        assert vs.get(f"{BASE}/users").status_code == 403
        assert vs.post(f"{BASE}/company/change-credentials",
                       json={"current_password": STABLE_PW, "new_password": "Hax1234"}).status_code == 403

    def test_20_cleanup_test_data(self, owner):
        for path in (f"/documents/{STATE.get('doc_id')}", f"/products/{STATE.get('product_id')}",
                     f"/clients/{STATE.get('client_id')}"):
            if "None" in path:
                continue
            r = owner.delete(f"{BASE}{path}")
            assert r.status_code in (200, 204, 404), f"{path} -> {r.status_code}"
        if STATE.get("doc_id"):
            assert owner.get(f"{BASE}/documents/{STATE['doc_id']}").status_code == 404
        for uid in list(STATE["created_users"]):
            r = owner.delete(f"{BASE}/users/{uid}")
            assert r.status_code in (200, 204, 404), f"user delete -> {r.status_code}"
        STATE["created_users"] = []
