# Gestor360 — Product Requirements Document

## Original Problem
Sistema de gestão web em português. Tela inicial com "Olá, [nome]" + data + local + hora. Barra de navegação para clientes, produtos, orçamentos e vendas. Orçamento e venda funcionam como planilha (código, descrição, quantidade, valor, desconto %), Enter pula para próxima coluna/linha. Geração de PDF profissional com cabeçalho da empresa, dados do cliente e tabela com valores bruto/desconto/líquido. Cores: branco com detalhes laranja. Nome: Gestor360.

## Users
- **Owner**: netozincaovendas@gmail.com (seeded)
- Futuramente: distribuir a grandes empresas (multi-tenant já pronto — cada usuário isolado)

## Stack
- Frontend: React 19 + shadcn/ui + tailwind + framer-motion + sonner + react-router-dom
- Backend: FastAPI + Motor (Mongo) + bcrypt + PyJWT + reportlab (PDF)
- Auth: JWT + Emergent Google OAuth (both supported)

## Implemented (2026-08-31)
- ✅ Login/Register JWT + Google OAuth (Emergent)
- ✅ Sticky header com Olá + data + hora + geolocalização (reverse geocode)
- ✅ Sidebar responsivo (drawer no mobile)
- ✅ Cadastro de clientes (CRUD, busca)
- ✅ Cadastro de produtos (CRUD, código único, unidade, preço, estoque opcional)
- ✅ Configuração da empresa (nome, CNPJ, endereço, telefone, email, logo upload, toggle estoque)
- ✅ Novo Documento (orçamento/venda) tipo planilha com Enter navigation e datalist de produtos
- ✅ Lista de documentos com filtros (todos/orçamento/venda)
- ✅ Conversão orçamento → venda (novo número sequencial)
- ✅ Numeração automática (contador por usuário/tipo)
- ✅ Validade 72h para orçamentos com indicador "Expirado"
- ✅ PDF profissional (reportlab) com logo, cabeçalho, cliente, tabela e totais
- ✅ Baixa automática de estoque em vendas quando estoque ativo
- ✅ Dashboard com estatísticas e receita do mês

## Backlog (P1)
- Duplicar documento
- Envio direto do PDF por email/WhatsApp
- Formas de pagamento e parcelamento
- Múltiplos usuários por empresa (RBAC)
- Relatórios de vendas por período/cliente

## Backlog (P2)
- Integração fiscal (NFe)
- Comissão de vendedores
- App mobile nativo

## Test credentials
- File: /app/memory/test_credentials.md
