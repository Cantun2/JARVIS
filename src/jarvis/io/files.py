"""Lecture de fichiers projet : abstraction + backends Mock (défaut) et Real (allow-list).

LECTURE SEULE, gaté par `Permission.FS_PROJECT_DIRS`. Consommé par NEMESIS (auditeur) et
CHIRON (tuteur). Le backend réel n'expose QUE les racines déclarées (`JARVIS_PROJECT_DIRS`),
avec garde-fous : containment de chemin résolu (bloque `..` et échappement symlink), plafonds
de taille/nombre, denylist de dossiers, détection binaire. Même moule que `io/mail.py`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from jarvis.config import Settings
from jarvis.logging import get_logger

log = get_logger("jarvis.files")

_DEFAULT_DENYLIST = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".idea",
        ".vscode",
        "var",
    }
)


class FileEntry(BaseModel):
    path: str  # relatif à la racine
    is_dir: bool
    size: int = 0


@runtime_checkable
class FileReader(Protocol):
    name: str

    async def list_roots(self) -> list[str]: ...
    async def list_dir(self, root: str, subpath: str = "") -> list[FileEntry]: ...
    async def read_file(self, root: str, relpath: str) -> str: ...


class FileAccessError(RuntimeError):
    """Accès refusé/introuvable (hors allow-list, traversal, trop gros…)."""


class MockFileReader:
    """Arbre en mémoire (hors-ligne). Racine « demo » par défaut avec du code d'exemple."""

    name = "mock"

    def __init__(self, tree: dict[str, dict[str, str]] | None = None) -> None:
        self._tree = tree if tree is not None else _DEMO_TREE

    async def list_roots(self) -> list[str]:
        return list(self._tree)

    async def list_dir(self, root: str, subpath: str = "") -> list[FileEntry]:
        files = self._tree.get(root, {})
        prefix = subpath.strip("/")
        entries: list[FileEntry] = []
        for path, content in files.items():
            if prefix and not path.startswith(f"{prefix}/"):
                continue
            entries.append(FileEntry(path=path, is_dir=False, size=len(content.encode("utf-8"))))
        return entries

    async def read_file(self, root: str, relpath: str) -> str:
        files = self._tree.get(root, {})
        if relpath not in files:
            raise FileAccessError(f"introuvable : {root}/{relpath}")
        return files[relpath]


class RealFileReader:
    """Lit sous des racines déclarées, en lecture seule, avec garde-fous stricts."""

    name = "real"

    def __init__(
        self,
        roots: list[str],
        *,
        max_bytes: int = 262144,
        max_files: int = 200,
        denylist: frozenset[str] = _DEFAULT_DENYLIST,
    ) -> None:
        # nom (basename) → chemin absolu résolu
        self._roots: dict[str, Path] = {}
        for r in roots:
            p = Path(r).expanduser().resolve()
            if p.is_dir():
                self._roots[p.name] = p
            else:
                log.warning("project_dir_absent", path=str(p))
        self._max_bytes = max_bytes
        self._max_files = max_files
        self._denylist = denylist

    async def list_roots(self) -> list[str]:
        return list(self._roots)

    def _resolve(self, root: str, rel: str) -> Path:
        base = self._roots.get(root)
        if base is None:
            raise FileAccessError(f"racine inconnue : {root}")
        target = (base / rel).resolve()
        # Containment : le chemin résolu doit rester sous la racine (bloque ../ et symlinks).
        if target != base and base not in target.parents:
            raise FileAccessError(f"hors périmètre : {root}/{rel}")
        return target

    async def list_dir(self, root: str, subpath: str = "") -> list[FileEntry]:
        return await asyncio.to_thread(self._list_dir_sync, root, subpath)

    def _list_dir_sync(self, root: str, subpath: str) -> list[FileEntry]:
        base = self._roots.get(root)
        if base is None:
            raise FileAccessError(f"racine inconnue : {root}")
        target = self._resolve(root, subpath)
        if not target.is_dir():
            raise FileAccessError(f"pas un dossier : {root}/{subpath}")
        entries: list[FileEntry] = []
        for child in sorted(target.iterdir()):
            if child.name in self._denylist:
                continue
            rel = child.relative_to(base).as_posix()
            is_dir = child.is_dir()
            size = 0 if is_dir else child.stat().st_size
            entries.append(FileEntry(path=rel, is_dir=is_dir, size=size))
            if len(entries) >= self._max_files:
                break
        return entries

    async def read_file(self, root: str, relpath: str) -> str:
        return await asyncio.to_thread(self._read_file_sync, root, relpath)

    def _read_file_sync(self, root: str, relpath: str) -> str:
        target = self._resolve(root, relpath)
        if not target.is_file():
            raise FileAccessError(f"pas un fichier : {root}/{relpath}")
        size = target.stat().st_size
        if size > self._max_bytes:
            raise FileAccessError(f"trop gros ({size} > {self._max_bytes}) : {root}/{relpath}")
        data = target.read_bytes()
        if b"\x00" in data:
            return "(fichier binaire — non affiché)"
        return data.decode("utf-8", errors="replace")


