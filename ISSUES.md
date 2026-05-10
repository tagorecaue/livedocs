# LiveDocs — Issues conhecidas e plano de melhoria

> Atualizado: 2026-05-09 após smoke test E2E em `/tmp/livedocs-smoke` + auditoria de código.
> Autor: Tagôre + co-pilot AI. Status: **v0.1.0 funciona ponta-a-ponta**, mas tem dívidas claras antes do v0.5.

## Sumário

| # | Issue | Prio | Esforço | Categoria |
|---|-------|------|---------|-----------|
| #1 | Modo non-interactive ausente | P1 | M | UX |
| #2 | `next_recommendation` é desperdiçada | P1 | S | UX |
| #3 | Custo/duração do agente não são logados | P2 | S | Observabilidade |
| #4 | i18n inline em 5 arquivos quebra a promessa multi-idioma | P0 | M | Arquitetura |
| #5 | `status="completed"` exibido como "Revisado" sem revisão humana | P1 | S | Semântica |
| #6 | `--permission-mode=acceptEdits` é foot-gun | P0 | S | Segurança |
| #7 | Faltam comandos de gestão de interview (regenerate, delete, abandon) | P1 | M | UX |
| #8 | Flag `--model` não exposta no CLI | P2 | S | UX |
| #9 | `schema_version` não validada na leitura | P2 | S | Robustez |
| #10 | `generate_guides` não verifica arquivos escritos | P1 | S | Robustez |
| #11 | `coverage_check` ignora respostas parciais | P2 | M | Qualidade |
| #12 | Zero testes apesar de pytest no `pyproject.toml` | P0 | L | Qualidade |
| #13 | Sem CI / sem distribuição (PyPI / uvx ainda não testados) | P1 | M | Distribuição |

**Legenda:** P0 = bloqueia v0.5, P1 = entra no v0.2, P2 = polimento, P3 = futuro. Esforço S = <2h, M = meio dia, L = 1+ dia.

---

## #1 — Modo non-interactive ausente
**Prio: P1 · Esforço: M · Categoria: UX**

### Descrição
Todo prompt do usuário passa por `questionary.text()` / `select()` / `confirm()`, que requerem TTY. Em pipe (`echo "/sair" | livedocs continue`) o questionary cai num loop visual feio com o aviso `Warning: Input is not a terminal (fd=0)` e re-renderiza a pergunta múltiplas vezes.

### Evidência
Smoke test (`/tmp/livedocs-smoke`):
```
? Sua resposta  (Finish with 'Alt+Enter' or 'Esc then Enter')
> 

   ? Sua resposta  (Finish with 'Alt+Enter' or 'Esc then Enter')
> /sair
```
Para popular um state de teste, **tive que escrever um script Python que importa `generate_guides` direto** — não dá pra dirigir o CLI por stdin.

### Impacto
- **Demos/CI impossíveis** sem mock manual. Prejudica adoção.
- Dogfood interno (<Client>) vai precisar disso pra automatizar regenerações.
- Bloqueia integração com Hermes/Paperclip no futuro.

### Plano de melhoria
**Fase 1 — Detecção e modo guard (S, 2h):**
- Detectar `not sys.stdin.isatty()` em `ui.ask_text/choice/confirm`.
- Quando detectado: levantar `NonInteractiveError` ao invés de chamar questionary.
- Adicionar flag global `--non-interactive` (curto: `-y`).

**Fase 2 — Comandos com input estruturado (M, 4h):**
- `livedocs new <slug> --domain X --title T --answers-file path.yaml`
  - YAML aceita: `{ A1: "...", A2: skip, B1: "..." }`
  - Pula entrevista interativa, vai direto pra `generate_guides`.
- `livedocs continue <slug> --answers-file path.yaml`: aplica respostas adicionais e gera se completo.
- `livedocs export-questions <slug> [--format yaml|json]`: dump das perguntas pendentes pra o usuário responder offline.

**Fase 3 — Stdout estruturado opcional (S, 1h):**
- Flag `--json` em `status` e `review` produz output parseável.
- Flag `--quiet` suprime splash + spinners.

