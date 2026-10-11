"""
tests/ai/knowledge/test_catalog_initialization_readiness.py
============================================================
Verification suite for idempotent knowledge catalog initialization
and readiness probing in production runtime (REALITY-008).
"""

import pytest
from ai.knowledge.catalog_service import KnowledgeCatalogService, get_knowledge_catalog_service
from api.services.health_service import HealthService


def test_knowledge_catalog_service_initialization_idempotence():
    """Verify that catalog initialization is idempotent and returns consistent counts."""
    service = KnowledgeCatalogService()
    assert not service.is_ready
    assert service.total_chunks == 0

    # First initialization
    count1 = service.initialize_catalog(verify_hash=True)
    assert count1 > 0
    assert service.is_ready
    assert service.total_chunks == count1
    assert service.status == "READY"

    # Second initialization without force: must be idempotent and return same count
    count2 = service.initialize_catalog(verify_hash=True)
    assert count2 == count1
    assert service.is_ready


def test_knowledge_catalog_readiness_probe():
    """Verify that get_readiness reports accurate metrics."""
    service = KnowledgeCatalogService()
    is_ready, details = service.get_readiness()
    assert not is_ready
    assert details["status"] == "UNINITIALIZED"

    service.initialize_catalog()
    is_ready, details = service.get_readiness()
    assert is_ready
    assert details["status"] == "READY"
    assert details["total_chunks"] > 0
    assert "error" in details
    assert details["error"] is None


def test_health_service_probes_knowledge_catalog():
    """Verify that HealthService includes knowledge_catalog in readiness probing."""
    # Ensure catalog is initialized
    service = get_knowledge_catalog_service()
    service.initialize_catalog()

    is_ready, details = HealthService.check_readiness()
    assert "knowledge_catalog" in details["checks"]
    cat_check = details["checks"]["knowledge_catalog"]
    assert cat_check["status"] == "READY"
    assert cat_check["total_chunks"] > 0
