# Gestor360 — ERP web em Português

Sistema de gestão em duas etapas de login (empresa + usuário), com clientes, produtos, orçamentos, vendas, PDFs profissionais, controle de estoque opcional, papéis (Dono/Gerente/Vendedor) e pagamentos flexíveis (PIX, dinheiro, débito, crédito com parcelas, boleto com múltiplos vencimentos, transferência).

## Stack
- **Frontend**: React 19 (Create React App) + Tailwind + shadcn/ui + sonner
- **Backend**: FastAPI + Uvicorn + Motor (MongoDB async) + ReportLab (PDF)
- **Banco**: MongoDB Atlas M0 (free)
- **Deploy**: Vercel (frontend) + Render Free (backend)

---

## 1. Preparar o MongoDB Atlas (banco gratuito M0)

1. Acesse https://www.mongodb.com/cloud/atlas/register e crie uma conta.
2. Na tela **Deploy a database**, escolha **M0 Free**, provedor à sua escolha (AWS/GCP/Azure) e uma região próxima.
3. Clique em **Create Cluster**.
4. Em **Security → Database Access**, crie um usuário do banco:
   - Autenticação: **Password**
   - Anote **usuário** e **senha** (sem caracteres especiais como `@`, `/`, `:` — ou codifique-os por URL).
   - Papel: **Read and write to any database**.
5. Em **Security → Network Access**, adicione um IP:
   - Para produção com o Render, use **0.0.0.0/0** (permite todos os IPs — Render Free não tem IP fixo).
6. Volte para **Deployment → Database**, clique em **Connect → Drivers**, escolha **Python 3.11+** e copie a **connection string**. Exemplo:
   ```
   mongodb+srv://usuario:senha@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
   ```
   Guarde essa string — ela é o `MONGO_URL`.

## 2. Subir o projeto para o GitHub

```bash
# na pasta do projeto (com backend/ e frontend/):
git init
git add .
git commit -m "Gestor360 initial"

# crie um repositório vazio em https://github.com/new (sem README/.gitignore)
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/gestor360.git
git push -u origin main
```

## 3. Publicar o backend no Render (Free)

1. Acesse https://render.com e crie uma conta com o GitHub.
2. Clique em **New → Web Service** e conecte o repositório do Gestor360.
3. Configure:
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
4. Em **Environment**, cadastre as variáveis:
   - `MONGO_URL` = a connection string do Atlas
   - `DB_NAME` = `gestor360`
   - `JWT_SECRET` = uma string longa e aleatória (ex.: gerada em https://www.random.org/passwords/)
   - `FRONTEND_URL` = deixe em branco por enquanto (preenchemos depois de publicar na Vercel)
   - `PYTHON_VERSION` = `3.11.9`
5. Clique em **Create Web Service**. Após o build, o Render fornece uma URL pública, por exemplo:
   ```
   https://gestor360-backend.onrender.com
   ```
   Guarde essa URL — ela é o `REACT_APP_BACKEND_URL`.

> **Alternativa via `render.yaml`**: o repositório já contém um `render.yaml` na raiz. Ao criar o serviço, você pode usar **New → Blueprint** e o Render lê essa configuração automaticamente. Mesmo assim, preencha as variáveis marcadas como `sync: false`.

## 4. Publicar o frontend na Vercel

1. Acesse https://vercel.com com sua conta do GitHub.
2. Clique em **Add New → Project** e importe o repositório do Gestor360.
3. Na tela de configuração:
   - **Framework Preset**: **Create React App**
   - **Root Directory**: `frontend`
   - **Build Command**: `yarn build` (ou aceite o padrão detectado)
   - **Output Directory**: `build`
4. Em **Environment Variables**, adicione:
   - `REACT_APP_BACKEND_URL` = a URL pública do Render (ex.: `https://gestor360-backend.onrender.com`)
5. Clique em **Deploy**. Ao terminar, a Vercel fornece a URL pública, por exemplo:
   ```
   https://gestor360.vercel.app
   ```

## 5. Fechar o CORS

1. Volte no Render e edite a variável `FRONTEND_URL` para a URL da Vercel (sem barra no final):
   ```
   FRONTEND_URL=https://gestor360.vercel.app
   ```
2. O Render reinicia o serviço automaticamente. A partir desse momento apenas o domínio da Vercel poderá chamar o backend.

## 6. Testes finais

- Acesse a URL da Vercel.
- Clique em **Sou o dono, entrar direto** e crie a conta owner com email/senha.
- Você será direcionado para `/setup` — defina o **código da empresa** e a **senha da empresa**.
- Verifique cada área:
  - Clientes: cadastrar, buscar por parte do nome, buscar CNPJ via BrasilAPI, editar, excluir.
  - Produtos: cadastrar com preço de tabela e preço de custo, unidade, estoque.
  - Novo Documento: montar orçamento com Enter navegando as colunas; buscar produto por código ou descrição; aba Pagamento com PIX + Crédito 1–12x + Boleto com vencimentos 30/60/90; desconto no total.
  - Documentos: baixar PDF (verificar cabeçalho da empresa, dados do cliente, tabela, totais, pagamento, datas em horário local).
  - Finanças (Dono/Gerente): estatísticas e receita do mês.
  - Equipe (Dono): criar vendedores/gerentes, resetar senha.
- Faça logout, volte à tela `/login/company`, use o código + senha da empresa e entre como o usuário criado — confirme que o vendedor só vê os próprios documentos.

---

## Como testar localmente

### Backend
```bash
cd backend
cp .env.example .env       # e preencha MONGO_URL, DB_NAME, JWT_SECRET
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```
Health-check: http://localhost:8001/api/ deve retornar `{"app":"Gestor360","ok":true}`.

### Frontend
```bash
cd frontend
cp .env.example .env       # e defina REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
yarn start
```
Aplicação: http://localhost:3000

## Variáveis de ambiente

### Backend (`backend/.env`)
| Variável | Uso |
|---|---|
| `MONGO_URL` | String de conexão do MongoDB Atlas |
| `DB_NAME` | Nome do banco (ex.: `gestor360`) |
| `JWT_SECRET` | Segredo para assinar tokens JWT |
| `FRONTEND_URL` | Domínio autorizado no CORS (produção) |
| `PORT` | Porta do servidor (Render define automaticamente) |

### Frontend (`frontend/.env`)
| Variável | Uso |
|---|---|
| `REACT_APP_BACKEND_URL` | URL pública do backend |

## Estrutura de pastas
```
gestor360/
├── backend/
│   ├── server.py            # FastAPI + endpoints + PDF (ReportLab)
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/               # pytest
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── components/      # Layout, ProtectedRoute, ui/*
│   │   ├── context/AuthContext.js
│   │   ├── lib/api.js
│   │   └── pages/           # CompanyLogin, UserLogin, OwnerLogin, Setup, ChangePassword, Dashboard, Clients, Products, QuoteBuilder, Documents, Finances, Team, Settings
│   ├── package.json
│   └── .env.example
├── render.yaml              # Blueprint do Render
└── README.md
```

## Observações

- Login com Google foi **removido** temporariamente. Toda a autenticação usa email/senha (owner) ou usuário/senha (equipe via dois passos).
- A geração de PDF permanece via ReportLab (backend) sem alterações — datas ajustadas pelo parâmetro `?tz=` enviado pelo frontend.
- Nenhum modelo, coleção ou regra de negócio foi alterado nesta preparação de deploy.
