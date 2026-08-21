"""Shared pytest fixtures for schema tests."""

import sys
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

# Ensure `app/` (this file's parent's parent) is on sys.path so
# `from app.models import PriceRow` resolves when pytest runs from app/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def session():
    """Provide an isolated in-memory SQLite session per test."""
    from app.models import AppSetting, PriceRow  # noqa: F401  (registers tables)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sess:
        yield sess
