# Gestor360

ERP multi-tenant (Owner / Gerente / Vendedor) para orçamentos, vendas e PDF profissional.
**Stack:** React 19 + Vite (frontend) · FastAPI + asyncpg (backend) · Supabase PostgreSQL (banco) · JWT customizado (auth 2-step).

---

## 1) Criar o projeto Supabase

1. https://supabase.com/dashboard → **New project**
2. Região: `South America (São Paulo)`
3. Defina uma **Database password** forte (você vai precisar dela)
4. Depois de criado, vá em **SQL Editor → New query**, cole todo o conteúdo de `backend/schema.sql` e execute (**Run**). Vai criar:
   - Tabelas: `companies`, `users`, `clients`, `products`, `documents`, `counters`
   - Todas com **Row Level Security** habilitada (bloqueio total para anon/authenticated)
   - Função `next_doc_number()` para numeração atômica de documentos
5. Vá em **Project Settings → API** e anote:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role secret` key → `SUPABASE_SERVICE_ROLE_KEY` (**NUNCA expor no frontend**)
6. **Project Settings → Database → Connection string → URI (Transaction pooler)**
   - Copie a string, substitua `[YOUR-PASSWORD]` pela senha do banco → `SUPABASE_DB_URL`

## 2) Backend (Render)

1. https://render.com → **New Web Service** → conecte o repositório
2. Configuração:
   - **Root Directory:** `backend`
   - **Environment:** `Python 3`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
3. **Environment** tab — adicione as variáveis (baseado em `backend/.env.example`):
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_DB_URL` ← **usar o Transaction pooler (porta 6543)**
   - `JWT_SECRET` (gere com `openssl rand -hex 48`)
   - `FRONTEND_URL` = URL público do frontend Vercel (sem barra no final)
   - (opcional) `SEED_OWNER_EMAIL` / `SEED_OWNER_NAME` / `SEED_OWNER_PASSWORD` — cria o primeiro dono no primeiro startup
4. Deploy. Aguarde `Build successful`. A URL final (ex.: `https://gestor360-api.onrender.com`) vai para o frontend.

## 3) Frontend (Vercel)

1. https://vercel.com → **Add New Project** → conecte o mesmo repositório
2. Configuração:
   - **Root Directory:** `frontend`
   - **Framework Preset:** `Vite` (autodetect)
   - **Build Command:** `yarn build`
   - **Output Directory:** `build`
3. **Environment Variables** — adicione (baseado em `frontend/.env.example`):
   - `REACT_APP_BACKEND_URL` = URL do Render (ex.: `https://gestor360-api.onrender.com`)
4. Deploy. Após o build, copie o URL público (ex.: `https://gestor360.vercel.app`).
5. Volte ao Render → atualize `FRONTEND_URL` com esse valor e redeploy o backend (necessário para CORS).

## 4) Primeiro acesso

- Se você **configurou** `SEED_OWNER_*` no Render, use essas credenciais em `/login/owner`.
- Se não, use `/login/owner` → clique em "Registrar" (usa `POST /api/auth/register`).
- Depois do primeiro login o dono é levado para `/setup`, onde define o **código** e a **senha da empresa** que os outros usuários (gerente/vendedor) usarão na Etapa 1 do login.

---

## Arquitetura

```
┌─────────────────┐   HTTPS  ┌────────────────────┐    asyncpg   ┌─────────────────┐
│  Vite frontend  │ ───────► │  FastAPI backend   │ ───────────► │ Supabase Postgres │
│  (Vercel)       │  JWT +   │  (Render)          │  service-role│ (multi-tenant)  │
│  jsPDF PDFs     │  cookies │  bcrypt · JWT 2step│              │  RLS defensiva  │
└─────────────────┘          └────────────────────┘              └─────────────────┘
```

### Multi-tenancy
- Cada `users.company_id` amarra o usuário à sua empresa.
- **Backend enforce**: toda query passa `WHERE company_id = $1`.
- **Postgres enforce**: RLS habilitada + forçada em todas as tabelas, com política restritiva `USING (false)` para `anon` e `authenticated` — se algum dia a `anon_key` vazar, nada volta.
- O backend usa a `service_role` connection, que bypassa RLS. É o único jeito legítimo de ler dados.

### PDF
- Gerado 100% no browser com **jsPDF** (`src/lib/pdf.js`).
- Layout preserva o visual do ReportLab: cabeçalho da empresa (com logo), tabela dark header + zebra, totais com destaque laranja, condições de pagamento com vencimentos de boleto.
- Timezone é do próprio browser — nada de query param.

### Auth
- Login em duas etapas:
  1. `POST /api/auth/company-login` → cookie `company_session` (30 min)
  2. `POST /api/auth/user-login` → cookie `jwt_token` (7 dias) + token no body (usado pelo interceptor axios)
- Dono pode entrar direto em `/login/owner` (email/senha, sem código de empresa).
- Papéis: **owner** (tudo), **gerente** (tudo exceto Team/change-credentials), **vendedor** (só vê próprios documentos, não vê `cost_price`).

## Desenvolvimento local

```bash
# Backend
cd backend
cp .env.example .env         # preencha SUPABASE_* + JWT_SECRET
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend
cp .env.example .env         # REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
yarn dev                     # http://localhost:3000
```

## Segurança

- `SUPABASE_SERVICE_ROLE_KEY` **nunca** vai para o frontend nem para o Git — só existe no Render.
- `JWT_SECRET` idem — gere um forte com `openssl rand -hex 48`.
- CORS restrito a `FRONTEND_URL` + localhost em dev.
- Senhas em `bcrypt`.
- Isolamento entre empresas garantido por `WHERE company_id = $1` em **todas** as queries + RLS defensiva.