### Arquivos afetados
- `livedocs/ui.py` (detecção)
- `livedocs/cli.py` (flags globais)
- `livedocs/commands/new.py`, `cont.py` (--answers-file)
- `livedocs/commands/status.py`, `review.py` (--json)

### Critério de aceite
- `echo "" | livedocs new foo --non-interactive` falha com mensagem clara em vez de loop visual.
- `livedocs new foo --domain x --answers-file ans.yaml` completa sem prompt.

---

## #2 — `next_recommendation` é desperdiçada
**Prio: P1 · Esforço: S · Categoria: UX**

### Descrição
O prompt `PROMPT_GENERATE_GUIDES` instrui o agente a retornar JSON com `files_written`, `summary` e `next_recommendation` (próximo guia sugerido com slug, domínio e razão). Mas em `interview.py:286-305`:

```python
text = result.text or ""
if text.strip().startswith("{"):
    try:
        data = json.loads(text.strip())
        written = list(data.get("files_written", []))
    except Exception:
        pass
# ...
elif text:
    ui.console.print(text[:1500])
```

Só `files_written` é extraído. `summary` e `next_recommendation` são jogados num `print(text[:1500])` truncado, ou **descartados silenciosamente** quando `files_written` foi extraído com sucesso.

### Evidência
No teste, o agente retornou:
```json
"next_recommendation": {
  "slug": "planos-e-pacotes",
  "domain": "produto",
  "reason": "Os três planos comerciais (...) ainda não está documentado..."
}
```
A sugestão sumiu. O usuário nunca vê.

### Impacto
- Perde-se o gancho mais importante pro fluxo "qual o próximo guia?" — coração do `livedocs` (sem args).
- O agente já fez o trabalho intelectual de identificar a fronteira aberta; jogar fora é desperdício de tokens pagos.

### Plano de melhoria
**Fase 1 — Extrair e exibir (S, 1h):**
- Em `generate_guides`, extrair `next_recommendation` do JSON.
- Após o `ui.success(t("interview_complete"))`:
  ```
  ✓ Entrevista concluída!
  
  Arquivos criados:
    docs/produto/billing-engine.md
    docs/produto/billing-engine.tech.md
    docs/produto/_meta/billing-engine.interview.md
  
  💡 Próximo guia sugerido: planos-e-pacotes (produto)
     "Os três planos comerciais foram citados como peça central..."
  
     Rode: livedocs new planos-e-pacotes --domain produto
  ```

**Fase 2 — Persistir sugestão no state (S, 1h):**
- Adicionar campo `GlobalState.suggested_next: list[NextRecommendation]`.
- Mostrar no `livedocs` (root menu) como opção de menu: "Começar guia sugerido: planos-e-pacotes".

### Arquivos afetados
- `livedocs/state.py` (`NextRecommendation` model)
- `livedocs/commands/interview.py` (extração)
- `livedocs/commands/root.py` (consumo no menu)
- `livedocs/i18n.py` (strings novas)

### Critério de aceite
- Após `livedocs new` completo, sugestão aparece destacada.
- Em `livedocs` (sem args), com sugestão pendente, ela vira opção no menu.

---

## #3 — Custo/duração do agente não são logados
**Prio: P2 · Esforço: S · Categoria: Observabilidade**

### Descrição
`agent.py:135-142` retorna `AgentResult.cost_usd` e `duration_ms` mas nenhum chamador registra isso em lugar nenhum. O usuário não sabe se uma entrevista custou $0.05 ou $5.

### Impacto
- Sem visibilidade pra dimensionar custos antes de v2 (cloud paga).
- Usuário não consegue justificar custo de re-runs.
- Bug de custo (loop, prompt grande demais) passa silencioso.

### Plano de melhoria
**Fase 1 — Acumular no state (S, 1h):**
- Adicionar a `InterviewState`:
  ```python
  total_cost_usd: float = 0.0
  total_duration_ms: int = 0
  agent_calls: int = 0
  ```
