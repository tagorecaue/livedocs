"""i18n — sistema simples de tradução baseado em dicts.

Auto-detecta locale do SO. Suporta pt-BR e en por padrão.
A primeira execução do `livedocs init` confirma o idioma com o usuário.
"""

from __future__ import annotations

import contextlib
import locale
import os
from typing import Literal

Lang = Literal["pt-BR", "en"]

# ---------------------------------------------------------------------------
# Strings
# ---------------------------------------------------------------------------

STRINGS: dict[str, dict[Lang, str]] = {
    # ---- shared ----
    "yes": {"pt-BR": "sim", "en": "yes"},
    "no": {"pt-BR": "não", "en": "no"},
    "cancel": {"pt-BR": "cancelar", "en": "cancel"},
    "back": {"pt-BR": "voltar", "en": "back"},
    "continue": {"pt-BR": "continuar", "en": "continue"},
    "skip": {"pt-BR": "pular", "en": "skip"},
    "exit": {"pt-BR": "sair", "en": "exit"},
    # ---- splash ----
    "tagline": {
        "pt-BR": "documentação viva, guiada por entrevista",
        "en": "living documentation, interview-driven",
    },
    # ---- root menu (livedocs sem args) ----
    "no_project_title": {
        "pt-BR": "Nenhum projeto LiveDocs detectado neste diretório.",
        "en": "No LiveDocs project detected in this directory.",
    },
    "no_project_hint": {
        "pt-BR": "Rode [bold]livedocs init[/bold] para começar.",
        "en": "Run [bold]livedocs init[/bold] to get started.",
    },
    "no_project_init_q": {
        "pt-BR": "Quer inicializar o LiveDocs neste diretório agora?",
        "en": "Initialize LiveDocs in this directory now?",
    },
    "where_we_left": {
        "pt-BR": "Onde paramos",
        "en": "Where we left off",
    },
    "what_now": {
        "pt-BR": "O que vamos fazer agora?",
        "en": "What shall we do now?",
    },
    # ---- init wizard ----
    "init_welcome": {
        "pt-BR": "Vamos configurar o LiveDocs neste projeto.",
        "en": "Let's set up LiveDocs in this project.",
    },
    "init_lang_q": {
        "pt-BR": "Em qual idioma os guias devem ser escritos?",
        "en": "In which language should the guides be written?",
    },
    "init_lang_detected": {
        "pt-BR": "(detectei [bold]{lang}[/bold] no seu sistema)",
        "en": "(I detected [bold]{lang}[/bold] on your system)",
    },
    "init_project_name_q": {
        "pt-BR": "Nome curto do projeto (slug)?",
        "en": "Short name for the project (slug)?",
    },
    "init_provider_q": {
        "pt-BR": "Qual agente IA você quer usar?",
        "en": "Which AI agent do you want to use?",
    },
    "init_provider_detected": {
        "pt-BR": "Detectado: [bold]{provider}[/bold]",
        "en": "Detected: [bold]{provider}[/bold]",
    },
    "init_provider_not_found": {
        "pt-BR": "[yellow]Aviso:[/yellow] Claude Code CLI ([bold]claude[/bold]) não foi encontrada no PATH. Instale antes de rodar entrevistas.",
        "en": "[yellow]Warning:[/yellow] Claude Code CLI ([bold]claude[/bold]) not found on PATH. Install before running interviews.",
    },
    "init_docs_dir_q": {
        "pt-BR": "Diretório de saída dos guias?",
        "en": "Output directory for guides?",
    },
    "init_docs_dir_existing": {
        "pt-BR": "Detectei [bold]{path}[/bold] já existente com {count} arquivo(s) .md.",
        "en": "I detected an existing [bold]{path}[/bold] with {count} .md file(s).",
    },
    "init_docs_dir_action_q": {
        "pt-BR": "O que fazer?",
        "en": "What should we do?",
    },
    "init_docs_dir_use": {
        "pt-BR": "Reaproveitar (importar guias existentes)",
        "en": "Reuse (import existing guides)",
    },
    "init_docs_dir_other": {
        "pt-BR": "Usar outro diretório",
        "en": "Use another directory",
    },
    "init_docs_dir_fresh": {
        "pt-BR": "Começar do zero (em outro diretório)",
        "en": "Start fresh (in another directory)",
    },
    "init_graphify_detected": {
        "pt-BR": "Detectei [bold]graphify[/bold] disponível — podemos gerar um grafo do código pra ajudar nas perguntas.",
        "en": "I detected [bold]graphify[/bold] available — we can generate a code graph to help with the questions.",
    },
    "init_graphify_q": {
        "pt-BR": "Quer usar o graphify agora?",
        "en": "Want to use graphify now?",
    },
    "init_done": {
        "pt-BR": "Pronto! LiveDocs configurado em [bold]{path}[/bold].",
        "en": "Done! LiveDocs configured at [bold]{path}[/bold].",
    },
    "init_next_step": {
        "pt-BR": "Rode [bold]livedocs[/bold] (sem argumentos) e eu te guio a partir daqui.",
        "en": "Run [bold]livedocs[/bold] (no args) and I'll guide you from there.",
    },
    "init_style_q": {
        "pt-BR": "Qual estilo de escrita você quer para os guias?",
        "en": "Which writing style do you want for your guides?",
    },
    "init_style_hint": {
        "pt-BR": "Você pode personalizar isso depois editando [bold].livedocs/style.md[/bold]",
        "en": "You can customize this later by editing [bold].livedocs/style.md[/bold]",
    },
    "init_style_customize": {
        "pt-BR": "Para personalizar o estilo: edite [bold]{path}[/bold].",
        "en": "To customize the style: edit [bold]{path}[/bold].",
    },
    "init_guides_subdir_detected": {
        "pt-BR": "Layout [bold]{subdir}/<dom>/<slug>.md[/bold] detectado — vou usar.",
        "en": "Layout [bold]{subdir}/<domain>/<slug>.md[/bold] detected — using it.",
    },
    "init_imported_guides": {
        "pt-BR": "Importei {n} guia(s) existente(s) — rode [bold]livedocs status[/bold] para ver.",
        "en": "Imported {n} existing guide(s) — run [bold]livedocs status[/bold] to see them.",
    },
    # ---- free-text intent (rewritten for v0.2 fact-driven flow) ----
    "intent_q": {
        "pt-BR": "O que você quer documentar?",
        "en": "What do you want to document?",
    },
    # ---- new guide ----
    "new_slug_q": {
        "pt-BR": "Slug do guia (kebab-case, ex: pagamento-de-repasses):",
        "en": "Guide slug (kebab-case, e.g. payment-routing):",
    },
    "new_domain_q": {
        "pt-BR": "Em qual domínio vai esse guia?",
        "en": "Which domain does this guide belong to?",
    },
    "new_domain_new": {
        "pt-BR": "+ Novo domínio…",
        "en": "+ New domain…",
    },
    # ---- interview ----
    "interview_starting": {
        "pt-BR": "Iniciando entrevista para [bold]{slug}[/bold]…",
        "en": "Starting interview for [bold]{slug}[/bold]…",
    },
    "interview_thinking": {
        "pt-BR": "O agente está lendo o código e preparando perguntas",
        "en": "The agent is reading the code and preparing questions",
    },
    "interview_block": {
        "pt-BR": "Bloco {block} — {topic}",
        "en": "Block {block} — {topic}",
    },
    "interview_question_n": {
        "pt-BR": "Pergunta {n} de {total}",
        "en": "Question {n} of {total}",
    },
    "interview_answer_q": {
        "pt-BR": "Sua resposta",
        "en": "Your answer",
    },
    "interview_skip_hint": {
        "pt-BR": "(deixe vazio para pular, [bold]/sair[/bold] para voltar depois, [bold]/editor[/bold] pra abrir o editor)",
        "en": "(leave empty to skip, [bold]/exit[/bold] to come back later, [bold]/editor[/bold] to open editor)",
    },
    "interview_covered_others": {
        "pt-BR": "Sua resposta também cobriu: {questions}",
        "en": "Your answer also covered: {questions}",
    },
    "interview_covered_q": {
        "pt-BR": "Marcar essas como respondidas?",
        "en": "Mark those as answered?",
    },
    "interview_paused": {
        "pt-BR": "Entrevista pausada. Rode [bold]livedocs continue[/bold] quando quiser retomar.",
        "en": "Interview paused. Run [bold]livedocs continue[/bold] when you want to resume.",
    },
    "interview_complete": {
        "pt-BR": "Entrevista concluída!",
        "en": "Interview complete!",
    },
    "interview_generating": {
        "pt-BR": "Gerando guia v1 com cross-links",
        "en": "Generating v1 guide with cross-links",
    },
    "interview_files_created": {
        "pt-BR": "Arquivos criados/atualizados:",
        "en": "Files created/updated:",
    },
    "interview_files_missing": {
        "pt-BR": "Agente alegou criar {total} arquivos mas {n} não existem no disco:",
        "en": "Agent claimed to create {total} files but {n} are missing on disk:",
    },
    "interview_files_missing_hint": {
        "pt-BR": "Entrevista mantida em [bold]in_progress[/bold]. Rode [bold]livedocs continue[/bold] para tentar regerar.",
        "en": "Interview kept as [bold]in_progress[/bold]. Run [bold]livedocs continue[/bold] to retry.",
    },
    "interview_no_files_written": {
        "pt-BR": "Agente não retornou lista de arquivos e nenhum guia foi encontrado em disco.",
        "en": "Agent returned no file list and no guides were found on disk.",
    },
    "interview_files_recovered": {
        "pt-BR": "Agente não detalhou arquivos no JSON, mas {n} guia(s) foram encontrados em disco e aceitos.",
        "en": "Agent did not list files in JSON, but {n} guide(s) were found on disk and accepted.",
    },
    "cost_summary": {
        "pt-BR": "{calls} chamada(s) ao agente, US${cost:.4f}, {secs:.1f}s",
        "en": "{calls} agent call(s), US${cost:.4f}, {secs:.1f}s",
    },
    "interview_next_suggested": {
        "pt-BR": "Próximo guia sugerido:",
        "en": "Suggested next guide:",
    },
    "interview_next_command": {
        "pt-BR": "Quando quiser começar: [bold]livedocs new {slug} --domain {domain}[/bold]",
        "en": "When ready: [bold]livedocs new {slug} --domain {domain}[/bold]",
    },
    # ---- status ----
    "status_title": {
        "pt-BR": "Estado dos guias",
        "en": "Guide status",
    },
    "status_total": {
        "pt-BR": "Total: {n} guia(s)",
        "en": "Total: {n} guide(s)",
    },
    "status_total_cost": {
        "pt-BR": "Custo acumulado: {calls} chamada(s), US${cost:.4f}",
        "en": "Accumulated cost: {calls} call(s), US${cost:.4f}",
    },
    "status_no_guides": {
        "pt-BR": "Nenhum guia ainda. Rode [bold]livedocs new <slug>[/bold] para começar o primeiro.",
        "en": "No guides yet. Run [bold]livedocs new <slug>[/bold] to start the first one.",
    },
    "status_in_progress": {
        "pt-BR": "Em andamento",
        "en": "In progress",
    },
    "status_generated": {
        "pt-BR": "Gerado (aguardando aprovação)",
        "en": "Generated (awaiting approval)",
    },
    "status_reviewed": {
        "pt-BR": "Revisado",
        "en": "Reviewed",
    },
    "status_draft": {
        "pt-BR": "Rascunho",
        "en": "Draft",
    },
    "status_stale": {
        "pt-BR": "Defasado (código mudou)",
        "en": "Stale (code changed)",
    },
    # ---- errors / common ----
    "err_no_claude": {
        "pt-BR": "Claude Code CLI não encontrada. Instale: [link=https://claude.com/code]claude.com/code[/link]",
        "en": "Claude Code CLI not found. Install: [link=https://claude.com/code]claude.com/code[/link]",
    },
    "err_not_a_repo": {
        "pt-BR": "Este diretório não é um repositório git. Rode [bold]git init[/bold] antes.",
        "en": "This directory is not a git repo. Run [bold]git init[/bold] first.",
    },
    "err_no_project": {
        "pt-BR": "Nenhum projeto LiveDocs aqui. Rode [bold]livedocs init[/bold] primeiro.",
        "en": "No LiveDocs project here. Run [bold]livedocs init[/bold] first.",
    },
    "abort": {
        "pt-BR": "Cancelado.",
        "en": "Aborted.",
    },
    # ---- non-interactive (#1) ----
    "answers_file_applied": {
        "pt-BR": "Respostas aplicadas: {answered} respondidas, {skipped} puladas (de {total}).",
        "en": "Answers applied: {answered} answered, {skipped} skipped (of {total}).",
    },
    "answers_file_unknown_ids": {
        "pt-BR": "IDs de pergunta desconhecidos no arquivo (ignorados): {ids}",
        "en": "Unknown question IDs in file (ignored): {ids}",
    },
    "err_non_interactive_needs_answers": {
        "pt-BR": "Modo não-interativo exige [bold]--answers-file[/bold]. Sem ele, a entrevista precisaria perguntar e não há TTY.",
        "en": "Non-interactive mode requires [bold]--answers-file[/bold]. Without it, the interview would need to prompt and there's no TTY.",
    },
    # ---- approve ----
    "approve_none_pending": {
        "pt-BR": "Nenhum guia aguardando aprovação.",
        "en": "No guides awaiting approval.",
    },
    "approve_pick_q": {
        "pt-BR": "Qual guia aprovar?",
        "en": "Which guide do you want to approve?",
    },
    "approve_wrong_status": {
        "pt-BR": "[bold]{slug}[/bold] está em [bold]{status}[/bold] — só guias em [bold]generated[/bold] podem ser aprovados.",
        "en": "[bold]{slug}[/bold] is [bold]{status}[/bold] — only [bold]generated[/bold] guides can be approved.",
    },
    "approve_done": {
        "pt-BR": "Guia [bold]{slug}[/bold] aprovado. Status: [ok]reviewed[/ok].",
        "en": "Guide [bold]{slug}[/bold] approved. Status: [ok]reviewed[/ok].",
    },
    "err_slug_not_found": {
        "pt-BR": "Slug [bold]{slug}[/bold] não encontrado.",
        "en": "Slug [bold]{slug}[/bold] not found.",
    },
    # ---- bootstrap pipeline (phases 0-7) ----
    "bootstrap_guidance_intro": {
        "pt-BR": "LiveDocs vai documentar seu sistema. Antes de começar, conta um pouco sobre o contexto:",
        "en": "LiveDocs will document your system. Before we start, tell us a bit about the context:",
    },
    "bootstrap_guidance_prompt": {
        "pt-BR": (
            "Me conta aqui quem você é, o que o sistema faz, para que serve.\n"
            "Você pode colar referências, instruções gerais ou qualquer coisa que ajude a IA durante o processo de documentação.\n"
            "(Vazio é ok — pressione Enter sem digitar.)"
        ),
        "en": (
            "Tell us who you are, what the system does, and what it's for.\n"
            "You can paste references, general instructions, or anything that helps the AI while it documents.\n"
            "(Empty is fine — just press Enter.)"
        ),
    },
    "bootstrap_guidance_too_long": {
        "pt-BR": "Orientação muito longa ({n} caracteres). Aceita, mas pode encher contexto.",
        "en": "Guidance is very long ({n} chars). Accepted, but may bloat context.",
    },
    "bootstrap_phase_guidance": {
        "pt-BR": "Fase 0/7 — Orientação",
        "en": "Phase 0/7 — Guidance",
    },
    "bootstrap_phase_scan": {
        "pt-BR": "Fase 1/7 — Varredura do código",
        "en": "Phase 1/7 — Code scan",
    },
    "bootstrap_phase_taxonomy": {
        "pt-BR": "Fase 2/7 — Taxonomia proposta",
        "en": "Phase 2/7 — Proposed taxonomy",
    },
    "bootstrap_phase_taxonomy_review": {
        "pt-BR": "Fase 3/7 — Revisão da taxonomia",
        "en": "Phase 3/7 — Taxonomy review",
    },
    "bootstrap_graphify_missing": {
        "pt-BR": "graphify não encontrado no PATH — sigo sem o grafo. (Instale com `pip install graphify` se quiser.)",
        "en": "graphify not found on PATH — continuing without graph. (Install via `pip install graphify` if you want it.)",
    },
    "bootstrap_scan_done": {
        "pt-BR": "Scan: {routes} rota(s), {i18n} chave(s) i18n, {models} modelo(s).",
        "en": "Scan: {routes} route(s), {i18n} i18n key(s), {models} model(s).",
    },
    "bootstrap_taxonomy_deriving": {
        "pt-BR": "Derivando capacidades e jornadas a partir do scan…",
        "en": "Deriving capabilities and journeys from the scan…",
    },
    "bootstrap_taxonomy_bad_json": {
        "pt-BR": "O agente não devolveu JSON de taxonomia válido.",
        "en": "Agent did not return valid taxonomy JSON.",
    },
    "bootstrap_review_actions": {
        "pt-BR": "O que você quer fazer com a taxonomia?",
        "en": "What do you want to do with the taxonomy?",
    },
    "bootstrap_review_aborted": {
        "pt-BR": "Revisão abortada pelo usuário.",
        "en": "Review aborted by user.",
    },
    "bootstrap_review_approved": {
        "pt-BR": "Taxonomia aprovada com {caps} capacidade(s) e {jrn} jornada(s).",
        "en": "Taxonomy approved with {caps} capability/ies and {jrn} journey(s).",
    },
    "bootstrap_review_preview_written": {
        "pt-BR": "Preview salvo em [bold]{path}[/bold]",
        "en": "Preview written to [bold]{path}[/bold]",
    },
    "bootstrap_phases_4_7_todo": {
        "pt-BR": "Fases 4-7 ainda não implementadas. Rode novamente com [bold]livedocs bootstrap --resume[/bold] quando estiverem.",
        "en": "Phases 4-7 not implemented yet. Run [bold]livedocs bootstrap --resume[/bold] again later.",
    },
    "bootstrap_need_init": {
        "pt-BR": "Nenhum projeto LiveDocs aqui. Rode [bold]livedocs init[/bold] antes do bootstrap.",
        "en": "No LiveDocs project here. Run [bold]livedocs init[/bold] before bootstrapping.",
    },
    # ---- v0.2 — Adaptive interview (fact-driven) — only the NEW keys.
    # Keys reused from v0.1 (intent_q, interview_*) are NOT redefined.
    "intent_hint": {
        "pt-BR": "Ex.: \"a tela de pagamento de repasses do menu financeiro\"",
        "en": "E.g.: \"the payment routing screen in the finance menu\"",
    },
    "intent_parsing": {
        "pt-BR": "Interpretando sua intenção",
        "en": "Parsing your intent",
    },
    "intent_parse_failed": {
        "pt-BR": "Não consegui interpretar a descrição. Tente reformular ou usar [bold]--slug[/bold]/[bold]--domain[/bold].",
        "en": "Could not parse the description. Try rephrasing or use [bold]--slug[/bold]/[bold]--domain[/bold].",
    },
    "intent_review_q": {
        "pt-BR": "Vou documentar [bold]{title}[/bold] (slug=[accent]{slug}[/accent], domínio=[accent]{domain}[/accent]). Confirma?",
        "en": "I'll document [bold]{title}[/bold] (slug=[accent]{slug}[/accent], domain=[accent]{domain}[/accent]). Confirm?",
    },
    "intent_new_domain": {
        "pt-BR": "[brand]Domínio novo[/brand] — vou criar.",
        "en": "[brand]New domain[/brand] — will be created.",
    },
    "intent_clarification": {
        "pt-BR": "Pergunta de esclarecimento da IA: {q}",
        "en": "Agent clarification needed: {q}",
    },
    "intent_edit_slug_q": {
        "pt-BR": "Slug (kebab-case)",
        "en": "Slug (kebab-case)",
    },
    "intent_edit_domain_q": {
        "pt-BR": "Domínio",
        "en": "Domain",
    },
    "intent_edit_title_q": {
        "pt-BR": "Título",
        "en": "Title",
    },
    "skeleton_building": {
        "pt-BR": "Lendo o código e montando esqueleto de fatos para [bold]{slug}[/bold]",
        "en": "Reading code and building fact skeleton for [bold]{slug}[/bold]",
    },
    "skeleton_thinking": {
        "pt-BR": "Mapeando fatos e evidências",
        "en": "Mapping facts and evidence",
    },
    "skeleton_failed": {
        "pt-BR": "Falha ao montar o esqueleto. O agente não retornou JSON válido.",
        "en": "Failed to build skeleton. The agent did not return valid JSON.",
    },
    "skeleton_ready": {
        "pt-BR": "{total} fato(s) mapeado(s) · [ok]{confirmed} confirmados[/ok] · [warn]{pending} a confirmar[/warn] · [muted]{hypothesized} hipóteses[/muted]",
        "en": "{total} fact(s) mapped · [ok]{confirmed} confirmed[/ok] · [warn]{pending} to confirm[/warn] · [muted]{hypothesized} hypotheses[/muted]",
    },
    "skeleton_split_suggested": {
        "pt-BR": "O tema parece grande. Sugiro dividir em guias menores antes de prosseguir.",
        "en": "The topic looks big. I suggest splitting it into smaller guides before continuing.",
    },
    "skeleton_split_hint": {
        "pt-BR": "(Vou continuar com este tema agora. Se preferir dividir, pause com /sair e refaça.)",
        "en": "(I'll continue with this topic. If you prefer to split, pause with /exit and redo.)",
    },
    "reflect_thinking": {
        "pt-BR": "Conferindo no código",
        "en": "Cross-checking with code",
    },
    "reflect_skipped": {
        "pt-BR": "Cross-check ignorado",
        "en": "Cross-check skipped",
    },
    "reflect_corrected": {
        "pt-BR": "Cruzando com o código, achei uma nuance:",
        "en": "Cross-checking the code, I found a nuance:",
    },
    "reflect_contradiction": {
        "pt-BR": "Achei uma divergência entre sua resposta e o código.",
        "en": "I found a divergence between your answer and the code.",
    },
    "reflect_contradiction_hint": {
        "pt-BR": "Vou registrar como [bold]contradicted[/bold]. Você pode revisar/editar o guia depois.",
        "en": "I'll record this as [bold]contradicted[/bold]. You can review/edit the guide later.",
    },
    "reflect_covered_others": {
        "pt-BR": "Sua resposta também cobriu: {ids}",
        "en": "Your answer also covered: {ids}",
    },
    "reflect_new_facts": {
        "pt-BR": "Apareceram {n} fato(s) novo(s) durante essa resposta — adicionados ao esqueleto.",
        "en": "{n} new fact(s) emerged from your answer — added to the skeleton.",
    },
    "pregen_audit": {
        "pt-BR": "Auditando evidências antes de gerar",
        "en": "Auditing evidence before generation",
    },
    # ---- Closing question (open free-form catch-all at the end of interview) ----
    "closing_q_title": {
        "pt-BR": "Algo a acrescentar?",
        "en": "Anything to add?",
    },
    "closing_q_hint": {
        "pt-BR": "Esta é sua chance de registrar regras, dúvidas comuns ou detalhes "
                 "que não apareceram nas perguntas. Pode falar livre, eu organizo.",
        "en": "This is your chance to register rules, common doubts or details "
              "the questions didn't surface. Speak freely — I'll organize.",
    },
    "closing_q": {
        "pt-BR": "Gostaria de acrescentar algo? (deixe em branco para pular)",
        "en": "Want to add anything? (leave blank to skip)",
    },
    "closing_saved_short": {
        "pt-BR": "Salvo nas notas do guia.",
        "en": "Saved to the guide notes.",
    },
    "closing_processing": {
        "pt-BR": "Organizando sua resposta",
        "en": "Organizing your answer",
    },
    "closing_saved_notes_only": {
        "pt-BR": "Salvo nas notas (nada para estruturar como fato).",
        "en": "Saved to notes (nothing to structure as a fact).",
    },
    "closing_added_facts": {
        "pt-BR": "{n} fato(s) extraído(s) da sua resposta.",
        "en": "{n} fact(s) extracted from your answer.",
    },
    # ---- `livedocs refine` — apply free-form instruction to existing guide ----
    "refine_title": {
        "pt-BR": "Refinar guia: {slug}",
        "en": "Refine guide: {slug}",
    },
    "refine_hint": {
        "pt-BR": "Escreva o que você quer mudar. Exemplos: 'adicione um caso de "
                 "uso sobre estorno', 'tom mais narrativo na seção X', "
                 "'confira se R5 ainda bate com o código'.",
        "en": "Write what you want to change. Examples: 'add a use case about "
              "refunds', 'narrative tone in section X', 'recheck R5 against the "
              "current code'.",
    },
    "refine_prompt": {
        "pt-BR": "Instrução de refinamento (deixe em branco para cancelar)",
        "en": "Refinement instruction (leave blank to cancel)",
    },
    "refine_thinking": {
        "pt-BR": "Refinando guia",
        "en": "Refining guide",
    },
    "refine_failed": {
        "pt-BR": "Falha ao refinar — agente não devolveu JSON válido.",
        "en": "Refine failed — agent did not return valid JSON.",
    },
    "refine_no_changes": {
        "pt-BR": "O agente decidiu não fazer mudanças.",
        "en": "The agent decided not to make any changes.",
    },
    "refine_done": {
        "pt-BR": "{n} mudança(s) aplicada(s) em {files} arquivo(s).",
        "en": "{n} change(s) applied to {files} file(s).",
    },
    "refine_status_flipped": {
        "pt-BR": "Status voltou para [bold]generated[/bold] — re-aprove com "
                 "[bold]livedocs approve[/bold] quando estiver satisfeito.",
        "en": "Status flipped back to [bold]generated[/bold] — re-approve with "
              "[bold]livedocs approve[/bold] when you're satisfied.",
    },
    "refine_code_checks": {
        "pt-BR": "Verificações no código durante o refinamento:",
        "en": "Code checks performed during the refinement:",
    },
    "refine_status_blocked": {
        "pt-BR": "Não dá para refinar [bold]{slug}[/bold] no status [bold]{status}[/bold]. "
                 "Use [bold]livedocs continue[/bold] ou [bold]livedocs new[/bold].",
        "en": "Cannot refine [bold]{slug}[/bold] while it's [bold]{status}[/bold]. "
              "Use [bold]livedocs continue[/bold] or [bold]livedocs new[/bold].",
    },
    "refine_no_eligible": {
        "pt-BR": "Nenhum guia em estado [bold]generated[/bold] ou [bold]reviewed[/bold] para refinar.",
        "en": "No guides in [bold]generated[/bold] or [bold]reviewed[/bold] state to refine.",
    },
    "refine_file_missing": {
        "pt-BR": "Arquivo do guia não encontrado em disco: {path}",
        "en": "Guide file not found on disk: {path}",
    },
    "refine_pick_guide": {
        "pt-BR": "Qual guia você quer refinar?",
        "en": "Which guide do you want to refine?",
    },
    "refine_menu_option": {
        "pt-BR": "Refinar um guia (instrução livre)",
        "en": "Refine a guide (free-form instruction)",
    },
    # ---- Phase D.1 — Post-generation evaluators ----
    "eval_running": {
        "pt-BR": "Auditando o guia gerado em 3 dimensões",
        "en": "Auditing the generated guide on 3 dimensions",
    },
    "eval_running_hint": {
        "pt-BR": "(Rodando em paralelo. Cada chamada lê o guia com uma persona diferente.)",
        "en": "(Running in parallel. Each call reads the guide with a different persona.)",
    },
    "eval_dim_failed": {
        "pt-BR": "Dimensão [bold]{dim}[/bold] falhou: {err}",
        "en": "Dimension [bold]{dim}[/bold] failed: {err}",
    },
    "eval_dim_product_clarity": {
        "pt-BR": "Clareza de produto",
        "en": "Product clarity",
    },
    "eval_dim_tech_completeness": {
        "pt-BR": "Completude técnica",
        "en": "Tech completeness",
    },
    "eval_dim_base_coherence": {
        "pt-BR": "Coerência com a base",
        "en": "Base coherence",
    },
    # ---- Phase D.2 — Internal iteration ----
    "iter_cycle": {
        "pt-BR": "Ciclo {n}/{total} — aplicando {fixes} ajuste(s)",
        "en": "Cycle {n}/{total} — applying {fixes} fix(es)",
    },
    "iter_applying": {
        "pt-BR": "Aplicando {n} ajuste(s) automáticos",
        "en": "Applying {n} auto-fix(es)",
    },
    "iter_no_progress": {
        "pt-BR": "Não consegui aplicar ajustes adicionais; saindo do loop.",
        "en": "Could not apply further fixes; exiting loop.",
    },
    "iter_polished": {
        "pt-BR": "Polido em {n} ciclo(s)",
        "en": "Polished in {n} cycle(s)",
    },
    # ---- Phase D.3 — Inbox ----
    "inbox_title": {
        "pt-BR": "Inbox — {n} item(s) pendente(s)",
        "en": "Inbox — {n} pending item(s)",
    },
    "inbox_empty": {
        "pt-BR": "Nenhum item pendente na inbox.",
        "en": "Inbox is empty.",
    },
    "inbox_action_q": {
        "pt-BR": "O que fazer com este item?",
        "en": "What to do with this item?",
    },
    "inbox_accept": {
        "pt-BR": "Aceitar (aplicar)",
        "en": "Accept (apply)",
    },
    "inbox_reject": {
        "pt-BR": "Rejeitar (descartar)",
        "en": "Reject (drop)",
    },
    "inbox_snooze": {
        "pt-BR": "Adiar (manter pendente)",
        "en": "Snooze (keep pending)",
    },
    "inbox_view": {
        "pt-BR": "Ver detalhes completos",
        "en": "View full details",
    },
    "inbox_quit": {
        "pt-BR": "Sair da inbox",
        "en": "Exit inbox",
    },
    "inbox_accepted": {
        "pt-BR": "[ok]✓[/ok] {id} aplicado.",
        "en": "[ok]✓[/ok] {id} applied.",
    },
    "inbox_apply_failed": {
        "pt-BR": "[err]✗[/err] Falha ao aplicar {id}.",
        "en": "[err]✗[/err] Failed to apply {id}.",
    },
    "inbox_rejected": {
        "pt-BR": "Rejeitado.",
        "en": "Rejected.",
    },
    "inbox_snoozed": {
        "pt-BR": "Adiado.",
        "en": "Snoozed.",
    },
    "inbox_remaining": {
        "pt-BR": "{n} item(s) ainda pendente(s) — rode [bold]livedocs inbox[/bold] de novo quando quiser.",
        "en": "{n} item(s) still pending — run [bold]livedocs inbox[/bold] again when you want.",
    },
    "inbox_cleared": {
        "pt-BR": "Inbox limpa!",
        "en": "Inbox cleared!",
    },
    "inbox_applying": {
        "pt-BR": "Aplicando a edição",
        "en": "Applying the edit",
    },
    "inbox_items_added": {
        "pt-BR": "{n} sugestão(ões) adicionada(s) à inbox. Veja com [bold]livedocs inbox[/bold].",
        "en": "{n} suggestion(s) added to the inbox. See with [bold]livedocs inbox[/bold].",
    },
    "reverse_link_sweeping": {
        "pt-BR": "Propondo cross-links reversos pra outros guias",
        "en": "Proposing reverse cross-links to other guides",
    },
    # ---- Fact kinds (translated labels for UI) ----
    "fact_kind_trigger": {"pt-BR": "gatilho", "en": "trigger"},
    "fact_kind_invariant": {"pt-BR": "invariante", "en": "invariant"},
    "fact_kind_edge_case": {"pt-BR": "edge case", "en": "edge case"},
    "fact_kind_terminology": {"pt-BR": "terminologia", "en": "terminology"},
    "fact_kind_flow": {"pt-BR": "fluxo", "en": "flow"},
    "fact_kind_value": {"pt-BR": "valor", "en": "value"},
    "fact_kind_actor": {"pt-BR": "ator", "en": "actor"},
    "fact_kind_ui_surface": {"pt-BR": "tela/UI", "en": "UI surface"},
}


