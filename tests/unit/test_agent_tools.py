"""Tests for the agent's tool whitelist (issue #6).

We don't actually spawn `claude` here — we monkeypatch subprocess.Popen
to capture the command line and assert on it.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from livedocs import agent as agent_mod


class _FakeStdout:
    def __init__(self, lines: list[str]):
        self._lines = list(lines)
        self._iter = iter(self._lines)

    def __iter__(self):
        return self._iter

    def read(self) -> str:
        return "".join(self._lines)


class _FakeProc:
    def __init__(self, cmd: list[str], envelope: dict[str, Any]):
        self.cmd = cmd
        line = json.dumps(envelope) + "\n"
        self.stdout = _FakeStdout([line])
        self.stderr = io.StringIO("")
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        self.returncode = -9


@pytest.fixture
def captured_cmds(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    captured: list[list[str]] = []

    envelope = {
        "type": "result",
        "result": "ok",
        "is_error": False,
        "total_cost_usd": 0.01,
        "duration_ms": 10,
    }

    def fake_popen(cmd, **_kwargs):
        captured.append(list(cmd))
        return _FakeProc(cmd, envelope)

    monkeypatch.setattr(agent_mod.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(agent_mod, "claude_available", lambda: True)
    return captured


def test_agent_cmd_uses_allowed_tools_whitelist(tmp_path: Path, captured_cmds):
    a = agent_mod.ClaudeAgent(repo_root=tmp_path, lang="en")
    a.call("# Task: x\n\nhi", timeout=5)
    assert captured_cmds, "Popen should have been called"
    cmd = captured_cmds[0]

    # whitelist present
    assert "--allowedTools" in cmd
    idx = cmd.index("--allowedTools")
    assert cmd[idx + 1] == "Read,Glob,Grep,Write"

    # blocklist present
    assert "--disallowedTools" in cmd
    didx = cmd.index("--disallowedTools")
    assert "Edit" in cmd[didx + 1]
    assert "Bash" in cmd[didx + 1]

    # acceptEdits is gone (issue #6)
    assert "--permission-mode=acceptEdits" not in cmd
    assert "acceptEdits" not in " ".join(cmd)


def test_agent_call_allows_per_call_tool_override(tmp_path: Path, captured_cmds):
    a = agent_mod.ClaudeAgent(repo_root=tmp_path, lang="en")
    a.call("# Task: x\n\nhi", timeout=5, allowed_tools=["Read", "Write"])
    cmd = captured_cmds[0]
    idx = cmd.index("--allowedTools")
    assert cmd[idx + 1] == "Read,Write"
