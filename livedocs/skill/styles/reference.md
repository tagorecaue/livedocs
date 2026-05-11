# Estilo: Técnico de Referência

> Esse arquivo guia como os guias `flavor: produto` devem ser escritos.
> Editá-lo customiza a voz dos seus guias. Apagar volta ao default embutido.

## Para quem

API, SDK, devtool, infraestrutura. Cliente final **é dev**. Quer rastreabilidade
alta, citações de código abundantes, frases diretas.

## Voz

- **Segunda pessoa diretiva** (`você configura...`, `chame o endpoint X com...`)
- **Parágrafos curtos** (3-5 linhas máx).
- **Code blocks frequentes**. Mostre o exato comando/payload/snippet sempre que aplicável.
- **Cada afirmação carrega referência**. `file:line`, comando, endpoint, payload.
- **Sem narrativa de "porquê"** detalhada — assume que o leitor sabe e quer o como.
- **Tom seco, profissional, sem floreios.** Sem humor, sem analogias.

## Estrutura preferida

Abertura é **descritiva e factual**: o que esse recurso faz, em uma frase.

Seguido de **pré-requisitos listados** antes de qualquer instrução: API key, scope, configuração, dependências.

Depois o **fluxo principal** em parágrafos curtos com code blocks intercalados.

Seção "Casos do dia a dia" vira **cenários técnicos** (rate limits, retry logic,
edge cases de payload, autorização específica) com exemplos de code/payload.

## Vocabulário — usar

- Nomes exatos de endpoints, métodos, classes, payload fields
- Códigos de erro HTTP, exit codes, exceções
- Versões de API/SDK quando relevante
- Termos técnicos sem abstrair (`IndexedDB`, `idempotency-key`, `rate limit`)

## Vocabulário — NÃO usar

- Diminutivos / informalidade ("legal", "rapidinho", "tá")
- Analogias ("como uma caixinha de bombons")
- Step-by-step com numeração robótica quando uma lista de bullets já basta
- Frases passivas longas

## Exemplo de abertura

> O endpoint `POST /captures` aceita um arquivo `.webm` codificado em chunks de
> até 4MB. Cada upload retorna um `tour_id` que é a chave primária pra todo o
> pipeline downstream — `compile`, `publish`, `agent/ask`.
>
> Pré-requisitos:
> - API key com scope `capture:write`
> - Domínio de origem em `agent_config.allowed_domains` (`packages/api/src/routes/agent.ts:48`)

## Exemplo de "casos do dia a dia"

> **Upload acima de 4MB.** Use multipart, não chunked encoding. Cada parte
> retorna um `etag` que você passa no `POST /captures/{id}/complete`. Se a parte
> falhar, retry com mesma `Content-MD5` é idempotente.

## Quando usar mermaid

Sempre que houver máquina de estado, fluxo de retry, ou sequência distribuída
(webhooks, cron, fila assíncrona).

## Inspirações

- Stripe API docs
- AWS docs (versão limpa, ex: Lambda, EventBridge)
- DataDog reference
- Hono.dev
- Vercel API reference
