# Gestor360 — Test Credentials (v2 multi-tenant)

## Owner (semeado no startup)
- Email: `netozincaovendas@gmail.com`
- Senha: `Gestor360!`
- Papel: **owner** (Dono)
- Auth: `POST /api/auth/owner-login` (email/senha) OU Google OAuth (Emergent)
- **Após primeiro login, o owner é levado a `/setup` para definir código + senha da empresa**

## Login em duas etapas (para todos após setup completo)
1. `POST /api/auth/company-login` — `{code, password}` → seta cookie `company_session` + retorna `{company, users}`
2. `POST /api/auth/user-login` — `{username, password}` (com cookie `company_session`) → retorna `{user, token, must_change_password}`

## Endpoints principais
- `POST /api/auth/setup-company` — owner define `code`, `password`, `name`
- `GET /api/auth/lookup-company?code=XXX` — público, retorna nome
- `POST /api/auth/change-password` — troca senha (obrigatório em primeiro acesso)
- `GET/POST/PUT/DELETE /api/users` — CRUD equipe (owner only)

## Vendedor (role=vendedor)
- Vê apenas documentos criados por ele (`created_by == user_id`)
- Sem acesso a Finanças, Equipe, Empresa (editar)
- Compartilha clientes e produtos com a empresa toda

## Gerente (role=gerente)
- Vê todos os documentos
- Gerencia clientes e produtos
- Pode ver/editar Empresa
- Não gerencia usuários (Equipe)

## Papéis (Role)
- `owner` · `gerente` · `vendedor`
