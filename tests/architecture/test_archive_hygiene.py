#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/architecture/test_archive_hygiene.py — Archive script hygiene and boundary tests (REALITY-022 / REALITY-014).
Verifies that all 28 archived scripts are accounted for, retained, and never imported by active production runtimes.
"""

from pathlib import Path


def test_archive_inventory_document_exists_and_complete():
    doc = Path("documentation/architecture/ARCHIVE_SCRIPTS_INVENTORY.md")
    assert doc.exists(), "ARCHIVE_SCRIPTS_INVENTORY.md missing"
    content = doc.read_text(encoding="utf-8")

    # Verify inventory covers all 28 archived source scripts
    archive_dir = Path("scripts/archive")
    assert archive_dir.exists()

    archived_files = [
        f for f in archive_dir.glob("**/*")
        if f.is_file() and not f.name.endswith(".pyc") and f.name != "__init__.py" and "__pycache__" not in str(f)
    ]
    assert len(archived_files) == 30, f"Expected 30 archived files, found {len(archived_files)}"

    for f in archived_files:
        rel = f.relative_to(archive_dir)
        assert str(rel) in content or f.name in content, f"Archived file {rel} not documented in inventory"


def test_production_code_does_not_import_archive_scripts():
    production_roots = [
        Path("api"),
        Path("scripts/core"),
        Path("scripts/gates"),
        Path("contracts"),
        Path("remotion-app/src"),
    ]

    for root in production_roots:
        if not root.exists():
            continue
        for source_file in root.glob("**/*"):
            if not source_file.is_file():
                continue
            if source_file.suffix not in (".py", ".ts", ".tsx"):
                continue
            if "__pycache__" in str(source_file):
                continue

            text = source_file.read_text(encoding="utf-8", errors="ignore")
            assert "scripts.archive" not in text, f"Active production file {source_file} imports from scripts.archive"
            assert "from '../archive" not in text and 'from "../archive' not in text, f"Active production file {source_file} imports from archive"
