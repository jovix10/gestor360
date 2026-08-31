from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt as pyjwt
import requests as http_requests
import re
import unicodedata
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Gestor360")
api_router = APIRouter(prefix="/api")

JWT_SECRET = os.environ.get('JWT_SECRET', 'gestor360-dev-secret-change-in-prod')
JWT_ALG = 'HS256'
ORANGE = colors.HexColor('#F05D23')
DARK = colors.HexColor('#09090B')
GRAY = colors.HexColor('#71717A')
LIGHT = colors.HexColor('#F4F4F5')

Role = Literal['owner', 'gerente', 'vendedor']


# ============ MODELS ============
class Company(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str = ""            # unique slug (empresa login)
    password_hash: str = ""   # empresa password hash
    owner_id: str = ""        # user_id of the owner
    name: str = ""
    cnpj: str = ""
    ie: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    logo_data_url: str = ""
    stock_enabled: bool = False
    pending_setup: bool = True


class CompanyPublic(BaseModel):
    id: str
    code: str
    name: str
    cnpj: str = ""
    ie: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    logo_data_url: str = ""
    stock_enabled: bool = False
    pending_setup: bool = False


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


class UserPublic(BaseModel):
    user_id: str
    company_id: str
    email: str = ""
    name: str
    username: str
    role: Role = "vendedor"
    picture: str = ""


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


class SessionIn(BaseModel):
    session_id: str


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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    description: str
    price: float = 0.0
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


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_type: Literal["orcamento", "venda"] = "orcamento"
    number: int = 0
    client_id: str
    lines: List[DocLine] = []
    payments: List[PaymentPart] = []
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None
    converted_from: Optional[str] = None
    status: str = "ativo"
    created_by: str = ""


class DocumentIn(BaseModel):
    doc_type: Literal["orcamento", "venda"] = "orcamento"
    client_id: str
    lines: List[DocLine] = []
    payments: List[PaymentPart] = []
    notes: str = ""


class DocumentUpdate(BaseModel):
    client_id: Optional[str] = None
    lines: Optional[List[DocLine]] = None
    payments: Optional[List[PaymentPart]] = None
    notes: Optional[str] = None


# ============ AUTH HELPERS ============
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_jwt(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(days=7),
        'iat': datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_company_session(company_id: str) -> str:
    payload = {
        'company_id': company_id,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\-_]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text


async def get_current_user(request: Request) -> dict:
    token = None
    session_token = request.cookies.get('session_token')
    if session_token:
        sess = await db.user_sessions.find_one({'session_token': session_token}, {'_id': 0})
        if sess:
            exp = sess.get('expires_at')
            if isinstance(exp, str):
                exp = datetime.fromisoformat(exp)
            if exp and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp and exp >= datetime.now(timezone.utc):
                user = await db.users.find_one({'user_id': sess['user_id']}, {'_id': 0, 'password_hash': 0})
                if user:
                    return user

    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth[7:]
    elif request.cookies.get('jwt_token'):
        token = request.cookies.get('jwt_token')
    if token:
        try:
            payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            user = await db.users.find_one({'user_id': payload['user_id']}, {'_id': 0, 'password_hash': 0})
            if user:
                return user
        except Exception:
            pass
    raise HTTPException(status_code=401, detail="Não autenticado")


async def get_company_of_user(user: dict) -> dict:
    company = await db.companies.find_one({'id': user['company_id']}, {'_id': 0, 'password_hash': 0})
    if not company:
        raise HTTPException(400, "Empresa não encontrada")
    return company


def require_roles(user: dict, allowed: List[str]):
    if user.get('role') not in allowed:
        raise HTTPException(403, "Sem permissão para essa ação")


def _sanitize_user(u: dict) -> dict:
    return {
        'user_id': u['user_id'],
        'company_id': u.get('company_id', ''),
        'email': u.get('email', ''),
        'name': u.get('name', ''),
        'username': u.get('username', ''),
        'role': u.get('role', 'vendedor'),
        'picture': u.get('picture', ''),
    }


# ============ AUTH ROUTES ============
@api_router.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    """Sign-up creates a fresh COMPANY with the user as owner."""
    existing = await db.users.find_one({'email': payload.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    company_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    # Company (pending_setup=True)
    await db.companies.insert_one({
        'id': company_id, 'code': '', 'password_hash': '', 'owner_id': user_id,
        'name': payload.name + " — Empresa", 'cnpj': '', 'ie': '', 'address': '',
        'phone': '', 'email': payload.email.lower(), 'logo_data_url': '',
        'stock_enabled': False, 'pending_setup': True,
    })
    # Owner user
    await db.users.insert_one({
        'user_id': user_id, 'company_id': company_id,
        'email': payload.email.lower(), 'name': payload.name,
        'username': 'admin',
        'password_hash': hash_password(payload.password),
        'auth_provider': 'email', 'role': 'owner',
        'must_change_password': False, 'created_at': now,
    })
    token = create_jwt(user_id)
    response.set_cookie('jwt_token', token, httponly=True, secure=True, samesite='none', path='/', max_age=7*24*3600)
    return {'user': _sanitize_user({'user_id': user_id, 'company_id': company_id, 'email': payload.email.lower(), 'name': payload.name, 'username': 'admin', 'role': 'owner'}), 'token': token, 'must_change_password': False}


@api_router.post("/auth/owner-login")
async def owner_login(payload: LoginIn, response: Response):
    """Legacy email/password login — owner only (also used during company setup)."""
    user = await db.users.find_one({'email': payload.email.lower()})
    if not user or not user.get('password_hash') or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(401, "Credenciais inválidas")
    if user.get('role') != 'owner':
        raise HTTPException(403, "Este login é apenas para o dono. Peça o código da empresa para entrar como equipe.")
    token = create_jwt(user['user_id'])
    response.set_cookie('jwt_token', token, httponly=True, secure=True, samesite='none', path='/', max_age=7*24*3600)
    return {'user': _sanitize_user(user), 'token': token, 'must_change_password': user.get('must_change_password', False)}


@api_router.post("/auth/company-login")
async def company_login(payload: CompanyLoginIn, response: Response):
    code = slugify(payload.code)
    if not code:
        raise HTTPException(401, "Empresa não encontrada ou senha inválida")
    company = await db.companies.find_one({'code': code}, {'_id': 0})
    if not company or not company.get('password_hash') or not verify_password(payload.password, company['password_hash']):
        raise HTTPException(401, "Empresa não encontrada ou senha inválida")
    session = create_company_session(company['id'])
    response.set_cookie('company_session', session, httponly=True, secure=True, samesite='none', path='/', max_age=1800)
    users = await db.users.find({'company_id': company['id']}, {'_id': 0, 'password_hash': 0}).to_list(200)
    return {
        'company': {'id': company['id'], 'code': company['code'], 'name': company['name']},
        'users': [{'user_id': u['user_id'], 'name': u['name'], 'username': u.get('username', ''), 'role': u.get('role', 'vendedor'), 'picture': u.get('picture', '')} for u in users],
    }


@api_router.post("/auth/user-login")
async def user_login(payload: UserLoginIn, request: Request, response: Response):
    comp_token = request.cookies.get('company_session')
    if not comp_token:
        raise HTTPException(401, "Sessão de empresa expirada — reentre na empresa")
    try:
        cp = pyjwt.decode(comp_token, JWT_SECRET, algorithms=[JWT_ALG])
        company_id = cp['company_id']
    except Exception:
        raise HTTPException(401, "Sessão de empresa inválida")
    username = payload.username.lower().strip()
    user = await db.users.find_one({'company_id': company_id, 'username': username})
    if not user or not user.get('password_hash') or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(401, "Usuário ou senha inválidos")
    token = create_jwt(user['user_id'])
    response.set_cookie('jwt_token', token, httponly=True, secure=True, samesite='none', path='/', max_age=7*24*3600)
    response.delete_cookie('company_session', path='/')
    return {'user': _sanitize_user(user), 'token': token, 'must_change_password': user.get('must_change_password', False)}


@api_router.post("/auth/session")
async def emergent_session(payload: SessionIn, response: Response):
    """Emergent Google OAuth callback — owner only."""
    r = http_requests.get(
        'https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data',
        headers={'X-Session-ID': payload.session_id},
        timeout=10,
    )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Session inválido")
    data = r.json()
    email = data['email'].lower()
    user = await db.users.find_one({'email': email})
    if not user:
        # New Google signup → create company + owner user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        company_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.companies.insert_one({
            'id': company_id, 'code': '', 'password_hash': '', 'owner_id': user_id,
            'name': data.get('name', email) + " — Empresa", 'cnpj': '', 'ie': '',
            'address': '', 'phone': '', 'email': email, 'logo_data_url': '',
            'stock_enabled': False, 'pending_setup': True,
        })
        user = {
            'user_id': user_id, 'company_id': company_id,
            'email': email, 'name': data.get('name', email),
            'username': 'admin', 'picture': data.get('picture', ''),
            'auth_provider': 'google', 'role': 'owner',
            'must_change_password': False, 'created_at': now,
        }
        await db.users.insert_one(dict(user))
    else:
        if user.get('role') != 'owner':
            raise HTTPException(403, "Login com Google só está disponível para o dono da empresa.")
        await db.users.update_one({'user_id': user['user_id']}, {'$set': {
            'picture': data.get('picture', user.get('picture', '')),
        }})

    session_token = data['session_token']
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        'user_id': user['user_id'],
        'session_token': session_token,
        'expires_at': expires_at.isoformat(),
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    response.set_cookie('session_token', session_token, httponly=True, secure=True, samesite='none', path='/', max_age=7*24*3600)
    return {'user': _sanitize_user(user), 'must_change_password': user.get('must_change_password', False)}


@api_router.post("/auth/setup-company")
async def setup_company(payload: SetupCompanyIn, user: dict = Depends(get_current_user)):
    require_roles(user, ['owner'])
    code = slugify(payload.code)
    if len(code) < 3:
        raise HTTPException(400, "Código muito curto (mínimo 3 caracteres)")
    if len(payload.password) < 4:
        raise HTTPException(400, "Senha muito curta")
    other = await db.companies.find_one({'code': code, 'id': {'$ne': user['company_id']}})
    if other:
        raise HTTPException(400, "Código já em uso por outra empresa")
    await db.companies.update_one(
        {'id': user['company_id']},
        {'$set': {
            'code': code,
            'password_hash': hash_password(payload.password),
            'name': payload.name,
            'pending_setup': False,
        }},
    )
    return {'ok': True, 'code': code}


@api_router.get("/auth/lookup-company")
async def lookup_company(code: str):
    """Public endpoint — returns just the company name (for two-step login UX)."""
    slug = slugify(code)
    if len(slug) < 3:
        return {'found': False}
    company = await db.companies.find_one({'code': slug}, {'_id': 0, 'name': 1, 'code': 1})
    if not company:
        return {'found': False}
    return {'found': True, 'name': company.get('name', ''), 'code': company.get('code', '')}


@api_router.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    company = await get_company_of_user(user)
    return {
        **_sanitize_user(user),
        'must_change_password': user.get('must_change_password', False),
        'company': {
            'id': company['id'],
            'code': company.get('code', ''),
            'name': company.get('name', ''),
            'pending_setup': company.get('pending_setup', False),
        },
    }


@api_router.post("/auth/change-password")
async def change_password(payload: ChangePasswordIn, user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({'user_id': user['user_id']})
    if not doc or not verify_password(payload.current_password, doc.get('password_hash', '')):
        raise HTTPException(400, "Senha atual incorreta")
    if len(payload.new_password) < 4:
        raise HTTPException(400, "Nova senha muito curta")
    await db.users.update_one(
        {'user_id': user['user_id']},
        {'$set': {'password_hash': hash_password(payload.new_password), 'must_change_password': False}},
    )
    return {'ok': True}


@api_router.post("/auth/logout")
async def logout(response: Response, request: Request):
    session_token = request.cookies.get('session_token')
    if session_token:
        await db.user_sessions.delete_one({'session_token': session_token})
    response.delete_cookie('session_token', path='/')
    response.delete_cookie('jwt_token', path='/')
    response.delete_cookie('company_session', path='/')
    return {'ok': True}


# ============ TEAM (USERS) — owner only ============
@api_router.get("/users")
async def list_users(user: dict = Depends(get_current_user)):
    require_roles(user, ['owner'])
    rows = await db.users.find({'company_id': user['company_id']}, {'_id': 0, 'password_hash': 0}).to_list(200)
    return [
        {
            'user_id': u['user_id'], 'name': u['name'], 'username': u.get('username', ''),
            'role': u.get('role', 'vendedor'), 'email': u.get('email', ''),
            'picture': u.get('picture', ''), 'must_change_password': u.get('must_change_password', False),
        }
        for u in rows
    ]


@api_router.post("/users")
async def create_user(payload: CreateUserIn, user: dict = Depends(get_current_user)):
    require_roles(user, ['owner'])
    if payload.role == 'owner':
        raise HTTPException(400, "Não é permitido criar outro dono para a empresa")
    username = payload.username.lower().strip()
    if len(username) < 2:
        raise HTTPException(400, "Nome de usuário muito curto")
    existing = await db.users.find_one({'company_id': user['company_id'], 'username': username})
    if existing:
        raise HTTPException(400, "Nome de usuário já em uso na empresa")
    if len(payload.password) < 4:
        raise HTTPException(400, "Senha muito curta")
    new_user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        'user_id': new_user_id, 'company_id': user['company_id'],
        'name': payload.name, 'username': username,
        'email': payload.email.lower() if payload.email else '',
        'password_hash': hash_password(payload.password),
        'auth_provider': 'email', 'role': payload.role,
        'must_change_password': True, 'picture': '',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return {'user_id': new_user_id, 'name': payload.name, 'username': username, 'role': payload.role}


@api_router.put("/users/{target_user_id}")
async def update_user(target_user_id: str, payload: UpdateUserIn, user: dict = Depends(get_current_user)):
    require_roles(user, ['owner'])
    target = await db.users.find_one({'user_id': target_user_id, 'company_id': user['company_id']})
    if not target:
        raise HTTPException(404, "Usuário não encontrado")
    if target.get('role') == 'owner' and payload.role and payload.role != 'owner':
        raise HTTPException(400, "Não é possível rebaixar o dono")
    update = {}
    if payload.name is not None: update['name'] = payload.name
    if payload.role is not None: update['role'] = payload.role
    if payload.password is not None:
        if len(payload.password) < 4:
            raise HTTPException(400, "Senha muito curta")
        update['password_hash'] = hash_password(payload.password)
        update['must_change_password'] = True
    if payload.must_change_password is not None:
        update['must_change_password'] = payload.must_change_password
    if update:
        await db.users.update_one({'user_id': target_user_id}, {'$set': update})
    return {'ok': True}


@api_router.delete("/users/{target_user_id}")
async def delete_user(target_user_id: str, user: dict = Depends(get_current_user)):
    require_roles(user, ['owner'])
    target = await db.users.find_one({'user_id': target_user_id, 'company_id': user['company_id']})
    if not target:
        raise HTTPException(404, "Usuário não encontrado")
    if target.get('role') == 'owner':
        raise HTTPException(400, "Não é possível excluir o dono")
    await db.users.delete_one({'user_id': target_user_id})
    return {'ok': True}


# ============ COMPANY ============
@api_router.get("/company")
async def get_company(user: dict = Depends(get_current_user)):
    company = await get_company_of_user(user)
    return company


@api_router.put("/company")
async def update_company(payload: CompanyUpdateIn, user: dict = Depends(get_current_user)):
    require_roles(user, ['owner', 'gerente'])
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if update:
        await db.companies.update_one({'id': user['company_id']}, {'$set': update})
    return await get_company_of_user(user)


@api_router.post("/company/change-credentials")
async def change_company_credentials(payload: ChangeCompanyCredentialsIn, user: dict = Depends(get_current_user)):
    require_roles(user, ['owner'])
    company = await db.companies.find_one({'id': user['company_id']})
    if not company or not verify_password(payload.current_password, company.get('password_hash', '')):
        raise HTTPException(400, "Senha atual da empresa incorreta")
    update = {}
    if payload.new_code:
        new_code = slugify(payload.new_code)
        if len(new_code) < 3:
            raise HTTPException(400, "Código muito curto (mínimo 3 caracteres)")
        other = await db.companies.find_one({'code': new_code, 'id': {'$ne': user['company_id']}})
        if other:
            raise HTTPException(400, "Código já em uso por outra empresa")
        update['code'] = new_code
    if payload.new_password:
        if len(payload.new_password) < 4:
            raise HTTPException(400, "Nova senha muito curta")
        update['password_hash'] = hash_password(payload.new_password)
    if not update:
        raise HTTPException(400, "Informe um novo código ou nova senha")
    await db.companies.update_one({'id': user['company_id']}, {'$set': update})
    return {'ok': True, 'code': update.get('code', company.get('code', ''))}


# ============ CLIENTS ============
@api_router.get("/clients", response_model=List[Client])
async def list_clients(user: dict = Depends(get_current_user)):
    rows = await db.clients.find({'company_id': user['company_id']}, {'_id': 0, 'company_id': 0}).to_list(5000)
    return rows


@api_router.post("/clients", response_model=Client)
async def create_client(payload: Client, user: dict = Depends(get_current_user)):
    if not payload.id:
        payload.id = str(uuid.uuid4())
    doc = payload.model_dump()
    doc['company_id'] = user['company_id']
    await db.clients.insert_one(dict(doc))
    doc.pop('company_id', None)
    return doc


@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, payload: Client, user: dict = Depends(get_current_user)):
    payload.id = client_id
    res = await db.clients.update_one(
        {'id': client_id, 'company_id': user['company_id']},
        {'$set': {**payload.model_dump(), 'company_id': user['company_id']}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Cliente não encontrado")
    return payload


@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, user: dict = Depends(get_current_user)):
    await db.clients.delete_one({'id': client_id, 'company_id': user['company_id']})
    return {'ok': True}


# ============ PRODUCTS ============
@api_router.get("/products", response_model=List[Product])
async def list_products(user: dict = Depends(get_current_user)):
    rows = await db.products.find({'company_id': user['company_id']}, {'_id': 0, 'company_id': 0}).to_list(10000)
    return rows


@api_router.post("/products", response_model=Product)
async def create_product(payload: Product, user: dict = Depends(get_current_user)):
    if not payload.id:
        payload.id = str(uuid.uuid4())
    exists = await db.products.find_one({'company_id': user['company_id'], 'code': payload.code})
    if exists:
        raise HTTPException(400, detail="Código de produto já existe")
    doc = payload.model_dump()
    doc['company_id'] = user['company_id']
    await db.products.insert_one(dict(doc))
    doc.pop('company_id', None)
    return doc


@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, payload: Product, user: dict = Depends(get_current_user)):
    payload.id = product_id
    await db.products.update_one(
        {'id': product_id, 'company_id': user['company_id']},
        {'$set': {**payload.model_dump(), 'company_id': user['company_id']}},
    )
    return payload


@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(get_current_user)):
    await db.products.delete_one({'id': product_id, 'company_id': user['company_id']})
    return {'ok': True}


# ============ DOCUMENTS ============
async def next_doc_number(company_id: str, doc_type: str) -> int:
    counter = await db.counters.find_one_and_update(
        {'company_id': company_id, 'doc_type': doc_type},
        {'$inc': {'value': 1}},
        upsert=True,
        return_document=True,
    )
    return counter['value'] if counter else 1


def _serialize_doc(doc: dict) -> dict:
    for key in ('created_at', 'valid_until'):
        if key in doc and isinstance(doc[key], datetime):
            doc[key] = doc[key].isoformat()
    return doc


def _doc_visibility_filter(user: dict) -> dict:
    """Vendedor sees only own documents; gerente/owner see everything in the company."""
    base = {'company_id': user['company_id']}
    if user.get('role') == 'vendedor':
        base['created_by'] = user['user_id']
    return base


@api_router.get("/documents")
async def list_documents(user: dict = Depends(get_current_user)):
    q = _doc_visibility_filter(user)
    rows = await db.documents.find(q, {'_id': 0, 'company_id': 0}).sort('created_at', -1).to_list(2000)
    client_ids = list({r['client_id'] for r in rows if r.get('client_id')})
    clients = {c['id']: c for c in await db.clients.find({'company_id': user['company_id'], 'id': {'$in': client_ids}}, {'_id': 0}).to_list(2000)}
    # created_by name map
    user_ids = list({r.get('created_by') for r in rows if r.get('created_by')})
    users = {u['user_id']: u for u in await db.users.find({'user_id': {'$in': user_ids}}, {'_id': 0, 'password_hash': 0}).to_list(200)}
    for r in rows:
        c = clients.get(r.get('client_id'), {})
        r['client_name'] = c.get('name', '—')
        creator = users.get(r.get('created_by'), {})
        r['created_by_name'] = creator.get('name', '')
        total = 0.0
        for line in r.get('lines', []):
            gross = float(line.get('quantity', 0)) * float(line.get('unit_price', 0))
            total += gross * (1 - float(line.get('discount_pct', 0)) / 100)
        r['total'] = round(total, 2)
    return rows


@api_router.post("/documents")
async def create_document(payload: DocumentIn, user: dict = Depends(get_current_user)):
    cli = await db.clients.find_one({'id': payload.client_id, 'company_id': user['company_id']})
    if not cli:
        raise HTTPException(400, detail="Cliente inválido")
    number = await next_doc_number(user['company_id'], payload.doc_type)
    now = datetime.now(timezone.utc)
    doc = Document(
        doc_type=payload.doc_type,
        number=number,
        client_id=payload.client_id,
        lines=payload.lines,
        payments=payload.payments,
        notes=payload.notes,
        created_at=now,
        valid_until=(now + timedelta(hours=72)) if payload.doc_type == 'orcamento' else None,
        created_by=user['user_id'],
    ).model_dump()
    doc['company_id'] = user['company_id']
    doc = _serialize_doc(doc)

    company = await get_company_of_user(user)
    if company.get('stock_enabled') and payload.doc_type == 'venda':
        for line in payload.lines:
            if line.product_id:
                await db.products.update_one(
                    {'id': line.product_id, 'company_id': user['company_id']},
                    {'$inc': {'stock': -float(line.quantity)}},
                )
    await db.documents.insert_one(dict(doc))
    doc.pop('company_id', None)
    return doc


@api_router.get("/documents/{doc_id}")
async def get_document(doc_id: str, user: dict = Depends(get_current_user)):
    q = {**_doc_visibility_filter(user), 'id': doc_id}
    doc = await db.documents.find_one(q, {'_id': 0, 'company_id': 0})
    if not doc:
        raise HTTPException(404, "Documento não encontrado")
    return doc


@api_router.put("/documents/{doc_id}")
async def update_document(doc_id: str, payload: DocumentUpdate, user: dict = Depends(get_current_user)):
    q = {**_doc_visibility_filter(user), 'id': doc_id}
    doc = await db.documents.find_one(q, {'_id': 0})
    if not doc:
        raise HTTPException(404, "Documento não encontrado")
    update = {}
    if payload.client_id is not None:
        cli = await db.clients.find_one({'id': payload.client_id, 'company_id': user['company_id']})
        if not cli:
            raise HTTPException(400, "Cliente inválido")
        update['client_id'] = payload.client_id
    if payload.lines is not None:
        update['lines'] = [l.model_dump() for l in payload.lines]
    if payload.payments is not None:
        update['payments'] = [p.model_dump() for p in payload.payments]
    if payload.notes is not None:
        update['notes'] = payload.notes
    if update:
        await db.documents.update_one({'id': doc_id, 'company_id': user['company_id']}, {'$set': update})
    updated = await db.documents.find_one({'id': doc_id, 'company_id': user['company_id']}, {'_id': 0, 'company_id': 0})
    return updated


@api_router.post("/documents/{doc_id}/convert")
async def convert_document(doc_id: str, user: dict = Depends(get_current_user)):
    q = {**_doc_visibility_filter(user), 'id': doc_id}
    src = await db.documents.find_one(q, {'_id': 0})
    if not src:
        raise HTTPException(404, "Orçamento não encontrado")
    if src['doc_type'] != 'orcamento':
        raise HTTPException(400, "Só orçamentos podem ser convertidos")
    number = await next_doc_number(user['company_id'], 'venda')
    now = datetime.now(timezone.utc)
    new_doc = {
        'id': str(uuid.uuid4()),
        'doc_type': 'venda',
        'number': number,
        'client_id': src['client_id'],
        'lines': src.get('lines', []),
        'payments': src.get('payments', []),
        'notes': src.get('notes', ''),
        'created_at': now.isoformat(),
        'valid_until': None,
        'converted_from': src['id'],
        'status': 'ativo',
        'company_id': user['company_id'],
        'created_by': user['user_id'],
    }
    company = await get_company_of_user(user)
    if company.get('stock_enabled'):
        for line in src.get('lines', []):
            if line.get('product_id'):
                await db.products.update_one(
                    {'id': line['product_id'], 'company_id': user['company_id']},
                    {'$inc': {'stock': -float(line.get('quantity', 0))}},
                )
    await db.documents.insert_one(dict(new_doc))
    new_doc.pop('company_id', None)
    return new_doc


@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    q = {**_doc_visibility_filter(user), 'id': doc_id}
    await db.documents.delete_one(q)
    return {'ok': True}


# ============ PDF ============
def _fmt_money(v: float) -> str:
    return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _build_pdf(doc: dict, company: dict, client: dict) -> BytesIO:
    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.2*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle('t', parent=styles['Heading1'], fontSize=20, textColor=DARK, spaceAfter=0, leading=24)
    small = ParagraphStyle('s', parent=styles['Normal'], fontSize=9, textColor=GRAY, leading=12)
    body = ParagraphStyle('b', parent=styles['Normal'], fontSize=10, textColor=DARK, leading=13)
    label = ParagraphStyle('l', parent=styles['Normal'], fontSize=8, textColor=GRAY, leading=10)
    doc_title = ParagraphStyle('dt', parent=styles['Heading2'], fontSize=14, textColor=ORANGE, spaceAfter=0)

    story = []
    header_left = []
    if company.get('logo_data_url', '').startswith('data:image'):
        try:
            import base64
            b64 = company['logo_data_url'].split(',', 1)[1]
            img_buf = BytesIO(base64.b64decode(b64))
            header_left.append(Image(img_buf, width=3.5*cm, height=3.5*cm, kind='proportional'))
        except Exception:
            header_left.append(Paragraph(f"<b>{company.get('name', '')}</b>", title))
    else:
        header_left.append(Paragraph(f"<b>{company.get('name') or 'Sua Empresa'}</b>", title))

    header_left.append(Spacer(1, 4))
    header_left.append(Paragraph(f"CNPJ: {company.get('cnpj', '—')}", small))
    if company.get('ie'):
        header_left.append(Paragraph(f"IE: {company['ie']}", small))
    header_left.append(Paragraph(company.get('address', ''), small))
    header_left.append(Paragraph(f"Tel: {company.get('phone', '')}   {company.get('email', '')}", small))

    doc_type_label = 'ORÇAMENTO' if doc['doc_type'] == 'orcamento' else 'VENDA'
    header_right = []
    header_right.append(Paragraph(f"<b>{doc_type_label}</b>", doc_title))
    header_right.append(Paragraph(f"Nº {doc['number']:06d}", body))
    created = doc['created_at']
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    header_right.append(Paragraph(f"Emissão: {created.strftime('%d/%m/%Y %H:%M')}", small))
    if doc.get('valid_until'):
        vu = doc['valid_until']
        if isinstance(vu, str):
            vu = datetime.fromisoformat(vu)
        header_right.append(Paragraph(f"Validade: {vu.strftime('%d/%m/%Y %H:%M')}", small))

    header_table = Table([[header_left, header_right]], colWidths=[11*cm, 6.5*cm])
    header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    sep = Table([['']], colWidths=[18*cm], rowHeights=[3])
    sep.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), ORANGE)]))
    story.append(sep)
    story.append(Spacer(1, 14))

    story.append(Paragraph("CLIENTE", label))
    story.append(Spacer(1, 4))
    parts = []
    if client.get('street'):
        s = client['street']
        if client.get('number'): s += f", {client['number']}"
        if client.get('complement'): s += f" — {client['complement']}"
        parts.append(s)
    if client.get('district'): parts.append(client['district'])
    if client.get('city'):
        parts.append(f"{client['city']}/{client.get('state','')}" if client.get('state') else client['city'])
    if client.get('cep'): parts.append(f"CEP {client['cep']}")
    full_address = " · ".join(parts) if parts else (client.get('address') or '—')
    client_rows = [
        [Paragraph("<b>Nome</b>", small), Paragraph(client.get('name', '—'), body),
         Paragraph("<b>Documento</b>", small), Paragraph(client.get('document', '—'), body)],
        [Paragraph("<b>Endereço</b>", small), Paragraph(full_address, body),
         Paragraph("<b>Telefone</b>", small), Paragraph(client.get('phone', '—'), body)],
        [Paragraph("<b>Email</b>", small), Paragraph(client.get('email', '—'), body),
         Paragraph("<b>IE</b>", small), Paragraph(client.get('ie', '—'), body)],
    ]
    ct = Table(client_rows, colWidths=[2.5*cm, 7*cm, 2.5*cm, 6*cm])
    ct.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#E4E4E7')),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#E4E4E7')),
    ]))
    story.append(ct)
    story.append(Spacer(1, 14))

    header_row = ['Cód.', 'Descrição', 'Qtd.', 'Valor Unit.', 'Bruto', 'Líquido']
    lines = doc.get('lines', [])
    total_gross = 0.0
    total_disc = 0.0
    total_net = 0.0
    data = [header_row]
    for line in lines:
        qty = float(line.get('quantity', 0))
        price = float(line.get('unit_price', 0))
        disc = float(line.get('discount_pct', 0))
        gross = qty * price
        net = gross * (1 - disc / 100)
        disc_val = gross - net
        total_gross += gross
        total_disc += disc_val
        total_net += net
        data.append([
            line.get('code', '') or '—',
            line.get('description', '') or '',
            f"{qty:g}",
            _fmt_money(price),
            _fmt_money(gross),
            _fmt_money(net),
        ])
    table = Table(data, colWidths=[1.8*cm, 7.4*cm, 1.8*cm, 2.6*cm, 2.5*cm, 2.5*cm], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), DARK),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('LINEBELOW', (0, 0), (-1, 0), 1, ORANGE),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))

    totals_data = [
        ['Subtotal Bruto', _fmt_money(total_gross)],
        ['Desconto Total', f"- {_fmt_money(total_disc)}"],
        ['TOTAL LÍQUIDO', _fmt_money(total_net)],
    ]
    tot = Table(totals_data, colWidths=[10*cm, 4.5*cm])
    tot.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, 1), GRAY),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, 2), 13),
        ('TEXTCOLOR', (0, 2), (-1, 2), DARK),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#FDF0EC')),
        ('LINEABOVE', (0, 2), (-1, 2), 1.5, ORANGE),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    wrap = Table([['', tot]], colWidths=[3*cm, 14.5*cm])
    wrap.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(wrap)

    if doc.get('notes'):
        story.append(Spacer(1, 16))
        story.append(Paragraph("OBSERVAÇÕES", label))
        story.append(Paragraph(doc['notes'], body))

    if doc.get('payments'):
        story.append(Spacer(1, 14))
        story.append(Paragraph("CONDIÇÕES DE PAGAMENTO", label))
        story.append(Spacer(1, 4))
        method_labels = {'pix': 'PIX', 'dinheiro': 'Dinheiro', 'credito': 'Cartão de Crédito', 'debito': 'Cartão de Débito', 'boleto': 'Boleto', 'transferencia': 'Transferência'}
        pay_data = []
        for p in doc['payments']:
            m = method_labels.get(p.get('method', ''), p.get('method', ''))
            amount = float(p.get('amount', 0))
            inst = int(p.get('installments', 1) or 1)
            detail = ''
            if p.get('method') == 'credito' and inst > 1:
                per = amount / inst
                detail = f" · {inst}x de {_fmt_money(per)}"
            pay_data.append([Paragraph(m, body), Paragraph(_fmt_money(amount) + detail, body)])
        pay_table = Table(pay_data, colWidths=[10*cm, 7.5*cm])
        pay_table.setStyle(TableStyle([
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#E4E4E7')),
        ]))
        story.append(pay_table)

    story.append(Spacer(1, 24))
    footer = Paragraph(f"<font color='#A1A1AA'>Documento gerado por Gestor360 · {datetime.now(timezone.utc).strftime('%d/%m/%Y')}</font>", small)
    story.append(footer)

    pdf.build(story)
    buf.seek(0)
    return buf


