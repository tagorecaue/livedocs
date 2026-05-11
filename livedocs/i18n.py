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