- Cada call em `start_new_interview`, `_check_coverage`, `generate_guides` soma.

**Fase 2 — Exibir em status / review (S, 30min):**
- Coluna opcional `Custo` em `livedocs status` (--with-cost).
- Mostrar custo da rodada após cada `generate_guides`.

**Fase 3 — Flag `--verbose` global (S, 30min):**
- Loga `[agent] 12.3s, $0.04` no fim de cada chamada quando ativo.

### Arquivos afetados
- `livedocs/state.py`, `livedocs/agent.py`, `livedocs/commands/interview.py`, `livedocs/commands/status.py`

### Critério de aceite
- Após um `livedocs new`, `state.toml` contém `total_cost_usd > 0`.
- `livedocs status --with-cost` mostra coluna.

---

## #4 — i18n inline em 5 arquivos quebra a promessa multi-idioma
**Prio: P0 · Esforço: M · Categoria: Arquitetura**

### Descrição
README declara: *"Multi-idioma desde o dia 1 — auto-detecta idioma do sistema."* Mas espalhado pelo código:

```python
# new.py:49
ui.warn(f"'{slug}' já existe — use [bold]livedocs continue {slug}[/bold]." if cfg.lang == "pt-BR"
        else f"'{slug}' already exists — use [bold]livedocs continue {slug}[/bold].")

# review.py:25
ui.warn(f"{docs} {'não existe' if cfg.lang == 'pt-BR' else 'does not exist'}")

# cont.py:28
ui.info("Nenhuma entrevista em andamento." if cfg.lang == "pt-BR"
        else "No interview in progress.")

# root.py:49,52,53,54,76 — vários
```

Adicionar um terceiro idioma (ES, FR) requer caçar literais por todo o repo, não só editar `i18n.py`.

### Impacto
- Adicionar idioma novo é ~10x mais caro do que deveria.
- A condicional `if cfg.lang == "pt-BR" else ...` é frágil: o **default `_active_lang = "en"`** em `i18n.py:248` significa que se `cfg.lang` não for setado a tempo, alguns lugares mostram em pt-BR e outros em en (testei: `livedocs status` num projeto pt-BR ainda imprime "Em andamento" via `t()` mas o cabeçalho de tabela usa string literal).

### Evidência
```bash
$ rg "if .*\.lang ==" livedocs/
livedocs/commands/new.py:49:   ...
livedocs/commands/cont.py:28:  ...
livedocs/commands/review.py:25:...
livedocs/commands/root.py:49,52,53,54,76: ...
livedocs/commands/interview.py:108: ...
```
**6 arquivos com 12+ ocorrências.**

### Plano de melhoria
**Fase 1 — Auditoria (S, 1h):**
- Script `scripts/audit_i18n.py`: regex `if.*\.lang ==` + literais pt-BR/en hardcoded.
- Lista todos pendentes.

**Fase 2 — Mover pra `i18n.py` (M, 3h):**
- Cada literal vira chave: `err_already_exists`, `err_no_interview_in_progress`, `path_not_exist`, etc.
- Substituir condicionais por `t("key", slug=slug)`.

**Fase 3 — Lint preventivo (S, 1h):**
- Adicionar regra ruff custom OU teste pytest que falha se acha `if .*lang ==` em qualquer `livedocs/commands/`.

**Fase 4 — Estrutura de strings escalável (S, 1h):**
- Migrar `STRINGS` de dict aninhado pra arquivos por idioma: `livedocs/i18n/pt-BR.toml`, `en.toml`.
- Carregar lazy. Facilita PR de tradução pra novo idioma sem mexer em código.

### Arquivos afetados
- Todos em `livedocs/commands/` + `livedocs/i18n.py` (refator estrutural).

### Critério de aceite
- `rg "if .*\.lang ==" livedocs/` retorna 0 resultados.
- Adicionar idioma novo = só criar `livedocs/i18n/<lang>.toml` + 1 entrada em `supported_langs()`.

---