@api_router.get("/documents/{doc_id}/pdf")
async def get_document_pdf(doc_id: str, user: dict = Depends(get_current_user)):
    q = {**_doc_visibility_filter(user), 'id': doc_id}
    doc = await db.documents.find_one(q, {'_id': 0})
    if not doc:
        raise HTTPException(404)
    company = await get_company_of_user(user)
    client = await db.clients.find_one({'id': doc['client_id'], 'company_id': user['company_id']}, {'_id': 0}) or {}
    buf = _build_pdf(doc, company, client)
    filename = f"{'orcamento' if doc['doc_type'] == 'orcamento' else 'venda'}_{doc['number']:06d}.pdf"
    return StreamingResponse(buf, media_type='application/pdf', headers={'Content-Disposition': f'inline; filename="{filename}"'})


# ============ STATS ============
@api_router.get("/stats")
async def stats(user: dict = Depends(get_current_user)):
    base_cli = {'company_id': user['company_id']}
    doc_filter = _doc_visibility_filter(user)
    clients_count = await db.clients.count_documents(base_cli)
    products_count = await db.products.count_documents(base_cli)
    orc_count = await db.documents.count_documents({**doc_filter, 'doc_type': 'orcamento'})
    ven_count = await db.documents.count_documents({**doc_filter, 'doc_type': 'venda'})
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()
    sales = await db.documents.find({**doc_filter, 'doc_type': 'venda', 'created_at': {'$gte': month_start}}, {'_id': 0}).to_list(5000)
    revenue = 0.0
    for s in sales:
        for line in s.get('lines', []):
            gross = float(line.get('quantity', 0)) * float(line.get('unit_price', 0))
            revenue += gross * (1 - float(line.get('discount_pct', 0)) / 100)
    return {
        'clients': clients_count,
        'products': products_count,
        'orcamentos': orc_count,
        'vendas': ven_count,
        'revenue_month': round(revenue, 2),
        'scope': 'own' if user.get('role') == 'vendedor' else 'company',
    }


