# Plano — Tela de estrutura do help center (manutenção pós-bootstrap)

> Status: parqueado. Origem: conversa 2026-05-21 durante bootstrap real
> na <Client>. Usuário pediu uma forma visual de navegar a hierarquia
> e operar sobre qualquer nó (split, regenerar, renomear, remover)
> depois que o bootstrap já rodou — sem precisar lembrar comandos.

## Por quê

O bootstrap entrega um help center estruturado, mas hoje não há um
ponto de operação contínuo depois. Pra evoluir (split adicional,
regenerar artigo, mover entre capacidades) o usuário tem que editar
TOML à mão ou rodar `--restart`/`--re-tax`, que destroem progresso.

## Visão

Um comando único — `livedocs` (sem args) ou `livedocs structure` —
abre uma árvore navegável do help center inteiro. Cada nó (capacidade,
artigo, jornada) tem submenu contextual com as operações naquele nó.
Inclusive depois de `done`, fica reabrível para manutenção.

## Comportamento aprovado nesta conversa

- Árvore com nós colapsáveis: capacidades expandidas mostram artigos.
  Jornadas em seção separada.
- Submenus contextuais por tipo de nó:
  - **Capacidade**: inspecionar, split, gerenciar artigos, renomear,
    ver no editor.
  - **Artigo**: ver, regenerar, mover pra outra capacidade, remover,
    toggle is_intro, renomear.
  - **Jornada**: ver, regenerar, renomear, editar refs de capacidade,
    remover.
- Split pós-geração preserva artigos que já existem com mesmo slug;
  novos viram `pending` e entram na próxima passada 1. Intros
  preservadas por default (regen sob ação explícita).
- Ao sair, se há artigos `pending` recém-criados, oferece gerar
  agora (roda passada 1 só nesses + passada 2 incremental).
- UI: `prompt_toolkit` direto (mais controle de navegação por
  setas / expand-collapse / busca incremental que `questionary`).
- Sem flags extras — usuário operacional é o autor, simplicidade
  vence configurabilidade.

## Não-objetivos

- Manutenção por PR / diff de código → escopo do Plano B (Chatwoot
  + maintain).
- Hierarquia profunda → fora; Chatwoot é 2 níveis fixos.

## Esboço técnico (rascunho)

- Novo módulo `livedocs/structure/` separado de `bootstrap/`.
- Reaproveita ações da fase 3 (inspect, split, gerenciar articles)
  como funções puras chamáveis fora do orquestrador.
- Função pública `open_structure(repo_root)` carrega
  `bootstrap.toml`, monta árvore, entra no loop interativo.
- "Regenerar artigo" = marcar `GuideRecord.status = pending` +
  rodar `run_pass1(state, filter=[slug])`.
- "Gerar agora?" ao sair = `run_pass1` + `run_pass2` em modo
  incremental (filtra por status `pending`).

## Dependências bloqueantes

- Plano A (bootstrap) precisa estar estável (já está).
- Refatorar fase 3 pra expor ações como funções reutilizáveis
  (hoje estão acopladas ao loop de review). Trabalho pequeno.

## Prioridade

Pegamos quando o bootstrap real na <Client> estiver maduro e
quisermos abrir caminho pra manutenção contínua. Não antes.
