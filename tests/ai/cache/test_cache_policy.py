"""
tests/ai/cache/test_cache_policy.py
===================================
Capability-driven cache policy tests (S27.12).

Invariants verified:
- Cache eligibility comes directly from authoritative Capability Registry.
- CachePolicy.NEVER capabilities strictly bypass cache (IMAGE_GENERATION, VIDEO_GENERATION, MUSIC_GENERATION).
- Cacheable capabilities (DETERMINISTIC, CONTENT_HASH) permit caching.
- Explicit bypass_cache=True forces cache bypass even for cacheable capabilities.
"""

from ai.cache.policy import is_capability_cacheable, should_evaluate_cache
from ai.contracts.common import CapabilityTypeEnum


def test_capability_cacheability_mapping():
    # Cacheable capabilities
    assert is_capability_cacheable(CapabilityTypeEnum.TEXT_GENERATION) is True
    assert is_capability_cacheable(CapabilityTypeEnum.REASONING) is True
    assert is_capability_cacheable(CapabilityTypeEnum.PLANNING) is True
    assert is_capability_cacheable(CapabilityTypeEnum.SUMMARIZATION) is True
    assert is_capability_cacheable(CapabilityTypeEnum.TRANSLATION) is True
    assert is_capability_cacheable(CapabilityTypeEnum.SPEECH_TO_TEXT) is True
    assert is_capability_cacheable(CapabilityTypeEnum.EMBEDDING) is True

    # Non-cacheable capabilities (CachePolicy.NEVER)
    assert is_capability_cacheable(CapabilityTypeEnum.IMAGE_GENERATION) is False
    assert is_capability_cacheable(CapabilityTypeEnum.VIDEO_GENERATION) is False
    assert is_capability_cacheable(CapabilityTypeEnum.MUSIC_GENERATION) is False


def test_should_evaluate_cache_with_bypass():
    # Cacheable without bypass -> True
    assert should_evaluate_cache(CapabilityTypeEnum.TEXT_GENERATION, bypass_cache=False) is True

    # Cacheable with explicit bypass -> False
    assert should_evaluate_cache(CapabilityTypeEnum.TEXT_GENERATION, bypass_cache=True) is False

    # Non-cacheable without bypass -> False
    assert should_evaluate_cache(CapabilityTypeEnum.VIDEO_GENERATION, bypass_cache=False) is False

    # Non-cacheable with bypass -> False
    assert should_evaluate_cache(CapabilityTypeEnum.VIDEO_GENERATION, bypass_cache=True) is False