@api_router.get("/")
async def root():
    return {'app': 'Gestor360', 'ok': True}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def migrate_and_seed():
    """Migrate v1 (single-tenant per user) to v2 (multi-user per company)."""
    # 1) Migrate legacy company docs (user_id scoped, no 'id' field)
    async for old_comp in db.companies.find({'code': {'$exists': False}}):
        user_id = old_comp.get('user_id')
        if not user_id:
            continue
        company_id = str(uuid.uuid4())
        old_user = await db.users.find_one({'user_id': user_id})
        company_name = (old_user.get('name', '') if old_user else '') + " — Empresa"
        await db.companies.update_one(
            {'_id': old_comp['_id']},
            {
                '$set': {
                    'id': company_id,
                    'owner_id': user_id,
                    'code': '',
                    'password_hash': '',
                    'ie': old_comp.get('ie', ''),
                    'pending_setup': True,
                    'name': old_comp.get('name') or company_name,
                },
                '$unset': {'user_id': ''},
            },
        )
        await db.users.update_one(
            {'user_id': user_id},
            {'$set': {
                'company_id': company_id, 'role': 'owner',
                'username': 'admin', 'must_change_password': False,
            }},
        )
        await db.clients.update_many({'user_id': user_id}, {'$set': {'company_id': company_id}, '$unset': {'user_id': ''}})
        await db.products.update_many({'user_id': user_id}, {'$set': {'company_id': company_id}, '$unset': {'user_id': ''}})
        await db.documents.update_many({'user_id': user_id}, {'$set': {'company_id': company_id, 'created_by': user_id}, '$unset': {'user_id': ''}})
        await db.counters.update_many({'user_id': user_id}, {'$set': {'company_id': company_id}, '$unset': {'user_id': ''}})
        logger.info(f"Migrated v1 → v2 for user {user_id} → company {company_id}")

    # 2) Seed owner if missing
    owner_email = 'netozincaovendas@gmail.com'
    existing = await db.users.find_one({'email': owner_email})
    if not existing:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        company_id = str(uuid.uuid4())
        await db.companies.insert_one({
            'id': company_id, 'code': '', 'password_hash': '', 'owner_id': user_id,
            'name': 'Gestor360', 'cnpj': '', 'ie': '', 'address': '',
            'phone': '', 'email': owner_email, 'logo_data_url': '',
            'stock_enabled': False, 'pending_setup': True,
        })
        await db.users.insert_one({
            'user_id': user_id, 'company_id': company_id,
            'email': owner_email, 'name': 'Neto', 'username': 'admin',
            'password_hash': hash_password('Gestor360!'),
            'auth_provider': 'email', 'role': 'owner',
            'must_change_password': False,
            'created_at': datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Seeded owner {owner_email}")
    else:
        # Ensure the seeded user has role/username/company after migration
        upd = {}
        if not existing.get('role'): upd['role'] = 'owner'
        if not existing.get('username'): upd['username'] = 'admin'
        if upd:
            await db.users.update_one({'user_id': existing['user_id']}, {'$set': upd})

    # 3) Fallback: any user without a company gets one (pending setup)
    async for u in db.users.find({'company_id': {'$exists': False}}):
        company_id = str(uuid.uuid4())
        await db.companies.insert_one({
            'id': company_id, 'code': '', 'password_hash': '', 'owner_id': u['user_id'],
            'name': u.get('name', 'Minha Empresa'), 'cnpj': '', 'ie': '',
            'address': '', 'phone': '', 'email': u.get('email', ''),
            'logo_data_url': '', 'stock_enabled': False, 'pending_setup': True,
        })
        await db.users.update_one({'user_id': u['user_id']}, {'$set': {
            'company_id': company_id, 'role': 'owner', 'username': u.get('username', 'admin'),
        }})


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