## #5 — `status="completed"` exibido como "Revisado" sem revisão humana
**Prio: P1 · Esforço: S · Categoria: Semântica**

### Descrição
`status.py` mapeia `InterviewState.status == "completed"` → label `t("status_reviewed")` = "Revisado". Mas "completed" significa *o agente terminou de gerar*, não *o humano revisou*.

### Evidência
No smoke test, depois do `generate_guides`, sem nenhum input humano:
```
┃ slug           ┃ domain  ┃ status   ┃
│ billing-engine │ produto │ Revisado │
```

### Impacto
- Mente pro usuário: ele acha que já revisou guias que nunca abriu.
- Em equipe, alguém olha o status e assume "ok, aprovado". Não foi.
- Quebra o princípio do README: *"Sempre humano-no-loop — IA propõe, dev aprova."*

### Plano de melhoria
**Fase 1 — Separar conceitos (S, 1h):**
- `InterviewState.status` ganha mais um valor: `"generated"` (entre completed e reviewed).
  ```
  draft → in_progress → generated → reviewed → stale
  ```
- `generate_guides` seta para `"generated"`, NÃO `"completed"`.
- Adicionar comando `livedocs approve <slug>` que seta `"reviewed"`.

**Fase 2 — Front-matter `status` (S, 30min):**
- Hoje o agente já escreve `status: reviewed` no front-matter por instrução do prompt. Mudar pra `status: generated` por default.
- `livedocs approve` reescreve o front-matter pra `reviewed`.

**Fase 3 — Lembretes (S, 30min):**
- `livedocs status` mostra "⚠️ 3 guias gerados aguardando aprovação".
- `livedocs review` ao final pergunta "marcar como aprovado?" se passou nos checks.

### Arquivos afetados
- `livedocs/state.py` (status enum)
- `livedocs/commands/interview.py` (set generated)
- `livedocs/skill/__init__.py` (prompt: `status: generated`)
- `livedocs/commands/status.py` (label novo)
- `livedocs/commands/approve.py` (novo)
- `livedocs/i18n.py` (chaves novas)

### Critério de aceite
- Após `livedocs new`, status fica "Gerado, aguardando aprovação".
- `livedocs approve foo` muda pra "Aprovado".

---

## #6 — `--permission-mode=acceptEdits` é foot-gun
**Prio: P0 · Esforço: S · Categoria: Segurança**

### Descrição
`agent.py:73` usa:
```python
"--permission-mode=acceptEdits",
```

Isso **dá ao Claude Code permissão de editar qualquer arquivo no diretório `--add-dir`** sem prompt. O prompt instrui o agente a só escrever os 3 .md em `docs/<domain>/`, mas o agente pode confundir e editar `app/billing.py` (ele tem o tool Edit habilitado).

### Impacto
- **Risco real de modificação não-autorizada de código fonte.** Especialmente perigoso em monorepos como <Client> (cwd = `~/dev/<client>/main`).
- O usuário não tem como auditar o que foi modificado fora de `docs/`.
- Quebra o princípio do README: *"Sempre humano-no-loop"*. Edições acontecem sem o humano.

### Plano de melhoria
**Fase 1 — Whitelist de tools, não permission-mode (S, 1h):**
- Trocar `--permission-mode=acceptEdits` por:
  ```python
  "--allowedTools", "Read,Glob,Grep,Write",
  "--disallowedTools", "Edit,Bash,WebFetch",
  ```
- `Write` cria arquivos novos (basta pros .md). `Edit` modificaria existentes (não queremos).
- Verificar com `claude --print --help` o nome exato da flag (pode ser `--allowed-tools`).

**Fase 2 — Restringir cwd a `docs_dir` quando possível (S, 1h):**
- `--add-dir <repo>` pra leitura de código (necessário pra entender contexto).
- Mas o write deve ser monitorado. Pós-call: comparar `git status` antes/depois e abortar/avisar se o agente tocou em arquivos fora de `<docs_dir>/`.

