# Plano — Hospedagem gratuita do Gestor360

## Como o projeto está montado hoje

- **Front-end**: React 19 (Create React App), Tailwind + shadcn/ui, Axios, React Router. É um SPA que compila para arquivos estáticos.
- **Back-end**: FastAPI + Uvicorn (Python 3.11), MongoDB via driver Motor (assíncrono). Gera PDF com ReportLab. Autenticação por JWT (email/senha) + Google OAuth via serviço Emergent. Consultas grátis a ViaCEP e BrasilAPI são feitas direto do navegador.
- **Banco**: MongoDB (coleções: `companies`, `users`, `clients`, `products`, `documents`, `counters`, `user_sessions`).
- **Variáveis de ambiente**:
  - `backend/.env`: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`
  - `frontend/.env`: `REACT_APP_BACKEND_URL`

## O projeto pode ser separado em front-end e back-end?
Sim. O front-end é 100 % estático depois do build; o back-end é uma API HTTP independente. Cada parte pode ir para uma hospedagem diferente, desde que o front-end saiba o URL público do back-end.

## Combinação recomendada (100 % gratuita, sem cartão)

- **Front-end** → **Vercel** (deploy automático via GitHub, HTTPS grátis, sem "cold start", domínio `*.vercel.app` incluso). Alternativa igualmente boa: Netlify ou Cloudflare Pages.
- **Back-end** → **Render** (Free Web Service): 750 h/mês, HTTPS grátis, deploy via GitHub. Único incômodo: o serviço "adormece" após 15 min sem tráfego e demora ~30 s na primeira chamada. Alternativa sem cold-start: **Fly.io** (3 VMs pequenas grátis), um pouco mais chato de configurar.
- **Banco** → **MongoDB Atlas Free (M0)**: 512 MB, gratuito para sempre, ~1 clique.

Custo total previsto: **R$ 0**. Nenhuma das três exige cartão de crédito.

## Decisão pendente sobre o Google Login
O botão "Continuar com Google" hoje usa o serviço **Emergent** (`auth.emergentagent.com`), que é da plataforma onde o projeto está sendo desenvolvido. Fora dessa plataforma, três caminhos são possíveis:

- **A. Remover o login com Google no primeiro deploy** — deixa só usuário/senha. Zero trabalho, zero custo. Recomendado para subir rápido.
- **B. Migrar para Google OAuth próprio** — criar credencial no Google Cloud Console (também grátis). Precisa de ~1 h de ajustes no back-end. Melhor para longo prazo.
- **C. Manter o Emergent OAuth** — só funciona se o serviço estiver acessível fora da preview; não temos essa garantia.

Precisa escolher A, B ou C antes de começar.

## Ajustes necessários (nenhuma alteração feita ainda)
Para o deploy funcionar, será preciso:

1. Restringir CORS ao domínio público do front-end (hoje aceita `*`).
2. Confirmar que os cookies (`SameSite=None; Secure`) continuam funcionando — Vercel e Render já dão HTTPS, então não muda nada.
3. Criar `.env.example` em cada lado documentando as chaves esperadas.
4. Adicionar `render.yaml` (start command + porta dinâmica via `$PORT`) e `runtime.txt` marcando Python 3.11.
5. Escrever `README.md` na raiz com passo-a-passo: criar cluster no Atlas → subir back-end no Render → subir front-end na Vercel → conectar tudo.
6. Conta GitHub com repositório do projeto (Render e Vercel fazem deploy direto do GitHub).

## O que a pessoa recebe depois da aprovação
- `README.md` com o passo-a-passo completo (Atlas + Render + Vercel).
- `render.yaml` e `.env.example` prontos.
- Ajuste de CORS e leitura das envs conforme a decisão de Google OAuth.
- Zero alteração em regras de negócio, banco ou UI.

## O que a pessoa precisa decidir
1. Aceita a combinação **Vercel + Render + MongoDB Atlas**? Ou prefere trocar alguma peça (ex.: Netlify no lugar da Vercel, Fly.io no lugar do Render)?
2. Como resolver o **login com Google**: A (remover), B (migrar) ou C (manter Emergent)?
3. Já existe **repositório no GitHub** para este projeto, ou o build precisa incluir o passo de subir o código para lá?
