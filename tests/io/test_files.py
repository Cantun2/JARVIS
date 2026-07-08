"""FileReader : mock, backend réel (allow-list), rejet traversal, plafonds, denylist, gating."""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.agents.conversational import ConversationalAgent, ConversationInput, ConversationOutput
from jarvis.assembly import JarvisContext
from jarvis.config import Settings
from jarvis.core.contracts import AgentContract, Permission
from jarvis.core.errors import PermissionDenied
from jarvis.io.files import (
    FileAccessError,
    FileReader,
    MockFileReader,
    RealFileReader,
    build_files,
)


def test_mock_satisfies_protocol() -> None:
    assert isinstance(MockFileReader(), FileReader)


async def test_mock_reads_demo_tree() -> None:
    fr = MockFileReader()
    roots = await fr.list_roots()
    assert "demo" in roots
    content = await fr.read_file("demo", "app.py")
    assert "divide" in content


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "README.md").write_text("# Proj\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("secret", encoding="utf-8")
    return root


async def test_real_lists_and_reads(project: Path) -> None:
    fr = RealFileReader([str(project)])
    assert await fr.list_roots() == ["proj"]
    entries = await fr.list_dir("proj")
    names = {e.path for e in entries}
    assert "README.md" in names and "src" in names
    assert ".git" not in names  # denylist
    assert "print('hi')" in await fr.read_file("proj", "src/main.py")


async def test_real_rejects_traversal(project: Path) -> None:
    fr = RealFileReader([str(project)])
    with pytest.raises(FileAccessError):
        await fr.read_file("proj", "../outside.txt")
    with pytest.raises(FileAccessError):
        await fr.read_file("proj", "../../etc/passwd")


async def test_real_rejects_unknown_root(project: Path) -> None:
    fr = RealFileReader([str(project)])
    with pytest.raises(FileAccessError):
        await fr.read_file("autre", "x")


async def test_real_enforces_size_cap(project: Path) -> None:
    (project / "big.txt").write_text("x" * 5000, encoding="utf-8")
    fr = RealFileReader([str(project)], max_bytes=100)
    with pytest.raises(FileAccessError):
        await fr.read_file("proj", "big.txt")


async def test_real_binary_detection(project: Path) -> None:
    (project / "blob.bin").write_bytes(b"\x00\x01\x02data")
    fr = RealFileReader([str(project)])
    assert "binaire" in await fr.read_file("proj", "blob.bin")


def test_build_defaults_to_mock() -> None:
    assert build_files(Settings(mode="mock")).name == "mock"
    # Même en real, sans project_dirs → mock. (project_dirs_raw="" ignore le .env local.)
    assert build_files(Settings(mode="real", project_dirs_raw="")).name == "mock"


def test_build_real_when_dirs_present(project: Path) -> None:
    settings = Settings(mode="real", JARVIS_PROJECT_DIRS=str(project))
    fr = build_files(settings)
    assert fr.name == "real"


# --- Gating de permission ----------------------------------------------------


class _NoFilesAgent(ConversationalAgent):
    contract = AgentContract(
        name="NOFILES",
        mode="on_demand",
        permissions=(Permission.NET_CLOUD_INFERENCE,),  # pas de FS_PROJECT_DIRS
        inputs=ConversationInput,
        outputs=ConversationOutput,
        conversational=True,
    )
    _tier = "local"

    async def _augment(self, messages, data, ctx):  # type: ignore[no-untyped-def]
        ctx.require_files()  # doit lever
        return messages


async def test_files_denied_without_permission(ctx: JarvisContext) -> None:
    with pytest.raises(PermissionDenied):
        await ctx.runner.run(_NoFilesAgent(), ConversationInput(message="x"))
