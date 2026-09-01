# Gestor360 — PRD (v2 multi-tenant)

## Missão
Sistema de gestão ERP para pequenas/médias empresas. Cadastro de clientes e produtos, montagem de orçamentos/vendas tipo planilha, PDF profissional. Multi-usuário por empresa com papéis (Dono/Gerente/Vendedor).

## Stack
- Frontend: React 19 + shadcn/ui + tailwind + framer-motion + sonner + react-router-dom
- Backend: FastAPI + Motor (MongoDB) + bcrypt + PyJWT + reportlab
- Integrações: ViaCEP (endereço), BrasilAPI (CNPJ). Emergent Google OAuth REMOVIDO (deploy externo Render/Vercel usa apenas JWT email+senha).

## Deploy externo (Render/Vercel)
- `emergentintegrations==0.2.0` removido de `backend/requirements.txt` (Feb 2026)
- `litellm` (pinada em URL do domínio emergentagent.com, não usada no código) removida (Feb 2026)
- Backend agora zero dependências Emergent — pronto para `pip install -r requirements.txt` no Render

## Users
- **Dono (owner)**: acesso total, gerencia equipe e empresa
- **Gerente (gerente)**: vê tudo da empresa; gerencia clientes/produtos/documentos
- **Vendedor (vendedor)**: só vê os próprios documentos; compartilha clientes/produtos

## Fluxo de login (v2)
1. `/login/company` — código + senha da empresa
2. `/login/user` — escolhe usuário + senha
3. Dono pode entrar direto em `/login/owner` (email/senha)
4. Primeiro acesso: `/change-password` obrigatório se `must_change_password`
5. Dono pós-onboarding: `/setup` para definir código e senha da empresa

## Implementado
- ✅ Multi-tenancy (Company + User models)
- ✅ Autenticação em duas etapas + fallback owner (email/senha)
- ✅ Setup wizard (`/setup`) e troca de senha obrigatória
- ✅ CRUD Equipe (`/equipe`, owner only)
- ✅ Filtro por papel: vendedor só vê próprios documentos e stats
- ✅ Escopo por company_id em clients/products/documents/counters
- ✅ Cliente com endereço estruturado + CEP + IE + lookup CNPJ (BrasilAPI)
- ✅ Empresa com IE
- ✅ Orçamento/Venda com aba Pagamento (PIX, dinheiro, crédito 1x-12x, débito, boleto customizado, transferência)
- ✅ Descontos global (%) e valor fixo, arredondamento de total
- ✅ Edição de documento (`/orcamento?id=…`)
- ✅ Busca de produto por código OU descrição
- ✅ Auto-desconto ao editar valor abaixo do preço de tabela
- ✅ PDF localizado por timezone do usuário (via `Intl.DateTimeFormat`)
- ✅ Conversão orçamento→venda com payments
- ✅ Baixa de estoque em vendas quando estoque ativado
- ✅ Header com geolocalização (cidade/UF)
- ✅ Sidebar mobile auto-close ao navegar

## Code Quality — Onda 1 (Feb 2026)
- ✅ `test_iteration6.py`: credenciais de teste movidas para env vars (`TEST_COMPANY_CODE`, `TEST_COMPANY_PW`, `TEST_COMPANY_NAME`)
- ✅ Trocado `is True/False` por `== True/False` em test_iteration4/5/6/7
- ✅ `AuthContext.js`: funções envolvidas em `useCallback`, `value` em `useMemo`, catches vazios agora logam erros
- ✅ `Team.jsx`, `Documents.jsx`, `Clients.jsx`: `load` envolvido em `useCallback` + incluído em deps do useEffect
- ✅ `Layout.jsx`: catch vazio do reverse geocoding agora loga erro
- ✅ `QuoteBuilder.jsx`: chaves estáveis via `crypto.randomUUID()` para lines/payments; ternários aninhados extraídos para `remainingClass()` e `saveButtonLabel()`
- ✅ `craco.config.js`: `console.warn` de visual-edits removido (silent skip)

## Backlog (Onda 2 — refactors grandes, adiados)
- 🟠 P1: Aprovação de descontos (fluxo vendedor→gerente para >10%)
- 🟡 P2: Comissão de vendedores + dashboard comparativo
- 🟡 P2: Multi-empresa por usuário
- 🔵 Refactor: quebrar `_build_pdf()` (204 linhas) em helpers menores
- 🔵 Refactor: quebrar `QuoteBuilder` (562 linhas) em `QuoteForm/ProductSelector/LineItemsTable/QuoteSummary`
- 🔵 Refactor: quebrar `Clients` (261 linhas) em `ClientList/ClientForm/ClientFilters`
- 🔵 Refactor: extrair `useWeather()` de `Layout`
- 🔵 Refactor: quebrar `server.py` em routers FastAPI (auth, clients, products, documents, pdf)
- 🔵 Security: migrar JWT de localStorage para httpOnly cookies (grande refactor: backend seta cookies, CSRF, frontend)

## Test coverage
- `/app/backend/tests/test_iteration4..8.py` — suíte pytest cobrindo auth 2-step, RBAC, CRUD, PDF, migrations
- Falha conhecida: `test_iteration4::test_oauth_bad_session` — testa endpoint `/api/auth/session` removido junto com Emergent OAuth. Não é regressão.
