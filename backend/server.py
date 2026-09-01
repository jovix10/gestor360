"""Gestor360 backend — FastAPI + asyncpg (Supabase Postgres).

All tenant-scoped queries filter by `company_id`. The service-role connection
used here bypasses RLS, so the WHERE clause is the *only* isolation layer.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Literal, Optional

import bcrypt
import jwt as pyjwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from db import close_pool, execute, fetch, fetchrow, fetchval, get_pool, row_to_dict, rows_to_list

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

JWT_SECRET = os.environ.get("JWT_SECRET") or "gestor360-dev-secret-change-in-prod"
JWT_ALG = "HS256"

app = FastAPI(title="Gestor360")
api_router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

Role = Literal["owner", "gerente", "vendedor"]


# =====================================================================
# Pydantic models (unchanged wire contract vs. previous version)
# =====================================================================
class CompanyUpdateIn(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    ie: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_data_url: Optional[str] = None
    stock_enabled: Optional[bool] = None


class SetupCompanyIn(BaseModel):
    code: str
    password: str
    name: str


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class CompanyLoginIn(BaseModel):
    code: str
    password: str


class UserLoginIn(BaseModel):
    username: str
    password: str


class CreateUserIn(BaseModel):
    name: str
    username: str
    password: str
    role: Role = "vendedor"
    email: str = ""


class UpdateUserIn(BaseModel):
    name: Optional[str] = None
    role: Optional[Role] = None
    password: Optional[str] = None
    must_change_password: Optional[bool] = None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class ChangeCompanyCredentialsIn(BaseModel):
    current_password: str
    new_code: Optional[str] = None
    new_password: Optional[str] = None


class Client(BaseModel):
    id: Optional[str] = None
    name: str
    document: str = ""
    ie: str = ""
    email: str = ""
    phone: str = ""
    cep: str = ""
    street: str = ""
    number: str = ""
    complement: str = ""
    district: str = ""
    city: str = ""
    state: str = ""
    address: str = ""
    notes: str = ""


class Product(BaseModel):
    id: Optional[str] = None
    code: str
    description: str
    price: float = 0.0
    cost_price: float = 0.0
    stock: float = 0.0
    unit: str = "UN"


class DocLine(BaseModel):
    product_id: Optional[str] = None
    code: str = ""
    description: str = ""
    quantity: float = 1
    unit_price: float = 0
    discount_pct: float = 0


class PaymentPart(BaseModel):
    method: str = "pix"
    amount: float = 0.0
    installments: int = 1
    boleto_days: List[int] = []


class DocumentIn(BaseModel):
    doc_type: Literal["orcamento", "venda"] = "orcamento"
    client_id: str
    lines: List[DocLine] = []
    payments: List[PaymentPart] = []
    global_discount_pct: float = 0.0
    global_discount_amount: float = 0.0
    notes: str = ""


class DocumentUpdate(BaseModel):
    client_id: Optional[str] = None
    lines: Optional[List[DocLine]] = None
    payments: Optional[List[PaymentPart]] = None
    global_discount_pct: Optional[float] = None
    global_discount_amount: Optional[float] = None
    notes: Optional[str] = None


# =====================================================================
# Auth helpers
# =====================================================================
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), (hashed or "").encode())
    except Exception:
        return False


def create_jwt(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_company_session(company_id: str) -> str:
    payload = {
        "company_id": company_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\-_]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


COOKIE_KW = dict(httponly=True, secure=True, samesite="none", path="/")


async def get_current_user(request: Request) -> dict:
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("jwt_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    user = await fetchrow(
        "SELECT user_id, company_id, email, name, username, role, picture, "
        "must_change_password FROM public.users WHERE user_id = $1",
        payload.get("user_id", ""),
    )
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    d = row_to_dict(user)
    d["company_id"] = str(d["company_id"])
    return d


async def get_company_of_user(user: dict) -> dict:
    row = await fetchrow(
        "SELECT * FROM public.companies WHERE id = $1",
        uuid.UUID(user["company_id"]),
    )
    if not row:
        raise HTTPException(400, "Empresa não encontrada")
    c = row_to_dict(row)
    c["id"] = str(c["id"])
    c.pop("password_hash", None)
    return c


def require_roles(user: dict, allowed: List[str]):
    if user.get("role") not in allowed:
        raise HTTPException(403, "Sem permissão para essa ação")


def _sanitize_user(u: dict) -> dict:
    return {
        "user_id": u["user_id"],
        "company_id": str(u.get("company_id", "")),
        "email": u.get("email", "") or "",
        "name": u.get("name", "") or "",
        "username": u.get("username", "") or "",
        "role": u.get("role", "vendedor") or "vendedor",
        "picture": u.get("picture", "") or "",
    }


def _serialize_dt(dt):
    if isinstance(dt, datetime):
        return dt.astimezone(timezone.utc).isoformat()
    return dt


def _doc_row_out(row: dict) -> dict:
    """Normalize Postgres row → JSON payload compatible with existing frontend."""
    if not row:
        return row
    d = dict(row)
    d["id"] = str(d["id"])
    d["client_id"] = str(d["client_id"])
    if d.get("converted_from"):
        d["converted_from"] = str(d["converted_from"])
    d.pop("company_id", None)
    for k in ("created_at", "valid_until"):
        if d.get(k):
            d[k] = _serialize_dt(d[k])
    # numeric → float
    for k in ("global_discount_pct", "global_discount_amount"):
        if d.get(k) is not None:
            d[k] = float(d[k])
    return d


# =====================================================================
# AUTH routes
# =====================================================================
@api_router.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    existing = await fetchrow(
        "SELECT user_id FROM public.users WHERE LOWER(email) = LOWER($1)", payload.email
    )
    if existing:
        raise HTTPException(400, "Email já cadastrado")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    company_id = str(uuid.uuid4())
    await execute(
        "INSERT INTO public.companies (id, code, password_hash, owner_id, name, email, pending_setup) "
        "VALUES ($1, '', '', $2, $3, $4, TRUE)",
        uuid.UUID(company_id), user_id, payload.name + " — Empresa", payload.email.lower(),
    )
    await execute(
        "INSERT INTO public.users (user_id, company_id, email, name, username, password_hash, "
        "auth_provider, role, must_change_password) "
        "VALUES ($1, $2, $3, $4, 'admin', $5, 'email', 'owner', FALSE)",
        user_id, uuid.UUID(company_id), payload.email.lower(), payload.name,
        hash_password(payload.password),
    )
    token = create_jwt(user_id)
    response.set_cookie("jwt_token", token, max_age=7 * 24 * 3600, **COOKIE_KW)
    return {
        "user": _sanitize_user({
            "user_id": user_id, "company_id": company_id,
            "email": payload.email.lower(), "name": payload.name,
            "username": "admin", "role": "owner",
        }),
        "token": token,
        "must_change_password": False,
    }


@api_router.post("/auth/owner-login")
async def owner_login(payload: LoginIn, response: Response):
    row = await fetchrow(
        "SELECT * FROM public.users WHERE LOWER(email) = LOWER($1)", payload.email
    )
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Credenciais inválidas")
    user = row_to_dict(row)
    if user.get("role") != "owner":
        raise HTTPException(403, "Este login é apenas para o dono.")
    token = create_jwt(user["user_id"])
    response.set_cookie("jwt_token", token, max_age=7 * 24 * 3600, **COOKIE_KW)
    return {"user": _sanitize_user(user), "token": token,
            "must_change_password": bool(user.get("must_change_password"))}


@api_router.post("/auth/company-login")
async def company_login(payload: CompanyLoginIn, response: Response):
    code = slugify(payload.code)
    if not code:
        raise HTTPException(401, "Empresa não encontrada ou senha inválida")
    row = await fetchrow("SELECT * FROM public.companies WHERE code = $1", code)
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Empresa não encontrada ou senha inválida")
    company = row_to_dict(row)
    company["id"] = str(company["id"])
    session = create_company_session(company["id"])
    response.set_cookie("company_session", session, max_age=1800, **COOKIE_KW)
    users = await fetch(
        "SELECT user_id, name, username, role, picture FROM public.users "
        "WHERE company_id = $1 ORDER BY role='owner' DESC, name",
        uuid.UUID(company["id"]),
    )
    return {
        "company": {"id": company["id"], "code": company["code"], "name": company["name"]},
        "users": [dict(u) for u in users],
    }


@api_router.post("/auth/user-login")
async def user_login(payload: UserLoginIn, request: Request, response: Response):
    comp_token = request.cookies.get("company_session")
    if not comp_token:
        raise HTTPException(401, "Sessão de empresa expirada — reentre na empresa")
    try:
        cp = pyjwt.decode(comp_token, JWT_SECRET, algorithms=[JWT_ALG])
        company_id = cp["company_id"]
    except Exception:
        raise HTTPException(401, "Sessão de empresa inválida")
    username = payload.username.lower().strip()
    row = await fetchrow(
        "SELECT * FROM public.users WHERE company_id = $1 AND LOWER(username) = $2",
        uuid.UUID(company_id), username,
    )
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Usuário ou senha inválidos")
    user = row_to_dict(row)
    user["company_id"] = str(user["company_id"])
    token = create_jwt(user["user_id"])
    response.set_cookie("jwt_token", token, max_age=7 * 24 * 3600, **COOKIE_KW)
    response.delete_cookie("company_session", path="/")
    return {"user": _sanitize_user(user), "token": token,
            "must_change_password": bool(user.get("must_change_password"))}


@api_router.post("/auth/setup-company")
async def setup_company(payload: SetupCompanyIn, user: dict = Depends(get_current_user)):
    require_roles(user, ["owner"])
    code = slugify(payload.code)
    if len(code) < 3:
        raise HTTPException(400, "Código muito curto (mínimo 3 caracteres)")
    if len(payload.password) < 4:
        raise HTTPException(400, "Senha muito curta")
    other = await fetchrow(
        "SELECT id FROM public.companies WHERE code = $1 AND id <> $2",
        code, uuid.UUID(user["company_id"]),
    )
    if other:
        raise HTTPException(400, "Código já em uso por outra empresa")
    await execute(
        "UPDATE public.companies SET code = $1, password_hash = $2, name = $3, "
        "pending_setup = FALSE WHERE id = $4",
        code, hash_password(payload.password), payload.name, uuid.UUID(user["company_id"]),
    )
    return {"ok": True, "code": code}


@api_router.get("/auth/lookup-company")
async def lookup_company(code: str):
    slug = slugify(code)
    if len(slug) < 3:
        return {"found": False}
    row = await fetchrow("SELECT name, code FROM public.companies WHERE code = $1", slug)
    if not row:
        return {"found": False}
    return {"found": True, "name": row["name"], "code": row["code"]}


@api_router.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    company = await get_company_of_user(user)
    return {
        **_sanitize_user(user),
        "must_change_password": bool(user.get("must_change_password")),
        "company": {
            "id": company["id"],
            "code": company.get("code", ""),
            "name": company.get("name", ""),
            "pending_setup": bool(company.get("pending_setup")),
        },
    }


@api_router.post("/auth/change-password")
async def change_password(payload: ChangePasswordIn, user: dict = Depends(get_current_user)):
    row = await fetchrow("SELECT password_hash FROM public.users WHERE user_id = $1", user["user_id"])
    if not row or not verify_password(payload.current_password, row["password_hash"]):
        raise HTTPException(400, "Senha atual incorreta")
    if len(payload.new_password) < 4:
        raise HTTPException(400, "Nova senha muito curta")
    await execute(
        "UPDATE public.users SET password_hash = $1, must_change_password = FALSE WHERE user_id = $2",
        hash_password(payload.new_password), user["user_id"],
    )
    return {"ok": True}


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("jwt_token", path="/")
    response.delete_cookie("company_session", path="/")
    return {"ok": True}


# =====================================================================
# TEAM (users) — owner only
# =====================================================================
@api_router.get("/users")
async def list_users(user: dict = Depends(get_current_user)):
    require_roles(user, ["owner"])
    rows = await fetch(
        "SELECT user_id, name, username, role, email, picture, must_change_password "
        "FROM public.users WHERE company_id = $1 ORDER BY role='owner' DESC, name",
        uuid.UUID(user["company_id"]),
    )
    return [dict(r) for r in rows]


@api_router.post("/users")
async def create_user(payload: CreateUserIn, user: dict = Depends(get_current_user)):
    require_roles(user, ["owner"])
    if payload.role == "owner":
        raise HTTPException(400, "Não é permitido criar outro dono para a empresa")
    username = payload.username.lower().strip()
    if len(username) < 2:
        raise HTTPException(400, "Nome de usuário muito curto")
    dup = await fetchrow(
        "SELECT user_id FROM public.users WHERE company_id = $1 AND LOWER(username) = $2",
        uuid.UUID(user["company_id"]), username,
    )
    if dup:
        raise HTTPException(400, "Nome de usuário já em uso na empresa")
    if len(payload.password) < 4:
        raise HTTPException(400, "Senha muito curta")
    new_id = f"user_{uuid.uuid4().hex[:12]}"
    await execute(
        "INSERT INTO public.users (user_id, company_id, email, name, username, password_hash, "
        "auth_provider, role, must_change_password) VALUES "
        "($1, $2, $3, $4, $5, $6, 'email', $7, TRUE)",
        new_id, uuid.UUID(user["company_id"]),
        (payload.email or "").lower(), payload.name, username,
        hash_password(payload.password), payload.role,
    )
    return {"user_id": new_id, "name": payload.name, "username": username, "role": payload.role}


@api_router.put("/users/{target_user_id}")
async def update_user(target_user_id: str, payload: UpdateUserIn, user: dict = Depends(get_current_user)):
    require_roles(user, ["owner"])
    target = await fetchrow(
        "SELECT role FROM public.users WHERE user_id = $1 AND company_id = $2",
        target_user_id, uuid.UUID(user["company_id"]),
    )
    if not target:
        raise HTTPException(404, "Usuário não encontrado")
    if target["role"] == "owner" and payload.role and payload.role != "owner":
        raise HTTPException(400, "Não é possível rebaixar o dono")
    sets: list[str] = []
    args: list = []
    idx = 1
    if payload.name is not None:
        sets.append(f"name = ${idx}"); args.append(payload.name); idx += 1
    if payload.role is not None:
        sets.append(f"role = ${idx}"); args.append(payload.role); idx += 1
    if payload.password is not None:
        if len(payload.password) < 4:
            raise HTTPException(400, "Senha muito curta")
        sets.append(f"password_hash = ${idx}"); args.append(hash_password(payload.password)); idx += 1
        sets.append(f"must_change_password = TRUE")
    if payload.must_change_password is not None:
        sets.append(f"must_change_password = ${idx}"); args.append(payload.must_change_password); idx += 1
    if sets:
        args.append(target_user_id)
        await execute(f"UPDATE public.users SET {', '.join(sets)} WHERE user_id = ${idx}", *args)
    return {"ok": True}


@api_router.delete("/users/{target_user_id}")
async def delete_user(target_user_id: str, user: dict = Depends(get_current_user)):
    require_roles(user, ["owner"])
    target = await fetchrow(
        "SELECT role FROM public.users WHERE user_id = $1 AND company_id = $2",
        target_user_id, uuid.UUID(user["company_id"]),
    )
    if not target:
        raise HTTPException(404, "Usuário não encontrado")
    if target["role"] == "owner":
        raise HTTPException(400, "Não é possível excluir o dono")
    await execute("DELETE FROM public.users WHERE user_id = $1", target_user_id)
    return {"ok": True}


# =====================================================================
# COMPANY
# =====================================================================
@api_router.get("/company")
async def get_company(user: dict = Depends(get_current_user)):
    return await get_company_of_user(user)


@api_router.put("/company")
async def update_company(payload: CompanyUpdateIn, user: dict = Depends(get_current_user)):
    require_roles(user, ["owner", "gerente"])
    data = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if data:
        sets: list[str] = []
        args: list = []
        idx = 1
        for k, v in data.items():
            sets.append(f"{k} = ${idx}"); args.append(v); idx += 1
        args.append(uuid.UUID(user["company_id"]))
        await execute(f"UPDATE public.companies SET {', '.join(sets)} WHERE id = ${idx}", *args)
    return await get_company_of_user(user)


@api_router.post("/company/change-credentials")
async def change_company_credentials(
    payload: ChangeCompanyCredentialsIn, user: dict = Depends(get_current_user)
):
    require_roles(user, ["owner"])
    row = await fetchrow(
        "SELECT code, password_hash FROM public.companies WHERE id = $1",
        uuid.UUID(user["company_id"]),
    )
    if not row or not verify_password(payload.current_password, row["password_hash"]):
        raise HTTPException(400, "Senha atual da empresa incorreta")
    sets: list[str] = []
    args: list = []
    idx = 1
    new_code_final = row["code"]
    if payload.new_code:
        new_code = slugify(payload.new_code)
        if len(new_code) < 3:
            raise HTTPException(400, "Código muito curto (mínimo 3 caracteres)")
        dup = await fetchrow(
            "SELECT id FROM public.companies WHERE code = $1 AND id <> $2",
            new_code, uuid.UUID(user["company_id"]),
        )
        if dup:
            raise HTTPException(400, "Código já em uso por outra empresa")
        sets.append(f"code = ${idx}"); args.append(new_code); idx += 1
        new_code_final = new_code
    if payload.new_password:
        if len(payload.new_password) < 4:
            raise HTTPException(400, "Nova senha muito curta")
        sets.append(f"password_hash = ${idx}"); args.append(hash_password(payload.new_password)); idx += 1
    if not sets:
        raise HTTPException(400, "Informe um novo código ou nova senha")
    args.append(uuid.UUID(user["company_id"]))
    await execute(f"UPDATE public.companies SET {', '.join(sets)} WHERE id = ${idx}", *args)
    return {"ok": True, "code": new_code_final}


# =====================================================================
# CLIENTS
# =====================================================================
CLIENT_COLS = [
    "id", "name", "document", "ie", "email", "phone", "cep", "street",
    "number", "complement", "district", "city", "state", "address", "notes",
]


@api_router.get("/clients")
async def list_clients(user: dict = Depends(get_current_user)):
    rows = await fetch(
        f"SELECT {', '.join(CLIENT_COLS)} FROM public.clients "
        "WHERE company_id = $1 ORDER BY name",
        uuid.UUID(user["company_id"]),
    )
    out = []
    for r in rows:
        d = dict(r); d["id"] = str(d["id"]); out.append(d)
    return out


@api_router.post("/clients")
async def create_client(payload: Client, user: dict = Depends(get_current_user)):
    new_id = payload.id or str(uuid.uuid4())
    doc = payload.model_dump()
    doc["id"] = new_id
    cols = ", ".join(["company_id"] + CLIENT_COLS)
    placeholders = ", ".join(f"${i+1}" for i in range(len(CLIENT_COLS) + 1))
    vals = [uuid.UUID(user["company_id"]), uuid.UUID(new_id)] + [doc[c] for c in CLIENT_COLS[1:]]
    await execute(f"INSERT INTO public.clients ({cols}) VALUES ({placeholders})", *vals)
    doc["id"] = new_id
    return doc


@api_router.put("/clients/{client_id}")
async def update_client(client_id: str, payload: Client, user: dict = Depends(get_current_user)):
    doc = payload.model_dump()
    doc["id"] = client_id
    sets = ", ".join(f"{c} = ${i+1}" for i, c in enumerate(CLIENT_COLS[1:]))
    args = [doc[c] for c in CLIENT_COLS[1:]] + [uuid.UUID(client_id), uuid.UUID(user["company_id"])]
    res = await execute(
        f"UPDATE public.clients SET {sets} WHERE id = ${len(CLIENT_COLS)} AND company_id = ${len(CLIENT_COLS)+1}",
        *args,
    )
    if res.endswith("0"):
        raise HTTPException(404, "Cliente não encontrado")
    return doc


@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, user: dict = Depends(get_current_user)):
    await execute(
        "DELETE FROM public.clients WHERE id = $1 AND company_id = $2",
        uuid.UUID(client_id), uuid.UUID(user["company_id"]),
    )
    return {"ok": True}


# =====================================================================
# PRODUCTS
# =====================================================================
PRODUCT_COLS = ["id", "code", "description", "price", "cost_price", "stock", "unit"]


def _strip_cost(rows, user):
    if user.get("role") == "vendedor":
        for r in rows:
            r.pop("cost_price", None)
    return rows


@api_router.get("/products")
async def list_products(user: dict = Depends(get_current_user)):
    rows = await fetch(
        f"SELECT {', '.join(PRODUCT_COLS)} FROM public.products "
        "WHERE company_id = $1 ORDER BY code, description",
        uuid.UUID(user["company_id"]),
    )
    out = []
    for r in rows:
        d = dict(r); d["id"] = str(d["id"])
        for k in ("price", "cost_price", "stock"):
            d[k] = float(d[k])
        out.append(d)
    return _strip_cost(out, user)


@api_router.post("/products")
async def create_product(payload: Product, user: dict = Depends(get_current_user)):
    dup = await fetchrow(
        "SELECT id FROM public.products WHERE company_id = $1 AND code = $2",
        uuid.UUID(user["company_id"]), payload.code,
    )
    if dup:
        raise HTTPException(400, "Código de produto já existe")
    new_id = payload.id or str(uuid.uuid4())
    cost = 0.0 if user.get("role") == "vendedor" else payload.cost_price
    await execute(
        "INSERT INTO public.products (id, company_id, code, description, price, cost_price, stock, unit) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        uuid.UUID(new_id), uuid.UUID(user["company_id"]),
        payload.code, payload.description, payload.price, cost, payload.stock, payload.unit,
    )
    out = payload.model_dump(); out["id"] = new_id; out["cost_price"] = cost
    return _strip_cost([out], user)[0]


@api_router.put("/products/{product_id}")
async def update_product(product_id: str, payload: Product, user: dict = Depends(get_current_user)):
    existing = await fetchrow(
        "SELECT cost_price FROM public.products WHERE id = $1 AND company_id = $2",
        uuid.UUID(product_id), uuid.UUID(user["company_id"]),
    )
    if not existing:
        raise HTTPException(404, "Produto não encontrado")
    cost = float(existing["cost_price"]) if user.get("role") == "vendedor" else payload.cost_price
    await execute(
        "UPDATE public.products SET code=$1, description=$2, price=$3, cost_price=$4, "
        "stock=$5, unit=$6 WHERE id=$7 AND company_id=$8",
        payload.code, payload.description, payload.price, cost, payload.stock, payload.unit,
        uuid.UUID(product_id), uuid.UUID(user["company_id"]),
    )
    out = payload.model_dump(); out["id"] = product_id; out["cost_price"] = cost
    return _strip_cost([out], user)[0]


@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(get_current_user)):
    await execute(
        "DELETE FROM public.products WHERE id = $1 AND company_id = $2",
        uuid.UUID(product_id), uuid.UUID(user["company_id"]),
    )
    return {"ok": True}


# =====================================================================
# DOCUMENTS
# =====================================================================
async def next_doc_number(company_id: str, doc_type: str) -> int:
    return int(await fetchval("SELECT public.next_doc_number($1, $2)", uuid.UUID(company_id), doc_type))


def _doc_where_filter(user: dict, base_alias: str = "d") -> tuple[str, list]:
    """Build tenant + role visibility WHERE fragment (starts at $1)."""
    args = [uuid.UUID(user["company_id"])]
    where = f"{base_alias}.company_id = $1"
    if user.get("role") == "vendedor":
        args.append(user["user_id"])
        where += f" AND {base_alias}.created_by = $2"
    return where, args


def _compute_total(row: dict) -> float:
    line_total = 0.0
    for line in row.get("lines") or []:
        gross = float(line.get("quantity") or 0) * float(line.get("unit_price") or 0)
        line_total += gross * (1 - float(line.get("discount_pct") or 0) / 100)
    gpct = float(row.get("global_discount_pct") or 0)
    gamt = float(row.get("global_discount_amount") or 0)
    return round(max(line_total * (1 - gpct / 100) - gamt, 0), 2)


@api_router.get("/documents")
async def list_documents(user: dict = Depends(get_current_user)):
    where, args = _doc_where_filter(user)
    rows = await fetch(
        f"""
        SELECT d.id, d.doc_type, d.number, d.client_id, d.lines, d.payments,
               d.global_discount_pct, d.global_discount_amount, d.notes,
               d.created_at, d.valid_until, d.converted_from, d.status, d.created_by,
               c.name AS client_name,
               u.name AS created_by_name
        FROM public.documents d
        LEFT JOIN public.clients c ON c.id = d.client_id
        LEFT JOIN public.users u ON u.user_id = d.created_by
        WHERE {where}
        ORDER BY d.created_at DESC
        LIMIT 2000
        """,
        *args,
    )
    out = []
    for r in rows:
        d = _doc_row_out(dict(r))
        d["client_name"] = r["client_name"] or "—"
        d["created_by_name"] = r["created_by_name"] or ""
        d["total"] = _compute_total(d)
        out.append(d)
    return out


@api_router.post("/documents")
async def create_document(payload: DocumentIn, user: dict = Depends(get_current_user)):
    cli = await fetchrow(
        "SELECT id FROM public.clients WHERE id = $1 AND company_id = $2",
        uuid.UUID(payload.client_id), uuid.UUID(user["company_id"]),
    )
    if not cli:
        raise HTTPException(400, "Cliente inválido")
    number = await next_doc_number(user["company_id"], payload.doc_type)
    now = datetime.now(timezone.utc)
    valid_until = now + timedelta(hours=72) if payload.doc_type == "orcamento" else None
    new_id = str(uuid.uuid4())
    lines = [l.model_dump() for l in payload.lines]
    payments = [p.model_dump() for p in payload.payments]

    company = await get_company_of_user(user)
    if company.get("stock_enabled") and payload.doc_type == "venda":
        for line in payload.lines:
            if line.product_id:
                await execute(
                    "UPDATE public.products SET stock = stock - $1 WHERE id = $2 AND company_id = $3",
                    float(line.quantity), uuid.UUID(line.product_id), uuid.UUID(user["company_id"]),
                )

    await execute(
        """
        INSERT INTO public.documents
          (id, company_id, doc_type, number, client_id, lines, payments,
           global_discount_pct, global_discount_amount, notes,
           created_at, valid_until, created_by, status)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,'ativo')
        """,
        uuid.UUID(new_id), uuid.UUID(user["company_id"]), payload.doc_type, number,
        uuid.UUID(payload.client_id), lines, payments,
        payload.global_discount_pct, payload.global_discount_amount, payload.notes,
        now, valid_until, user["user_id"],
    )
    return {
        "id": new_id, "doc_type": payload.doc_type, "number": number,
        "client_id": payload.client_id, "lines": lines, "payments": payments,
        "global_discount_pct": payload.global_discount_pct,
        "global_discount_amount": payload.global_discount_amount,
        "notes": payload.notes,
        "created_at": _serialize_dt(now),
        "valid_until": _serialize_dt(valid_until),
        "status": "ativo", "created_by": user["user_id"],
    }


@api_router.get("/documents/{doc_id}")
async def get_document(doc_id: str, user: dict = Depends(get_current_user)):
    where, args = _doc_where_filter(user)
    args.append(uuid.UUID(doc_id))
    row = await fetchrow(
        f"SELECT * FROM public.documents d WHERE {where} AND d.id = ${len(args)}",
        *args,
    )
    if not row:
        raise HTTPException(404, "Documento não encontrado")
    return _doc_row_out(dict(row))


@api_router.put("/documents/{doc_id}")
async def update_document(doc_id: str, payload: DocumentUpdate, user: dict = Depends(get_current_user)):
    where, args = _doc_where_filter(user)
    args.append(uuid.UUID(doc_id))
    existing = await fetchrow(
        f"SELECT id FROM public.documents d WHERE {where} AND d.id = ${len(args)}",
        *args,
    )
    if not existing:
        raise HTTPException(404, "Documento não encontrado")
    sets: list[str] = []
    upd_args: list = []
    idx = 1
    if payload.client_id is not None:
        cli = await fetchrow(
            "SELECT id FROM public.clients WHERE id = $1 AND company_id = $2",
            uuid.UUID(payload.client_id), uuid.UUID(user["company_id"]),
        )
        if not cli:
            raise HTTPException(400, "Cliente inválido")
        sets.append(f"client_id = ${idx}"); upd_args.append(uuid.UUID(payload.client_id)); idx += 1
    if payload.lines is not None:
        sets.append(f"lines = ${idx}::jsonb"); upd_args.append([l.model_dump() for l in payload.lines]); idx += 1
    if payload.payments is not None:
        sets.append(f"payments = ${idx}::jsonb"); upd_args.append([p.model_dump() for p in payload.payments]); idx += 1
    if payload.global_discount_pct is not None:
        sets.append(f"global_discount_pct = ${idx}"); upd_args.append(payload.global_discount_pct); idx += 1
    if payload.global_discount_amount is not None:
        sets.append(f"global_discount_amount = ${idx}"); upd_args.append(payload.global_discount_amount); idx += 1
    if payload.notes is not None:
        sets.append(f"notes = ${idx}"); upd_args.append(payload.notes); idx += 1
    if sets:
        upd_args.extend([uuid.UUID(doc_id), uuid.UUID(user["company_id"])])
        await execute(
            f"UPDATE public.documents SET {', '.join(sets)} "
            f"WHERE id = ${idx} AND company_id = ${idx+1}",
            *upd_args,
        )
    row = await fetchrow(
        "SELECT * FROM public.documents WHERE id = $1 AND company_id = $2",
        uuid.UUID(doc_id), uuid.UUID(user["company_id"]),
    )
    return _doc_row_out(dict(row))


@api_router.post("/documents/{doc_id}/convert")
async def convert_document(doc_id: str, user: dict = Depends(get_current_user)):
    where, args = _doc_where_filter(user)
    args.append(uuid.UUID(doc_id))
    src = await fetchrow(
        f"SELECT * FROM public.documents d WHERE {where} AND d.id = ${len(args)}",
        *args,
    )
    if not src:
        raise HTTPException(404, "Orçamento não encontrado")
    if src["doc_type"] != "orcamento":
        raise HTTPException(400, "Só orçamentos podem ser convertidos")
    number = await next_doc_number(user["company_id"], "venda")
    now = datetime.now(timezone.utc)
    new_id = str(uuid.uuid4())
    lines = src["lines"] or []
    payments = src["payments"] or []
    company = await get_company_of_user(user)
    if company.get("stock_enabled"):
        for line in lines:
            if line.get("product_id"):
                await execute(
                    "UPDATE public.products SET stock = stock - $1 WHERE id = $2 AND company_id = $3",
                    float(line.get("quantity") or 0), uuid.UUID(line["product_id"]),
                    uuid.UUID(user["company_id"]),
                )
    await execute(
        """
        INSERT INTO public.documents
          (id, company_id, doc_type, number, client_id, lines, payments,
           global_discount_pct, global_discount_amount, notes,
           created_at, valid_until, converted_from, status, created_by)
        VALUES ($1,$2,'venda',$3,$4,$5,$6,$7,$8,$9,$10,NULL,$11,'ativo',$12)
        """,
        uuid.UUID(new_id), uuid.UUID(user["company_id"]), number,
        src["client_id"], lines, payments,
        float(src["global_discount_pct"] or 0), float(src["global_discount_amount"] or 0),
        src["notes"] or "", now, src["id"], user["user_id"],
    )
    row = await fetchrow(
        "SELECT * FROM public.documents WHERE id = $1", uuid.UUID(new_id)
    )
    return _doc_row_out(dict(row))


@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    where, args = _doc_where_filter(user)
    args.append(uuid.UUID(doc_id))
    await execute(
        f"DELETE FROM public.documents d WHERE {where} AND d.id = ${len(args)}",
        *args,
    )
    return {"ok": True}


# =====================================================================
# STATS
# =====================================================================
@api_router.get("/stats")
async def stats(user: dict = Depends(get_current_user)):
    company_uuid = uuid.UUID(user["company_id"])
    clients_count = await fetchval("SELECT COUNT(*) FROM public.clients WHERE company_id = $1", company_uuid)
    products_count = await fetchval("SELECT COUNT(*) FROM public.products WHERE company_id = $1", company_uuid)
    doc_where, doc_args = _doc_where_filter(user)
    orc_count = await fetchval(
        f"SELECT COUNT(*) FROM public.documents d WHERE {doc_where} AND d.doc_type = 'orcamento'",
        *doc_args,
    )
    ven_count = await fetchval(
        f"SELECT COUNT(*) FROM public.documents d WHERE {doc_where} AND d.doc_type = 'venda'",
        *doc_args,
    )
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    sales = await fetch(
        f"SELECT lines, global_discount_pct, global_discount_amount FROM public.documents d "
        f"WHERE {doc_where} AND d.doc_type = 'venda' AND d.created_at >= ${len(doc_args)+1}",
        *doc_args, month_start,
    )
    revenue = 0.0
    for s in sales:
        revenue += _compute_total(dict(s))
    return {
        "clients": int(clients_count or 0),
        "products": int(products_count or 0),
        "orcamentos": int(orc_count or 0),
        "vendas": int(ven_count or 0),
        "revenue_month": round(revenue, 2),
        "scope": "own" if user.get("role") == "vendedor" else "company",
    }


@api_router.get("/")
async def root():
    return {"app": "Gestor360", "ok": True}


app.include_router(api_router)

# CORS: restrict to configured frontend + localhost for dev
_frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
_allowed_origins = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]
if _frontend_url:
    _allowed_origins.append(_frontend_url)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    """Optionally seed a first owner. Requires SEED_OWNER_* env vars."""
    seed_email = os.environ.get("SEED_OWNER_EMAIL", "").strip().lower()
    seed_name = os.environ.get("SEED_OWNER_NAME", "").strip()
    seed_pw = os.environ.get("SEED_OWNER_PASSWORD", "")
    if not (seed_email and seed_name and seed_pw):
        return
    try:
        await get_pool()  # connects lazily
        exists = await fetchrow("SELECT user_id FROM public.users WHERE LOWER(email) = $1", seed_email)
        if exists:
            return
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        company_id = uuid.uuid4()
        await execute(
            "INSERT INTO public.companies (id, code, password_hash, owner_id, name, email, pending_setup) "
            "VALUES ($1, '', '', $2, $3, $4, TRUE)",
            company_id, user_id, seed_name + " — Empresa", seed_email,
        )
        await execute(
            "INSERT INTO public.users (user_id, company_id, email, name, username, password_hash, "
            "auth_provider, role, must_change_password) "
            "VALUES ($1, $2, $3, $4, 'admin', $5, 'email', 'owner', FALSE)",
            user_id, company_id, seed_email, seed_name, hash_password(seed_pw),
        )
        logger.info("Seeded owner %s", seed_email)
    except Exception as exc:
        logger.warning("Seed skipped: %s", exc)


@app.on_event("shutdown")
async def on_shutdown():
    await close_pool()
