"""Shared test fixtures."""

import pytest


@pytest.fixture
def output_dir(tmp_path):
    """Temporary output directory for test file writes."""
    d = tmp_path / "docs"
    d.mkdir()
    return d
