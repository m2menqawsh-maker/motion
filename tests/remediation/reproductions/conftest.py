import pytest

def pytest_addoption(parser):
    try:
        parser.addoption(
            "--run-reproductions",
            action="store_true",
            default=False,
            help="Run RED reproduction tests for remediation findings"
        )
    except ValueError:
        pass

REPRODUCTION_METADATA = {
    "test_asset_009_path_traversal.py": {"finding": "ASSET-009", "owner": "S02", "closed": True},
    "test_led_019_approval_bypass.py": {"finding": "LED-019", "owner": "S02", "closed": True},
    "test_led_022_skip_strict_qc.py": {"finding": "LED-022", "owner": "S02", "closed": True},
    "test_state_001_lifecycle_bypass.py": {"finding": "STATE-001 / LED-018", "owner": "S03", "closed": True},
    "test_gate_001_facade_reproductions.py": {"finding": "GATE-001 (A/B/C)", "owner": "S04", "closed": True},
    "test_conc_001_lost_update.py": {"finding": "CONC-001", "owner": "S05", "closed": True},
    "test_led_005_artifact_records_erasure.py": {"finding": "LED-005", "owner": "S06", "closed": True},
    "test_rec_001_recovery_empty_evidence.py": {"finding": "REC-001", "owner": "S06", "closed": True},
    "test_led_008_corrupt_state.py": {"finding": "LED-008", "owner": "S07", "closed": True},
    "test_led_054_props_divergence.py": {"finding": "LED-054", "owner": "S17", "closed": True},
    "test_s18_reproductions.py": {"finding": "LED-047/LED-048/LED-049/LED-050", "owner": "S18", "closed": True},
    "test_s19_reproductions.py": {"finding": "LED-051/LED-052/LED-053", "owner": "S19", "closed": True},
}

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-reproductions", False):
        for item in items:
            if "reproductions" in str(item.fspath):
                meta = REPRODUCTION_METADATA.get(item.fspath.basename)
                if meta and not meta["closed"]:
                    skip_marker = pytest.mark.skip(
                        reason=f"Pending Expected-RED remediation reproduction for {meta['finding']} (Owner: {meta['owner']}; run with --run-reproductions)"
                    )
                    item.add_marker(skip_marker)