**Fase 3 — Modo paranoia (S, 1h):**
- Flag `--paranoid`: agent gera guides em `/tmp/livedocs-staging/`, CLI move pra `docs/` após `git diff` aprovado pelo usuário.

### Arquivos afetados
- `livedocs/agent.py` (flags)
- `livedocs/commands/interview.py` (verificação pós-call)

### Critério de aceite
- Test: agente recebe prompt malicioso ("delete o README"), não consegue (tool não permitido).
- Test: arquivos fora de `docs/` não foram modificados depois de `livedocs new`.

---

## #7 — Faltam comandos de gestão de interview
**Prio: P1 · Esforço: M · Categoria: UX**

### Descrição
Hoje só existe: `init`, `new`, `continue`, `status`, `review`, `version`. Não existe:
- **`livedocs delete <slug>`** — apagar entrevista (e arquivos gerados?)
- **`livedocs regenerate <slug>`** — regerar os .md a partir do state existente (sem refazer entrevista)
- **`livedocs reopen <slug>`** — voltar uma entrevista "completed" pra "in_progress" (descobriu que faltou perguntar algo)
- **`livedocs approve <slug>`** — marcar como reviewed (vide #5)

Pra apagar uma entrevista hoje, **edita-se `state.toml` na mão**. Pra regenerar, mesma coisa.

### Impacto
- Workflow real fica travado. Tagôre vai precisar pelo menos de `regenerate` no dogfood do <Client> (várias iterações).
- Editar `state.toml` à mão é frágil (TOML aninhado, fácil corromper).

### Plano de melhoria
**Fase 1 — Comandos básicos (M, 4h):**
```
livedocs delete <slug>        # remove do state, opcional --keep-files
livedocs regenerate <slug>    # mesmo state, novos .md (útil após editar resposta no state.toml)
livedocs reopen <slug>        # status → in_progress, permite continue
livedocs approve <slug>       # status → reviewed (vide #5)
```

**Fase 2 — Editar resposta sem CLI (S, 2h):**
- `livedocs edit <slug> <question_id>` abre `$EDITOR` na resposta dessa pergunta. Salva no state. Marca interview como `needs_regenerate`.

**Fase 3 — Listagem detalhada (S, 2h):**
- `livedocs status <slug>` mostra detalhes daquela entrevista: blocos, perguntas, respostas, custo, datas.

### Arquivos afetados
- `livedocs/commands/delete.py`, `regenerate.py`, `reopen.py`, `approve.py`, `edit.py` (novos)
- `livedocs/cli.py` (registrar)
- `livedocs/i18n.py`

### Critério de aceite
- `livedocs delete foo --keep-files` remove do state mas mantém os .md.
- `livedocs regenerate foo` chama só `generate_guides`, sem nova entrevista.
- `livedocs reopen foo` permite `livedocs continue foo` depois.

---

## #8 — Flag `--model` não exposta no CLI
**Prio: P2 · Esforço: S · Categoria: UX**

### Descrição
`ClaudeAgent.__init__` aceita `model: str | None`. Útil pra escolher entre Sonnet/Opus/Haiku conforme custo. Mas o CLI nunca passa: `agent = ClaudeAgent(repo_root, lang=cfg.lang)` em todos os call sites.

### Impacto
- Usuário gasta com modelo default (Opus 4) mesmo quando Haiku seria suficiente (ex: coverage check é trivial).
- Não dá pra forçar Sonnet em CI pra economizar.

### Plano de melhoria
**Fase 1 — Config persistente (S, 1h):**
- Adicionar a `ProjectConfig`:
  ```python
  model_interview: str | None = None      # gerar perguntas + guides
  model_coverage: str | None = None       # coverage check (default mais barato)
  ```
- `livedocs init` pergunta opcionalmente.

**Fase 2 — Flag CLI override (S, 30min):**
- `livedocs new foo --model claude-sonnet-4` sobrescreve.
- `livedocs new foo --cheap` usa preset (Haiku pra coverage, Sonnet pra resto).

**Fase 3 — Telemetria pra default inteligente (futuro):**
- Após N rodadas, sugerir modelo baseado em razão custo/qualidade no histórico.

### Arquivos afetados
- `livedocs/state.py`, `livedocs/cli.py`, `livedocs/agent.py`, todos os comandos.

### Critério de aceite
- `livedocs new foo --model claude-haiku-4` passa `--model` ao Claude CLI.
- `config.toml` aceita `model_interview = "claude-sonnet-4"`.

---

## #9 — `schema_version` não validada na leitura
**Prio: P2 · Esforço: S · Categoria: Robustez**

### Descrição
`ProjectConfig.schema_version: int = 1` e `GlobalState.schema_version: int = 1` existem. Mas `load_config` e `load_state` fazem `model_validate(data)` direto. Se eu mudar pra `schema_version=2` e o usuário tem state v1, **Pydantic carrega ignorando**.

### Impacto
- Pequeno **agora**. Sério **depois** que o schema evoluir (e vai evoluir — vide #5, #7).
- Sem migrations, todo upgrade quebra silenciosamente.

### Plano de melhoria
**Fase 1 — Validar e errar claro (S, 30min):**
- Em `load_config`/`load_state`:
  ```python
  if data.get("schema_version", 1) > CURRENT_SCHEMA_VERSION:
      raise ValueError("state.toml é de uma versão mais nova do livedocs (vX). Atualize o livedocs.")
  ```

**Fase 2 — Migrations explícitas (S, 1h):**
- `livedocs/migrations.py` com função `migrate(data, from_v, to_v)`.
- Rodar antes de `model_validate`.
- Backup do `state.toml` em `.bak` antes de migrar.

### Arquivos afetados
- `livedocs/state.py` + `livedocs/migrations.py` (novo).

### Critério de aceite
- State de versão futura erra com mensagem clara.
- State de versão passada migra automaticamente com backup.

---

## #10 — `generate_guides` não verifica arquivos escritos
**Prio: P1 · Esforço: S · Categoria: Robustez**

### Descrição
Em `interview.py:285-303`:
```python
if text.strip().startswith("{"):
    try:
        data = json.loads(text.strip())
        written = list(data.get("files_written", []))
    except Exception:
        pass
ui.success(t("interview_complete"))
```

**Confia no que o agente disse**, sem checar se os arquivos existem. Se o agente:
- Errou o caminho (`docs/produto/foo.md` mas escreveu em `docs/foo.md`)
- Não conseguiu escrever (sem permissão)
- Retornou JSON inventado (alucinação)

→ CLI declara sucesso, status vai pra "completed", mas **não há .md no disco**.

### Impacto
- Falha silenciosa. Usuário só descobre quando vai abrir o guide.
- Detectada apenas pelo `livedocs review` que vai dizer "Sem guias ainda" — mas a interview tá "completed".

### Plano de melhoria
**Fase 1 — Verificar existência (S, 30min):**
- Após call, fazer:
  ```python
  missing = [f for f in written if not (repo_root / f).exists()]
  if missing:
      ui.error(f"Agente alegou criar {len(written)} arquivos mas {len(missing)} não existem: {missing}")
      interview.status = "in_progress"  # não marca como completed
      return False
  ```

**Fase 2 — Pré-condição: limpar staging (S, 30min):**
- Antes da call, snapshot de `<docs_dir>/<domain>/` (lista de arquivos + mtimes).
- Após call, computar diff. Se `files_written` ≠ diff real, alertar.

**Fase 3 — Validação de conteúdo (S, 1h):**
- Cada `.md` gerado: tem front-matter? tem `flavor` correto? body não-vazio?
- Reusa parser de `review.py`.

### Arquivos afetados
- `livedocs/commands/interview.py`, `livedocs/commands/review.py` (extrair `_validate_guide`).

### Critério de aceite
- Mock: agente retorna `files_written=["fake.md"]`, CLI detecta e não marca como completed.

---

## #11 — `coverage_check` ignora respostas parciais
**Prio: P2 · Esforço: M · Categoria: Qualidade**

### Descrição
`PROMPT_COVERAGE_CHECK` (skill) instrui o agente a retornar:
```json
{ "covered": ["A2"], "partial": [{"id": "A4", "missing": "still unclear about X"}] }
```

Mas `_check_coverage` em `interview.py:191-212`:
```python
raw = data.get("covered", [])
return [str(x) for x in raw if isinstance(x, str)]
```

`partial` é jogado fora. Informação valiosa perdida — o agente identificou que A4 foi *parcialmente* coberto e disse exatamente o que falta. Poderíamos:
- Anexar o `missing` à pergunta A4 como contexto extra
- Mostrar pra dev: "💡 A4 já foi quase respondida, falta só: still unclear about X"

### Impacto
- Entrevistas mais longas que poderiam ser.
- Frustração do dev: "já respondi isso!" mas o sistema não soube cruzar.

### Plano de melhoria
**Fase 1 — Capturar partial (S, 2h):**
- `QuestionState` ganha `hint_from_other: str | None = None`.
- Quando partial chega, salvar o `missing` lá.
- Quando a pergunta vira a próxima, exibir hint antes do prompt:
  ```
  💡 Você já tocou nesse assunto antes (em A2). 
     Falta esclarecer: still unclear about X
  ```

**Fase 2 — Coverage agressivo opcional (M, 3h):**
- Flag `--smart-coverage`: ao invés de só uma pergunta por vez, agente analisa TODA a resposta vs TODAS as pendentes em batches de 5.
- Mais cara mas reduz drasticamente o número de perguntas.

### Arquivos afetados
- `livedocs/state.py`, `livedocs/commands/interview.py`, `livedocs/skill/__init__.py`.

### Critério de aceite
- Após responder A1 com "fatura interna mas NF é externa", a pergunta A4 sobre fonte da verdade exibe hint contextual.

---

## #12 — Zero testes apesar de pytest no `pyproject.toml`
**Prio: P0 · Esforço: L · Categoria: Qualidade**

### Descrição
`pyproject.toml` declara `pytest>=8.0.0` em dev. Não há diretório `tests/`. Não há um único teste.

```bash
$ find . -name "test_*.py" -o -name "*_test.py" -not -path "./.venv/*"
# (nada)
```

### Impacto
- Cada refactor (e #4 + #7 vão exigir refactors profundos) é roleta russa.
- Smoke test E2E só foi possível com Claude rodando — caro pra repetir.
- v1+ vai virar bola de neve sem rede de proteção.

### Plano de melhoria
**Fase 1 — Mock do Claude (S, 2h):**
- `tests/_fakes.py`: `FakeClaudeAgent` com respostas fixadas em fixtures JSON.
- Injetar via env var `LIVEDOCS_FAKE_AGENT=tests/fixtures/billing-interview.json`.

**Fase 2 — Unit tests (M, 4h):**
- `test_state.py`: round-trip TOML, schema_version, migrations.
- `test_i18n.py`: detecção de locale, fallback, kwargs.
- `test_review.py`: front-matter parsing, casos edge (yaml inválido, body vazio).
- `test_detect.py`: has_git_repo em mock filesystem, project_slug_suggestion.

**Fase 3 — E2E com fake agent (M, 4h):**
- `test_e2e_new.py`: simula `livedocs new` ponta-a-ponta com FakeClaudeAgent.
- Verifica state.toml + .md no filesystem temporário.

**Fase 4 — Smoke real opcional (S, 1h):**
- Marker `@pytest.mark.real_agent` skipado por default. Roda só com `pytest -m real_agent` (CI semanal, manual).

**Fase 5 — Coverage gate (S, 30min):**
- `pytest-cov` com gate de 70% mínimo em `livedocs/`.

### Arquivos afetados
- `tests/` (novo dir), `pyproject.toml` (pytest config, ruff exclude tests).

### Critério de aceite
- `pytest` passa com 30+ tests.
- Coverage ≥70%.
- `pytest -m real_agent` testa um fluxo real (custo conhecido).

---

## #13 — Sem CI / sem distribuição
**Prio: P1 · Esforço: M · Categoria: Distribuição**

### Descrição
- Sem GitHub Actions / CI.
- Não publicado em PyPI.
- `uvx livedocs` (objetivo declarado em A1 do `lacunas.md`) **nunca foi testado**.
- README diz "alpha — dogfood interno" mas não diz como instalar.

### Impacto
- Outros não conseguem testar nem com clone manual.
- Bugs de empacotamento (exemplo: `livedocs/skill/SKILL.md` está em `force-include` no hatch — funciona em dev mas não verificado em wheel build) só aparecem em produção.

### Plano de melhoria
**Fase 1 — CI básico (S, 2h):**
- `.github/workflows/ci.yml`: ruff + pytest (após #12) + build wheel + verificar wheel.
- Matrix Python 3.11 / 3.12 / 3.13.

**Fase 2 — Testar uvx local (S, 1h):**
- `uv build`, `uvx --from ./dist/livedocs-0.1.0-py3-none-any.whl livedocs --help`.
- Verificar que SKILL.md tá no wheel: `unzip -l dist/*.whl | grep SKILL`.

**Fase 3 — Publicar TestPyPI (S, 1h):**
- Conta TestPyPI, `uv publish --publish-url https://test.pypi.org/legacy/`.
- Testar `uvx --from livedocs-test livedocs`.

**Fase 4 — Release workflow (M, 3h):**
- Tag → build → publish PyPI automático.
- Changelog.md.
- v0.1.1 release real após #4 + #6 + #12.

### Arquivos afetados
- `.github/workflows/ci.yml`, `.github/workflows/release.yml` (novos).
- `CHANGELOG.md` (novo).
- `pyproject.toml` (ajustes hatch).

### Critério de aceite
- PR aciona CI, ruff + pytest verde.
- `uvx livedocs --help` funciona em máquina limpa.

---

## Plano de execução sugerido (3 sprints)

### Sprint 1 — Hardening (P0)
**Meta:** v0.1.1 — confiável o suficiente pra dogfood <Client>.
- #6 segurança (acceptEdits → allowedTools) — bloqueante
- #4 i18n consolidado — refactor estrutural antes de adicionar features
- #12 fundação de testes (Fase 1+2 mínimo)
- #5 separar generated/reviewed

### Sprint 2 — UX (P1)
**Meta:** v0.2.0 — fluxo de iteração real.
- #7 comandos de gestão (delete, regenerate, reopen, approve)
- #1 modo non-interactive (Fases 1+2)
- #2 next_recommendation
- #10 verificar arquivos escritos
- #13 CI + TestPyPI

### Sprint 3 — Polish (P2)
**Meta:** v0.3.0 — pronto pra publicar publicamente.
- #3 custos
- #8 model selection
- #9 schema versioning
- #11 partial coverage
- #12 testes E2E (Fase 3+4)
- #13 PyPI release oficial

Depois do Sprint 3, **v0.5 (graphify integration)** entra com base sólida.

---

## Notas de descoberta

1. **Smoke test passou ponta-a-ponta** em `/tmp/livedocs-smoke` — Claude leu app sample (4 arquivos, 24 LOC), gerou 24 perguntas em 6 blocos com referências precisas ao código (`PLAN_PRICES`, `monthly_invoice:13-15`), produziu 391 linhas de markdown coerente em 80s.
2. **Qualidade dos guides gerados foi alta** — narrativa correta em pt-BR, hipóteses marcadas com 🟡 conforme instruído, mermaid funcionando, `file:line` citados, regras invariantes R1-R5 numeradas, 13 pendências marcadas para perguntas puladas.
3. **Custo do test:** ~80s wall-clock, 2 chamadas (interview prep + generate guides). Coverage check só roda quando há resposta + outras pendentes; pulamos diretas pra simular então não rodou no smoke.

A base é sólida. As issues acima são realista pra um v0 que acabou de nascer — nenhuma é showstopper, mas as P0 (#4, #6, #12) precisam sair antes de mais features porque elas mudam a forma como o resto será escrito.
