# Gestor360 — PRD (v3 · Supabase + Vercel)

## Missão
ERP multi-tenant para pequenas/médias empresas. Cadastro de clientes/produtos, orçamento/venda tipo planilha, PDF profissional. Multi-usuário por empresa com papéis (Dono/Gerente/Vendedor).

## Stack (Feb 2026)
- **Frontend**: Vite + React 19 + JavaScript + Tailwind + shadcn/ui + React Router + Axios + jsPDF
- **Backend**: FastAPI + asyncpg (Python 3.11)
- **Banco**: Supabase PostgreSQL (multi-tenant com RLS defensiva + service_role no backend)
- **Deploy**: Vercel (frontend) + Render (backend)
- **Auth**: JWT customizado 2-step (código empresa + user/senha), bcrypt

## Migração v2 (Mongo/CRA) → v3 (Supabase/Vite) — Feb 2026
- ✅ Backend reescrito com asyncpg (`server.py` + `db.py`)
- ✅ `schema.sql` completo com 6 tabelas + RLS FORCE + política `USING (false)` para anon/authenticated
- ✅ Frontend migrado CRA/Craco → Vite 5 (`vite.config.js`, `main.jsx`, `index.html` na raiz)
- ✅ PDF migrado ReportLab (Python) → jsPDF (browser) em `src/lib/pdf.js`, preservando layout
- ✅ Auth 2-step preservada (cookies + JWT no header)
- ✅ CORS restrito por `FRONTEND_URL`
- ✅ Removido: Motor, PyMongo, reportlab, emergentintegrations, litellm, craco, @emergentbase/visual-edits
- ✅ `.env.example` (backend + frontend) sem credenciais reais
- ✅ `vercel.json` + `render.yaml` prontos para deploy
- ✅ README com passo-a-passo Supabase + Render + Vercel

## Fluxo de login (mantido)
1. `/login/company` — código + senha da empresa (POST `/api/auth/company-login`, seta cookie `company_session` 30min)
2. `/login/user` — escolhe usuário + senha (POST `/api/auth/user-login`, seta cookie `jwt_token` 7d)
3. Dono pode entrar direto em `/login/owner` (email/senha)
4. Primeiro acesso: `/change-password` obrigatório se `must_change_password`
5. Dono pós-onboarding: `/setup` para definir código e senha da empresa

## Multi-tenancy
- **Camada 1 (backend)**: toda query passa `WHERE company_id = $1`. Vendedor recebe também `AND created_by = $2`.
- **Camada 2 (Postgres)**: RLS habilitada + forçada em todas as 6 tabelas com política `USING (false)` para `anon` e `authenticated`. Backend usa `service_role` DSN (bypassa RLS).
- Isolamento entre empresas garantido em duas camadas — se a `anon_key` vazar, ninguém lê nada.

## Papéis
- **owner**: acesso total, gerencia equipe e credenciais da empresa
- **gerente**: vê tudo; gerencia clientes/produtos/documentos + empresa (sem trocar credenciais)
- **vendedor**: só vê os próprios documentos; não vê `cost_price` de produtos

## Endpoints REST (25+)
Auth: `/auth/register`, `/auth/owner-login`, `/auth/company-login`, `/auth/user-login`, `/auth/setup-company`, `/auth/lookup-company`, `/auth/me`, `/auth/change-password`, `/auth/logout`
Team: `GET/POST /users`, `PUT/DELETE /users/:id`
Company: `GET/PUT /company`, `POST /company/change-credentials`
Data: `GET/POST /clients`, `PUT/DELETE /clients/:id`; idem `/products`; idem `/documents` + `POST /documents/:id/convert`
Stats: `GET /stats`
Health: `GET /`

## Schema (schema.sql)
- `companies` (id UUID PK, code UNIQUE, password_hash, owner_id, name, cnpj, ie, address, phone, email, logo_data_url, stock_enabled, pending_setup)
- `users` (user_id TEXT PK, company_id FK, email, name, username, password_hash, role CHECK, picture, must_change_password)
- `clients` (id UUID PK, company_id FK, todos os campos de endereço estruturado)
- `products` (id UUID PK, company_id FK, code UNIQUE por empresa, description, price, cost_price, stock, unit)
- `documents` (id UUID PK, company_id FK, doc_type CHECK, number, client_id FK, lines JSONB, payments JSONB, global_discount_pct/amount, notes, created_at, valid_until, converted_from, status, created_by)
- `counters` (company_id, doc_type) — PK composta, incrementada via função `next_doc_number()` SECURITY DEFINER

## Variáveis a configurar em produção
- **Supabase**: rodar `schema.sql` no SQL Editor
- **Render** (backend): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`, `JWT_SECRET`, `FRONTEND_URL`, `SEED_OWNER_*` (opcional)
- **Vercel** (frontend): `REACT_APP_BACKEND_URL`

## Backlog (P1/P2 — mantidos da v2)
- Aprovação de descontos (>10% pede aprovação do gerente)
- Comissão de vendedores + dashboard comparativo
- Multi-empresa por usuário (hoje 1:1 estrito)
- Substituir localStorage por httpOnly cookies (defense-in-depth extra — cookies já existem)

## Notas importantes
- MongoDB Atlas continua rodando como backup — não excluir até validação completa em produção.
- Dados de teste podem ser recriados do zero via UI depois que a empresa for setupada.
