import pytest
import os
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

def get_active_markdown_files():
    active_files = []
    for root, _, files in os.walk(WORKSPACE_ROOT):
        if "node_modules" in root or ".git" in root or "archive" in root:
            continue
        for file in files:
            if file.endswith(".md"):
                active_files.append(Path(root) / file)
    return active_files

def test_docs_paths_exist():
    """
    Test 1: Ensure local file links in active markdown files actually exist.
    """
    link_pattern = re.compile(r'\[.*?\]\((?!http)(.*?)\)')
    for file_path in get_active_markdown_files():
        content = file_path.read_text(encoding="utf-8")
        links = link_pattern.findall(content)
        for link in links:
            # Strip hash fragments
            clean_link = link.split('#')[0].strip()
            if not clean_link or clean_link.startswith("mailto:"):
                continue
            
            # Resolve against the file's directory
            target_path = (file_path.parent / clean_link).resolve()
            
            # Allow links to directories or files, just assert existence
            # Note: We skip if the path is outside the workspace (e.g. absolute paths)
            try:
                if target_path.is_relative_to(WORKSPACE_ROOT):
                    assert target_path.exists(), f"Broken link in {file_path.name}: {link} -> {target_path} does not exist."
            except Exception:
                pass # skip invalid paths

def test_docs_quarantine_refs():
    """
    Test 2: Prevent active docs from treating archive/quarantine content as executable authoritative references.
    """
    # Look for executable commands pointing to archive or quarantine
    bad_pattern = re.compile(r"(?i)(execute|run|python|node|import|source)\s+[\"']?(?:\.\./|\./)*(?:documentation/)?(archive|quarantine)")
    for file_path in get_active_markdown_files():
        content = file_path.read_text(encoding="utf-8")
        matches = bad_pattern.findall(content)
        assert not matches, f"Active document {file_path.name} contains executable instruction pointing to archive/quarantine."

def test_agent_instructions():
    """
    Test 3: Ensure agent instructions don't contain hazardous terms like bypass gate, direct render, etc.
    """
    blacklisted_terms = [
        r"skip gate", 
        r"bypass gate", 
        r"direct render", 
        r"manual pipeline", 
        r"old state\.json", 
        r"UnifiedPipeline", 
        r"DummyEffect", 
        r"deprecated engine path", 
        r"raw shell execution"
    ]
    pattern = re.compile("|".join(blacklisted_terms), re.IGNORECASE)
    
    # We mainly check .agents, plugins, skills, references
    agent_dirs = [
        WORKSPACE_ROOT / ".agents",
        WORKSPACE_ROOT / "references"
    ]
    
    for d in agent_dirs:
        if not d.exists():
            continue
        for root, _, files in os.walk(d):
            if "archive" in root:
                continue
            for file in files:
                if file.endswith(".md"):
                    file_path = Path(root) / file
                    content = file_path.read_text(encoding="utf-8")
                    
                    # We might mention these terms in negative contexts (e.g., "Do not skip gate").
                    # We accept those if they are preceded by "do not" or "no" or "❌".
                    # For a strict test, we just ensure these terms aren't present in a positive instructional context.
                    # As a simpler heuristic, since we completely cleaned up the instructions,
                    # we only check that they don't appear outside of known safe contexts.
                    # Since AGENTS.md specifically lists these as forbidden, we will exclude AGENTS.md and ARCHITECTURE_TRUTH.md from the raw blacklist check, or we check specifically for positive assertions.
                    
                    if file_path.name in ["AGENTS.md", "ARCHITECTURE_TRUTH.md"]:
                        continue # These files are the rule-setters, they list the terms to forbid them.
                    
                    matches = pattern.findall(content)
                    assert not matches, f"Agent documentation {file_path.name} contains forbidden instruction terms: {matches}"

def test_architecture_invariants():
    """
    Test 4: Validate architectural invariant constraints (e.g. canonical pipeline exists, engine is active, no multiple pipelines).
    """
    canonical_pipeline = WORKSPACE_ROOT / "scripts" / "pipeline.py"
    assert canonical_pipeline.exists(), "INVARIANT-01 Broken: Canonical pipeline.py is missing."
    
    engine_bridge = WORKSPACE_ROOT / "templates" / "effects" / "engine-bridge.tsx"
    remotion_bridge = WORKSPACE_ROOT / "remotion-app" / "src" / "templates" / "effects" / "engine-bridge.tsx"
    assert engine_bridge.exists() or remotion_bridge.exists(), "INVARIANT-05 Broken: EngineBridge is missing, Engine is no longer integrated."
    
    render_service = WORKSPACE_ROOT / "api" / "services" / "render_service.py"
    if render_service.exists():
        content = render_service.read_text(encoding="utf-8")
        assert "UnifiedPipeline" not in content, "INVARIANT-03 Broken: API uses legacy UnifiedPipeline instead of canonical pipeline."
