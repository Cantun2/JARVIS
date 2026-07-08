"""UI mono-processus : le backend sert l'UI buildée quand JARVIS_UI_DIST pointe un dossier."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jarvis.api.app import create_app
from jarvis.assembly import build_context
from jarvis.config import Settings


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    d = tmp_path / "dist"
    d.mkdir()
    (d / "index.html").write_text("<!doctype html><title>JARVIS</title>", encoding="utf-8")
    return d


def test_serves_index_and_keeps_api(dist: Path) -> None:
    ctx = build_context(Settings(mode="mock", db_path=":memory:", ui_dist=str(dist)))
    with TestClient(create_app(ctx)) as c:
        root = c.get("/")
        assert root.status_code == 200
        assert "JARVIS" in root.text
        # /api reste prioritaire sur le montage "/".
        assert c.get("/api/health").status_code == 200
    ctx.close()


def test_no_mount_without_ui_dist() -> None:
    ctx = build_context(Settings(mode="mock", db_path=":memory:"))
    with TestClient(create_app(ctx)) as c:
        # Sans ui_dist, "/" n'est pas servi (mode dev via Vite) → 404.
        assert c.get("/").status_code == 404
        assert c.get("/api/health").status_code == 200
    ctx.close()
