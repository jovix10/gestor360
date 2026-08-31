# Plano — Cidade + estado no cabeçalho

## Como está hoje
No cabeçalho aparece apenas "Acre" (só o estado), porque a consulta de localização usa um nível regional pouco detalhado — quando o ponto é longe de uma cidade cadastrada nesse nível, o serviço devolve só o estado.

## O que muda
- Consultar a localização em nível de cidade (detalhamento maior).
- Formatar como **"Cidade/UF"** (ex.: "Rio Branco/AC" no lugar de "Acre"), no mesmo estilo que o cadastro de clientes usa.
- Se, mesmo assim, só vier estado, mostra o estado sozinho como fallback.

## Nenhuma decisão pendente
Único item da mudança. Impacto zero no restante do app.
