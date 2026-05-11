# Estilo: Narrativo de Produto

> Esse arquivo guia como os guias `flavor: produto` devem ser escritos.
> Editá-lo customiza a voz dos seus guias. Apagar volta ao default embutido.

## Para quem

SaaS B2B operacional/financeiro. Cliente final é humano não-técnico: operador,
suporte, comercial, cliente direto do produto.

## Voz

- **Terceira pessoa do usuário** (`o usuário escolhe...`, `o cliente vê...`)
- **Prosa contínua** em parágrafos. Bullets só quando é lista mesmo.
- **Frases médias** (15-25 palavras). Subordinadas curtas.
- **Porquê antes do como.** Antes de instruir, situa: por que isso existe, qual problema resolve, onde encaixa no fluxo do usuário.
- **Decisões de produto explicadas.** "Esse countdown serve a dois propósitos: dar tempo de se preparar e garantir que o usuário não apareça no vídeo final."
- **Tom calmo, confiante, sem condescendência.**

## Estrutura preferida

Abertura ("Por que isso existe") **não-instrutiva**. Não soa como release notes nem manual. É narrativa, contextual, situa o leitor.

Seção "Como o usuário vivencia" é **prosa contínua, narrativa**. Não step-by-step. Conta a experiência como se fosse pra alguém.

Seção "Casos do dia a dia" usa **primeira pessoa do usuário entre aspas**, seguido da explicação:

```
**"Quero fazer um vídeo curto pra um cliente."** O usuário escolhe Quick Share
no Intent Picker. Como Quick Share não usa slides de intro nem outro e tem
prompts de IA mais conversacionais, o vídeo sai com cara de mensagem pessoal.
```

Esse padrão casa com perguntas reais que aparecem em widget RAG futuro.

## Vocabulário — NÃO usar

- Nomes de classe (`OffscreenRecorder`, `PaymentService`)
- Nomes de coluna/tabela (`tour_modes`, `cart.status`)
- Siglas técnicas sem abstrair (`IndexedDB` → "banco local do navegador", `S3` → "armazenamento na nuvem")
- Passos numerados imperativos quando dá pra narrar
- "O sistema X faz", "o backend Y" — preferir ação do usuário ou nome do produto

## Vocabulário — usar

- Termos do produto (Intent Picker, Quick Share, Tour, Compartilhar Áudio)
- Nome da empresa/produto quando importa ("a extensão Nexa registra...")
- Linguagem que o cliente final usa na conversa dele

## Exemplo de abertura

> A primeira coisa que alguém faz no Nexa é gravar a própria tela. Toda a cadeia
> de valor do produto — vídeo, artigo, agente — nasce dessa única gravação. Por
> isso, capturar precisa ser sem fricção: o usuário entra na aba, abre o painel,
> escolhe rapidamente o que está fazendo, e segue trabalhando enquanto a extensão
> grava em silêncio.

## Exemplo de "casos do dia a dia"

> **"Vou gravar a versão mobile da nossa interface."** O usuário marca a
> proporção celular antes de gravar. A janela do Chrome é estreitada para a
> largura de um iPhone 14 Pro e a gravação acontece nesse formato vertical.

## Quando usar mermaid

Só quando o fluxo tem **divergência** (if/else, paralelismo, retry). Fluxo
linear simples se conta melhor em prosa.

## Inspirações

- Stripe Docs (parte de produto, não API reference)
- Linear changelog
- O guia `gravar-tela-com-extensao.md` do Nexa
- Os guias da <Client> (`ciclo-de-vida.md`, `parceiros-do-projeto.md`)
