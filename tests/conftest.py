"""Fixtures shared by the suite.

The workbook is read with openpyxl twice, for Excel's cached values and for its
formulas, so the suite runs on Linux CI against the committed workbook without
Excel.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _load(data_only: bool):
    import openpyxl

    import layout as L
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return openpyxl.load_workbook(ROOT / "workbook" / L.WORKBOOK, data_only=data_only)


@pytest.fixture(scope="session")
def values():
    return _load(True)


@pytest.fixture(scope="session")
def formulas():
    return _load(False)


@pytest.fixture(scope="session")
def gold():
    import reference

    return reference.load()


@pytest.fixture(scope="session")
def selected(gold):
    import layout as L
    import reference

    return reference.municipality_id(gold, L.DEFAULT_MUNICIPALITY)
