# Conceitos

O LiveDocs documenta um SaaS através de um vocabulário pequeno e
opinativo. As escolhas abaixo vieram todas de uma fonte: tentar
manter o conjunto de docs **mantível** depois de uns ~20 artigos,
onde abordagens ingênuas degradam rápido.

## O que ganha página própria — Capability, Journey, Screen

Uma **capability** é uma área de negócio do jeito que o usuário
pensa nela ("Cobrança recorrente", "Onboarding de morador",
"Régua de cobrança"). É a unidade primária — tipicamente 10–25
delas em um SaaS de porte médio, cada uma vira uma categoria no
help center.

Uma **journey** é um fluxo cross-cutting que atravessa várias
capabilities para entregar um resultado ("Do cadastro da unidade
até a primeira fatura paga"). Secundária e opcional — criada só
quando explicar o caminho ponta-a-ponta entrega mais valor do que
explicar capability por capability. Geralmente 5–15 por SaaS.

Uma **screen** é uma rota da UI. E aqui o ponto importante:
**screens NÃO são unidades documentais de primeira classe** — elas
vivem como seções ou âncoras de screenshot dentro do artigo da
capability a que servem. Conhecimento pertence a uma área de
domínio, não a um botão. Promover screens a artigos isolados
fragmenta a documentação em uma-página-por-rota, que escala mal
e dá ao usuário um help center que espelha a sua nav em vez do seu
domínio.

(Exceção: uma screen tão conceitualmente densa que o conteúdo dela
não cabe dentro da capability pai ganha página própria. Raro.)

## Dois flavors por tópico, nunca cross-linkando entre si

Cada artigo é gerado como par: `<slug>.md` (produto) e
`<slug>.tech.md` (técnico). Mesmo conhecimento de domínio, duas
audiências.

O flavor de produto usa a linguagem que o usuário final vê na UI —
sem nomes de coluna, sem valores de enum, sem caminhos de rota na
prosa. O flavor técnico é a contraparte para dev/IA, com citações
`arquivo:linha`, invariantes numerados, âncoras de código.

Os dois nunca se linkam mutuamente. Cross-references vão só para
outros guides do mesmo flavor. Eles descrevem a mesma coisa para
audiências diferentes; linká-los cria um loop que não adiciona
valor e confunde o leitor sobre em qual flavor está.

## Pending questions, em vez de interrupção

Quando o agente acha algo que o código não revela (intenção,
racional de UX, comportamento de integração sob falha), ele **NÃO**
pausa e interrompe o usuário. Ele registra uma **pending question**,
escreve um palpite provisório no draft com flag de confiança, e
segue.

As perguntas acumulam durante Phase 4 e Phase 5. A Phase 5.5
checa cada uma contra o código, respondendo automaticamente as
que têm evidência literal e patcheando o artigo que deveria ter
tido a resposta. O que sobreviver chega na Phase 6 — uma entrevista
única em lote, organizada em blocos temáticos (significado /
transições / invariantes / UX-e-suporte / bordas de código /
direção).

O custo de fazer o humano trocar de contexto ("responde isso
agora") é maior que o custo de uma fase extra. Entrevistas em lote
também se beneficiam de dedup cross-pergunta — uma resposta
geralmente resolve várias.

## Contexto isolado por draft

A Phase 4 gera cada artigo em **contexto isolado**. O sub-agente vê:
o texto de guidance, um menu de títulos dos outros artigos (sem
corpo), as âncoras de código do artigo em si, o guia de estilo.
Nada mais. Sem "toda a documentação no prompt" globalmente.

Duas razões: **custo** (prompts que crescem com N artigos ficam
caros rápido) e **coerência** (a atenção de uma LLM degrada quando
ela tem que manter todos os outros artigos na cabeça enquanto
escreve esse). Cross-linking acontece depois, na Phase 5, onde o
input é um índice curto em markdown, não código bruto.

## Texto de guidance + ponto de captura do código

Parte do conhecimento de produto não está no código: o racional
por trás de uma decisão, o perfil do cliente, a peculiaridade de
uma integração que a pessoa que mantém guarda na cabeça. A Phase 0
coleta um **texto de guidance** livre que entra em todos os prompts
seguintes como instrução, não como conteúdo a ser copiado.

A disciplina complementar é o **ponto de captura do código** — o
SHA do commit git no momento do scan, persistido junto com a
taxonomia. Ele fixa "esta documentação foi gerada a partir deste
estado do código". O SHA fica importante quando a manutenção
incremental chegar.
