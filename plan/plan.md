# Plano — Login em duas etapas (Empresa + Usuário)

## O que muda hoje
Hoje cada pessoa que entra no Gestor360 tem sua própria conta isolada. Cadastros, produtos, orçamentos e vendas ficam presos ao próprio login. Não existe noção de "empresa" com várias pessoas dentro.

## O que vai passar a existir

### 1. Duas telas de login em sequência
- **Tela 1 — Entrar na empresa**: a pessoa digita o **código da empresa** (ex.: `neto-materiais`) e uma **senha da empresa** definida pelo Dono. Isso destrava o espaço da empresa naquele navegador.
- **Tela 2 — Entrar como usuário**: aparece a lista de usuários cadastrados naquela empresa. A pessoa escolhe o próprio perfil (ou digita o usuário) e informa a sua senha pessoal. Entra com o próprio nome, papel e permissões.

O saudação "Olá, [nome]" passa a mostrar o nome do usuário logado, e o cabeçalho ganha o nome da empresa ao lado.

### 2. Três papéis (roles)
- **Dono**: acesso total. Cria/apaga usuários, altera dados da empresa, define senha da empresa, vê tudo.
- **Gerente**: gerencia clientes e produtos, cria/edita todos os documentos, converte orçamento em venda, vê finanças da empresa inteira. Não mexe em usuários nem nos dados da empresa.
- **Vendedor**: cria clientes e produtos, cria orçamentos e vendas. Só vê e edita **os próprios documentos**. Não acessa Finanças da empresa toda — vê só o próprio desempenho.

### 3. Gestão de usuários
- Nova aba **Equipe** (visível só para o Dono) para adicionar/remover usuários, resetar senha e trocar o papel.
- Ao adicionar um vendedor/gerente: define nome, usuário (login curto, ex.: `joao`), senha inicial e papel.
- O primeiro acesso obriga a trocar a senha.

### 4. Migração de quem já usa
- Sua conta atual (`netozincaovendas@gmail.com`) vira **Dono** de uma empresa nova chamada "Gestor360" (nome editável em Empresa).
- Todos os clientes, produtos e documentos que você já tem passam a pertencer à empresa. Nada se perde.
- Você define o **código da empresa** e a **senha da empresa** no primeiro acesso após a atualização (uma tela guiada).

### 5. Login Google (Emergent)
- Continua funcionando, mas só para o Dono (o único e-mail vinculado à empresa como Google login).
- Vendedores e gerentes usam sempre usuário + senha simples (não têm e-mail Google individual amarrado).

## Decisões que precisam do seu OK

1. **Vendedor vê preço de custo ou só preço de tabela?**  
   *Proposto: vendedor vê apenas preço de tabela. Preço de custo aparece só para Dono e Gerente (se um dia existir).*

2. **Desconto máximo por papel**  
   *Proposto: vendedor pode aplicar até 10% de desconto sem aprovação; acima disso o documento fica "aguardando aprovação" e um gerente/dono precisa liberar. Se preferir simples no começo, começamos SEM esse limite — todos aplicam qualquer desconto.*

3. **Gerente pode criar outros usuários?**  
   *Proposto: não. Só o Dono cria usuários. Deixa o controle simples.*

4. **Documentos entre vendedores**  
   *Proposto: vendedor não enxerga documentos de outro vendedor, nem na lista. Gerente e Dono enxergam tudo. Confirma?*

5. **Login por usuário (não email)**  
   *Proposto: vendedores/gerentes entram por um **nome de usuário curto** (ex.: `joao`, `maria`) e não por e-mail — mais rápido no balcão. Confirma?*

## O que NÃO está incluído neste plano
- Assinatura digital, aprovações em cadeia, comissão de vendedores, metas por vendedor, dashboard comparativo entre vendedores. Podem virar plano futuro.
- Multi-empresas para a mesma pessoa (ex.: um vendedor trabalhando em duas empresas). Cada usuário pertence a uma empresa só.

## Resumo curto
Duas telas de login em sequência: primeiro a empresa se identifica, depois o usuário se identifica. Três papéis com permissões diferentes. Sua conta atual vira Dono automaticamente, com uma tela guiada para você definir o código e a senha da empresa. Precisa do seu OK nos 5 pontos acima antes de construir.
