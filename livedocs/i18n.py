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
    # ---- intent ("documentação completa" vs "por partes") ----
    "intent_q": {
        "pt-BR": "Como você quer começar?",
        "en": "How do you want to start?",
    },
    "intent_full": {
        "pt-BR": "Documentação inicial completa (mapeio domínios e crio rascunhos pra refinar)",
        "en": "Full initial pass (I'll map domains and create drafts for you to refine)",
    },
    "intent_one_by_one": {
        "pt-BR": "Por partes (você escolhe um domínio/fluxo por vez)",
        "en": "One by one (you pick one domain/flow at a time)",
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


def t(key: str, **kwargs: object) -> str:
    """Translate a key using the active language. Falls back to en, then to the key itself."""
    entry = STRINGS.get(key)
    if not entry:
        return key  # fail open: untranslated literal shows up as itself
    s = entry.get(_active_lang) or entry.get("en") or key
    if kwargs:
        with contextlib.suppress(KeyError, IndexError):
            s = s.format(**kwargs)
    return s


def supported_langs() -> list[Lang]:
    return ["pt-BR", "en"]


def lang_label(lang: Lang) -> str:
    return {"pt-BR": "Português (Brasil)", "en": "English"}[lang]