# ---------------------------------------------------------------------------
# Detection / runtime
# ---------------------------------------------------------------------------

_active_lang: Lang = "en"


def detect_system_locale() -> Lang:
    """Detect best-effort the system locale and return one of the supported langs."""
    candidates: list[str] = []

    # 1. explicit env override
    for k in ("LIVEDOCS_LANG", "LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        v = os.environ.get(k)
        if v:
            candidates.append(v)

    # 2. fall back to python locale
    try:
        loc = locale.getlocale()
        if loc and loc[0]:
            candidates.append(loc[0])
    except Exception:
        pass

    for c in candidates:
        c_lower = c.lower().replace("_", "-")
        if c_lower.startswith("pt"):
            return "pt-BR"
        if c_lower.startswith("en"):
            return "en"

    return "en"


def set_lang(lang: Lang) -> None:
    global _active_lang
    _active_lang = lang


def get_lang() -> Lang:
    return _active_lang


def t(key: str, *, default_: str | None = None, **kwargs: object) -> str:
    """Translate a key using the active language. Falls back to default_/en/key.

    `default_` (trailing underscore avoids colliding with `default` format args)
    is used when the key is not in the STRINGS dict — useful for kinds/labels
    that may not need translation.
    """
    entry = STRINGS.get(key)
    if not entry:
        return default_ if default_ is not None else key
    s = entry.get(_active_lang) or entry.get("en") or default_ or key
    if kwargs:
        with contextlib.suppress(KeyError, IndexError):
            s = s.format(**kwargs)
    return s


def supported_langs() -> list[Lang]:
    return ["pt-BR", "en"]


def lang_label(lang: Lang) -> str:
    return {"pt-BR": "Português (Brasil)", "en": "English"}[lang]
