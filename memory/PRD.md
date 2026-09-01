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
- **Dono (owner)**: acesso total, gerencia equipe e empresa, único que pode Google-login
- **Gerente (gerente)**: vê tudo da empresa; gerencia clientes/produtos/documentos
- **Vendedor (vendedor)**: só vê os próprios documentos; compartilha clientes/produtos

## Fluxo de login (v2)
1. `/login/company` — código + senha da empresa
2. `/login/user` — escolhe usuário + senha
3. Dono pode entrar direto em `/login/owner` (email/senha ou Google)
4. Primeiro acesso: `/change-password` obrigatório se `must_change_password`
5. Dono pós-onboarding: `/setup` para definir código e senha da empresa

## Implementado
- ✅ Multi-tenancy (Company + User models; migração v1→v2 no startup)
- ✅ Autenticação em duas etapas + fallback owner (email/Google)
- ✅ Setup wizard (`/setup`)
- ✅ Troca de senha obrigatória
- ✅ CRUD Equipe (`/equipe`, owner only)
- ✅ Filtro por papel: vendedor só vê próprios documentos e stats
- ✅ Escopo por company_id em clients/products/documents/counters
- ✅ Cliente com endereço estruturado + CEP + IE
- ✅ Empresa com IE
- ✅ Orçamento/Venda com aba Pagamento (PIX, dinheiro, crédito 1x-12x, débito, boleto, transferência)
- ✅ Edição de documento (`/orcamento?id=…`)
- ✅ Busca de produto por código OU descrição (dropdown startsWith)
- ✅ Auto-desconto ao editar valor abaixo do preço de tabela
- ✅ PDF sem % de desconto (só valor)
- ✅ Conversão orçamento→venda com payments
- ✅ Baixa de estoque em vendas quando estoque ativado

## Backlog (P1)
- Duplicar documento
- WhatsApp share do PDF
- Dashboard comparativo (owner/gerente): vendedores × metas
- Aprovação de descontos acima de X%
- Nome do cliente no filename do PDF

## Backlog (P2)
- Multi-empresa por usuário
- Assinatura digital
- Comissão de vendedores
- Integração fiscal (NFe)

## Test credentials
Ver `/app/memory/test_credentials.md`
