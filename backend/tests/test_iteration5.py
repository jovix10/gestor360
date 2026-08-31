"""Iteration 5 — company-code normalization (slugify parity) bugfix tests.

Covers: company-login slugify parity, lookup-company slugify parity,
setup+login round-trip with spaces/accents, 401 semantics, two-step flow regression.
Run: pytest /app/backend/tests/test_iteration5.py -v
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
KIRIUS_CODE = "equipe-kirius"
KIRIUS_NAME = "KIRIUS EMPREENDIMENTOS"

STATE = {}


def creds():
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:password|senha)(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    if not email or not pw:
        pytest.skip("credentials not parseable")
    return email.group(1), pw.group(1)


OWNER_EMAIL, OWNER_PW = creds()


def session(token=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def owner():
    s = session()
    r = s.post(f"{BASE}/auth/owner-login", json={"email": OWNER_EMAIL, "password": OWNER_PW})
    if r.status_code != 200:
        pytest.fail(f"owner login failed {r.status_code}: {r.text[:300]}")
    STATE["owner_token"] = r.json()["token"]
    STATE["owner_user_id"] = r.json()["user"]["user_id"]
    return session(r.json()["token"])


class TestSlugifyParity:
    def test_00_health(self):
        r = requests.get(f"{BASE}/")
        assert r.status_code == 200 and r.json().get("ok") is True

    # ---------- company-login slugify parity on existing stable company ----------
    @pytest.mark.parametrize("code_variant", [
        "gestor360", "Gestor360", "GESTOR360", " gestor360 ", "  Gestor360",
    ])
    def test_company_login_variants_ok(self, code_variant):
        s = session()
        r = s.post(f"{BASE}/auth/company-login", json={"code": code_variant, "password": STABLE_PW})
        assert r.status_code == 200, f"{code_variant!r} -> {r.status_code}: {r.text[:200]}"
        d = r.json()
        assert d["company"]["code"] == STABLE_CODE
        assert d["company"]["name"] == STABLE_NAME
        assert isinstance(d["users"], list) and len(d["users"]) >= 1
        assert "company_session" in s.cookies.get_dict()

    def test_company_login_space_variant_not_found(self):
        """'gestor 360' -> 'gestor-360' which does not exist -> 401 (per spec)."""
        r = requests.post(f"{BASE}/auth/company-login", json={"code": "gestor 360", "password": STABLE_PW})
        assert r.status_code == 401, f"got {r.status_code}: {r.text[:200]}"

    def test_company_login_bad_password(self):
        r = requests.post(f"{BASE}/auth/company-login", json={"code": "Gestor360", "password": "wrong-pw"})
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_company_login_nonexistent_code(self):
        r = requests.post(f"{BASE}/auth/company-login", json={"code": f"nope-{SUFFIX}", "password": "x"})
        assert r.status_code == 401, f"expected 401 not {r.status_code}"

    def test_company_login_empty_slug_code(self):
        """Codes that slugify to '' must not authenticate a pending-setup company."""
        for bad in ["   ", "!!!", "---", "@@@"]:
            r = requests.post(f"{BASE}/auth/company-login", json={"code": bad, "password": ""})
            assert r.status_code in (401, 422), f"{bad!r} -> {r.status_code}: {r.text[:150]}"

    # ---------- kirius (real user company) ----------
    @pytest.mark.parametrize("code_variant", [
        "equipe-kirius", "Equipe Kirius", "EQUIPE KIRIUS", "equipe kirius", " equipe-kirius ",
    ])
    def test_lookup_company_kirius_variants(self, code_variant):
        r = requests.get(f"{BASE}/auth/lookup-company", params={"code": code_variant})
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert d["found"] is True, f"{code_variant!r} -> {d}"
        assert d["name"] == KIRIUS_NAME
        assert d["code"] == KIRIUS_CODE

    @pytest.mark.parametrize("code_variant", ["Equipe Kirius", "EQUIPE KIRIUS", "equipe kirius"])
    def test_company_login_kirius_normalizes_to_401_wrong_pw(self, code_variant):
        """Password unknown → must be 401 'not found or wrong password', never 500."""
        r = requests.post(f"{BASE}/auth/company-login", json={"code": code_variant, "password": f"wrong{SUFFIX}"})
        assert r.status_code == 401, f"{code_variant!r} -> {r.status_code}: {r.text[:200]}"

    def test_lookup_company_empty_slug(self):
        """A code slugifying to '' must NOT leak the pending-setup company."""
        findings = []
        for bad in ["   ", "!!!", "---"]:
            r = requests.get(f"{BASE}/auth/lookup-company", params={"code": bad})
            assert r.status_code == 200, r.text[:150]
            if r.json().get("found") is True:
                findings.append(f"lookup-company({bad!r}) -> {r.json()}")
        STATE["lookup_empty_findings"] = findings
        assert not findings, "; ".join(findings)

    def test_lookup_company_not_found(self):
        r = requests.get(f"{BASE}/auth/lookup-company", params={"code": f"nope{SUFFIX}"})
        assert r.status_code == 200 and r.json()["found"] is False


    # ---------- setup + login round-trip (same class: xdist loadscope keeps order) ----------
    def test_yy_setup_with_spaces_then_login_raw(self, owner):
        raw = "Neto Materiais"
        r = owner.post(f"{BASE}/auth/setup-company",
                       json={"code": raw, "password": STABLE_PW, "name": "TEST Neto Materiais"})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["code"] == "neto-materiais"
        STATE["dirty"] = True

        # lookup with the raw string
        lk = requests.get(f"{BASE}/auth/lookup-company", params={"code": raw})
        assert lk.status_code == 200 and lk.json()["found"] is True
        assert lk.json()["code"] == "neto-materiais"

        # login with the raw string + case variants
        for variant in (raw, "NETO MATERIAIS", " neto materiais ", "neto-materiais"):
            s = session()
            lg = s.post(f"{BASE}/auth/company-login", json={"code": variant, "password": STABLE_PW})
            assert lg.status_code == 200, f"{variant!r} -> {lg.status_code}: {lg.text[:200]}"
            assert lg.json()["company"]["code"] == "neto-materiais"

    def test_yy2_setup_with_accents(self, owner):
        raw = "Néto Açaí"
        r = owner.post(f"{BASE}/auth/setup-company",
                       json={"code": raw, "password": STABLE_PW, "name": "TEST Accent"})
        assert r.status_code == 200, r.text[:300]
        slug = r.json()["code"]
        STATE["accent_slug"] = slug
        # login with the raw accented string must work (same normalization both sides)
        s = session()
        lg = s.post(f"{BASE}/auth/company-login", json={"code": raw, "password": STABLE_PW})
        assert lg.status_code == 200, f"accented raw login failed: {lg.status_code} {lg.text[:200]}"
        assert lg.json()["company"]["code"] == slug

    def test_zz_restore_stable_code_and_two_step(self, owner):
        r = owner.post(f"{BASE}/auth/setup-company",
                       json={"code": STABLE_CODE, "password": STABLE_PW, "name": STABLE_NAME})
        assert r.status_code == 200, r.text[:300]
        assert r.json()["code"] == STABLE_CODE

        # regression: full two-step flow with cookie
        s = session()
        c = s.post(f"{BASE}/auth/company-login", json={"code": STABLE_CODE, "password": STABLE_PW})
        assert c.status_code == 200, c.text[:200]
        assert "company_session" in s.cookies.get_dict()
        u = s.post(f"{BASE}/auth/user-login", json={"username": "admin", "password": OWNER_PW})
        assert u.status_code == 200, u.text[:300]
        d = u.json()
        assert d["user"]["role"] == "owner"
        assert isinstance(d["token"], str) and len(d["token"]) > 10

        # token works
        me = session(d["token"]).get(f"{BASE}/auth/me")
        assert me.status_code == 200
        assert me.json()["company"]["code"] == STABLE_CODE
        assert me.json()["company"]["pending_setup"] is False
