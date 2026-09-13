"""Shared pytest fixtures for the Aether RAG test suite."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_CONFIGS_DIR = REPO_ROOT / "configs"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing at a writable copy of the repo `configs/` directory."""
    dest = tmp_path / "configs"
    shutil.copytree(REPO_CONFIGS_DIR, dest, dirs_exist_ok=True)
    return Settings(configs_dir=dest)
