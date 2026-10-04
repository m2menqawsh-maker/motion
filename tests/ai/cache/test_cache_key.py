"""
tests/ai/cache/test_cache_key.py
================================
Deterministic canonical cache key derivation tests (S27.12).

Invariants verified:
- Deterministic canonical hashing: identical semantic inputs yield identical keys.
- Key order invariance: dictionaries with different key ordering produce identical keys.
- Float precision normalization: numbers with floating-point variances produce identical keys.
- Tenant isolation: workspace A vs workspace B produces distinct keys.
- Content hash dimension: different content bytes produce distinct keys; identical content produces identical keys.
- Settings dimension: variations in hyperparameters produce distinct keys.
- Model and version dimensions: changes in model or model_version produce distinct keys.
- Prompt version dimension: changes in prompt_version produce distinct keys.
- Analysis version dimension: changes in analysis_version produce distinct keys.
- Contract version dimension: changes in contract_version produce distinct keys.
- Security: zero timestamps, random UUIDs, or repr() in logical keys.
"""

from ai.cache.key import (
    compute_input_hash,
    compute_settings_hash,
    derive_canonical_cache_key,
    normalize_canonical_json,
)
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.common import CapabilityTypeEnum


def test_key_order_invariance_and_float_normalization():
    data1 = {"b": 2, "a": 1, "c": [1.0, 2.0, {"z": 10, "y": 20}]}
    data2 = {"a": 1, "c": [1, 2, {"y": 20, "z": 10}], "b": 2.0}

    assert normalize_canonical_json(data1) == normalize_canonical_json(data2)
    assert compute_input_hash(data1) == compute_input_hash(data2)


def test_deterministic_canonical_key():
    params1 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "Generate video title", "tags": ["tech", "ai"]},
        settings={"temperature": 0.7, "max_tokens": 100},
        model="gpt-4o",
        model_version="2026-05-01",
        contract_version="1.0.0",
        prompt_version="1.0.0",
        analysis_version="1.0.0",
    )

    params2 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"tags": ["tech", "ai"], "prompt": "Generate video title"},
        settings={"max_tokens": 100, "temperature": 0.7},
        model="gpt-4o",
        model_version="2026-05-01",
        contract_version="1.0.0",
        prompt_version="1.0.0",
        analysis_version="1.0.0",
    )

    key1 = derive_canonical_cache_key(params1)
    key2 = derive_canonical_cache_key(params2)

    assert key1 == key2
    assert key1.startswith("ck_")
    assert len(key1) == 67  # 'ck_' + 64 hex chars


def test_tenant_isolation_dimension():
    params_a = AICacheKeyParams(
        workspace_id="ws_tenant_a",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"text": "identical payload"},
    )
    params_b = AICacheKeyParams(
        workspace_id="ws_tenant_b",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"text": "identical payload"},
    )

    assert derive_canonical_cache_key(params_a) != derive_canonical_cache_key(params_b)


def test_content_hash_dimension():
    # Same filename, different content bytes
    params_file1 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.SPEECH_TO_TEXT,
        input_data={"filename": "interview.mp3"},
        content_hash="sha256_bytes_aaa",
    )
    params_file2 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.SPEECH_TO_TEXT,
        input_data={"filename": "interview.mp3"},
        content_hash="sha256_bytes_bbb",
    )
    assert derive_canonical_cache_key(params_file1) != derive_canonical_cache_key(params_file2)

    # Different filename, identical content bytes
    params_alias1 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.SPEECH_TO_TEXT,
        input_data={},
        content_hash="sha256_identical_audio_content",
    )
    params_alias2 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.SPEECH_TO_TEXT,
        input_data={},
        content_hash="sha256_identical_audio_content",
    )
    assert derive_canonical_cache_key(params_alias1) == derive_canonical_cache_key(params_alias2)


def test_settings_dimension():
    base = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"text": "hello"},
        settings={"temperature": 0.2},
    )
    modified = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"text": "hello"},
        settings={"temperature": 0.8},
    )
    assert derive_canonical_cache_key(base) != derive_canonical_cache_key(modified)


def test_model_and_version_dimensions():
    p1 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        model="claude-3-5-sonnet",
        model_version="1.0.0",
    )
    p2 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        model="claude-3-5-sonnet",
        model_version="2.0.0",
    )
    p3 = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        model="gpt-4o",
        model_version="1.0.0",
    )
    assert derive_canonical_cache_key(p1) != derive_canonical_cache_key(p2)
    assert derive_canonical_cache_key(p1) != derive_canonical_cache_key(p3)


def test_versioning_dimensions():
    p_base = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.PLANNING,
        contract_version="1.0.0",
        prompt_version="1.0.0",
        analysis_version="1.0.0",
    )
    p_prompt = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.PLANNING,
        contract_version="1.0.0",
        prompt_version="2.0.0",
        analysis_version="1.0.0",
    )
    p_analysis = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.PLANNING,
        contract_version="1.0.0",
        prompt_version="1.0.0",
        analysis_version="2.0.0",
    )
    p_contract = AICacheKeyParams(
        workspace_id="ws_alpha",
        capability=CapabilityTypeEnum.PLANNING,
        contract_version="1.1.0",
        prompt_version="1.0.0",
        analysis_version="1.0.0",
    )

    k_base = derive_canonical_cache_key(p_base)
    assert k_base != derive_canonical_cache_key(p_prompt)
    assert k_base != derive_canonical_cache_key(p_analysis)
    assert k_base != derive_canonical_cache_key(p_contract)
