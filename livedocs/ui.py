"""UI helpers — Rich-based terminal UI with a consistent visual identity.

The look-and-feel goal: clean, calm, friendly. No emojis-galore, no ascii art mess.
Just clear hierarchy with color and spacing.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager

import questionary
from questionary import Style as QStyle
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from livedocs import __version__
from livedocs.i18n import t

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

THEME = Theme(
    {
        "brand": "bold #7c5cff",
        "brand.dim": "#7c5cff",
        "accent": "#22d3ee",
        "muted": "dim",
        "ok": "bold green",
        "warn": "bold yellow",
        "err": "bold red",
        "kbd": "bold #f59e0b",
    }
)

console = Console(theme=THEME, highlight=False)


# Questionary styling that matches the Rich theme
QUESTIONARY_STYLE = QStyle(
    [
        ("qmark", "fg:#7c5cff bold"),
        ("question", "bold"),
        ("answer", "fg:#22d3ee bold"),
        ("pointer", "fg:#7c5cff bold"),
        ("highlighted", "fg:#7c5cff bold"),
        ("selected", "fg:#22d3ee"),
        ("separator", "fg:#888888"),
        ("instruction", "fg:#888888"),
        ("text", ""),
        ("disabled", "fg:#666666 italic"),
    ]
)


# ---------------------------------------------------------------------------
# Splash
# ---------------------------------------------------------------------------

LOGO = r"""
  _  _          ___
 | |(_)_ _____ |   \ ___  __ _
 | || \ V / -_)| |) / _ \/ _|
 |_||_|\_/\___||___/\___/\__/ s
"""


def splash(subtitle: str | None = None) -> None:
    """Render a soft brand splash. Uses gradient-ish coloring across the logo."""
    text = Text()
    for i, line in enumerate(LOGO.strip("\n").splitlines()):
        # subtle stripe: header lines slightly more saturated
        color = "#7c5cff" if i % 2 == 0 else "#a78bfa"
        text.append(line + "\n", style=color)

    sub_text = Text()
    sub_text.append(f"v{__version__}", style="muted")
    sub_text.append("  ·  ", style="muted")
    sub_text.append(subtitle or t("tagline"), style="accent")

    body = Group(
        Align.left(text),
        Align.left(sub_text),
    )
    console.print(Panel.fit(body, border_style="brand.dim", padding=(0, 2)))
    console.print()


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def hr() -> None:
    console.rule(style="brand.dim")


def section(title: str, *, hint: str | None = None) -> None:
    """Render a section header used between major steps."""
    console.print()
    text = Text(title, style="brand")
    if hint:
        text.append("   ")
        text.append(hint, style="muted")
    console.print(text)
    console.rule(style="brand.dim")


def info(msg: str) -> None:
    console.print(f"[muted]·[/muted] {msg}")


def success(msg: str) -> None:
    console.print(f"[ok]✓[/ok] {msg}")


def warn(msg: str) -> None:
    console.print(f"[warn]![/warn] {msg}")


def error(msg: str) -> None:
    console.print(f"[err]✗[/err] {msg}")


def hint(msg: str) -> None:
    console.print(f"[muted]{msg}[/muted]")


def blank() -> None:
    console.print()


# ---------------------------------------------------------------------------
# Prompts (questionary wrappers — uniform styling, easier mocking)
# ---------------------------------------------------------------------------

def ask_text(message: str, *, default: str = "", multiline: bool = False) -> str | None:
    """Returns answer or None when user aborts (Ctrl-C)."""
    try:
        if multiline:
            return questionary.text(
                message,
                default=default,
                multiline=True,
                style=QUESTIONARY_STYLE,
            ).ask()
        return questionary.text(message, default=default, style=QUESTIONARY_STYLE).ask()
    except (KeyboardInterrupt, EOFError):
        return None


def ask_confirm(message: str, *, default: bool = True) -> bool | None:
    try:
        return questionary.confirm(message, default=default, style=QUESTIONARY_STYLE).ask()
    except (KeyboardInterrupt, EOFError):
        return None


def ask_choice(
    message: str,
    choices: Iterable[str | tuple[str, str]],
    *,
    default: str | None = None,
) -> str | None:
    """choices: list of either str or (label, value) tuples. Returns the *value*."""
    qchoices: list = []
    for c in choices:
        if isinstance(c, tuple):
            label, value = c
            qchoices.append(questionary.Choice(title=label, value=value))
        else:
            qchoices.append(questionary.Choice(title=c, value=c))
    try:
        return questionary.select(
            message,
            choices=qchoices,
            default=default,
            style=QUESTIONARY_STYLE,
            qmark="›",
        ).ask()
    except (KeyboardInterrupt, EOFError):
        return None


def ask_path(message: str, *, default: str = "", only_directories: bool = False) -> str | None:
    try:
        return questionary.path(
            message,
            default=default,
            only_directories=only_directories,
            style=QUESTIONARY_STYLE,
        ).ask()
    except (KeyboardInterrupt, EOFError):
        return None


# ---------------------------------------------------------------------------
# Spinner / progress
# ---------------------------------------------------------------------------

@contextmanager
def spinner(message: str) -> Iterator[None]:
    """Indeterminate spinner during a blocking task."""
    with Progress(
        SpinnerColumn(style="brand"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as p:
        p.add_task(description=message, total=None)
        yield


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def make_table(*headers: str) -> Table:
    table = Table(show_lines=False, header_style="brand", border_style="brand.dim")
    for h in headers:
        table.add_column(h)
    return table
