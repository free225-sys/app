"""Guard: test suites that write, publish or delete are refused on the shared preproduction database."""
import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

PREPROD_DB = dotenv_values(Path(__file__).resolve().parents[1] / ".env").get("DB_NAME")
WRITING_SUITES = {"test_backend.py", "test_phase2.py", "test_phase4.py", "test_phase5.py", "test_phase6.py", "test_roles_2026_10.py"}


def preprod_target() -> bool:
    target = os.environ.get("CASA_TEST_DB")
    return not target or target == PREPROD_DB


def refuse_if_preprod(name: str):
    if preprod_target():
        raise SystemExit(f"{name} refusé : il écrit dans la base de préproduction partagée ({PREPROD_DB}). Définir CASA_TEST_DB vers une base clonée dédiée.")


def pytest_collection_modifyitems(config, items):
    if not preprod_target():
        return
    block = pytest.mark.skip(reason=f"Suite en écriture refusée sur la préproduction partagée ({PREPROD_DB}) — consigne client.")
    for item in items:
        if Path(str(item.fspath)).name in WRITING_SUITES:
            item.add_marker(block)
