# Case study — um bootstrap real, do começo ao fim

Exemplo concreto para você saber o que esperar do `livedocs-bootstrap`.
Foi o que aconteceu em um SaaS brasileiro real em que o autor
dogfoodou a skill — um codebase de produção de porte médio (~38k
nós semânticos pelo `graphify`), backend completo + frontend em
Vue 3, ~3 anos de código, multi-tenant.

O agente foi o [Hermes](https://github.com/NousResearch/hermes)
rodando no Opus 4.7 da Anthropic. Wall-clock total: aproximadamente
uma semana de trabalho, na maior parte acompanhada; as partes longas
foram do tipo "deixa rodando e volta depois do jantar".

## Detalhamento por fase

| Phase | O que o agente fez | Números deste run |
|---|---|---|
| 0 — Guidance | Pediu ao mantenedor para soltar contexto, detectou pt-BR | ~10 min, US$ 0 |
| 1 — Scan | Rodou `graphify extract`, parseou rotas/i18n/models | run do graphify ~25 min; 139 rotas, 272 chaves i18n, 18 models; grafo de 38k nós |
| 2 — Taxonomy | Propôs 22 capabilities + 6 journeys a partir dos sinais | 1 chamada de LLM, ~US$ 0,40 |
| 3 — Review | Mantenedor fez split / merge / rename via menu interativo | ~30 min de tempo humano, algumas chamadas de split |
| 4 — Drafts | 1 sub-agente por artigo, todos em batches paralelos | 76 artigos × 2 flavors = 152 arquivos; ~US$ 74 no total |
| 5 — Stitch | Cross-links resolvidos, terminologia harmonizada | ~US$ 20; sinalizou algumas contradições como pending questions |
| **5.5 — Triage** | **Re-checou 314 pending questions contra o código** | **~120 auto-respondidas com evidência `arquivo:linha`; ~28 artigos auto-patcheados; ~150 perguntas chegaram no humano** |
| 6 — Interview | Mantenedor respondeu as 150 em blocos temáticos (A–F) | ~3 horas de tempo humano, duas sentadas; respostas vagas aceitas e salvas |
| 7 — Global update | Artigos afetados reabertos e reescritos com as respostas | ~US$ 15; ~30 artigos tocados |

## Totais

- **~US$ 110** em gasto de LLM
- **~4 horas** de tempo humano acompanhado (na maior parte, a entrevista)
- **152 arquivos markdown** produzidos (76 artigos × flavor produto + tech)
- **6 journeys** documentando fluxos cross-cutting
- Uma semana de trabalho wall-clock, na maior parte mãos-fora

Estado final: uma árvore `docs/capacidades/` e `docs/jornadas/` que
o mantenedor revisa, edita e publica — arquivos pareados produto +
técnico para cada capability, com `skill_version` carimbado em cada
artigo para que manutenções futuras saibam o que gerou cada um.

## Lições que viraram regras permanentes

Coisas que apareceram nesse run e voltaram para a skill como
regras, para que o próximo run não repita os mesmos erros:

### O mantenedor lendo 300+ pending questions cruas era o ponto de dor

Antes da Phase 5.5 existir, cada pergunta respondível-pelo-código
(rótulo de um enum, valor de uma coluna, nome de um cron job)
chegava no humano via entrevista. O usuário gastava mais tempo
filtrando ruído do que dando input real de produto. **A Phase 5.5
veio daí** e agora remove a maior parte delas antes da entrevista
começar. As perguntas que sobrevivem são genuinamente sobre
intenção, UX, ou realidade operacional.

### Trocar de contexto a cada pergunta mata a entrevista

Perguntar "esse rótulo é `'Pending'` ou `'Em aberto'`?" logo depois
de "qual a expectativa de SLA no webhook de cobrança?" força uma
mudança de modo mental a cada turno. Custo cumulativo: alto.

**Blocos temáticos de entrevista** foram a solução:

- A: significado / glossário
- B: transições e gatilhos
- C: invariantes e constraints
- D: UX e suporte
- E: bordas sugeridas pelo código
- F: meta-direção do guide

Cada bloco mantém o humano em um modo mental por vez. Mesmas
perguntas, metade do cansaço.

### Sub-agente reportando sucesso às cegas é o pior modo de falha

Um sub-agente na Phase 5 escreveu um arquivo vazio, retornou
`{"status": "ok", "files_modified": [...]}`, e o orquestrador
avançou. O artigo aparecia normal no state mas estava vazio no
disco. Só foi pego por sorte durante revisão.

Depois desse incidente, **verificação pós-edit virou princípio
core**: todo sub-agente que escreve um arquivo precisa rodar `wc -c`
para checar tamanho > 0, fazer grep procurando uma sentinel
esperada, e retornar `verification_passed: true|false` no JSON. O
orquestrador nunca confia em auto-report sem verificação.

O anti-loop guard correspondente veio do mesmo run: um sub-agente
que bateu o mesmo erro de tool duas vezes seguidas aborta com
`status: "aborted"` em vez de tentar de novo em silêncio queimando
contexto.

## O que esse run NÃO exercitou

Honestidade sobre cobertura:

- **Multi-idioma** — esse foi um run só em pt-BR. O caminho em
  inglês está implementado mas é menos battle-tested.
- **Manutenção incremental** — bootstrap foi one-shot. Re-rodar a
  skill contra o mesmo projeto depois de mudanças no código está
  planejado para v2.0.
- **Publicação** — o mantenedor publicou no Chatwoot manualmente a
  partir da árvore local de `docs/`. Publicação automatizada está
  planejada para v2.0.
- **Entrevista cross-team** — um mantenedor único respondeu tudo.
  Quebrar a entrevista entre múltiplos especialistas no domínio
  ainda não é suportado.

Se você rodar a skill e bater em um caso que o acima não cobre,
isso é feedback útil — abra uma issue no projeto.
