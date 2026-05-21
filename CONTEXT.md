# LiveDocs — Glossário

> Linguagem canônica do produto. Sem detalhes de implementação.
> Editado durante sessões de grilling; cada termo aqui é uma decisão
> de produto, não uma escolha de código.

## Unidade de documentação

LiveDocs documenta um SaaS em três tipos de **guia**, em ordem de prioridade:

- **Capacidade** *(primary)* — uma área de negócio do produto, como o
  usuário pensa nele. Exemplos no <Client>: "Cobrança recorrente",
  "Onboarding de morador", "Régua de inadimplência". É a unidade
  default de uma página no help center. Granularidade típica: 10–25
  capacidades num SaaS médio.

- **Jornada** *(secondary, opcional)* — um fluxo cross-cutting que
  atravessa várias capacidades pra entregar um resultado. Exemplo:
  "Do cadastro da unidade até a primeira fatura paga". Existe quando
  o valor de explicar o caminho ponta-a-ponta supera o de explicar
  capacidade por capacidade. Granularidade típica: 5–15 por SaaS.

- **Tela** *(supporting, não é entrada de menu)* — uma rota/página da
  UI. Não vira página própria no help center por padrão; vira seção
  ou apêndice dentro do guia de capacidade que ela serve. Existe pra
  ancorar capturas de tela e referência rápida ("onde fica o
  botão X"), não pra carregar conceito.

> Telas SÓ promovem a guia próprio quando o conteúdo conceitual
> específico daquela tela não cabe na capacidade que ela serve
> (raro). Default: tela = seção dentro da capacidade.

## Pareamento produto/técnico

Cada guia (capacidade ou jornada) tem duas faces, geradas e
mantidas juntas:

- **Guia de produto** — para o usuário final do SaaS (cliente,
  operador). Linguagem do domínio, sem jargão de código.
- **Guia técnico** — para o dev/IA mantendo o SaaS. Mesmo
  conhecimento, expresso em termos de arquivos, modelos, jobs.

> "Documentação" sozinha é ambígua; sempre qualifique como "guia de
> produto" ou "guia técnico".

## Entrevista

Conversa estruturada entre o agente e o humano. Existe em dois
momentos distintos no ciclo de bootstrap; **não existe** uma
entrevista por guia.

- **Entrevista de seeding** — uma única rodada, antes do loop de
  geração começar. Valida a taxonomia (lista de capacidades e
  jornadas) que o agente propôs a partir do código. Custo baixo,
  feedback estrutural.

- **Entrevista de refinamento** — uma única rodada, depois do loop
  ter gerado rascunhos de todos os guias. Cobre o que o código não
  revela: propósito de negócio, intenção de UX, integrações
  externas, conexões implícitas entre módulos. As respostas
  disparam uma rodada global de atualização dos guias afetados.

> Durante o loop de geração, o agente NÃO entrevista. Lê o código
> como fonte primária e os guias já gerados como fonte secundária.
> Qualquer pergunta que surgir vira um item pendente para a
> entrevista de refinamento — não interrompe o loop.

## Pergunta pendente

Pergunta que o agente quis fazer enquanto documentava um guia mas
não pôde resolver só lendo código. Acumula numa fila durante o
loop e é apresentada ao humano em lote na entrevista de
refinamento. Cada pergunta carrega:

- o guia que a gerou (origem)
- o que o agente já assumiu provisoriamente no rascunho
- a confiança da suposição (alta / baixa)

> Antes de mostrar a fila ao humano, o agente reprocessa: uma
> resposta dada num item pode tornar outros itens obsoletos ou
> respondidos. Só o que sobrar vai pro humano.

## Bootstrap

Processo de criar a primeira versão completa da documentação de um
SaaS já existente, a partir de zero. Distinto da manutenção
incremental que ocorre depois (mudança de código → ajuste de guia).

Fases do bootstrap, nesta ordem:

1. **Scan** — graphify + leitura complementar (rotas, i18n, modelos)
   produzem um mapa do código.
2. **Taxonomia proposta** — agente deriva capacidades e jornadas
   candidatas a partir do scan. Resultado: um menu de help center
   em forma de árvore, com títulos e estrutura, sem conteúdo.
3. **Entrevista de seeding** — humano aprova/edita a taxonomia.
4. **Passada 1 — rascunho independente** — cada guia é gerado em
   contexto isolado, vendo apenas: código relevante, o menu
   aprovado, o estilo. Não vê outros guias. Pode produzir
   perguntas pendentes e TODOs internos ("linkar quando X existir").
5. **Passada 2 — costura** — cada guia é relido com a lista de
   títulos+resumos dos demais como contexto. O agente adiciona
   cross-links, harmoniza termos, sinaliza contradições. Custo
   fração da passada 1 porque entrada é markdown curto, não código.
6. **Entrevista de refinamento** — fila de perguntas pendentes
   apresentada ao humano em lote, após deduplicação.
7. **Rodada global de ajuste** — guias afetados pelas respostas
   são reabertos e atualizados.

> O bootstrap acontece uma vez por SaaS. Após ele, o sistema entra
> em modo de manutenção incremental (fora do escopo deste
> documento por enquanto).

## Contexto isolado

Sessão do agente IA com escopo restrito a um único guia. Garante
que o custo de tokens e a coerência de raciocínio não degradem
quando o número de guias cresce. Nenhuma passada do bootstrap usa
"toda a documentação no prompt"; cada passada define explicitamente
o que entra.

## Manutenção

Modo permanente de operação do LiveDocs depois que o bootstrap
terminou. Distinto do bootstrap em três pontos: é incremental, é
disparado por mudanças no código (não pelo humano), e respeita
edições humanas feitas no help center publicado.

Gatilho típico: um PR é aberto/atualizado. LiveDocs roda graphify
sobre o diff, compara com o grafo da última versão, identifica
quais capacidades/jornadas foram afetadas e atualiza só os guias
correspondentes. Se a mudança não puder ser entendida só pelo
código, gera perguntas pendentes para o dev — sem bloquear o PR.

## Texto guia

Input livre de texto que o dev pode anexar a qualquer operação do
LiveDocs (bootstrap, atualização por PR, regeneração avulsa). Vai
para o prompt do agente como instrução de orientação, não como
conteúdo a copiar. Existe pra cobrir o caso "o código mudou, mas o
*porquê* da mudança está na minha cabeça, não no diff".

## Publicação

Ato de enviar os guias gerados localmente para o help center
escolhido (Chatwoot, no MVP). É automática por default, mas o
projeto pode optar por modo draft (publicação manual). A
publicação é um movimento de uma via: do `.md` local pro Chatwoot.
O movimento contrário é a *sincronização*.

## Sincronização

Operação inversa da publicação: o LiveDocs baixa o estado atual
dos artigos do Chatwoot e reconcilia com os `.md` locais. Existe
porque o humano edita no Chatwoot (texto, imagens, prints) e essas
edições não podem ser sobrescritas pela próxima rodada de
manutenção.

## Edição humana preservada

Conteúdo de um artigo que veio do humano editando no Chatwoot e
NÃO do agente. Inclui:

- Imagens e prints anexados pelo humano
- Parágrafos reescritos pelo humano
- Seções inteiras adicionadas pelo humano

Durante a manutenção, o agente:

- Mantém o teor e as imagens intocados sempre que possível
- Aplica apenas o ajuste mínimo necessário quando o fluxo muda
- Mostra ao humano um diff do que alterou, antes de republicar

> Princípio: a autoridade do humano sobre conteúdo que ele tocou é
> superior à do agente, exceto quando esse conteúdo afirma algo
> que o código contradiz.

## Ponto de captura do código

SHA do commit git em que o scan de bootstrap rodou. Persistido no
`bootstrap.toml` junto com o resultado do scan. Estabelece o
pareamento "esta documentação foi gerada a partir deste estado do
código" e é pré-requisito do Plano B (manutenção por diff de PR
precisa de um SHA base pra calcular o diff).

## Diff de manutenção

Visão das alterações que o LiveDocs fez (ou pretende fazer) em
guias publicados, apresentada ao humano antes de subir ao
Chatwoot. Granularidade: por guia, por seção. Permite aprovar
seletivamente.