_TEXT_EXTENSIONS = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".c",
        ".h",
        ".cpp",
        ".cs",
        ".md",
        ".txt",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".cfg",
        ".ini",
        ".sh",
        ".ps1",
        ".html",
        ".css",
    }
)


def _is_texty(path: str) -> bool:
    dot = path.rfind(".")
    return dot != -1 and path[dot:].lower() in _TEXT_EXTENSIONS


async def pick_root(reader: FileReader, preferred: str | None = None) -> str | None:
    """Choisit une racine : celle demandée si valide, sinon la première disponible."""
    roots = await reader.list_roots()
    if preferred and preferred in roots:
        return preferred
    return roots[0] if roots else None


async def collect_excerpts(
    reader: FileReader,
    root: str,
    *,
    max_files: int = 12,
    max_chars_per_file: int = 2000,
) -> str:
    """Parcours borné (BFS) d'une racine → extraits concaténés des fichiers texte.

    Réutilisé par NEMESIS (audit) et CHIRON (aide sur le code). Best-effort : ignore
    silencieusement ce qui n'est pas lisible. Le service applique déjà denylist + plafonds.
    """
    out: list[str] = []
    queue: list[str] = [""]
    while queue and len(out) < max_files:
        sub = queue.pop(0)
        try:
            entries = await reader.list_dir(root, sub)
        except FileAccessError:
            continue
        for entry in entries:
            if len(out) >= max_files:
                break
            if entry.is_dir:
                queue.append(entry.path)
            elif _is_texty(entry.path):
                try:
                    content = await reader.read_file(root, entry.path)
                except FileAccessError:
                    continue
                out.append(f"### {entry.path}\n{content[:max_chars_per_file]}")
    return "\n\n".join(out)


def build_files(settings: Settings) -> FileReader:
    if settings.mode == "real" and settings.project_dirs:
        log.info("files_backend", backend="real", roots=len(settings.project_dirs))
        return RealFileReader(
            settings.project_dirs,
            max_bytes=settings.file_read_max_bytes,
            max_files=settings.file_read_max_files,
        )
    return MockFileReader()


# Arbre de démonstration (mode mock) : un petit projet avec un défaut évident à auditer.
_DEMO_TREE: dict[str, dict[str, str]] = {
    "demo": {
        "app.py": (
            "def divide(a, b):\n"
            "    return a / b  # pas de garde contre b == 0\n\n"
            "PASSWORD = 'admin123'  # secret en dur\n\n"
            "def run(items):\n"
            "    for i in range(len(items)):  # boucle non pythonique\n"
            "        print(items[i])\n"
        ),
        "README.md": "# Demo\n\nProjet d'exemple pour l'auditeur NEMESIS.\n",
    }
}
