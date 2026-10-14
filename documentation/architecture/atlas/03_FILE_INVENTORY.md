# MOTION Repository File Inventory

## 1. Executive Summary & Repository Metrics

- **Total Git-Tracked Files:** 2,615
- **Total Lines of Tracked Code/Text:** 566,506
- **Production-Critical Files:** 984

### Metrics by Subsystem

| Subsystem Key | Files | Lines of Code | Critical Files | Description |
| :--- | :--- | :--- | :--- | :--- |
| `tests_verification` | 628 | 127,489 | 0 | Test Suites & E2E Verification |
| `rendering_engine` | 504 | 61,762 | 478 | Remotion & FFmpeg Video Renderer |
| `miscellaneous` | 346 | 84,099 | 0 | Supporting Assets & Data |
| `contracts_schemas` | 310 | 89,815 | 310 | Contracts & Pydantic Schemas |
| `documentation_knowledge` | 298 | 108,327 | 0 | Architecture Documentation & ADRs |
| `agent_legacy` | 179 | 23,362 | 0 | Agent Directives, Plugins & Legacy |
| `dev_maintenance` | 145 | 32,292 | 0 | Developer & Maintenance Tooling |
| `context_knowledge_skills` | 53 | 10,840 | 53 | Context, Knowledge, Skills & Tools |
| `ai_creative` | 47 | 7,143 | 47 | AI Creative Intelligence & Narrative |
| `quality_control` | 28 | 4,953 | 28 | Quality Control & Automated Gates |
| `review_governance` | 25 | 5,313 | 25 | Review, Governance & Approvals |
| `http_transport` | 16 | 1,803 | 16 | HTTP Transport & Ingestion |
| `api_services` | 12 | 2,204 | 12 | Core Domain Services |
| `configuration` | 9 | 1,667 | 0 | Root Build & Project Configuration |
| `auth_tenancy` | 7 | 1,508 | 7 | Multi-Tenancy, Auth & Security |
| `durable_execution` | 6 | 3,093 | 6 | Durable Execution & Worker Engine |
| `storage_distribution` | 1 | 387 | 1 | Storage & Artifact Distribution |
| `canonical_documents` | 1 | 449 | 1 | Canonical Documents & Project State |

### Metrics by Role Classification

| Role Classification | File Count | Lines of Code | Critical Files | Operational Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `ACTIVE_RUNTIME` | 700 | 99,455 | 674 | Code directly executed during HTTP requests, workers, or rendering |
| `CONTRACT_SCHEMA` | 310 | 89,815 | 310 | Canonical schemas, Pydantic models, and strict interface contracts |
| `TEST_SUITE` | 628 | 127,489 | 0 | Automated unit, integration, and E2E verification test suites |
| `DEV_TOOLING` | 154 | 33,959 | 0 | Maintenance scripts, migrations, code generators, and dev tooling |
| `ARCHIVAL_DOC` | 298 | 108,327 | 0 | Technical documentation, ADRs, playbooks, and architecture atlas |
| `LEGACY_AGENT` | 179 | 23,362 | 0 | Legacy agent directives, MCP plugin configurations, and reference data |
| `SUPPORTING` | 346 | 84,099 | 0 | Supporting media assets, icons, audio samples, and data fixtures |
| **Total** | **2,615** | **566,506** | **984** | Fully reconciled repository file inventory |

---

## 2. Production-Critical Files Deep-Dive

Every file in this section represents an active, mission-critical component of MOTION. Failure or drift in any of these files directly halts or corrupts the production video generation pipeline.

| File Path | Subsystem | LOC | Role | Architectural Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| [`ai/narrative/__init__.py`](../../../ai/narrative/__init__.py) | `ai_creative` | 21 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/narrative/contracts.py`](../../../ai/narrative/contracts.py) | `ai_creative` | 36 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/narrative/metrics.py`](../../../ai/narrative/metrics.py) | `ai_creative` | 200 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/narrative/planner.py`](../../../ai/narrative/planner.py) | `ai_creative` | 407 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/__init__.py`](../../../ai/orchestration/__init__.py) | `ai_creative` | 104 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/activity.py`](../../../ai/orchestration/activity.py) | `ai_creative` | 261 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/activity_classification.py`](../../../ai/orchestration/activity_classification.py) | `ai_creative` | 254 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/dag.py`](../../../ai/orchestration/dag.py) | `ai_creative` | 179 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/errors.py`](../../../ai/orchestration/errors.py) | `ai_creative` | 107 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/lease.py`](../../../ai/orchestration/lease.py) | `ai_creative` | 35 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/recovery.py`](../../../ai/orchestration/recovery.py) | `ai_creative` | 312 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/repository.py`](../../../ai/orchestration/repository.py) | `ai_creative` | 252 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/retry.py`](../../../ai/orchestration/retry.py) | `ai_creative` | 84 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/service.py`](../../../ai/orchestration/service.py) | `ai_creative` | 407 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/state.py`](../../../ai/orchestration/state.py) | `ai_creative` | 129 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/orchestration/worker.py`](../../../ai/orchestration/worker.py) | `ai_creative` | 135 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/recipes/__init__.py`](../../../ai/recipes/__init__.py) | `ai_creative` | 31 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/recipes/contracts.py`](../../../ai/recipes/contracts.py) | `ai_creative` | 32 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/recipes/evaluator.py`](../../../ai/recipes/evaluator.py) | `ai_creative` | 189 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/recipes/registry.py`](../../../ai/recipes/registry.py) | `ai_creative` | 522 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/recipes/selector.py`](../../../ai/recipes/selector.py) | `ai_creative` | 307 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/taste/__init__.py`](../../../ai/taste/__init__.py) | `ai_creative` | 31 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/taste/context.py`](../../../ai/taste/context.py) | `ai_creative` | 56 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/taste/contracts.py`](../../../ai/taste/contracts.py) | `ai_creative` | 47 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/taste/engine.py`](../../../ai/taste/engine.py) | `ai_creative` | 90 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/taste/evaluator.py`](../../../ai/taste/evaluator.py) | `ai_creative` | 200 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`ai/taste/registry.py`](../../../ai/taste/registry.py) | `ai_creative` | 328 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/README.md`](../../../recipes/README.md) | `ai_creative` | 43 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/agent-browser-proof.json`](../../../recipes/agent-browser-proof.json) | `ai_creative` | 87 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/avatar-explainer.json`](../../../recipes/avatar-explainer.json) | `ai_creative` | 140 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/avatar-hook-broll.json`](../../../recipes/avatar-hook-broll.json) | `ai_creative` | 162 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/avatar-insta-split.json`](../../../recipes/avatar-insta-split.json) | `ai_creative` | 133 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/avatar-product-walkthrough.json`](../../../recipes/avatar-product-walkthrough.json) | `ai_creative` | 102 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/avatar-vo-broll.json`](../../../recipes/avatar-vo-broll.json) | `ai_creative` | 112 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/captioned-talking-head.json`](../../../recipes/captioned-talking-head.json) | `ai_creative` | 83 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/dynamic-montage-ad.json`](../../../recipes/dynamic-montage-ad.json) | `ai_creative` | 158 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/faceless-broll-ad.json`](../../../recipes/faceless-broll-ad.json) | `ai_creative` | 93 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/living-canvas-explainer.json`](../../../recipes/living-canvas-explainer.json) | `ai_creative` | 156 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/longform-repurpose.json`](../../../recipes/longform-repurpose.json) | `ai_creative` | 89 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/misotts-article-sprint.json`](../../../recipes/misotts-article-sprint.json) | `ai_creative` | 220 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/motion-collage-explainer.json`](../../../recipes/motion-collage-explainer.json) | `ai_creative` | 120 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/motion-graphics.json`](../../../recipes/motion-graphics.json) | `ai_creative` | 86 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/review-conquest-compilation.json`](../../../recipes/review-conquest-compilation.json) | `ai_creative` | 115 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/schema.json`](../../../recipes/schema.json) | `ai_creative` | 123 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/screencast-demo.json`](../../../recipes/screencast-demo.json) | `ai_creative` | 90 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/tabletop-levels-explainer.json`](../../../recipes/tabletop-levels-explainer.json) | `ai_creative` | 140 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`recipes/ugc-ai-ad.json`](../../../recipes/ugc-ai-ad.json) | `ai_creative` | 135 | `ACTIVE_RUNTIME` | Creative intelligence, narrative structuring, recipe selection, and blueprint compilation |
| [`api/services/__init__.py`](../../../api/services/__init__.py) | `api_services` | 4 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/authoring_service.py`](../../../api/services/authoring_service.py) | `api_services` | 260 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/brand_service.py`](../../../api/services/brand_service.py) | `api_services` | 150 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/capability_service.py`](../../../api/services/capability_service.py) | `api_services` | 244 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/creative_service.py`](../../../api/services/creative_service.py) | `api_services` | 521 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/domain_artifact_service.py`](../../../api/services/domain_artifact_service.py) | `api_services` | 122 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/gate_service.py`](../../../api/services/gate_service.py) | `api_services` | 32 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/health_service.py`](../../../api/services/health_service.py) | `api_services` | 423 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/output_service.py`](../../../api/services/output_service.py) | `api_services` | 153 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/override_service.py`](../../../api/services/override_service.py) | `api_services` | 223 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/render_service.py`](../../../api/services/render_service.py) | `api_services` | 29 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`api/services/scaffold_service.py`](../../../api/services/scaffold_service.py) | `api_services` | 43 | `ACTIVE_RUNTIME` | Domain service implementation for backend orchestration |
| [`scripts/core/security/__init__.py`](../../../scripts/core/security/__init__.py) | `auth_tenancy` | 71 | `ACTIVE_RUNTIME` | Authentication, tenant scoping, and cryptographic security guards |
| [`scripts/core/security/command_policy.py`](../../../scripts/core/security/command_policy.py) | `auth_tenancy` | 461 | `ACTIVE_RUNTIME` | Authentication, tenant scoping, and cryptographic security guards |
| [`scripts/core/security/env_policy.py`](../../../scripts/core/security/env_policy.py) | `auth_tenancy` | 227 | `ACTIVE_RUNTIME` | Authentication, tenant scoping, and cryptographic security guards |
| [`scripts/core/security/path_policy.py`](../../../scripts/core/security/path_policy.py) | `auth_tenancy` | 263 | `ACTIVE_RUNTIME` | Authentication, tenant scoping, and cryptographic security guards |
| [`scripts/core/security/permissions.py`](../../../scripts/core/security/permissions.py) | `auth_tenancy` | 240 | `ACTIVE_RUNTIME` | Authentication, tenant scoping, and cryptographic security guards |
| [`scripts/core/security/principal.py`](../../../scripts/core/security/principal.py) | `auth_tenancy` | 125 | `ACTIVE_RUNTIME` | Authentication, tenant scoping, and cryptographic security guards |
| [`scripts/core/security/settings.py`](../../../scripts/core/security/settings.py) | `auth_tenancy` | 121 | `ACTIVE_RUNTIME` | Authentication, tenant scoping, and cryptographic security guards |
| [`api/services/project_service.py`](../../../api/services/project_service.py) | `canonical_documents` | 449 | `ACTIVE_RUNTIME` | Canonical project state, revision CAS, and document authority |
| [`ai/context/__init__.py`](../../../ai/context/__init__.py) | `context_knowledge_skills` | 119 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/adapters/__init__.py`](../../../ai/context/adapters/__init__.py) | `context_knowledge_skills` | 6 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/adapters/knowledge_router_adapter.py`](../../../ai/context/adapters/knowledge_router_adapter.py) | `context_knowledge_skills` | 143 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/assembly.py`](../../../ai/context/assembly.py) | `context_knowledge_skills` | 139 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/budgeting.py`](../../../ai/context/budgeting.py) | `context_knowledge_skills` | 319 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/builder.py`](../../../ai/context/builder.py) | `context_knowledge_skills` | 222 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/compression.py`](../../../ai/context/compression.py) | `context_knowledge_skills` | 108 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/deduplication.py`](../../../ai/context/deduplication.py) | `context_knowledge_skills` | 161 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/needs.py`](../../../ai/context/needs.py) | `context_knowledge_skills` | 182 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/ranking.py`](../../../ai/context/ranking.py) | `context_knowledge_skills` | 127 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/retrieval.py`](../../../ai/context/retrieval.py) | `context_knowledge_skills` | 623 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/context/types.py`](../../../ai/context/types.py) | `context_knowledge_skills` | 341 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/__init__.py`](../../../ai/knowledge/__init__.py) | `context_knowledge_skills` | 87 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/catalog_service.py`](../../../ai/knowledge/catalog_service.py) | `context_knowledge_skills` | 121 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/contracts.py`](../../../ai/knowledge/contracts.py) | `context_knowledge_skills` | 151 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/indexer.py`](../../../ai/knowledge/indexer.py) | `context_knowledge_skills` | 187 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/loader.py`](../../../ai/knowledge/loader.py) | `context_knowledge_skills` | 382 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/registry.py`](../../../ai/knowledge/registry.py) | `context_knowledge_skills` | 135 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/retriever.py`](../../../ai/knowledge/retriever.py) | `context_knowledge_skills` | 540 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/router.py`](../../../ai/knowledge/router.py) | `context_knowledge_skills` | 125 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/knowledge/semantic.py`](../../../ai/knowledge/semantic.py) | `context_knowledge_skills` | 302 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/skills/__init__.py`](../../../ai/skills/__init__.py) | `context_knowledge_skills` | 71 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/skills/context.py`](../../../ai/skills/context.py) | `context_knowledge_skills` | 129 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/skills/contracts.py`](../../../ai/skills/contracts.py) | `context_knowledge_skills` | 90 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/skills/loader.py`](../../../ai/skills/loader.py) | `context_knowledge_skills` | 309 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/skills/registry.py`](../../../ai/skills/registry.py) | `context_knowledge_skills` | 115 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/skills/router.py`](../../../ai/skills/router.py) | `context_knowledge_skills` | 204 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/__init__.py`](../../../ai/tools/__init__.py) | `context_knowledge_skills` | 135 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/__init__.py`](../../../ai/tools/adapters/__init__.py) | `context_knowledge_skills` | 43 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/acquisition.py`](../../../ai/tools/adapters/acquisition.py) | `context_knowledge_skills` | 286 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/base.py`](../../../ai/tools/adapters/base.py) | `context_knowledge_skills` | 74 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/domain_service.py`](../../../ai/tools/adapters/domain_service.py) | `context_knowledge_skills` | 274 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/image_processing.py`](../../../ai/tools/adapters/image_processing.py) | `context_knowledge_skills` | 231 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/mcp.py`](../../../ai/tools/adapters/mcp.py) | `context_knowledge_skills` | 561 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/media_processing.py`](../../../ai/tools/adapters/media_processing.py) | `context_knowledge_skills` | 437 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/native.py`](../../../ai/tools/adapters/native.py) | `context_knowledge_skills` | 71 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/registry.py`](../../../ai/tools/adapters/registry.py) | `context_knowledge_skills` | 221 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/remote.py`](../../../ai/tools/adapters/remote.py) | `context_knowledge_skills` | 131 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/adapters/worker.py`](../../../ai/tools/adapters/worker.py) | `context_knowledge_skills` | 54 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/audit.py`](../../../ai/tools/audit.py) | `context_knowledge_skills` | 124 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/authorization.py`](../../../ai/tools/authorization.py) | `context_knowledge_skills` | 121 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/contracts.py`](../../../ai/tools/contracts.py) | `context_knowledge_skills` | 288 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/dispatcher.py`](../../../ai/tools/dispatcher.py) | `context_knowledge_skills` | 261 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/domain/__init__.py`](../../../ai/tools/domain/__init__.py) | `context_knowledge_skills` | 212 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/domain/assets.py`](../../../ai/tools/domain/assets.py) | `context_knowledge_skills` | 118 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/domain/blueprint.py`](../../../ai/tools/domain/blueprint.py) | `context_knowledge_skills` | 100 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/domain/projects.py`](../../../ai/tools/domain/projects.py) | `context_knowledge_skills` | 44 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/domain/qc.py`](../../../ai/tools/domain/qc.py) | `context_knowledge_skills` | 67 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/domain/runs.py`](../../../ai/tools/domain/runs.py) | `context_knowledge_skills` | 69 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/errors.py`](../../../ai/tools/errors.py) | `context_knowledge_skills` | 371 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/gateway.py`](../../../ai/tools/gateway.py) | `context_knowledge_skills` | 688 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/registry.py`](../../../ai/tools/registry.py) | `context_knowledge_skills` | 136 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/tools/types.py`](../../../ai/tools/types.py) | `context_knowledge_skills` | 285 | `ACTIVE_RUNTIME` | Context assembly, knowledge catalog, skill execution, and capability routing |
| [`ai/contracts/__init__.py`](../../../ai/contracts/__init__.py) | `contracts_schemas` | 638 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/activity.py`](../../../ai/contracts/activity.py) | `contracts_schemas` | 82 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/audio.py`](../../../ai/contracts/audio.py) | `contracts_schemas` | 103 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/base.py`](../../../ai/contracts/base.py) | `contracts_schemas` | 94 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/cache.py`](../../../ai/contracts/cache.py) | `contracts_schemas` | 132 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/capability.py`](../../../ai/contracts/capability.py) | `contracts_schemas` | 548 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/common.py`](../../../ai/contracts/common.py) | `contracts_schemas` | 168 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/__init__.py`](../../../ai/contracts/creative/__init__.py) | `contracts_schemas` | 235 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/brief.py`](../../../ai/contracts/creative/brief.py) | `contracts_schemas` | 138 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/conflict.py`](../../../ai/contracts/creative/conflict.py) | `contracts_schemas` | 95 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/cost.py`](../../../ai/contracts/creative/cost.py) | `contracts_schemas` | 339 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/directors.py`](../../../ai/contracts/creative/directors.py) | `contracts_schemas` | 77 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/feedback.py`](../../../ai/contracts/creative/feedback.py) | `contracts_schemas` | 220 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/narrative.py`](../../../ai/contracts/creative/narrative.py) | `contracts_schemas` | 70 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/plan.py`](../../../ai/contracts/creative/plan.py) | `contracts_schemas` | 208 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/recipe.py`](../../../ai/contracts/creative/recipe.py) | `contracts_schemas` | 111 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/regression.py`](../../../ai/contracts/creative/regression.py) | `contracts_schemas` | 254 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/skills_knowledge.py`](../../../ai/contracts/creative/skills_knowledge.py) | `contracts_schemas` | 174 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/taste.py`](../../../ai/contracts/creative/taste.py) | `contracts_schemas` | 87 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/creative/template_candidate.py`](../../../ai/contracts/creative/template_candidate.py) | `contracts_schemas` | 403 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/errors.py`](../../../ai/contracts/errors.py) | `contracts_schemas` | 139 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/evals.py`](../../../ai/contracts/evals.py) | `contracts_schemas` | 146 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/media.py`](../../../ai/contracts/media.py) | `contracts_schemas` | 334 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/media_ops.py`](../../../ai/contracts/media_ops.py) | `contracts_schemas` | 901 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/memory.py`](../../../ai/contracts/memory.py) | `contracts_schemas` | 110 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/model.py`](../../../ai/contracts/model.py) | `contracts_schemas` | 171 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/observability.py`](../../../ai/contracts/observability.py) | `contracts_schemas` | 82 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/prompt.py`](../../../ai/contracts/prompt.py) | `contracts_schemas` | 143 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/request.py`](../../../ai/contracts/request.py) | `contracts_schemas` | 87 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/response.py`](../../../ai/contracts/response.py) | `contracts_schemas` | 60 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/run.py`](../../../ai/contracts/run.py) | `contracts_schemas` | 134 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/specialized.py`](../../../ai/contracts/specialized.py) | `contracts_schemas` | 246 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/tools.py`](../../../ai/contracts/tools.py) | `contracts_schemas` | 111 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/usage.py`](../../../ai/contracts/usage.py) | `contracts_schemas` | 71 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`ai/contracts/vision.py`](../../../ai/contracts/vision.py) | `contracts_schemas` | 179 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/SceneContent.ts`](../../../contracts/SceneContent.ts) | `contracts_schemas` | 21 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/StyleSurface.ts`](../../../contracts/StyleSurface.ts) | `contracts_schemas` | 123 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/animations.ts`](../../../contracts/animations.ts) | `contracts_schemas` | 227 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/asset-resolver.ts`](../../../contracts/asset-resolver.ts) | `contracts_schemas` | 599 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/authoring.ts`](../../../contracts/authoring.ts) | `contracts_schemas` | 327 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/blueprint.ts`](../../../contracts/blueprint.ts) | `contracts_schemas` | 593 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/brand.ts`](../../../contracts/brand.ts) | `contracts_schemas` | 64 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/canonical-video.ts`](../../../contracts/canonical-video.ts) | `contracts_schemas` | 170 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/compositor.ts`](../../../contracts/compositor.ts) | `contracts_schemas` | 508 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/editor-session.ts`](../../../contracts/editor-session.ts) | `contracts_schemas` | 1,145 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/effects.ts`](../../../contracts/effects.ts) | `contracts_schemas` | 420 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/evaluator.ts`](../../../contracts/evaluator.ts) | `contracts_schemas` | 553 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/fixtures/asset_resolution_golden.json`](../../../contracts/fixtures/asset_resolution_golden.json) | `contracts_schemas` | 83 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/fonts.ts`](../../../contracts/fonts.ts) | `contracts_schemas` | 66 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/generated/ai_contracts.ts`](../../../contracts/generated/ai_contracts.ts) | `contracts_schemas` | 1,537 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/generated/creative_contracts.ts`](../../../contracts/generated/creative_contracts.ts) | `contracts_schemas` | 930 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/index.ts`](../../../contracts/index.ts) | `contracts_schemas` | 30 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/keyframes.ts`](../../../contracts/keyframes.ts) | `contracts_schemas` | 655 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/layers.ts`](../../../contracts/layers.ts) | `contracts_schemas` | 257 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/manifest.ts`](../../../contracts/manifest.ts) | `contracts_schemas` | 113 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/mutations.ts`](../../../contracts/mutations.ts) | `contracts_schemas` | 2,874 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/normalization.ts`](../../../contracts/normalization.ts) | `contracts_schemas` | 643 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/override-validator.ts`](../../../contracts/override-validator.ts) | `contracts_schemas` | 57 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/positions.ts`](../../../contracts/positions.ts) | `contracts_schemas` | 82 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/preview-fidelity.ts`](../../../contracts/preview-fidelity.ts) | `contracts_schemas` | 294 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/preview-proxy.ts`](../../../contracts/preview-proxy.ts) | `contracts_schemas` | 227 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/render-graph.ts`](../../../contracts/render-graph.ts) | `contracts_schemas` | 466 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/render-input.ts`](../../../contracts/render-input.ts) | `contracts_schemas` | 353 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/renderer.ts`](../../../contracts/renderer.ts) | `contracts_schemas` | 1,139 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/storage-service.ts`](../../../contracts/storage-service.ts) | `contracts_schemas` | 160 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/template-instantiator.ts`](../../../contracts/template-instantiator.ts) | `contracts_schemas` | 605 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/template-runtime-contract.json`](../../../contracts/template-runtime-contract.json) | `contracts_schemas` | 1,348 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/template-schemas.ts`](../../../contracts/template-schemas.ts) | `contracts_schemas` | 332 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/template-spec.ts`](../../../contracts/template-spec.ts) | `contracts_schemas` | 251 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/timeline.ts`](../../../contracts/timeline.ts) | `contracts_schemas` | 264 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`contracts/waveform.ts`](../../../contracts/waveform.ts) | `contracts_schemas` | 226 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_activity.schema.json`](../../../schemas/ai/ai_activity.schema.json) | `contracts_schemas` | 537 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_cache_entry.schema.json`](../../../schemas/ai/ai_cache_entry.schema.json) | `contracts_schemas` | 395 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_contracts.schema.json`](../../../schemas/ai/ai_contracts.schema.json) | `contracts_schemas` | 20,868 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_error.schema.json`](../../../schemas/ai/ai_error.schema.json) | `contracts_schemas` | 80 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_request.schema.json`](../../../schemas/ai/ai_request.schema.json) | `contracts_schemas` | 241 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_response.schema.json`](../../../schemas/ai/ai_response.schema.json) | `contracts_schemas` | 428 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_run.schema.json`](../../../schemas/ai/ai_run.schema.json) | `contracts_schemas` | 615 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_step.schema.json`](../../../schemas/ai/ai_step.schema.json) | `contracts_schemas` | 723 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/ai_trace.schema.json`](../../../schemas/ai/ai_trace.schema.json) | `contracts_schemas` | 390 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/align_audio_metadata_input.schema.json`](../../../schemas/ai/align_audio_metadata_input.schema.json) | `contracts_schemas` | 100 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/align_audio_metadata_output.schema.json`](../../../schemas/ai/align_audio_metadata_output.schema.json) | `contracts_schemas` | 175 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/aligned_segment_item.schema.json`](../../../schemas/ai/aligned_segment_item.schema.json) | `contracts_schemas` | 115 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/aligned_word_item.schema.json`](../../../schemas/ai/aligned_word_item.schema.json) | `contracts_schemas` | 53 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/analyze_loudness_input.schema.json`](../../../schemas/ai/analyze_loudness_input.schema.json) | `contracts_schemas` | 24 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/analyze_loudness_output.schema.json`](../../../schemas/ai/analyze_loudness_output.schema.json) | `contracts_schemas` | 69 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/audio_denoise_request.schema.json`](../../../schemas/ai/audio_denoise_request.schema.json) | `contracts_schemas` | 32 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/audio_denoise_result.schema.json`](../../../schemas/ai/audio_denoise_result.schema.json) | `contracts_schemas` | 127 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/audio_enhance_request.schema.json`](../../../schemas/ai/audio_enhance_request.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/audio_enhance_result.schema.json`](../../../schemas/ai/audio_enhance_result.schema.json) | `contracts_schemas` | 127 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/audio_intelligence.schema.json`](../../../schemas/ai/audio_intelligence.schema.json) | `contracts_schemas` | 558 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/audio_segment_item.schema.json`](../../../schemas/ai/audio_segment_item.schema.json) | `contracts_schemas` | 51 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/auto_crop_image_request.schema.json`](../../../schemas/ai/auto_crop_image_request.schema.json) | `contracts_schemas` | 67 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/auto_crop_image_result.schema.json`](../../../schemas/ai/auto_crop_image_result.schema.json) | `contracts_schemas` | 77 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/auto_crop_input.schema.json`](../../../schemas/ai/auto_crop_input.schema.json) | `contracts_schemas` | 32 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/auto_crop_output.schema.json`](../../../schemas/ai/auto_crop_output.schema.json) | `contracts_schemas` | 63 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/background_removal_request.schema.json`](../../../schemas/ai/background_removal_request.schema.json) | `contracts_schemas` | 30 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/background_removal_result.schema.json`](../../../schemas/ai/background_removal_result.schema.json) | `contracts_schemas` | 127 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/benchmark_debt.schema.json`](../../../schemas/ai/benchmark_debt.schema.json) | `contracts_schemas` | 49 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/cancel_job_input.schema.json`](../../../schemas/ai/cancel_job_input.schema.json) | `contracts_schemas` | 37 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/cancel_job_output.schema.json`](../../../schemas/ai/cancel_job_output.schema.json) | `contracts_schemas` | 36 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/capability_definition.schema.json`](../../../schemas/ai/capability_definition.schema.json) | `contracts_schemas` | 440 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/capability_request.schema.json`](../../../schemas/ai/capability_request.schema.json) | `contracts_schemas` | 494 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/capability_result.schema.json`](../../../schemas/ai/capability_result.schema.json) | `contracts_schemas` | 581 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/change_video_speed_input.schema.json`](../../../schemas/ai/change_video_speed_input.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/change_video_speed_output.schema.json`](../../../schemas/ai/change_video_speed_output.schema.json) | `contracts_schemas` | 49 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/check_cache_input.schema.json`](../../../schemas/ai/check_cache_input.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/check_cache_output.schema.json`](../../../schemas/ai/check_cache_output.schema.json) | `contracts_schemas` | 50 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/concatenate_videos_input.schema.json`](../../../schemas/ai/concatenate_videos_input.schema.json) | `contracts_schemas` | 40 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/concatenate_videos_output.schema.json`](../../../schemas/ai/concatenate_videos_output.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/convert_image_input.schema.json`](../../../schemas/ai/convert_image_input.schema.json) | `contracts_schemas` | 58 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/convert_image_output.schema.json`](../../../schemas/ai/convert_image_output.schema.json) | `contracts_schemas` | 59 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/convert_image_request.schema.json`](../../../schemas/ai/convert_image_request.schema.json) | `contracts_schemas` | 58 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/convert_image_result.schema.json`](../../../schemas/ai/convert_image_result.schema.json) | `contracts_schemas` | 59 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/cost_estimate.schema.json`](../../../schemas/ai/cost_estimate.schema.json) | `contracts_schemas` | 89 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/crop_image_ratio_request.schema.json`](../../../schemas/ai/crop_image_ratio_request.schema.json) | `contracts_schemas` | 52 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/crop_image_ratio_result.schema.json`](../../../schemas/ai/crop_image_ratio_result.schema.json) | `contracts_schemas` | 59 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/crop_ratio_input.schema.json`](../../../schemas/ai/crop_ratio_input.schema.json) | `contracts_schemas` | 30 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/crop_ratio_output.schema.json`](../../../schemas/ai/crop_ratio_output.schema.json) | `contracts_schemas` | 44 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/detect_black_frames_input.schema.json`](../../../schemas/ai/detect_black_frames_input.schema.json) | `contracts_schemas` | 40 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/detect_black_frames_output.schema.json`](../../../schemas/ai/detect_black_frames_output.schema.json) | `contracts_schemas` | 45 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/detect_silence_input.schema.json`](../../../schemas/ai/detect_silence_input.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/detect_silence_output.schema.json`](../../../schemas/ai/detect_silence_output.schema.json) | `contracts_schemas` | 93 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/download_icon_input.schema.json`](../../../schemas/ai/download_icon_input.schema.json) | `contracts_schemas` | 45 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/download_icon_output.schema.json`](../../../schemas/ai/download_icon_output.schema.json) | `contracts_schemas` | 37 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/download_remote_media_input.schema.json`](../../../schemas/ai/download_remote_media_input.schema.json) | `contracts_schemas` | 43 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/download_remote_media_output.schema.json`](../../../schemas/ai/download_remote_media_output.schema.json) | `contracts_schemas` | 45 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/downloaded_asset_item.schema.json`](../../../schemas/ai/downloaded_asset_item.schema.json) | `contracts_schemas` | 45 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/enforce_keyframes_input.schema.json`](../../../schemas/ai/enforce_keyframes_input.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/enforce_keyframes_output.schema.json`](../../../schemas/ai/enforce_keyframes_output.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/eval_dataset.schema.json`](../../../schemas/ai/eval_dataset.schema.json) | `contracts_schemas` | 226 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/eval_example.schema.json`](../../../schemas/ai/eval_example.schema.json) | `contracts_schemas` | 85 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/eval_result.schema.json`](../../../schemas/ai/eval_result.schema.json) | `contracts_schemas` | 136 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/extend_audio_input.schema.json`](../../../schemas/ai/extend_audio_input.schema.json) | `contracts_schemas` | 50 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/extend_audio_output.schema.json`](../../../schemas/ai/extend_audio_output.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/extend_video_input.schema.json`](../../../schemas/ai/extend_video_input.schema.json) | `contracts_schemas` | 37 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/extend_video_output.schema.json`](../../../schemas/ai/extend_video_output.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/extract_media_page_input.schema.json`](../../../schemas/ai/extract_media_page_input.schema.json) | `contracts_schemas` | 30 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/extract_media_page_output.schema.json`](../../../schemas/ai/extract_media_page_output.schema.json) | `contracts_schemas` | 79 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/get_job_status_input.schema.json`](../../../schemas/ai/get_job_status_input.schema.json) | `contracts_schemas` | 24 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/get_job_status_output.schema.json`](../../../schemas/ai/get_job_status_output.schema.json) | `contracts_schemas` | 65 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/icon_search_result_item.schema.json`](../../../schemas/ai/icon_search_result_item.schema.json) | `contracts_schemas` | 44 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/image_generation_request.schema.json`](../../../schemas/ai/image_generation_request.schema.json) | `contracts_schemas` | 73 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/image_generation_result.schema.json`](../../../schemas/ai/image_generation_result.schema.json) | `contracts_schemas` | 141 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/implementation_descriptor.schema.json`](../../../schemas/ai/implementation_descriptor.schema.json) | `contracts_schemas` | 84 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/inspect_media_input.schema.json`](../../../schemas/ai/inspect_media_input.schema.json) | `contracts_schemas` | 27 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/inspect_media_output.schema.json`](../../../schemas/ai/inspect_media_output.schema.json) | `contracts_schemas` | 300 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/lip_sync_request.schema.json`](../../../schemas/ai/lip_sync_request.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/lip_sync_result.schema.json`](../../../schemas/ai/lip_sync_result.schema.json) | `contracts_schemas` | 136 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/media_intelligence.schema.json`](../../../schemas/ai/media_intelligence.schema.json) | `contracts_schemas` | 1,980 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/media_intelligence_ref.schema.json`](../../../schemas/ai/media_intelligence_ref.schema.json) | `contracts_schemas` | 51 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/memory_query.schema.json`](../../../schemas/ai/memory_query.schema.json) | `contracts_schemas` | 90 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/memory_result.schema.json`](../../../schemas/ai/memory_result.schema.json) | `contracts_schemas` | 172 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/model_requirement.schema.json`](../../../schemas/ai/model_requirement.schema.json) | `contracts_schemas` | 307 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/model_selection.schema.json`](../../../schemas/ai/model_selection.schema.json) | `contracts_schemas` | 128 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/mutate_asset_status_input.schema.json`](../../../schemas/ai/mutate_asset_status_input.schema.json) | `contracts_schemas` | 44 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/mutate_asset_status_output.schema.json`](../../../schemas/ai/mutate_asset_status_output.schema.json) | `contracts_schemas` | 42 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/normalize_audio_input.schema.json`](../../../schemas/ai/normalize_audio_input.schema.json) | `contracts_schemas` | 54 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/normalize_audio_output.schema.json`](../../../schemas/ai/normalize_audio_output.schema.json) | `contracts_schemas` | 50 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/normalize_loudness_input.schema.json`](../../../schemas/ai/normalize_loudness_input.schema.json) | `contracts_schemas` | 39 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/normalize_loudness_output.schema.json`](../../../schemas/ai/normalize_loudness_output.schema.json) | `contracts_schemas` | 36 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/optimize_image_input.schema.json`](../../../schemas/ai/optimize_image_input.schema.json) | `contracts_schemas` | 68 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/optimize_image_output.schema.json`](../../../schemas/ai/optimize_image_output.schema.json) | `contracts_schemas` | 66 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/optimize_image_request.schema.json`](../../../schemas/ai/optimize_image_request.schema.json) | `contracts_schemas` | 68 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/optimize_image_result.schema.json`](../../../schemas/ai/optimize_image_result.schema.json) | `contracts_schemas` | 66 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/person_segmentation_request.schema.json`](../../../schemas/ai/person_segmentation_request.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/person_segmentation_result.schema.json`](../../../schemas/ai/person_segmentation_result.schema.json) | `contracts_schemas` | 136 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prepare_image_asset_input.schema.json`](../../../schemas/ai/prepare_image_asset_input.schema.json) | `contracts_schemas` | 108 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prepare_image_asset_output.schema.json`](../../../schemas/ai/prepare_image_asset_output.schema.json) | `contracts_schemas` | 78 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prepare_image_asset_request.schema.json`](../../../schemas/ai/prepare_image_asset_request.schema.json) | `contracts_schemas` | 108 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prepare_image_asset_result.schema.json`](../../../schemas/ai/prepare_image_asset_result.schema.json) | `contracts_schemas` | 78 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prepare_vo_segments_input.schema.json`](../../../schemas/ai/prepare_vo_segments_input.schema.json) | `contracts_schemas` | 54 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prepare_vo_segments_output.schema.json`](../../../schemas/ai/prepare_vo_segments_output.schema.json) | `contracts_schemas` | 104 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prepared_vo_segment_item.schema.json`](../../../schemas/ai/prepared_vo_segment_item.schema.json) | `contracts_schemas` | 57 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/probe_image_input.schema.json`](../../../schemas/ai/probe_image_input.schema.json) | `contracts_schemas` | 30 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/probe_image_output.schema.json`](../../../schemas/ai/probe_image_output.schema.json) | `contracts_schemas` | 101 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/probe_image_request.schema.json`](../../../schemas/ai/probe_image_request.schema.json) | `contracts_schemas` | 30 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/probe_image_result.schema.json`](../../../schemas/ai/probe_image_result.schema.json) | `contracts_schemas` | 101 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prompt_contract.schema.json`](../../../schemas/ai/prompt_contract.schema.json) | `contracts_schemas` | 171 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prompt_metadata.schema.json`](../../../schemas/ai/prompt_metadata.schema.json) | `contracts_schemas` | 70 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prompt_render_request.schema.json`](../../../schemas/ai/prompt_render_request.schema.json) | `contracts_schemas` | 55 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/prompt_render_result.schema.json`](../../../schemas/ai/prompt_render_result.schema.json) | `contracts_schemas` | 69 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/resize_image_request.schema.json`](../../../schemas/ai/resize_image_request.schema.json) | `contracts_schemas` | 102 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/resize_image_result.schema.json`](../../../schemas/ai/resize_image_result.schema.json) | `contracts_schemas` | 52 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/resize_video_input.schema.json`](../../../schemas/ai/resize_video_input.schema.json) | `contracts_schemas` | 44 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/resize_video_output.schema.json`](../../../schemas/ai/resize_video_output.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_icons_input.schema.json`](../../../schemas/ai/search_icons_input.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_icons_output.schema.json`](../../../schemas/ai/search_icons_output.schema.json) | `contracts_schemas` | 77 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_sound_effects_input.schema.json`](../../../schemas/ai/search_sound_effects_input.schema.json) | `contracts_schemas` | 50 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_sound_effects_output.schema.json`](../../../schemas/ai/search_sound_effects_output.schema.json) | `contracts_schemas` | 158 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_stock_audio_input.schema.json`](../../../schemas/ai/search_stock_audio_input.schema.json) | `contracts_schemas` | 32 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_stock_audio_output.schema.json`](../../../schemas/ai/search_stock_audio_output.schema.json) | `contracts_schemas` | 158 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_stock_images_input.schema.json`](../../../schemas/ai/search_stock_images_input.schema.json) | `contracts_schemas` | 45 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_stock_images_output.schema.json`](../../../schemas/ai/search_stock_images_output.schema.json) | `contracts_schemas` | 158 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_stock_videos_input.schema.json`](../../../schemas/ai/search_stock_videos_input.schema.json) | `contracts_schemas` | 45 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/search_stock_videos_output.schema.json`](../../../schemas/ai/search_stock_videos_output.schema.json) | `contracts_schemas` | 158 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/segment_speech_input.schema.json`](../../../schemas/ai/segment_speech_input.schema.json) | `contracts_schemas` | 220 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/segment_speech_output.schema.json`](../../../schemas/ai/segment_speech_output.schema.json) | `contracts_schemas` | 85 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/silence_interval_item.schema.json`](../../../schemas/ai/silence_interval_item.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/speech_intelligence.schema.json`](../../../schemas/ai/speech_intelligence.schema.json) | `contracts_schemas` | 417 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/speech_manifest_input.schema.json`](../../../schemas/ai/speech_manifest_input.schema.json) | `contracts_schemas` | 30 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/speech_manifest_output.schema.json`](../../../schemas/ai/speech_manifest_output.schema.json) | `contracts_schemas` | 45 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/speech_text_segment_item.schema.json`](../../../schemas/ai/speech_text_segment_item.schema.json) | `contracts_schemas` | 79 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/speech_timeline_input.schema.json`](../../../schemas/ai/speech_timeline_input.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/speech_timeline_output.schema.json`](../../../schemas/ai/speech_timeline_output.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/speech_to_text_input.schema.json`](../../../schemas/ai/speech_to_text_input.schema.json) | `contracts_schemas` | 56 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/split_speech_text_input.schema.json`](../../../schemas/ai/split_speech_text_input.schema.json) | `contracts_schemas` | 50 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/split_speech_text_output.schema.json`](../../../schemas/ai/split_speech_text_output.schema.json) | `contracts_schemas` | 126 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/stock_media_item.schema.json`](../../../schemas/ai/stock_media_item.schema.json) | `contracts_schemas` | 118 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/store_cache_input.schema.json`](../../../schemas/ai/store_cache_input.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/store_cache_output.schema.json`](../../../schemas/ai/store_cache_output.schema.json) | `contracts_schemas` | 44 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/thumbnail_input.schema.json`](../../../schemas/ai/thumbnail_input.schema.json) | `contracts_schemas` | 60 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/thumbnail_output.schema.json`](../../../schemas/ai/thumbnail_output.schema.json) | `contracts_schemas` | 52 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/thumbnail_request.schema.json`](../../../schemas/ai/thumbnail_request.schema.json) | `contracts_schemas` | 60 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/thumbnail_result.schema.json`](../../../schemas/ai/thumbnail_result.schema.json) | `contracts_schemas` | 52 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/tool_call.schema.json`](../../../schemas/ai/tool_call.schema.json) | `contracts_schemas` | 51 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/tool_result.schema.json`](../../../schemas/ai/tool_result.schema.json) | `contracts_schemas` | 160 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/trace_span_record.schema.json`](../../../schemas/ai/trace_span_record.schema.json) | `contracts_schemas` | 351 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/trim_audio_input.schema.json`](../../../schemas/ai/trim_audio_input.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/trim_audio_output.schema.json`](../../../schemas/ai/trim_audio_output.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/trim_silence_input.schema.json`](../../../schemas/ai/trim_silence_input.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/trim_silence_output.schema.json`](../../../schemas/ai/trim_silence_output.schema.json) | `contracts_schemas` | 52 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/trim_video_input.schema.json`](../../../schemas/ai/trim_video_input.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/trim_video_output.schema.json`](../../../schemas/ai/trim_video_output.schema.json) | `contracts_schemas` | 31 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/tts_request.schema.json`](../../../schemas/ai/tts_request.schema.json) | `contracts_schemas` | 73 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/tts_result.schema.json`](../../../schemas/ai/tts_result.schema.json) | `contracts_schemas` | 141 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/upscale_image_input.schema.json`](../../../schemas/ai/upscale_image_input.schema.json) | `contracts_schemas` | 60 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/upscale_image_output.schema.json`](../../../schemas/ai/upscale_image_output.schema.json) | `contracts_schemas` | 38 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/upscale_request.schema.json`](../../../schemas/ai/upscale_request.schema.json) | `contracts_schemas` | 60 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/upscale_result.schema.json`](../../../schemas/ai/upscale_result.schema.json) | `contracts_schemas` | 135 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/usage_record.schema.json`](../../../schemas/ai/usage_record.schema.json) | `contracts_schemas` | 158 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/video_generation_request.schema.json`](../../../schemas/ai/video_generation_request.schema.json) | `contracts_schemas` | 76 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/video_generation_result.schema.json`](../../../schemas/ai/video_generation_result.schema.json) | `contracts_schemas` | 155 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/visual_intelligence.schema.json`](../../../schemas/ai/visual_intelligence.schema.json) | `contracts_schemas` | 755 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/vocal_isolation_request.schema.json`](../../../schemas/ai/vocal_isolation_request.schema.json) | `contracts_schemas` | 30 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/ai/vocal_isolation_result.schema.json`](../../../schemas/ai/vocal_isolation_result.schema.json) | `contracts_schemas` | 147 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/blueprint.schema.json`](../../../schemas/blueprint.schema.json) | `contracts_schemas` | 578 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/brand.schema.json`](../../../schemas/brand.schema.json) | `contracts_schemas` | 63 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/blueprint_compilation_result.schema.json`](../../../schemas/creative/blueprint_compilation_result.schema.json) | `contracts_schemas` | 57 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/candidate_gate_result.schema.json`](../../../schemas/creative/candidate_gate_result.schema.json) | `contracts_schemas` | 66 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/candidate_promotion_record.schema.json`](../../../schemas/creative/candidate_promotion_record.schema.json) | `contracts_schemas` | 143 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/candidate_review_bundle.schema.json`](../../../schemas/creative/candidate_review_bundle.schema.json) | `contracts_schemas` | 144 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/candidate_review_decision.schema.json`](../../../schemas/creative/candidate_review_decision.schema.json) | `contracts_schemas` | 139 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/candidate_validation_report.schema.json`](../../../schemas/creative/candidate_validation_report.schema.json) | `contracts_schemas` | 271 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/compose_component_ref.schema.json`](../../../schemas/creative/compose_component_ref.schema.json) | `contracts_schemas` | 39 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/compose_evaluation_result.schema.json`](../../../schemas/creative/compose_evaluation_result.schema.json) | `contracts_schemas` | 192 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/composition_layer.schema.json`](../../../schemas/creative/composition_layer.schema.json) | `contracts_schemas` | 33 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/composition_plan.schema.json`](../../../schemas/creative/composition_plan.schema.json) | `contracts_schemas` | 128 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_brief.schema.json`](../../../schemas/creative/creative_brief.schema.json) | `contracts_schemas` | 423 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_case_grade.schema.json`](../../../schemas/creative/creative_case_grade.schema.json) | `contracts_schemas` | 142 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_conflict.schema.json`](../../../schemas/creative/creative_conflict.schema.json) | `contracts_schemas` | 116 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_constraints.schema.json`](../../../schemas/creative/creative_constraints.schema.json) | `contracts_schemas` | 116 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_contracts.schema.json`](../../../schemas/creative/creative_contracts.schema.json) | `contracts_schemas` | 11,220 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_cost_audit_run.schema.json`](../../../schemas/creative/creative_cost_audit_run.schema.json) | `contracts_schemas` | 223 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_eval_case.schema.json`](../../../schemas/creative/creative_eval_case.schema.json) | `contracts_schemas` | 349 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_eval_run.schema.json`](../../../schemas/creative/creative_eval_run.schema.json) | `contracts_schemas` | 191 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_feedback.schema.json`](../../../schemas/creative/creative_feedback.schema.json) | `contracts_schemas` | 355 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_intent.schema.json`](../../../schemas/creative/creative_intent.schema.json) | `contracts_schemas` | 113 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_plan.schema.json`](../../../schemas/creative/creative_plan.schema.json) | `contracts_schemas` | 954 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_plan_validation_result.schema.json`](../../../schemas/creative/creative_plan_validation_result.schema.json) | `contracts_schemas` | 40 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_project_cost_summary.schema.json`](../../../schemas/creative/creative_project_cost_summary.schema.json) | `contracts_schemas` | 200 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_tier_decision.schema.json`](../../../schemas/creative/creative_tier_decision.schema.json) | `contracts_schemas` | 455 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/creative_usage_event.schema.json`](../../../schemas/creative/creative_usage_event.schema.json) | `contracts_schemas` | 309 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/director_recommendation_bundle.schema.json`](../../../schemas/creative/director_recommendation_bundle.schema.json) | `contracts_schemas` | 332 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/effective_user_style.schema.json`](../../../schemas/creative/effective_user_style.schema.json) | `contracts_schemas` | 293 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/efficiency_finding.schema.json`](../../../schemas/creative/efficiency_finding.schema.json) | `contracts_schemas` | 113 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/emotion_direction.schema.json`](../../../schemas/creative/emotion_direction.schema.json) | `contracts_schemas` | 61 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/feedback_classification.schema.json`](../../../schemas/creative/feedback_classification.schema.json) | `contracts_schemas` | 206 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/field_provenance.schema.json`](../../../schemas/creative/field_provenance.schema.json) | `contracts_schemas` | 54 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/judge_calibration_record.schema.json`](../../../schemas/creative/judge_calibration_record.schema.json) | `contracts_schemas` | 53 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/knowledge_descriptor.schema.json`](../../../schemas/creative/knowledge_descriptor.schema.json) | `contracts_schemas` | 143 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/motion_direction.schema.json`](../../../schemas/creative/motion_direction.schema.json) | `contracts_schemas` | 74 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/narrative_beat.schema.json`](../../../schemas/creative/narrative_beat.schema.json) | `contracts_schemas` | 80 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/narrative_direction.schema.json`](../../../schemas/creative/narrative_direction.schema.json) | `contracts_schemas` | 67 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/narrative_plan.schema.json`](../../../schemas/creative/narrative_plan.schema.json) | `contracts_schemas` | 209 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/pairwise_grade_result.schema.json`](../../../schemas/creative/pairwise_grade_result.schema.json) | `contracts_schemas` | 43 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/promotion_decision.schema.json`](../../../schemas/creative/promotion_decision.schema.json) | `contracts_schemas` | 73 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/promotion_manifest.schema.json`](../../../schemas/creative/promotion_manifest.schema.json) | `contracts_schemas` | 114 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/recipe_definition.schema.json`](../../../schemas/creative/recipe_definition.schema.json) | `contracts_schemas` | 395 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/recipe_selection.schema.json`](../../../schemas/creative/recipe_selection.schema.json) | `contracts_schemas` | 168 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/recipe_stage.schema.json`](../../../schemas/creative/recipe_stage.schema.json) | `contracts_schemas` | 126 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/resolved_creative_guidance.schema.json`](../../../schemas/creative/resolved_creative_guidance.schema.json) | `contracts_schemas` | 781 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/resolved_template_decision.schema.json`](../../../schemas/creative/resolved_template_decision.schema.json) | `contracts_schemas` | 33 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/reuse_candidate_score.schema.json`](../../../schemas/creative/reuse_candidate_score.schema.json) | `contracts_schemas` | 52 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/reuse_evaluation_result.schema.json`](../../../schemas/creative/reuse_evaluation_result.schema.json) | `contracts_schemas` | 130 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/scene_intent.schema.json`](../../../schemas/creative/scene_intent.schema.json) | `contracts_schemas` | 195 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/sfx_direction.schema.json`](../../../schemas/creative/sfx_direction.schema.json) | `contracts_schemas` | 75 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/skill_definition.schema.json`](../../../schemas/creative/skill_definition.schema.json) | `contracts_schemas` | 211 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/style_decision_trace.schema.json`](../../../schemas/creative/style_decision_trace.schema.json) | `contracts_schemas` | 108 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/style_preference_provenance.schema.json`](../../../schemas/creative/style_preference_provenance.schema.json) | `contracts_schemas` | 101 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/taste_context.schema.json`](../../../schemas/creative/taste_context.schema.json) | `contracts_schemas` | 928 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/taste_decision.schema.json`](../../../schemas/creative/taste_decision.schema.json) | `contracts_schemas` | 76 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/taste_rule.schema.json`](../../../schemas/creative/taste_rule.schema.json) | `contracts_schemas` | 120 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/template_candidate.schema.json`](../../../schemas/creative/template_candidate.schema.json) | `contracts_schemas` | 290 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/trace_assertion.schema.json`](../../../schemas/creative/trace_assertion.schema.json) | `contracts_schemas` | 140 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/trace_assertion_result.schema.json`](../../../schemas/creative/trace_assertion_result.schema.json) | `contracts_schemas` | 34 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/user_style_profile.schema.json`](../../../schemas/creative/user_style_profile.schema.json) | `contracts_schemas` | 288 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/creative/validation_snapshot.schema.json`](../../../schemas/creative/validation_snapshot.schema.json) | `contracts_schemas` | 103 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/examples/prj_demo/blueprint.json`](../../../schemas/examples/prj_demo/blueprint.json) | `contracts_schemas` | 84 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/examples/prj_demo/brand.json`](../../../schemas/examples/prj_demo/brand.json) | `contracts_schemas` | 16 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/examples/prj_demo/manifest.json`](../../../schemas/examples/prj_demo/manifest.json) | `contracts_schemas` | 78 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/examples/prj_demo/overrides.json`](../../../schemas/examples/prj_demo/overrides.json) | `contracts_schemas` | 16 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/examples/prj_demo/project.json`](../../../schemas/examples/prj_demo/project.json) | `contracts_schemas` | 15 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/examples/prj_demo/state.json`](../../../schemas/examples/prj_demo/state.json) | `contracts_schemas` | 48 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/manifest.schema.json`](../../../schemas/manifest.schema.json) | `contracts_schemas` | 79 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/manifest.v2.schema.json`](../../../schemas/manifest.v2.schema.json) | `contracts_schemas` | 106 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/overrides.schema.json`](../../../schemas/overrides.schema.json) | `contracts_schemas` | 54 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/project.schema.json`](../../../schemas/project.schema.json) | `contracts_schemas` | 114 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/state.schema.json`](../../../schemas/state.schema.json) | `contracts_schemas` | 241 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`schemas/template_proposal_schema.json`](../../../schemas/template_proposal_schema.json) | `contracts_schemas` | 94 | `CONTRACT_SCHEMA` | Pydantic models, JSON schemas, and architectural interface contracts |
| [`api/services/pipeline_service.py`](../../../api/services/pipeline_service.py) | `durable_execution` | 389 | `ACTIVE_RUNTIME` | Durable run management, worker lease fencing, and pipeline orchestration |
| [`api/services/run_service.py`](../../../api/services/run_service.py) | `durable_execution` | 292 | `ACTIVE_RUNTIME` | Durable run management, worker lease fencing, and pipeline orchestration |
| [`scripts/core/project_lock.py`](../../../scripts/core/project_lock.py) | `durable_execution` | 249 | `ACTIVE_RUNTIME` | Durable run management, worker lease fencing, and pipeline orchestration |
| [`scripts/core/run_repository.py`](../../../scripts/core/run_repository.py) | `durable_execution` | 852 | `ACTIVE_RUNTIME` | Durable run management, worker lease fencing, and pipeline orchestration |
| [`scripts/core/worker.py`](../../../scripts/core/worker.py) | `durable_execution` | 766 | `ACTIVE_RUNTIME` | Durable run management, worker lease fencing, and pipeline orchestration |
| [`scripts/pipeline.py`](../../../scripts/pipeline.py) | `durable_execution` | 545 | `ACTIVE_RUNTIME` | Durable run management, worker lease fencing, and pipeline orchestration |
| [`api/main.py`](../../../api/main.py) | `http_transport` | 92 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/__init__.py`](../../../api/routers/__init__.py) | `http_transport` | 4 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/artifacts.py`](../../../api/routers/artifacts.py) | `http_transport` | 144 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/assets.py`](../../../api/routers/assets.py) | `http_transport` | 89 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/authoring.py`](../../../api/routers/authoring.py) | `http_transport` | 290 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/blueprint.py`](../../../api/routers/blueprint.py) | `http_transport` | 91 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/brand.py`](../../../api/routers/brand.py) | `http_transport` | 59 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/candidate_promotions.py`](../../../api/routers/candidate_promotions.py) | `http_transport` | 147 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/candidate_reviews.py`](../../../api/routers/candidate_reviews.py) | `http_transport` | 242 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/capabilities.py`](../../../api/routers/capabilities.py) | `http_transport` | 58 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/gates.py`](../../../api/routers/gates.py) | `http_transport` | 79 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/health.py`](../../../api/routers/health.py) | `http_transport` | 62 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/outputs.py`](../../../api/routers/outputs.py) | `http_transport` | 76 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/projects.py`](../../../api/routers/projects.py) | `http_transport` | 120 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/render.py`](../../../api/routers/render.py) | `http_transport` | 55 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`api/routers/runs.py`](../../../api/routers/runs.py) | `http_transport` | 195 | `ACTIVE_RUNTIME` | FastAPI endpoint routing and HTTP protocol handling |
| [`scripts/gates/__init__.py`](../../../scripts/gates/__init__.py) | `quality_control` | 0 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/asset_gate.py`](../../../scripts/gates/asset_gate.py) | `quality_control` | 109 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/code_template_gate.py`](../../../scripts/gates/code_template_gate.py) | `quality_control` | 267 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/final_qc.py`](../../../scripts/gates/final_qc.py) | `quality_control` | 833 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/motion_validator.py`](../../../scripts/gates/motion_validator.py) | `quality_control` | 380 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/plan_gate.py`](../../../scripts/gates/plan_gate.py) | `quality_control` | 251 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/probe_qc.py`](../../../scripts/gates/probe_qc.py) | `quality_control` | 741 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/smart_qc.py`](../../../scripts/gates/smart_qc.py) | `quality_control` | 229 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/taste_gate.py`](../../../scripts/gates/taste_gate.py) | `quality_control` | 140 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/validate_blueprint.py`](../../../scripts/gates/validate_blueprint.py) | `quality_control` | 191 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/gates/vo_quality_check.py`](../../../scripts/gates/vo_quality_check.py) | `quality_control` | 60 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/__init__.py`](../../../scripts/validators/__init__.py) | `quality_control` | 0 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/audit_imports.py`](../../../scripts/validators/audit_imports.py) | `quality_control` | 56 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/audit_skill.py`](../../../scripts/validators/audit_skill.py) | `quality_control` | 146 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/candidate_ast_worker.cjs`](../../../scripts/validators/candidate_ast_worker.cjs) | `quality_control` | 0 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/candidate_runtime_runner.py`](../../../scripts/validators/candidate_runtime_runner.py) | `quality_control` | 343 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/check_dependencies_lock.py`](../../../scripts/validators/check_dependencies_lock.py) | `quality_control` | 63 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/check_ground_truth_sync.py`](../../../scripts/validators/check_ground_truth_sync.py) | `quality_control` | 54 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/check_secrets.py`](../../../scripts/validators/check_secrets.py) | `quality_control` | 96 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/custom_code_validator.py`](../../../scripts/validators/custom_code_validator.py) | `quality_control` | 184 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/inspect_template.py`](../../../scripts/validators/inspect_template.py) | `quality_control` | 80 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/spec_validator.py`](../../../scripts/validators/spec_validator.py) | `quality_control` | 99 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/template_lint.py`](../../../scripts/validators/template_lint.py) | `quality_control` | 84 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/template_proposal_validator.py`](../../../scripts/validators/template_proposal_validator.py) | `quality_control` | 224 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/validate_schemas.py`](../../../scripts/validators/validate_schemas.py) | `quality_control` | 140 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/validate_template.py`](../../../scripts/validators/validate_template.py) | `quality_control` | 44 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/verify_links.py`](../../../scripts/validators/verify_links.py) | `quality_control` | 77 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`scripts/validators/verify_media_layer.py`](../../../scripts/validators/verify_media_layer.py) | `quality_control` | 62 | `ACTIVE_RUNTIME` | Automated technical QC, Probe QC, Final QC, and structural gate verification |
| [`remotion-app/build_caption_props.py`](../../../remotion-app/build_caption_props.py) | `rendering_engine` | 87 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/remotion.config.ts`](../../../remotion-app/remotion.config.ts) | `rendering_engine` | 82 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/BlueprintVideo.tsx`](../../../remotion-app/src/BlueprintVideo.tsx) | `rendering_engine` | 282 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/BrandContext.tsx`](../../../remotion-app/src/BrandContext.tsx) | `rendering_engine` | 35 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/CanonicalVideo.tsx`](../../../remotion-app/src/CanonicalVideo.tsx) | `rendering_engine` | 464 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/CursorInteractionContext.tsx`](../../../remotion-app/src/CursorInteractionContext.tsx) | `rendering_engine` | 5 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/Root.tsx`](../../../remotion-app/src/Root.tsx) | `rendering_engine` | 142 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/Showcase.tsx`](../../../remotion-app/src/Showcase.tsx) | `rendering_engine` | 66 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/TemplateGallery.tsx`](../../../remotion-app/src/TemplateGallery.tsx) | `rendering_engine` | 99 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/animations.ts`](../../../remotion-app/src/animations.ts) | `rendering_engine` | 121 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/captionLayout.ts`](../../../remotion-app/src/captionLayout.ts) | `rendering_engine` | 61 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/ai-composer-showcase/index.tsx`](../../../remotion-app/src/compositions/ai-composer-showcase/index.tsx) | `rendering_engine` | 323 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/ai-generation-canvas/index.tsx`](../../../remotion-app/src/compositions/ai-generation-canvas/index.tsx) | `rendering_engine` | 683 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/bento-pan/index.tsx`](../../../remotion-app/src/compositions/bento-pan/index.tsx) | `rendering_engine` | 224 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/browser-flow/index.tsx`](../../../remotion-app/src/compositions/browser-flow/index.tsx) | `rendering_engine` | 57 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/creator-reel/index.tsx`](../../../remotion-app/src/compositions/creator-reel/index.tsx) | `rendering_engine` | 175 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/dashboard-populate/index.tsx`](../../../remotion-app/src/compositions/dashboard-populate/index.tsx) | `rendering_engine` | 87 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/data-story/index.tsx`](../../../remotion-app/src/compositions/data-story/index.tsx) | `rendering_engine` | 212 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/deploy-reveal/index.tsx`](../../../remotion-app/src/compositions/deploy-reveal/index.tsx) | `rendering_engine` | 265 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/ecosystem-orbit/index.tsx`](../../../remotion-app/src/compositions/ecosystem-orbit/index.tsx) | `rendering_engine` | 274 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/hero-device-assemble/index.tsx`](../../../remotion-app/src/compositions/hero-device-assemble/index.tsx) | `rendering_engine` | 474 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/hero-loop/index.tsx`](../../../remotion-app/src/compositions/hero-loop/index.tsx) | `rendering_engine` | 828 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/image-expand/index.tsx`](../../../remotion-app/src/compositions/image-expand/index.tsx) | `rendering_engine` | 206 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/intro/index.tsx`](../../../remotion-app/src/compositions/intro/index.tsx) | `rendering_engine` | 168 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/landing-code-showcase/index.tsx`](../../../remotion-app/src/compositions/landing-code-showcase/index.tsx) | `rendering_engine` | 32 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/live-code-split/index.tsx`](../../../remotion-app/src/compositions/live-code-split/index.tsx) | `rendering_engine` | 365 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/podcast-clip/index.tsx`](../../../remotion-app/src/compositions/podcast-clip/index.tsx) | `rendering_engine` | 299 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/pricing-focus/index.tsx`](../../../remotion-app/src/compositions/pricing-focus/index.tsx) | `rendering_engine` | 284 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/showcase/index.tsx`](../../../remotion-app/src/compositions/showcase/index.tsx) | `rendering_engine` | 106 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/social-clip/index.tsx`](../../../remotion-app/src/compositions/social-clip/index.tsx) | `rendering_engine` | 101 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/tool-menu-slide/index.tsx`](../../../remotion-app/src/compositions/tool-menu-slide/index.tsx) | `rendering_engine` | 331 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/compositions/tutorial-clip/index.tsx`](../../../remotion-app/src/compositions/tutorial-clip/index.tsx) | `rendering_engine` | 150 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/audio/AudioManager.tsx`](../../../remotion-app/src/engine/audio/AudioManager.tsx) | `rendering_engine` | 63 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/audio/index.ts`](../../../remotion-app/src/engine/audio/index.ts) | `rendering_engine` | 8 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/audio/resolveCues.ts`](../../../remotion-app/src/engine/audio/resolveCues.ts) | `rendering_engine` | 65 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/audio/types.ts`](../../../remotion-app/src/engine/audio/types.ts) | `rendering_engine` | 27 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/camera/AutoZoom.tsx`](../../../remotion-app/src/engine/camera/AutoZoom.tsx) | `rendering_engine` | 85 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/camera/CameraRig.tsx`](../../../remotion-app/src/engine/camera/CameraRig.tsx) | `rendering_engine` | 43 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/camera/index.ts`](../../../remotion-app/src/engine/camera/index.ts) | `rendering_engine` | 11 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/camera/interpolate.ts`](../../../remotion-app/src/engine/camera/interpolate.ts) | `rendering_engine` | 48 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/camera/resolveTimeline.ts`](../../../remotion-app/src/engine/camera/resolveTimeline.ts) | `rendering_engine` | 38 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/camera/types.ts`](../../../remotion-app/src/engine/camera/types.ts) | `rendering_engine` | 26 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/choreography/filterCursorPath.ts`](../../../remotion-app/src/engine/choreography/filterCursorPath.ts) | `rendering_engine` | 18 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/choreography/index.ts`](../../../remotion-app/src/engine/choreography/index.ts) | `rendering_engine` | 4 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/choreography/mapCursorPath.ts`](../../../remotion-app/src/engine/choreography/mapCursorPath.ts) | `rendering_engine` | 93 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/choreography/resolveWindowPose.ts`](../../../remotion-app/src/engine/choreography/resolveWindowPose.ts) | `rendering_engine` | 94 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/cursor/Cursor.tsx`](../../../remotion-app/src/engine/cursor/Cursor.tsx) | `rendering_engine` | 313 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/cursor/CursorSprite.tsx`](../../../remotion-app/src/engine/cursor/CursorSprite.tsx) | `rendering_engine` | 111 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/cursor/arc.ts`](../../../remotion-app/src/engine/cursor/arc.ts) | `rendering_engine` | 124 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/cursor/index.ts`](../../../remotion-app/src/engine/cursor/index.ts) | `rendering_engine` | 17 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/cursor/resolveAnchor.ts`](../../../remotion-app/src/engine/cursor/resolveAnchor.ts) | `rendering_engine` | 52 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/cursor/types.ts`](../../../remotion-app/src/engine/cursor/types.ts) | `rendering_engine` | 67 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/fonts.ts`](../../../remotion-app/src/engine/fonts.ts) | `rendering_engine` | 9 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/index.ts`](../../../remotion-app/src/engine/index.ts) | `rendering_engine` | 96 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/layout/LayoutContext.tsx`](../../../remotion-app/src/engine/layout/LayoutContext.tsx) | `rendering_engine` | 45 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/layout/LayoutWindow.tsx`](../../../remotion-app/src/engine/layout/LayoutWindow.tsx) | `rendering_engine` | 76 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/layout/index.ts`](../../../remotion-app/src/engine/layout/index.ts) | `rendering_engine` | 13 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/layout/types.ts`](../../../remotion-app/src/engine/layout/types.ts) | `rendering_engine` | 46 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/layout/useWindowRect.ts`](../../../remotion-app/src/engine/layout/useWindowRect.ts) | `rendering_engine` | 7 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/layout/zones.ts`](../../../remotion-app/src/engine/layout/zones.ts) | `rendering_engine` | 142 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/CountUp.tsx`](../../../remotion-app/src/engine/primitives/CountUp.tsx) | `rendering_engine` | 88 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/EndCard.tsx`](../../../remotion-app/src/engine/primitives/EndCard.tsx) | `rendering_engine` | 113 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/Enter.tsx`](../../../remotion-app/src/engine/primitives/Enter.tsx) | `rendering_engine` | 69 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/Exit.tsx`](../../../remotion-app/src/engine/primitives/Exit.tsx) | `rendering_engine` | 69 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/Headline.tsx`](../../../remotion-app/src/engine/primitives/Headline.tsx) | `rendering_engine` | 277 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/Highlight.tsx`](../../../remotion-app/src/engine/primitives/Highlight.tsx) | `rendering_engine` | 102 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/Pulse.tsx`](../../../remotion-app/src/engine/primitives/Pulse.tsx) | `rendering_engine` | 66 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/ScenePush.tsx`](../../../remotion-app/src/engine/primitives/ScenePush.tsx) | `rendering_engine` | 75 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/Stagger.tsx`](../../../remotion-app/src/engine/primitives/Stagger.tsx) | `rendering_engine` | 78 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/TrafficLights.tsx`](../../../remotion-app/src/engine/primitives/TrafficLights.tsx) | `rendering_engine` | 29 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/TypeWriter.tsx`](../../../remotion-app/src/engine/primitives/TypeWriter.tsx) | `rendering_engine` | 72 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/Wallpaper.tsx`](../../../remotion-app/src/engine/primitives/Wallpaper.tsx) | `rendering_engine` | 38 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/Window.tsx`](../../../remotion-app/src/engine/primitives/Window.tsx) | `rendering_engine` | 114 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/AppFromDescriptor.tsx`](../../../remotion-app/src/engine/primitives/app-ui/AppFromDescriptor.tsx) | `rendering_engine` | 180 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/AppShell.tsx`](../../../remotion-app/src/engine/primitives/app-ui/AppShell.tsx) | `rendering_engine` | 71 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/Avatar.tsx`](../../../remotion-app/src/engine/primitives/app-ui/Avatar.tsx) | `rendering_engine` | 41 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/Badge.tsx`](../../../remotion-app/src/engine/primitives/app-ui/Badge.tsx) | `rendering_engine` | 35 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/Button.tsx`](../../../remotion-app/src/engine/primitives/app-ui/Button.tsx) | `rendering_engine` | 85 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/DataTable.tsx`](../../../remotion-app/src/engine/primitives/app-ui/DataTable.tsx) | `rendering_engine` | 111 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/ListItems.tsx`](../../../remotion-app/src/engine/primitives/app-ui/ListItems.tsx) | `rendering_engine` | 59 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/MessageList.tsx`](../../../remotion-app/src/engine/primitives/app-ui/MessageList.tsx) | `rendering_engine` | 109 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/NotificationToast.tsx`](../../../remotion-app/src/engine/primitives/app-ui/NotificationToast.tsx) | `rendering_engine` | 74 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/Panel.tsx`](../../../remotion-app/src/engine/primitives/app-ui/Panel.tsx) | `rendering_engine` | 75 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/PanelGrid.tsx`](../../../remotion-app/src/engine/primitives/app-ui/PanelGrid.tsx) | `rendering_engine` | 33 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/Placeholder.tsx`](../../../remotion-app/src/engine/primitives/app-ui/Placeholder.tsx) | `rendering_engine` | 40 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/SearchBar.tsx`](../../../remotion-app/src/engine/primitives/app-ui/SearchBar.tsx) | `rendering_engine` | 51 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/SidebarNav.tsx`](../../../remotion-app/src/engine/primitives/app-ui/SidebarNav.tsx) | `rendering_engine` | 120 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/StatCard.tsx`](../../../remotion-app/src/engine/primitives/app-ui/StatCard.tsx) | `rendering_engine` | 50 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/TabBar.tsx`](../../../remotion-app/src/engine/primitives/app-ui/TabBar.tsx) | `rendering_engine` | 82 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/TopNav.tsx`](../../../remotion-app/src/engine/primitives/app-ui/TopNav.tsx) | `rendering_engine` | 33 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/app-ui/index.ts`](../../../remotion-app/src/engine/primitives/app-ui/index.ts) | `rendering_engine` | 47 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/primitives/index.ts`](../../../remotion-app/src/engine/primitives/index.ts) | `rendering_engine` | 24 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/scenes/ChaosDesktop.tsx`](../../../remotion-app/src/engine/scenes/ChaosDesktop.tsx) | `rendering_engine` | 249 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/scenes/Closer.tsx`](../../../remotion-app/src/engine/scenes/Closer.tsx) | `rendering_engine` | 66 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/scenes/DynamicWindows.tsx`](../../../remotion-app/src/engine/scenes/DynamicWindows.tsx) | `rendering_engine` | 66 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/scenes/FeatureShowcase.tsx`](../../../remotion-app/src/engine/scenes/FeatureShowcase.tsx) | `rendering_engine` | 130 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/scenes/HeadlineResolution.tsx`](../../../remotion-app/src/engine/scenes/HeadlineResolution.tsx) | `rendering_engine` | 25 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/scenes/ProductReveal.tsx`](../../../remotion-app/src/engine/scenes/ProductReveal.tsx) | `rendering_engine` | 179 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/scenes/index.ts`](../../../remotion-app/src/engine/scenes/index.ts) | `rendering_engine` | 5 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/schema.ts`](../../../remotion-app/src/engine/schema.ts) | `rendering_engine` | 484 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/tokens.ts`](../../../remotion-app/src/engine/tokens.ts) | `rendering_engine` | 56 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/types.ts`](../../../remotion-app/src/engine/types.ts) | `rendering_engine` | 68 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/ui-state/UIStateProvider.tsx`](../../../remotion-app/src/engine/ui-state/UIStateProvider.tsx) | `rendering_engine` | 24 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/ui-state/generatePressKeyframes.ts`](../../../remotion-app/src/engine/ui-state/generatePressKeyframes.ts) | `rendering_engine` | 25 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/ui-state/index.ts`](../../../remotion-app/src/engine/ui-state/index.ts) | `rendering_engine` | 4 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/engine/ui-state/types.ts`](../../../remotion-app/src/engine/ui-state/types.ts) | `rendering_engine` | 39 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/fonts.ts`](../../../remotion-app/src/fonts.ts) | `rendering_engine` | 43 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/index.ts`](../../../remotion-app/src/index.ts) | `rendering_engine` | 5 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/canvas-schemas.ts`](../../../remotion-app/src/lib/onda/canvas-schemas.ts) | `rendering_engine` | 83 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/canvas.tsx`](../../../remotion-app/src/lib/onda/canvas.tsx) | `rendering_engine` | 129 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/choreography.ts`](../../../remotion-app/src/lib/onda/choreography.ts) | `rendering_engine` | 416 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/easing.ts`](../../../remotion-app/src/lib/onda/easing.ts) | `rendering_engine` | 27 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/elevation.ts`](../../../remotion-app/src/lib/onda/elevation.ts) | `rendering_engine` | 58 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/hooks.ts`](../../../remotion-app/src/lib/onda/hooks.ts) | `rendering_engine` | 242 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/motion.ts`](../../../remotion-app/src/lib/onda/motion.ts) | `rendering_engine` | 114 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/primitives/Camera.tsx`](../../../remotion-app/src/lib/onda/primitives/Camera.tsx) | `rendering_engine` | 74 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/primitives/Glow.tsx`](../../../remotion-app/src/lib/onda/primitives/Glow.tsx) | `rendering_engine` | 44 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/primitives/GridField.tsx`](../../../remotion-app/src/lib/onda/primitives/GridField.tsx) | `rendering_engine` | 46 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/primitives/Surface.tsx`](../../../remotion-app/src/lib/onda/primitives/Surface.tsx) | `rendering_engine` | 81 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/primitives/index.ts`](../../../remotion-app/src/lib/onda/primitives/index.ts) | `rendering_engine` | 10 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/random.ts`](../../../remotion-app/src/lib/onda/random.ts) | `rendering_engine` | 26 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/timing.ts`](../../../remotion-app/src/lib/onda/timing.ts) | `rendering_engine` | 103 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/onda/tokens.ts`](../../../remotion-app/src/lib/onda/tokens.ts) | `rendering_engine` | 110 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/remocn-ui/color.ts`](../../../remotion-app/src/lib/remocn-ui/color.ts) | `rendering_engine` | 87 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/remocn-ui/index.ts`](../../../remotion-app/src/lib/remocn-ui/index.ts) | `rendering_engine` | 27 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/remocn-ui/motion.ts`](../../../remotion-app/src/lib/remocn-ui/motion.ts) | `rendering_engine` | 17 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/remocn-ui/theme.ts`](../../../remotion-app/src/lib/remocn-ui/theme.ts) | `rendering_engine` | 108 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/remocn-ui/timeline.ts`](../../../remotion-app/src/lib/remocn-ui/timeline.ts) | `rendering_engine` | 96 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/remocn-ui/types.ts`](../../../remotion-app/src/lib/remocn-ui/types.ts) | `rendering_engine` | 5 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/snap-cn-ui/color.ts`](../../../remotion-app/src/lib/snap-cn-ui/color.ts) | `rendering_engine` | 101 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/snap-cn-ui/fonts.ts`](../../../remotion-app/src/lib/snap-cn-ui/fonts.ts) | `rendering_engine` | 79 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/snap-cn-ui/index.ts`](../../../remotion-app/src/lib/snap-cn-ui/index.ts) | `rendering_engine` | 29 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/snap-cn-ui/motion.ts`](../../../remotion-app/src/lib/snap-cn-ui/motion.ts) | `rendering_engine` | 17 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/snap-cn-ui/theme.ts`](../../../remotion-app/src/lib/snap-cn-ui/theme.ts) | `rendering_engine` | 151 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/snap-cn-ui/timeline.ts`](../../../remotion-app/src/lib/snap-cn-ui/timeline.ts) | `rendering_engine` | 101 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/lib/snap-cn-ui/types.ts`](../../../remotion-app/src/lib/snap-cn-ui/types.ts) | `rendering_engine` | 5 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/loadProjectData.ts`](../../../remotion-app/src/loadProjectData.ts) | `rendering_engine` | 63 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/merge.ts`](../../../remotion-app/src/merge.ts) | `rendering_engine` | 66 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/hooks/use-stagger.ts`](../../../remotion-app/src/remotion/hooks/use-stagger.ts) | `rendering_engine` | 15 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/ai-composer-utils.tsx`](../../../remotion-app/src/remotion/lib/ai-composer-utils.tsx) | `rendering_engine` | 252 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/audio-viz-utils.ts`](../../../remotion-app/src/remotion/lib/audio-viz-utils.ts) | `rendering_engine` | 528 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/caption-utils.ts`](../../../remotion-app/src/remotion/lib/caption-utils.ts) | `rendering_engine` | 279 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/chart-utils.ts`](../../../remotion-app/src/remotion/lib/chart-utils.ts) | `rendering_engine` | 265 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/code-syntax.tsx`](../../../remotion-app/src/remotion/lib/code-syntax.tsx) | `rendering_engine` | 313 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/displacement-presentation.tsx`](../../../remotion-app/src/remotion/lib/displacement-presentation.tsx) | `rendering_engine` | 213 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/displacement-transition.ts`](../../../remotion-app/src/remotion/lib/displacement-transition.ts) | `rendering_engine` | 267 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/gpu.ts`](../../../remotion-app/src/remotion/lib/gpu.ts) | `rendering_engine` | 230 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/layout.ts`](../../../remotion-app/src/remotion/lib/layout.ts) | `rendering_engine` | 95 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/map-utils.ts`](../../../remotion-app/src/remotion/lib/map-utils.ts) | `rendering_engine` | 187 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/media-utils.ts`](../../../remotion-app/src/remotion/lib/media-utils.ts) | `rendering_engine` | 63 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/motion-primitive.ts`](../../../remotion-app/src/remotion/lib/motion-primitive.ts) | `rendering_engine` | 245 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/motion-tokens.ts`](../../../remotion-app/src/remotion/lib/motion-tokens.ts) | `rendering_engine` | 51 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/motion-wrapper.tsx`](../../../remotion-app/src/remotion/lib/motion-wrapper.tsx) | `rendering_engine` | 37 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/path-morph.ts`](../../../remotion-app/src/remotion/lib/path-morph.ts) | `rendering_engine` | 261 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/path-utils.ts`](../../../remotion-app/src/remotion/lib/path-utils.ts) | `rendering_engine` | 184 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/sample-media.ts`](../../../remotion-app/src/remotion/lib/sample-media.ts) | `rendering_engine` | 77 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/springs.ts`](../../../remotion-app/src/remotion/lib/springs.ts) | `rendering_engine` | 22 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/text-emphasis.ts`](../../../remotion-app/src/remotion/lib/text-emphasis.ts) | `rendering_engine` | 74 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/text-fit-utils.ts`](../../../remotion-app/src/remotion/lib/text-fit-utils.ts) | `rendering_engine` | 24 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/text-split.ts`](../../../remotion-app/src/remotion/lib/text-split.ts) | `rendering_engine` | 455 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/timing.ts`](../../../remotion-app/src/remotion/lib/timing.ts) | `rendering_engine` | 63 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/lib/transition-timing.ts`](../../../remotion-app/src/remotion/lib/transition-timing.ts) | `rendering_engine` | 142 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/audio-pulse.tsx`](../../../remotion-app/src/remotion/primitives/audio-pulse.tsx) | `rendering_engine` | 118 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/audiogram-bars.tsx`](../../../remotion-app/src/remotion/primitives/audiogram-bars.tsx) | `rendering_engine` | 203 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/caption-highlight.tsx`](../../../remotion-app/src/remotion/primitives/caption-highlight.tsx) | `rendering_engine` | 124 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/counter.tsx`](../../../remotion-app/src/remotion/primitives/counter.tsx) | `rendering_engine` | 404 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/directional-wipe.tsx`](../../../remotion-app/src/remotion/primitives/directional-wipe.tsx) | `rendering_engine` | 135 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/fade-in.tsx`](../../../remotion-app/src/remotion/primitives/fade-in.tsx) | `rendering_engine` | 42 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/fade-out.tsx`](../../../remotion-app/src/remotion/primitives/fade-out.tsx) | `rendering_engine` | 58 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/karaoke-captions.tsx`](../../../remotion-app/src/remotion/primitives/karaoke-captions.tsx) | `rendering_engine` | 167 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/line-chart-draw.tsx`](../../../remotion-app/src/remotion/primitives/line-chart-draw.tsx) | `rendering_engine` | 311 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/map-markers.tsx`](../../../remotion-app/src/remotion/primitives/map-markers.tsx) | `rendering_engine` | 195 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/map-route.tsx`](../../../remotion-app/src/remotion/primitives/map-route.tsx) | `rendering_engine` | 229 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/multi-device-lineup.tsx`](../../../remotion-app/src/remotion/primitives/multi-device-lineup.tsx) | `rendering_engine` | 274 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/path-draw.tsx`](../../../remotion-app/src/remotion/primitives/path-draw.tsx) | `rendering_engine` | 146 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/slide-up.tsx`](../../../remotion-app/src/remotion/primitives/slide-up.tsx) | `rendering_engine` | 82 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/spring-in.tsx`](../../../remotion-app/src/remotion/primitives/spring-in.tsx) | `rendering_engine` | 66 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/stagger-children.tsx`](../../../remotion-app/src/remotion/primitives/stagger-children.tsx) | `rendering_engine` | 126 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/transition-fade.tsx`](../../../remotion-app/src/remotion/primitives/transition-fade.tsx) | `rendering_engine` | 89 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/transition-slide.tsx`](../../../remotion-app/src/remotion/primitives/transition-slide.tsx) | `rendering_engine` | 37 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/transition-wipe.tsx`](../../../remotion-app/src/remotion/primitives/transition-wipe.tsx) | `rendering_engine` | 36 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/typewriter.tsx`](../../../remotion-app/src/remotion/primitives/typewriter.tsx) | `rendering_engine` | 399 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/primitives/waveform-line.tsx`](../../../remotion-app/src/remotion/primitives/waveform-line.tsx) | `rendering_engine` | 297 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/animated-bar-chart/index.tsx`](../../../remotion-app/src/remotion/scenes/animated-bar-chart/index.tsx) | `rendering_engine` | 413 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/audiogram-scene/index.tsx`](../../../remotion-app/src/remotion/scenes/audiogram-scene/index.tsx) | `rendering_engine` | 134 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/auto-fit-title/index.tsx`](../../../remotion-app/src/remotion/scenes/auto-fit-title/index.tsx) | `rendering_engine` | 213 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/b-roll-stack/index.tsx`](../../../remotion-app/src/remotion/scenes/b-roll-stack/index.tsx) | `rendering_engine` | 360 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/calendar-month-fill/index.tsx`](../../../remotion-app/src/remotion/scenes/calendar-month-fill/index.tsx) | `rendering_engine` | 339 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/callout-spotlight/index.tsx`](../../../remotion-app/src/remotion/scenes/callout-spotlight/index.tsx) | `rendering_engine` | 322 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/caption-bumper/index.tsx`](../../../remotion-app/src/remotion/scenes/caption-bumper/index.tsx) | `rendering_engine` | 227 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/caption-scene/index.tsx`](../../../remotion-app/src/remotion/scenes/caption-scene/index.tsx) | `rendering_engine` | 373 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/changelog-entry/index.tsx`](../../../remotion-app/src/remotion/scenes/changelog-entry/index.tsx) | `rendering_engine` | 291 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/chat-gpt/index.tsx`](../../../remotion-app/src/remotion/scenes/chat-gpt/index.tsx) | `rendering_engine` | 556 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/chat-to-preview/index.tsx`](../../../remotion-app/src/remotion/scenes/chat-to-preview/index.tsx) | `rendering_engine` | 809 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/claude-chat/index.tsx`](../../../remotion-app/src/remotion/scenes/claude-chat/index.tsx) | `rendering_engine` | 437 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/claude-code/index.tsx`](../../../remotion-app/src/remotion/scenes/claude-code/index.tsx) | `rendering_engine` | 344 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/code-accordion/index.tsx`](../../../remotion-app/src/remotion/scenes/code-accordion/index.tsx) | `rendering_engine` | 457 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/code-diff-wipe/index.tsx`](../../../remotion-app/src/remotion/scenes/code-diff-wipe/index.tsx) | `rendering_engine` | 475 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/code-reveal/index.tsx`](../../../remotion-app/src/remotion/scenes/code-reveal/index.tsx) | `rendering_engine` | 494 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/comment-callout/index.tsx`](../../../remotion-app/src/remotion/scenes/comment-callout/index.tsx) | `rendering_engine` | 517 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/commit-graph/index.tsx`](../../../remotion-app/src/remotion/scenes/commit-graph/index.tsx) | `rendering_engine` | 372 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/comparison-table/index.tsx`](../../../remotion-app/src/remotion/scenes/comparison-table/index.tsx) | `rendering_engine` | 358 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/countdown-timer/index.tsx`](../../../remotion-app/src/remotion/scenes/countdown-timer/index.tsx) | `rendering_engine` | 223 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/data-flow-pipes/index.tsx`](../../../remotion-app/src/remotion/scenes/data-flow-pipes/index.tsx) | `rendering_engine` | 458 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/device-mockup-zoom/index.tsx`](../../../remotion-app/src/remotion/scenes/device-mockup-zoom/index.tsx) | `rendering_engine` | 950 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/drag-drop-flow/index.tsx`](../../../remotion-app/src/remotion/scenes/drag-drop-flow/index.tsx) | `rendering_engine` | 665 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/end-card/index.tsx`](../../../remotion-app/src/remotion/scenes/end-card/index.tsx) | `rendering_engine` | 364 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/faq-accordion/index.tsx`](../../../remotion-app/src/remotion/scenes/faq-accordion/index.tsx) | `rendering_engine` | 307 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/feature-list/index.tsx`](../../../remotion-app/src/remotion/scenes/feature-list/index.tsx) | `rendering_engine` | 290 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/file-tree-reveal/index.tsx`](../../../remotion-app/src/remotion/scenes/file-tree-reveal/index.tsx) | `rendering_engine` | 402 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/form-fill-sequence/index.tsx`](../../../remotion-app/src/remotion/scenes/form-fill-sequence/index.tsx) | `rendering_engine` | 388 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/hook-card/index.tsx`](../../../remotion-app/src/remotion/scenes/hook-card/index.tsx) | `rendering_engine` | 385 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/kanban-move/index.tsx`](../../../remotion-app/src/remotion/scenes/kanban-move/index.tsx) | `rendering_engine` | 418 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/logo-reveal/index.tsx`](../../../remotion-app/src/remotion/scenes/logo-reveal/index.tsx) | `rendering_engine` | 221 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/logo-wall/index.tsx`](../../../remotion-app/src/remotion/scenes/logo-wall/index.tsx) | `rendering_engine` | 265 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/lower-third/index.tsx`](../../../remotion-app/src/remotion/scenes/lower-third/index.tsx) | `rendering_engine` | 215 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/map-flight/index.tsx`](../../../remotion-app/src/remotion/scenes/map-flight/index.tsx) | `rendering_engine` | 243 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/media-frame/index.tsx`](../../../remotion-app/src/remotion/scenes/media-frame/index.tsx) | `rendering_engine` | 282 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/media-sequence/index.tsx`](../../../remotion-app/src/remotion/scenes/media-sequence/index.tsx) | `rendering_engine` | 169 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/metric-ticker/index.tsx`](../../../remotion-app/src/remotion/scenes/metric-ticker/index.tsx) | `rendering_engine` | 307 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/news-ticker-bar/index.tsx`](../../../remotion-app/src/remotion/scenes/news-ticker-bar/index.tsx) | `rendering_engine` | 256 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/notification-stack/index.tsx`](../../../remotion-app/src/remotion/scenes/notification-stack/index.tsx) | `rendering_engine` | 362 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/opencode/index.tsx`](../../../remotion-app/src/remotion/scenes/opencode/index.tsx) | `rendering_engine` | 232 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/org-chart-build/index.tsx`](../../../remotion-app/src/remotion/scenes/org-chart-build/index.tsx) | `rendering_engine` | 387 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/poll-overlay/index.tsx`](../../../remotion-app/src/remotion/scenes/poll-overlay/index.tsx) | `rendering_engine` | 320 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/pricing-card/index.tsx`](../../../remotion-app/src/remotion/scenes/pricing-card/index.tsx) | `rendering_engine` | 394 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/quiz-question/index.tsx`](../../../remotion-app/src/remotion/scenes/quiz-question/index.tsx) | `rendering_engine` | 302 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/quote-card/index.tsx`](../../../remotion-app/src/remotion/scenes/quote-card/index.tsx) | `rendering_engine` | 373 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/reaction-burst/index.tsx`](../../../remotion-app/src/remotion/scenes/reaction-burst/index.tsx) | `rendering_engine` | 185 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/roadmap-lanes/index.tsx`](../../../remotion-app/src/remotion/scenes/roadmap-lanes/index.tsx) | `rendering_engine` | 355 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/search-results-populate/index.tsx`](../../../remotion-app/src/remotion/scenes/search-results-populate/index.tsx) | `rendering_engine` | 417 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/split-screen/index.tsx`](../../../remotion-app/src/remotion/scenes/split-screen/index.tsx) | `rendering_engine` | 314 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/sports-scorebug/index.tsx`](../../../remotion-app/src/remotion/scenes/sports-scorebug/index.tsx) | `rendering_engine` | 320 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/stat-card/index.tsx`](../../../remotion-app/src/remotion/scenes/stat-card/index.tsx) | `rendering_engine` | 309 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/tab-switch-panel/index.tsx`](../../../remotion-app/src/remotion/scenes/tab-switch-panel/index.tsx) | `rendering_engine` | 431 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/talking-head-layout/index.tsx`](../../../remotion-app/src/remotion/scenes/talking-head-layout/index.tsx) | `rendering_engine` | 505 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/team-grid/index.tsx`](../../../remotion-app/src/remotion/scenes/team-grid/index.tsx) | `rendering_engine` | 287 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/terminal-simulator/index.tsx`](../../../remotion-app/src/remotion/scenes/terminal-simulator/index.tsx) | `rendering_engine` | 720 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/timeline-steps/index.tsx`](../../../remotion-app/src/remotion/scenes/timeline-steps/index.tsx) | `rendering_engine` | 430 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/title-card/index.tsx`](../../../remotion-app/src/remotion/scenes/title-card/index.tsx) | `rendering_engine` | 316 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/v0/index.tsx`](../../../remotion-app/src/remotion/scenes/v0/index.tsx) | `rendering_engine` | 434 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/weather-card/index.tsx`](../../../remotion-app/src/remotion/scenes/weather-card/index.tsx) | `rendering_engine` | 453 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/remotion/scenes/zoom-pan-frame/index.tsx`](../../../remotion-app/src/remotion/scenes/zoom-pan-frame/index.tsx) | `rendering_engine` | 190 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/brand-resolver.ts`](../../../remotion-app/src/templates/brand-resolver.ts) | `rendering_engine` | 32 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/custom/LevelOneScene.tsx`](../../../remotion-app/src/templates/custom/LevelOneScene.tsx) | `rendering_engine` | 38 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/custom/LevelZeroBox.tsx`](../../../remotion-app/src/templates/custom/LevelZeroBox.tsx) | `rendering_engine` | 33 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/BookFlipTransition.tsx`](../../../remotion-app/src/templates/effects/BookFlipTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/ClockWipeTransition.tsx`](../../../remotion-app/src/templates/effects/ClockWipeTransition.tsx) | `rendering_engine` | 23 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/CrossZoomTransition.tsx`](../../../remotion-app/src/templates/effects/CrossZoomTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/CrosswarpTransition.tsx`](../../../remotion-app/src/templates/effects/CrosswarpTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/DissolveTransition.tsx`](../../../remotion-app/src/templates/effects/DissolveTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/DreamyZoomTransition.tsx`](../../../remotion-app/src/templates/effects/DreamyZoomTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/FadeTransition.tsx`](../../../remotion-app/src/templates/effects/FadeTransition.tsx) | `rendering_engine` | 21 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/FilmBurnTransition.tsx`](../../../remotion-app/src/templates/effects/FilmBurnTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/FlipTransition.tsx`](../../../remotion-app/src/templates/effects/FlipTransition.tsx) | `rendering_engine` | 22 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/IrisTransition.tsx`](../../../remotion-app/src/templates/effects/IrisTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/LinearBlurTransition.tsx`](../../../remotion-app/src/templates/effects/LinearBlurTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/PushCutTransition.tsx`](../../../remotion-app/src/templates/effects/PushCutTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/RippleTransition.tsx`](../../../remotion-app/src/templates/effects/RippleTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/SlideTransition.tsx`](../../../remotion-app/src/templates/effects/SlideTransition.tsx) | `rendering_engine` | 21 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/SwapTransition.tsx`](../../../remotion-app/src/templates/effects/SwapTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/WipeTransition.tsx`](../../../remotion-app/src/templates/effects/WipeTransition.tsx) | `rendering_engine` | 21 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/ZoomBlurTransition.tsx`](../../../remotion-app/src/templates/effects/ZoomBlurTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/ZoomInOutTransition.tsx`](../../../remotion-app/src/templates/effects/ZoomInOutTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/effects/engine-bridge.tsx`](../../../remotion-app/src/templates/effects/engine-bridge.tsx) | `rendering_engine` | 31 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/AnimatedBarChartWrapper.tsx`](../../../remotion-app/src/templates/elements/AnimatedBarChartWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/AnimatedCounterWrapper.tsx`](../../../remotion-app/src/templates/elements/AnimatedCounterWrapper.tsx) | `rendering_engine` | 33 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/AnimatedTextWrapper.tsx`](../../../remotion-app/src/templates/elements/AnimatedTextWrapper.tsx) | `rendering_engine` | 30 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/AutoFitTitleWrapper.tsx`](../../../remotion-app/src/templates/elements/AutoFitTitleWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/BRollStackWrapper.tsx`](../../../remotion-app/src/templates/elements/BRollStackWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/BentoPanWrapper.tsx`](../../../remotion-app/src/templates/elements/BentoPanWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CalendarMonthFillWrapper.tsx`](../../../remotion-app/src/templates/elements/CalendarMonthFillWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CalloutSpotlightWrapper.tsx`](../../../remotion-app/src/templates/elements/CalloutSpotlightWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CaptionBumperWrapper.tsx`](../../../remotion-app/src/templates/elements/CaptionBumperWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/ChangelogEntryWrapper.tsx`](../../../remotion-app/src/templates/elements/ChangelogEntryWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/ChatToPreviewWrapper.tsx`](../../../remotion-app/src/templates/elements/ChatToPreviewWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CodeAccordionWrapper.tsx`](../../../remotion-app/src/templates/elements/CodeAccordionWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CodeBlockWrapper.tsx`](../../../remotion-app/src/templates/elements/CodeBlockWrapper.tsx) | `rendering_engine` | 25 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CodeDiffWipeWrapper.tsx`](../../../remotion-app/src/templates/elements/CodeDiffWipeWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CodeRevealWrapper.tsx`](../../../remotion-app/src/templates/elements/CodeRevealWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CommentCalloutWrapper.tsx`](../../../remotion-app/src/templates/elements/CommentCalloutWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CommitGraphWrapper.tsx`](../../../remotion-app/src/templates/elements/CommitGraphWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/ComparisonTableWrapper.tsx`](../../../remotion-app/src/templates/elements/ComparisonTableWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/CountdownTimerWrapper.tsx`](../../../remotion-app/src/templates/elements/CountdownTimerWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/DashboardPopulateWrapper.tsx`](../../../remotion-app/src/templates/elements/DashboardPopulateWrapper.tsx) | `rendering_engine` | 32 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/DeployRevealWrapper.tsx`](../../../remotion-app/src/templates/elements/DeployRevealWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/DeviceMockupZoomWrapper.tsx`](../../../remotion-app/src/templates/elements/DeviceMockupZoomWrapper.tsx) | `rendering_engine` | 32 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/EndCardWrapper.tsx`](../../../remotion-app/src/templates/elements/EndCardWrapper.tsx) | `rendering_engine` | 16 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/FaqAccordionWrapper.tsx`](../../../remotion-app/src/templates/elements/FaqAccordionWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/FeatureListWrapper.tsx`](../../../remotion-app/src/templates/elements/FeatureListWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/FileTreeRevealWrapper.tsx`](../../../remotion-app/src/templates/elements/FileTreeRevealWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/GradientWrapper.tsx`](../../../remotion-app/src/templates/elements/GradientWrapper.tsx) | `rendering_engine` | 18 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/HookCardWrapper.tsx`](../../../remotion-app/src/templates/elements/HookCardWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/ImageExpandWrapper.tsx`](../../../remotion-app/src/templates/elements/ImageExpandWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/KanbanMoveWrapper.tsx`](../../../remotion-app/src/templates/elements/KanbanMoveWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/LogoRevealWrapper.tsx`](../../../remotion-app/src/templates/elements/LogoRevealWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/LogoWallWrapper.tsx`](../../../remotion-app/src/templates/elements/LogoWallWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/LowerThirdWrapper.tsx`](../../../remotion-app/src/templates/elements/LowerThirdWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/MapFlightWrapper.tsx`](../../../remotion-app/src/templates/elements/MapFlightWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/MatrixRainWrapper.tsx`](../../../remotion-app/src/templates/elements/MatrixRainWrapper.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/MediaFrameWrapper.tsx`](../../../remotion-app/src/templates/elements/MediaFrameWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/MetricTickerWrapper.tsx`](../../../remotion-app/src/templates/elements/MetricTickerWrapper.tsx) | `rendering_engine` | 19 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/NewsTickerBarWrapper.tsx`](../../../remotion-app/src/templates/elements/NewsTickerBarWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/NotificationStackWrapper.tsx`](../../../remotion-app/src/templates/elements/NotificationStackWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/OrgChartBuildWrapper.tsx`](../../../remotion-app/src/templates/elements/OrgChartBuildWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/ParticleSystemWrapper.tsx`](../../../remotion-app/src/templates/elements/ParticleSystemWrapper.tsx) | `rendering_engine` | 22 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/PodcastClipWrapper.tsx`](../../../remotion-app/src/templates/elements/PodcastClipWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/PollOverlayWrapper.tsx`](../../../remotion-app/src/templates/elements/PollOverlayWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/PricingCardWrapper.tsx`](../../../remotion-app/src/templates/elements/PricingCardWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/PricingFocusWrapper.tsx`](../../../remotion-app/src/templates/elements/PricingFocusWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/QuizQuestionWrapper.tsx`](../../../remotion-app/src/templates/elements/QuizQuestionWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/QuoteCardWrapper.tsx`](../../../remotion-app/src/templates/elements/QuoteCardWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/ReactionBurstWrapper.tsx`](../../../remotion-app/src/templates/elements/ReactionBurstWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/RoadmapLanesWrapper.tsx`](../../../remotion-app/src/templates/elements/RoadmapLanesWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/Scene3DWrapper.tsx`](../../../remotion-app/src/templates/elements/Scene3DWrapper.tsx) | `rendering_engine` | 17 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/ScrollingImagesWrapper.tsx`](../../../remotion-app/src/templates/elements/ScrollingImagesWrapper.tsx) | `rendering_engine` | 29 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/SearchResultsPopulateWrapper.tsx`](../../../remotion-app/src/templates/elements/SearchResultsPopulateWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/SocialClipWrapper.tsx`](../../../remotion-app/src/templates/elements/SocialClipWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/SportsScorebugWrapper.tsx`](../../../remotion-app/src/templates/elements/SportsScorebugWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/StaggeredMotionWrapper.tsx`](../../../remotion-app/src/templates/elements/StaggeredMotionWrapper.tsx) | `rendering_engine` | 33 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/StatCardWrapper.tsx`](../../../remotion-app/src/templates/elements/StatCardWrapper.tsx) | `rendering_engine` | 19 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/THEMESWrapper.tsx`](../../../remotion-app/src/templates/elements/THEMESWrapper.tsx) | `rendering_engine` | 8 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/TabSwitchPanelWrapper.tsx`](../../../remotion-app/src/templates/elements/TabSwitchPanelWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/TerminalSimulatorWrapper.tsx`](../../../remotion-app/src/templates/elements/TerminalSimulatorWrapper.tsx) | `rendering_engine` | 22 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/TimelineStepsWrapper.tsx`](../../../remotion-app/src/templates/elements/TimelineStepsWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/TitleCardWrapper.tsx`](../../../remotion-app/src/templates/elements/TitleCardWrapper.tsx) | `rendering_engine` | 15 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/TutorialClipWrapper.tsx`](../../../remotion-app/src/templates/elements/TutorialClipWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/TypeWriterWrapper.tsx`](../../../remotion-app/src/templates/elements/TypeWriterWrapper.tsx) | `rendering_engine` | 25 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/WeatherCardWrapper.tsx`](../../../remotion-app/src/templates/elements/WeatherCardWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/elements/ZoomPanFrameWrapper.tsx`](../../../remotion-app/src/templates/elements/ZoomPanFrameWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/AiComposerShowcaseWrapper.tsx`](../../../remotion-app/src/templates/scenes/AiComposerShowcaseWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/AiGenerationCanvasWrapper.tsx`](../../../remotion-app/src/templates/scenes/AiGenerationCanvasWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/AudiogramSceneWrapper.tsx`](../../../remotion-app/src/templates/scenes/AudiogramSceneWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/BrowserFlowWrapper.tsx`](../../../remotion-app/src/templates/scenes/BrowserFlowWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/CaptionSceneWrapper.tsx`](../../../remotion-app/src/templates/scenes/CaptionSceneWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/CreatorReelWrapper.tsx`](../../../remotion-app/src/templates/scenes/CreatorReelWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/DataFlowPipesWrapper.tsx`](../../../remotion-app/src/templates/scenes/DataFlowPipesWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/DataStoryWrapper.tsx`](../../../remotion-app/src/templates/scenes/DataStoryWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/DragDropFlowWrapper.tsx`](../../../remotion-app/src/templates/scenes/DragDropFlowWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/EcosystemOrbitWrapper.tsx`](../../../remotion-app/src/templates/scenes/EcosystemOrbitWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/FormFillSequenceWrapper.tsx`](../../../remotion-app/src/templates/scenes/FormFillSequenceWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/HeroDeviceAssembleWrapper.tsx`](../../../remotion-app/src/templates/scenes/HeroDeviceAssembleWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/HeroLoopWrapper.tsx`](../../../remotion-app/src/templates/scenes/HeroLoopWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/IntroWrapper.tsx`](../../../remotion-app/src/templates/scenes/IntroWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/LandingCodeShowcaseWrapper.tsx`](../../../remotion-app/src/templates/scenes/LandingCodeShowcaseWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/LiveCodeSplitWrapper.tsx`](../../../remotion-app/src/templates/scenes/LiveCodeSplitWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/MediaSequenceWrapper.tsx`](../../../remotion-app/src/templates/scenes/MediaSequenceWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/ShowcaseWrapper.tsx`](../../../remotion-app/src/templates/scenes/ShowcaseWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/SplitScreenWrapper.tsx`](../../../remotion-app/src/templates/scenes/SplitScreenWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/TalkingHeadLayoutWrapper.tsx`](../../../remotion-app/src/templates/scenes/TalkingHeadLayoutWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/TeamGridWrapper.tsx`](../../../remotion-app/src/templates/scenes/TeamGridWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/templates/scenes/ToolMenuSlideWrapper.tsx`](../../../remotion-app/src/templates/scenes/ToolMenuSlideWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/types/ai_contracts.ts`](../../../remotion-app/src/types/ai_contracts.ts) | `rendering_engine` | 1,537 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/types/creative_contracts.ts`](../../../remotion-app/src/types/creative_contracts.ts) | `rendering_engine` | 930 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`remotion-app/src/types/state.ts`](../../../remotion-app/src/types/state.ts) | `rendering_engine` | 60 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/__init__.py`](../../../scripts/generators/__init__.py) | `rendering_engine` | 0 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/build_asset_index.py`](../../../scripts/generators/build_asset_index.py) | `rendering_engine` | 91 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/build_catalog.py`](../../../scripts/generators/build_catalog.py) | `rendering_engine` | 57 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/build_ground_truth.py`](../../../scripts/generators/build_ground_truth.py) | `rendering_engine` | 298 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/generate_drift_matrix.py`](../../../scripts/generators/generate_drift_matrix.py) | `rendering_engine` | 103 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/generate_matrix.ts`](../../../scripts/generators/generate_matrix.ts) | `rendering_engine` | 52 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/generate_plan.py`](../../../scripts/generators/generate_plan.py) | `rendering_engine` | 80 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/generate_registry.ts`](../../../scripts/generators/generate_registry.ts) | `rendering_engine` | 456 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/generate_s28_legacy_inventory.py`](../../../scripts/generators/generate_s28_legacy_inventory.py) | `rendering_engine` | 305 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/generate_schema.ts`](../../../scripts/generators/generate_schema.ts) | `rendering_engine` | 32 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/generate_template_aliases.py`](../../../scripts/generators/generate_template_aliases.py) | `rendering_engine` | 50 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/generate_template_contract.py`](../../../scripts/generators/generate_template_contract.py) | `rendering_engine` | 256 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/generators/materialize_project.py`](../../../scripts/generators/materialize_project.py) | `rendering_engine` | 89 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`scripts/render_project.py`](../../../scripts/render_project.py) | `rendering_engine` | 289 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/brand-resolver.ts`](../../../templates/brand-resolver.ts) | `rendering_engine` | 32 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/custom/LevelOneScene.tsx`](../../../templates/custom/LevelOneScene.tsx) | `rendering_engine` | 38 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/custom/LevelZeroBox.tsx`](../../../templates/custom/LevelZeroBox.tsx) | `rendering_engine` | 33 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/BookFlipTransition.tsx`](../../../templates/effects/BookFlipTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/ClockWipeTransition.tsx`](../../../templates/effects/ClockWipeTransition.tsx) | `rendering_engine` | 23 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/CrossZoomTransition.tsx`](../../../templates/effects/CrossZoomTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/CrosswarpTransition.tsx`](../../../templates/effects/CrosswarpTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/DissolveTransition.tsx`](../../../templates/effects/DissolveTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/DreamyZoomTransition.tsx`](../../../templates/effects/DreamyZoomTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/FadeTransition.tsx`](../../../templates/effects/FadeTransition.tsx) | `rendering_engine` | 21 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/FilmBurnTransition.tsx`](../../../templates/effects/FilmBurnTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/FlipTransition.tsx`](../../../templates/effects/FlipTransition.tsx) | `rendering_engine` | 22 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/IrisTransition.tsx`](../../../templates/effects/IrisTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/LinearBlurTransition.tsx`](../../../templates/effects/LinearBlurTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/PushCutTransition.tsx`](../../../templates/effects/PushCutTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/RippleTransition.tsx`](../../../templates/effects/RippleTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/SlideTransition.tsx`](../../../templates/effects/SlideTransition.tsx) | `rendering_engine` | 21 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/SwapTransition.tsx`](../../../templates/effects/SwapTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/WipeTransition.tsx`](../../../templates/effects/WipeTransition.tsx) | `rendering_engine` | 21 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/ZoomBlurTransition.tsx`](../../../templates/effects/ZoomBlurTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/ZoomInOutTransition.tsx`](../../../templates/effects/ZoomInOutTransition.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/effects/engine-bridge.tsx`](../../../templates/effects/engine-bridge.tsx) | `rendering_engine` | 31 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/AnimatedBarChartWrapper.tsx`](../../../templates/elements/AnimatedBarChartWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/AnimatedCounterWrapper.tsx`](../../../templates/elements/AnimatedCounterWrapper.tsx) | `rendering_engine` | 33 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/AnimatedTextWrapper.tsx`](../../../templates/elements/AnimatedTextWrapper.tsx) | `rendering_engine` | 30 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/AutoFitTitleWrapper.tsx`](../../../templates/elements/AutoFitTitleWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/BRollStackWrapper.tsx`](../../../templates/elements/BRollStackWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/BentoPanWrapper.tsx`](../../../templates/elements/BentoPanWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CalendarMonthFillWrapper.tsx`](../../../templates/elements/CalendarMonthFillWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CalloutSpotlightWrapper.tsx`](../../../templates/elements/CalloutSpotlightWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CaptionBumperWrapper.tsx`](../../../templates/elements/CaptionBumperWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/ChangelogEntryWrapper.tsx`](../../../templates/elements/ChangelogEntryWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/ChatToPreviewWrapper.tsx`](../../../templates/elements/ChatToPreviewWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CodeAccordionWrapper.tsx`](../../../templates/elements/CodeAccordionWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CodeBlockWrapper.tsx`](../../../templates/elements/CodeBlockWrapper.tsx) | `rendering_engine` | 25 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CodeDiffWipeWrapper.tsx`](../../../templates/elements/CodeDiffWipeWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CodeRevealWrapper.tsx`](../../../templates/elements/CodeRevealWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CommentCalloutWrapper.tsx`](../../../templates/elements/CommentCalloutWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CommitGraphWrapper.tsx`](../../../templates/elements/CommitGraphWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/ComparisonTableWrapper.tsx`](../../../templates/elements/ComparisonTableWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/CountdownTimerWrapper.tsx`](../../../templates/elements/CountdownTimerWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/DashboardPopulateWrapper.tsx`](../../../templates/elements/DashboardPopulateWrapper.tsx) | `rendering_engine` | 32 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/DeployRevealWrapper.tsx`](../../../templates/elements/DeployRevealWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/DeviceMockupZoomWrapper.tsx`](../../../templates/elements/DeviceMockupZoomWrapper.tsx) | `rendering_engine` | 32 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/EndCardWrapper.tsx`](../../../templates/elements/EndCardWrapper.tsx) | `rendering_engine` | 16 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/FaqAccordionWrapper.tsx`](../../../templates/elements/FaqAccordionWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/FeatureListWrapper.tsx`](../../../templates/elements/FeatureListWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/FileTreeRevealWrapper.tsx`](../../../templates/elements/FileTreeRevealWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/GradientWrapper.tsx`](../../../templates/elements/GradientWrapper.tsx) | `rendering_engine` | 18 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/HookCardWrapper.tsx`](../../../templates/elements/HookCardWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/ImageExpandWrapper.tsx`](../../../templates/elements/ImageExpandWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/KanbanMoveWrapper.tsx`](../../../templates/elements/KanbanMoveWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/LogoRevealWrapper.tsx`](../../../templates/elements/LogoRevealWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/LogoWallWrapper.tsx`](../../../templates/elements/LogoWallWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/LowerThirdWrapper.tsx`](../../../templates/elements/LowerThirdWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/MapFlightWrapper.tsx`](../../../templates/elements/MapFlightWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/MatrixRainWrapper.tsx`](../../../templates/elements/MatrixRainWrapper.tsx) | `rendering_engine` | 20 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/MediaFrameWrapper.tsx`](../../../templates/elements/MediaFrameWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/MetricTickerWrapper.tsx`](../../../templates/elements/MetricTickerWrapper.tsx) | `rendering_engine` | 19 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/NewsTickerBarWrapper.tsx`](../../../templates/elements/NewsTickerBarWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/NotificationStackWrapper.tsx`](../../../templates/elements/NotificationStackWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/OrgChartBuildWrapper.tsx`](../../../templates/elements/OrgChartBuildWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/ParticleSystemWrapper.tsx`](../../../templates/elements/ParticleSystemWrapper.tsx) | `rendering_engine` | 22 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/PodcastClipWrapper.tsx`](../../../templates/elements/PodcastClipWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/PollOverlayWrapper.tsx`](../../../templates/elements/PollOverlayWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/PricingCardWrapper.tsx`](../../../templates/elements/PricingCardWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/PricingFocusWrapper.tsx`](../../../templates/elements/PricingFocusWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/QuizQuestionWrapper.tsx`](../../../templates/elements/QuizQuestionWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/QuoteCardWrapper.tsx`](../../../templates/elements/QuoteCardWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/ReactionBurstWrapper.tsx`](../../../templates/elements/ReactionBurstWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/RoadmapLanesWrapper.tsx`](../../../templates/elements/RoadmapLanesWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/Scene3DWrapper.tsx`](../../../templates/elements/Scene3DWrapper.tsx) | `rendering_engine` | 17 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/ScrollingImagesWrapper.tsx`](../../../templates/elements/ScrollingImagesWrapper.tsx) | `rendering_engine` | 29 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/SearchResultsPopulateWrapper.tsx`](../../../templates/elements/SearchResultsPopulateWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/SocialClipWrapper.tsx`](../../../templates/elements/SocialClipWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/SportsScorebugWrapper.tsx`](../../../templates/elements/SportsScorebugWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/StaggeredMotionWrapper.tsx`](../../../templates/elements/StaggeredMotionWrapper.tsx) | `rendering_engine` | 33 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/StatCardWrapper.tsx`](../../../templates/elements/StatCardWrapper.tsx) | `rendering_engine` | 19 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/THEMESWrapper.tsx`](../../../templates/elements/THEMESWrapper.tsx) | `rendering_engine` | 8 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/TabSwitchPanelWrapper.tsx`](../../../templates/elements/TabSwitchPanelWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/TerminalSimulatorWrapper.tsx`](../../../templates/elements/TerminalSimulatorWrapper.tsx) | `rendering_engine` | 22 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/TimelineStepsWrapper.tsx`](../../../templates/elements/TimelineStepsWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/TitleCardWrapper.tsx`](../../../templates/elements/TitleCardWrapper.tsx) | `rendering_engine` | 15 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/TutorialClipWrapper.tsx`](../../../templates/elements/TutorialClipWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/TypeWriterWrapper.tsx`](../../../templates/elements/TypeWriterWrapper.tsx) | `rendering_engine` | 25 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/WeatherCardWrapper.tsx`](../../../templates/elements/WeatherCardWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/elements/ZoomPanFrameWrapper.tsx`](../../../templates/elements/ZoomPanFrameWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/AiComposerShowcaseWrapper.tsx`](../../../templates/scenes/AiComposerShowcaseWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/AiGenerationCanvasWrapper.tsx`](../../../templates/scenes/AiGenerationCanvasWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/AudiogramSceneWrapper.tsx`](../../../templates/scenes/AudiogramSceneWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/BrowserFlowWrapper.tsx`](../../../templates/scenes/BrowserFlowWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/CaptionSceneWrapper.tsx`](../../../templates/scenes/CaptionSceneWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/CreatorReelWrapper.tsx`](../../../templates/scenes/CreatorReelWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/DataFlowPipesWrapper.tsx`](../../../templates/scenes/DataFlowPipesWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/DataStoryWrapper.tsx`](../../../templates/scenes/DataStoryWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/DragDropFlowWrapper.tsx`](../../../templates/scenes/DragDropFlowWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/EcosystemOrbitWrapper.tsx`](../../../templates/scenes/EcosystemOrbitWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/FormFillSequenceWrapper.tsx`](../../../templates/scenes/FormFillSequenceWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/HeroDeviceAssembleWrapper.tsx`](../../../templates/scenes/HeroDeviceAssembleWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/HeroLoopWrapper.tsx`](../../../templates/scenes/HeroLoopWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/IntroWrapper.tsx`](../../../templates/scenes/IntroWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/LandingCodeShowcaseWrapper.tsx`](../../../templates/scenes/LandingCodeShowcaseWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/LiveCodeSplitWrapper.tsx`](../../../templates/scenes/LiveCodeSplitWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/MediaSequenceWrapper.tsx`](../../../templates/scenes/MediaSequenceWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/ShowcaseWrapper.tsx`](../../../templates/scenes/ShowcaseWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/SplitScreenWrapper.tsx`](../../../templates/scenes/SplitScreenWrapper.tsx) | `rendering_engine` | 19 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/TalkingHeadLayoutWrapper.tsx`](../../../templates/scenes/TalkingHeadLayoutWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/TeamGridWrapper.tsx`](../../../templates/scenes/TeamGridWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`templates/scenes/ToolMenuSlideWrapper.tsx`](../../../templates/scenes/ToolMenuSlideWrapper.tsx) | `rendering_engine` | 12 | `ACTIVE_RUNTIME` | React/Remotion canvas, template engine bridge, and FFmpeg video rendering |
| [`creative_governance/__init__.py`](../../../creative_governance/__init__.py) | `review_governance` | 9 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/__init__.py`](../../../creative_governance/candidates/__init__.py) | `review_governance` | 114 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/errors.py`](../../../creative_governance/candidates/errors.py) | `review_governance` | 98 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/__init__.py`](../../../creative_governance/candidates/gates/__init__.py) | `review_governance` | 37 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/aspect_gate.py`](../../../creative_governance/candidates/gates/aspect_gate.py) | `review_governance` | 169 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/ast_runner.py`](../../../creative_governance/candidates/gates/ast_runner.py) | `review_governance` | 75 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/base.py`](../../../creative_governance/candidates/gates/base.py) | `review_governance` | 70 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/candidate_qc_gate.py`](../../../creative_governance/candidates/gates/candidate_qc_gate.py) | `review_governance` | 190 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/contract_gate.py`](../../../creative_governance/candidates/gates/contract_gate.py) | `review_governance` | 203 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/dependency_gate.py`](../../../creative_governance/candidates/gates/dependency_gate.py) | `review_governance` | 199 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/probe_gate.py`](../../../creative_governance/candidates/gates/probe_gate.py) | `review_governance` | 151 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/render_smoke_gate.py`](../../../creative_governance/candidates/gates/render_smoke_gate.py) | `review_governance` | 119 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/runtime_contract_gate.py`](../../../creative_governance/candidates/gates/runtime_contract_gate.py) | `review_governance` | 106 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/security_gate.py`](../../../creative_governance/candidates/gates/security_gate.py) | `review_governance` | 114 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/static_code_gate.py`](../../../creative_governance/candidates/gates/static_code_gate.py) | `review_governance` | 172 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/template_schema_gate.py`](../../../creative_governance/candidates/gates/template_schema_gate.py) | `review_governance` | 170 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/gates/typescript_gate.py`](../../../creative_governance/candidates/gates/typescript_gate.py) | `review_governance` | 100 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/hashing.py`](../../../creative_governance/candidates/hashing.py) | `review_governance` | 133 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/policies.py`](../../../creative_governance/candidates/policies.py) | `review_governance` | 225 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/promotion_service.py`](../../../creative_governance/candidates/promotion_service.py) | `review_governance` | 527 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/repository.py`](../../../creative_governance/candidates/repository.py) | `review_governance` | 398 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/review_service.py`](../../../creative_governance/candidates/review_service.py) | `review_governance` | 738 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/runtime_runner.py`](../../../creative_governance/candidates/runtime_runner.py) | `review_governance` | 18 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/service.py`](../../../creative_governance/candidates/service.py) | `review_governance` | 520 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`creative_governance/candidates/validation_service.py`](../../../creative_governance/candidates/validation_service.py) | `review_governance` | 658 | `ACTIVE_RUNTIME` | Human approval gates, review bundle generation, and cryptographic seals |
| [`api/services/asset_service.py`](../../../api/services/asset_service.py) | `storage_distribution` | 387 | `ACTIVE_RUNTIME` | Content-addressable storage, asset delivery, and tenant-scoped media distribution |

---

## 3. Subsystem File Directory Maps

### Subsystem: Agent Directives, Plugins & Legacy (`agent_legacy`)
- **File Count:** 179
- **Lines of Code:** 23,362
- **Critical Files:** 0

<details>
<summary>Click to expand all 179 files in agent_legacy</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `.agents/AGENTS.md` | `LEGACY_AGENT` | 78 | 5,433 |
| `.agents/docker/Dockerfile.remotion` | `LEGACY_AGENT` | 0 | 2,702 |
| `.agents/guardian/behavior_guard.py` | `LEGACY_AGENT` | 114 | 4,411 |
| `.agents/guardian/circuit_breaker.json` | `LEGACY_AGENT` | 1 | 87 |
| `.agents/guardian/command_guard.py` | `LEGACY_AGENT` | 143 | 6,006 |
| `.agents/guardian/post_executor.py` | `LEGACY_AGENT` | 78 | 2,816 |
| `.agents/guardian/utils.py` | `LEGACY_AGENT` | 176 | 6,002 |
| `.agents/guardian/write_guard.py` | `LEGACY_AGENT` | 81 | 3,051 |
| `.agents/logs/guardrails.log` | `LEGACY_AGENT` | 0 | 173,286 |
| `.agents/plugins/super-video-maker-plugin/.gitignore` | `LEGACY_AGENT` | 0 | 494 |
| `.agents/plugins/super-video-maker-plugin/commands/avatar-insta-reel.md` | `LEGACY_AGENT` | 19 | 961 |
| `.agents/plugins/super-video-maker-plugin/mcp_config.json` | `LEGACY_AGENT` | 85 | 2,414 |
| `.agents/plugins/super-video-maker-plugin/package.json` | `LEGACY_AGENT` | 10 | 288 |
| `.agents/plugins/super-video-maker-plugin/plugin.json` | `LEGACY_AGENT` | 23 | 807 |
| `.agents/plugins/super-video-maker-plugin/reference/ground-truth/template_catalog.json` | `LEGACY_AGENT` | 1 | 2 |
| `.agents/plugins/super-video-maker-plugin/skills/INDEX.md` | `LEGACY_AGENT` | 1 | 237 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/SKILL.md` | `LEGACY_AGENT` | 56 | 3,608 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/anatomy.md` | `LEGACY_AGENT` | 88 | 9,362 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/changelog.md` | `LEGACY_AGENT` | 55 | 3,409 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/cli-tool-demo.md` | `LEGACY_AGENT` | 79 | 7,602 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/feature-announcement.md` | `LEGACY_AGENT` | 46 | 4,015 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/index.md` | `LEGACY_AGENT` | 28 | 2,095 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/logo-bumper.md` | `LEGACY_AGENT` | 56 | 5,166 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/oss-showcase.md` | `LEGACY_AGENT` | 60 | 6,445 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/pricing-reveal.md` | `LEGACY_AGENT` | 67 | 5,759 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/product-demo.md` | `LEGACY_AGENT` | 116 | 7,900 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/testimonial-reel.md` | `LEGACY_AGENT` | 51 | 5,311 |
| `.agents/plugins/super-video-maker-plugin/skills/remocn/references/archetypes/year-in-review.md` | `LEGACY_AGENT` | 57 | 6,333 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/SKILL.md` | `LEGACY_AGENT` | 56 | 3,608 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/anatomy.md` | `LEGACY_AGENT` | 88 | 9,045 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/anti-patterns.md` | `LEGACY_AGENT` | 93 | 3,406 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/changelog.md` | `LEGACY_AGENT` | 54 | 3,297 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/cli-tool-demo.md` | `LEGACY_AGENT` | 75 | 6,412 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/feature-announcement.md` | `LEGACY_AGENT` | 46 | 4,324 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/index.md` | `LEGACY_AGENT` | 93 | 5,034 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/logo-bumper.md` | `LEGACY_AGENT` | 56 | 5,231 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/oss-showcase.md` | `LEGACY_AGENT` | 60 | 6,561 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/pricing-reveal.md` | `LEGACY_AGENT` | 67 | 5,755 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/product-demo.md` | `LEGACY_AGENT` | 128 | 7,829 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/testimonial-reel.md` | `LEGACY_AGENT` | 51 | 5,361 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/archetypes/year-in-review.md` | `LEGACY_AGENT` | 57 | 6,257 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/announce-title.md` | `LEGACY_AGENT` | 53 | 1,908 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/answer-stream.md` | `LEGACY_AGENT` | 59 | 2,008 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/block-wordmark.md` | `LEGACY_AGENT` | 55 | 1,809 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/caret.md` | `LEGACY_AGENT` | 55 | 1,597 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/follower-rush.md` | `LEGACY_AGENT` | 51 | 1,584 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/hero-launch.md` | `LEGACY_AGENT` | 43 | 1,364 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/index.md` | `LEGACY_AGENT` | 151 | 11,799 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/input.md` | `LEGACY_AGENT` | 53 | 1,727 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/karaoke-captions.md` | `LEGACY_AGENT` | 53 | 1,911 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/laptop-frame.md` | `LEGACY_AGENT` | 54 | 1,859 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/logo-assemble.md` | `LEGACY_AGENT` | 52 | 1,627 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/logo-flicker.md` | `LEGACY_AGENT` | 51 | 1,563 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/moodboard-reveal.md` | `LEGACY_AGENT` | 47 | 1,626 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/orbit-gallery.md` | `LEGACY_AGENT` | 61 | 1,955 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/phone-frame.md` | `LEGACY_AGENT` | 53 | 1,867 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/prompt-zoom.md` | `LEGACY_AGENT` | 58 | 1,870 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/pulsing-border.md` | `LEGACY_AGENT` | 54 | 1,671 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/search-typing.md` | `LEGACY_AGENT` | 61 | 2,090 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/snap-cn-ui.md` | `LEGACY_AGENT` | 41 | 1,381 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/status-cycle.md` | `LEGACY_AGENT` | 54 | 1,958 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/terminal-simulator.md` | `LEGACY_AGENT` | 55 | 2,039 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/text-build.md` | `LEGACY_AGENT` | 57 | 1,874 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/text-highlight.md` | `LEGACY_AGENT` | 60 | 2,225 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/text-reveal.md` | `LEGACY_AGENT` | 67 | 3,027 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/text-swap.md` | `LEGACY_AGENT` | 57 | 2,020 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/text-swell.md` | `LEGACY_AGENT` | 61 | 2,048 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/word-captions.md` | `LEGACY_AGENT` | 53 | 1,915 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components/word-flip.md` | `LEGACY_AGENT` | 63 | 2,012 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/design.md` | `LEGACY_AGENT` | 121 | 3,964 |
| `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/motion-principles.md` | `LEGACY_AGENT` | 131 | 6,353 |
| `.agents/plugins/super-video-maker-plugin/tools/ad_quality_gate.py` | `LEGACY_AGENT` | 666 | 27,542 |
| `.agents/plugins/super-video-maker-plugin/tools/agent_browser_recorder.py` | `LEGACY_AGENT` | 270 | 10,811 |
| `.agents/plugins/super-video-maker-plugin/tools/broll_layout_qc.py` | `LEGACY_AGENT` | 364 | 14,047 |
| `.agents/plugins/super-video-maker-plugin/tools/elevenlabs_voice.py` | `LEGACY_AGENT` | 85 | 4,186 |
| `.agents/plugins/super-video-maker-plugin/tools/fal_seedance_video.py` | `LEGACY_AGENT` | 378 | 14,530 |
| `.agents/plugins/super-video-maker-plugin/tools/ffmpeg_qc.py` | `LEGACY_AGENT` | 135 | 4,027 |
| `.agents/plugins/super-video-maker-plugin/tools/heygen_client.py` | `LEGACY_AGENT` | 279 | 11,508 |
| `.agents/plugins/super-video-maker-plugin/tools/image_provider.py` | `LEGACY_AGENT` | 110 | 3,755 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/.device_capability.json` | `LEGACY_AGENT` | 4 | 52 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/.gitignore` | `LEGACY_AGENT` | 0 | 119 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/.python-version` | `LEGACY_AGENT` | 0 | 6 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/README.md` | `LEGACY_AGENT` | 0 | 0 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/complex_test_result.json` | `LEGACY_AGENT` | 281 | 7,344 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/pyproject.toml` | `LEGACY_AGENT` | 18 | 393 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/server.py` | `LEGACY_AGENT` | 204 | 8,146 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/src/audio_tools_mcp/__init__.py` | `LEGACY_AGENT` | 2 | 63 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/test_result.json` | `LEGACY_AGENT` | 113 | 2,765 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/utils/ffmpeg_ops.py` | `LEGACY_AGENT` | 337 | 14,251 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/utils/manifest_builder.py` | `LEGACY_AGENT` | 251 | 9,949 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/utils/sentence_splitter.py` | `LEGACY_AGENT` | 260 | 9,528 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/utils/timeline_builder.py` | `LEGACY_AGENT` | 215 | 8,512 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/utils/voiceover_ops.py` | `LEGACY_AGENT` | 366 | 15,046 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/voiceover_manifest.json` | `LEGACY_AGENT` | 553 | 15,198 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp/.gitignore` | `LEGACY_AGENT` | 0 | 119 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp/.python-version` | `LEGACY_AGENT` | 0 | 6 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp/README.md` | `LEGACY_AGENT` | 0 | 0 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp/pyproject.toml` | `LEGACY_AGENT` | 17 | 366 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp/server.py` | `LEGACY_AGENT` | 87 | 3,455 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp/src/common_tools_mcp/__init__.py` | `LEGACY_AGENT` | 2 | 64 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp/utils/cache_ops.py` | `LEGACY_AGENT` | 90 | 3,331 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/.gitignore` | `LEGACY_AGENT` | 0 | 387 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/Dockerfile` | `LEGACY_AGENT` | 0 | 157 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/LICENSE` | `LEGACY_AGENT` | 0 | 1,095 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/README.md` | `LEGACY_AGENT` | 195 | 5,666 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/package-lock.json` | `LEGACY_AGENT` | 165 | 5,932 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/package.json` | `LEGACY_AGENT` | 32 | 691 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/scripts/.gitkeep` | `LEGACY_AGENT` | 0 | 0 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/server.js` | `LEGACY_AGENT` | 688 | 25,598 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server/test/.gitkeep` | `LEGACY_AGENT` | 0 | 0 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp/.gitignore` | `LEGACY_AGENT` | 0 | 119 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp/.python-version` | `LEGACY_AGENT` | 0 | 6 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp/README.md` | `LEGACY_AGENT` | 0 | 0 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp/pyproject.toml` | `LEGACY_AGENT` | 18 | 386 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp/server.py` | `LEGACY_AGENT` | 55 | 2,253 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp/src/image_tools_mcp/__init__.py` | `LEGACY_AGENT` | 2 | 63 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp/utils/image_ops.py` | `LEGACY_AGENT` | 168 | 7,381 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/.env.example` | `LEGACY_AGENT` | 0 | 119 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/.gitignore` | `LEGACY_AGENT` | 0 | 34 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/.python-version` | `LEGACY_AGENT` | 0 | 6 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/README.md` | `LEGACY_AGENT` | 0 | 0 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/dump.html` | `LEGACY_AGENT` | 0 | 347,078 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/dump_html.py` | `LEGACY_AGENT` | 26 | 915 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/pyproject.toml` | `LEGACY_AGENT` | 23 | 520 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/pyrightconfig.json` | `LEGACY_AGENT` | 10 | 142 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/server.py` | `LEGACY_AGENT` | 118 | 5,036 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/src/media_sources_mcp/__init__.py` | `LEGACY_AGENT` | 2 | 65 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_attrs.py` | `LEGACY_AGENT` | 44 | 1,847 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_click.py` | `LEGACY_AGENT` | 50 | 2,062 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_internal_api.py` | `LEGACY_AGENT` | 15 | 537 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_network.py` | `LEGACY_AGENT` | 41 | 1,570 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_pix.py` | `LEGACY_AGENT` | 25 | 894 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_playwright.py` | `LEGACY_AGENT` | 44 | 1,647 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_regex.py` | `LEGACY_AGENT` | 41 | 1,478 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_scrape.py` | `LEGACY_AGENT` | 34 | 1,241 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_workflow.py` | `LEGACY_AGENT` | 65 | 2,221 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/test_workflow_final.py` | `LEGACY_AGENT` | 50 | 2,234 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/tools/freesound.py` | `LEGACY_AGENT` | 20 | 682 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/tools/iconify.py` | `LEGACY_AGENT` | 52 | 1,879 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/tools/pexels.py` | `LEGACY_AGENT` | 33 | 1,184 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/tools/pixabay.py` | `LEGACY_AGENT` | 35 | 1,153 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/utils/downloader.py` | `LEGACY_AGENT` | 134 | 5,386 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/utils/file_organizer.py` | `LEGACY_AGENT` | 62 | 2,496 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/utils/http_client.py` | `LEGACY_AGENT` | 27 | 1,378 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp/utils/pixabay_scraper.py` | `LEGACY_AGENT` | 104 | 4,761 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp/.gitignore` | `LEGACY_AGENT` | 0 | 119 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp/.python-version` | `LEGACY_AGENT` | 0 | 6 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp/README.md` | `LEGACY_AGENT` | 0 | 0 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp/pyproject.toml` | `LEGACY_AGENT` | 17 | 363 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp/server.py` | `LEGACY_AGENT` | 68 | 3,249 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp/src/video_tools_mcp/__init__.py` | `LEGACY_AGENT` | 2 | 63 |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp/utils/ffmpeg_ops.py` | `LEGACY_AGENT` | 268 | 9,872 |
| `.agents/plugins/super-video-maker-plugin/tools/media_pipeline.py` | `LEGACY_AGENT` | 404 | 16,493 |
| `.agents/plugins/super-video-maker-plugin/tools/music_provider.py` | `LEGACY_AGENT` | 71 | 1,986 |
| `.agents/plugins/super-video-maker-plugin/tools/replicate_video.py` | `LEGACY_AGENT` | 93 | 3,468 |
| `.agents/plugins/super-video-maker-plugin/tools/screen_recorder.py` | `LEGACY_AGENT` | 419 | 16,356 |
| `.agents/plugins/super-video-maker-plugin/tools/video_captioner.py` | `LEGACY_AGENT` | 580 | 22,474 |
| `.agents/plugins/super-video-maker-plugin/verify.py` | `LEGACY_AGENT` | 95 | 3,417 |
| `.agents/rules/video-production-protocol.md` | `LEGACY_AGENT` | 110 | 6,848 |
| `.agents/secrets/.qc_salt` | `LEGACY_AGENT` | 0 | 32 |
| `.agents/skills/prompt-engineering-expert` | `LEGACY_AGENT` | 0 | 0 |
| `ground-truth/ASSET_INDEX.json` | `LEGACY_AGENT` | 983 | 27,849 |
| `ground-truth/CANONICAL_PATHS.json` | `LEGACY_AGENT` | 23 | 608 |
| `ground-truth/CINEMATIC_INDEX.md` | `LEGACY_AGENT` | 72 | 5,769 |
| `ground-truth/MCP_INDEX.md` | `LEGACY_AGENT` | 41 | 4,479 |
| `ground-truth/PLAYBOOKS_INDEX.md` | `LEGACY_AGENT` | 8 | 224 |
| `ground-truth/RECIPES_INDEX.md` | `LEGACY_AGENT` | 26 | 3,692 |
| `ground-truth/TEMPLATE_DUPLICATES.md` | `LEGACY_AGENT` | 21 | 3,050 |
| `ground-truth/TEMPLATE_INDEX.md` | `LEGACY_AGENT` | 300 | 19,176 |
| `ground-truth/TOOLS_INDEX.md` | `LEGACY_AGENT` | 21 | 1,397 |
| `ground-truth/VOCAB_REMAP.md` | `LEGACY_AGENT` | 24 | 1,661 |
| `ground-truth/adapter_family_candidates.json` | `LEGACY_AGENT` | 1,560 | 37,361 |
| `ground-truth/collections/ads.md` | `LEGACY_AGENT` | 18 | 348 |
| `ground-truth/collections/explainers.md` | `LEGACY_AGENT` | 18 | 355 |
| `ground-truth/collections/product.md` | `LEGACY_AGENT` | 18 | 352 |
| `ground-truth/collections/saas.md` | `LEGACY_AGENT` | 18 | 349 |
| `ground-truth/collections/social.md` | `LEGACY_AGENT` | 18 | 351 |
| `ground-truth/orchestration_resolved_spec.json` | `LEGACY_AGENT` | 153 | 4,252 |
| `ground-truth/template_catalog.json` | `LEGACY_AGENT` | 6,071 | 117,295 |

</details>

### Subsystem: AI Creative Intelligence & Narrative (`ai_creative`)
- **File Count:** 47
- **Lines of Code:** 7,143
- **Critical Files:** 47

<details>
<summary>Click to expand all 47 files in ai_creative</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `ai/narrative/__init__.py` | `ACTIVE_RUNTIME` | 21 | 527 |
| `ai/narrative/contracts.py` | `ACTIVE_RUNTIME` | 36 | 1,677 |
| `ai/narrative/metrics.py` | `ACTIVE_RUNTIME` | 200 | 9,004 |
| `ai/narrative/planner.py` | `ACTIVE_RUNTIME` | 407 | 18,053 |
| `ai/orchestration/__init__.py` | `ACTIVE_RUNTIME` | 104 | 3,029 |
| `ai/orchestration/activity.py` | `ACTIVE_RUNTIME` | 261 | 10,402 |
| `ai/orchestration/activity_classification.py` | `ACTIVE_RUNTIME` | 254 | 13,321 |
| `ai/orchestration/dag.py` | `ACTIVE_RUNTIME` | 179 | 7,725 |
| `ai/orchestration/errors.py` | `ACTIVE_RUNTIME` | 107 | 2,838 |
| `ai/orchestration/lease.py` | `ACTIVE_RUNTIME` | 35 | 1,131 |
| `ai/orchestration/recovery.py` | `ACTIVE_RUNTIME` | 312 | 14,505 |
| `ai/orchestration/repository.py` | `ACTIVE_RUNTIME` | 252 | 8,200 |
| `ai/orchestration/retry.py` | `ACTIVE_RUNTIME` | 84 | 3,105 |
| `ai/orchestration/service.py` | `ACTIVE_RUNTIME` | 407 | 16,574 |
| `ai/orchestration/state.py` | `ACTIVE_RUNTIME` | 129 | 4,266 |
| `ai/orchestration/worker.py` | `ACTIVE_RUNTIME` | 135 | 4,865 |
| `ai/recipes/__init__.py` | `ACTIVE_RUNTIME` | 31 | 666 |
| `ai/recipes/contracts.py` | `ACTIVE_RUNTIME` | 32 | 830 |
| `ai/recipes/evaluator.py` | `ACTIVE_RUNTIME` | 189 | 7,506 |
| `ai/recipes/registry.py` | `ACTIVE_RUNTIME` | 522 | 25,228 |
| `ai/recipes/selector.py` | `ACTIVE_RUNTIME` | 307 | 14,307 |
| `ai/taste/__init__.py` | `ACTIVE_RUNTIME` | 31 | 792 |
| `ai/taste/context.py` | `ACTIVE_RUNTIME` | 56 | 2,155 |
| `ai/taste/contracts.py` | `ACTIVE_RUNTIME` | 47 | 1,556 |
| `ai/taste/engine.py` | `ACTIVE_RUNTIME` | 90 | 4,104 |
| `ai/taste/evaluator.py` | `ACTIVE_RUNTIME` | 200 | 8,945 |
| `ai/taste/registry.py` | `ACTIVE_RUNTIME` | 328 | 19,177 |
| `recipes/README.md` | `ACTIVE_RUNTIME` | 43 | 2,446 |
| `recipes/agent-browser-proof.json` | `ACTIVE_RUNTIME` | 87 | 2,823 |
| `recipes/avatar-explainer.json` | `ACTIVE_RUNTIME` | 140 | 4,728 |
| `recipes/avatar-hook-broll.json` | `ACTIVE_RUNTIME` | 162 | 7,380 |
| `recipes/avatar-insta-split.json` | `ACTIVE_RUNTIME` | 133 | 8,770 |
| `recipes/avatar-product-walkthrough.json` | `ACTIVE_RUNTIME` | 102 | 3,373 |
| `recipes/avatar-vo-broll.json` | `ACTIVE_RUNTIME` | 112 | 5,708 |
| `recipes/captioned-talking-head.json` | `ACTIVE_RUNTIME` | 83 | 2,633 |
| `recipes/dynamic-montage-ad.json` | `ACTIVE_RUNTIME` | 158 | 5,920 |
| `recipes/faceless-broll-ad.json` | `ACTIVE_RUNTIME` | 93 | 3,295 |
| `recipes/living-canvas-explainer.json` | `ACTIVE_RUNTIME` | 156 | 14,393 |
| `recipes/longform-repurpose.json` | `ACTIVE_RUNTIME` | 89 | 2,745 |
| `recipes/misotts-article-sprint.json` | `ACTIVE_RUNTIME` | 220 | 16,129 |
| `recipes/motion-collage-explainer.json` | `ACTIVE_RUNTIME` | 120 | 5,494 |
| `recipes/motion-graphics.json` | `ACTIVE_RUNTIME` | 86 | 2,741 |
| `recipes/review-conquest-compilation.json` | `ACTIVE_RUNTIME` | 115 | 5,363 |
| `recipes/schema.json` | `ACTIVE_RUNTIME` | 123 | 3,156 |
| `recipes/screencast-demo.json` | `ACTIVE_RUNTIME` | 90 | 2,967 |
| `recipes/tabletop-levels-explainer.json` | `ACTIVE_RUNTIME` | 140 | 10,519 |
| `recipes/ugc-ai-ad.json` | `ACTIVE_RUNTIME` | 135 | 4,557 |

</details>

### Subsystem: Core Domain Services (`api_services`)
- **File Count:** 12
- **Lines of Code:** 2,204
- **Critical Files:** 12

<details>
<summary>Click to expand all 12 files in api_services</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `api/services/__init__.py` | `ACTIVE_RUNTIME` | 4 | 152 |
| `api/services/authoring_service.py` | `ACTIVE_RUNTIME` | 260 | 10,646 |
| `api/services/brand_service.py` | `ACTIVE_RUNTIME` | 150 | 5,800 |
| `api/services/capability_service.py` | `ACTIVE_RUNTIME` | 244 | 10,368 |
| `api/services/creative_service.py` | `ACTIVE_RUNTIME` | 521 | 24,448 |
| `api/services/domain_artifact_service.py` | `ACTIVE_RUNTIME` | 122 | 5,037 |
| `api/services/gate_service.py` | `ACTIVE_RUNTIME` | 32 | 1,552 |
| `api/services/health_service.py` | `ACTIVE_RUNTIME` | 423 | 16,990 |
| `api/services/output_service.py` | `ACTIVE_RUNTIME` | 153 | 6,146 |
| `api/services/override_service.py` | `ACTIVE_RUNTIME` | 223 | 9,350 |
| `api/services/render_service.py` | `ACTIVE_RUNTIME` | 29 | 1,204 |
| `api/services/scaffold_service.py` | `ACTIVE_RUNTIME` | 43 | 1,488 |

</details>

### Subsystem: Multi-Tenancy, Auth & Security (`auth_tenancy`)
- **File Count:** 7
- **Lines of Code:** 1,508
- **Critical Files:** 7

<details>
<summary>Click to expand all 7 files in auth_tenancy</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `scripts/core/security/__init__.py` | `ACTIVE_RUNTIME` | 71 | 1,858 |
| `scripts/core/security/command_policy.py` | `ACTIVE_RUNTIME` | 461 | 19,231 |
| `scripts/core/security/env_policy.py` | `ACTIVE_RUNTIME` | 227 | 7,883 |
| `scripts/core/security/path_policy.py` | `ACTIVE_RUNTIME` | 263 | 10,132 |
| `scripts/core/security/permissions.py` | `ACTIVE_RUNTIME` | 240 | 8,411 |
| `scripts/core/security/principal.py` | `ACTIVE_RUNTIME` | 125 | 4,649 |
| `scripts/core/security/settings.py` | `ACTIVE_RUNTIME` | 121 | 4,533 |

</details>

### Subsystem: Canonical Documents & Project State (`canonical_documents`)
- **File Count:** 1
- **Lines of Code:** 449
- **Critical Files:** 1

<details>
<summary>Click to expand all 1 files in canonical_documents</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `api/services/project_service.py` | `ACTIVE_RUNTIME` | 449 | 20,700 |

</details>

### Subsystem: Root Build & Project Configuration (`configuration`)
- **File Count:** 9
- **Lines of Code:** 1,667
- **Critical Files:** 0

<details>
<summary>Click to expand all 9 files in configuration</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `.env.example` | `DEV_TOOLING` | 0 | 1,500 |
| `.gitignore` | `DEV_TOOLING` | 0 | 1,608 |
| `LICENSE` | `DEV_TOOLING` | 0 | 1,102 |
| `package.json` | `DEV_TOOLING` | 46 | 2,420 |
| `pyproject.toml` | `DEV_TOOLING` | 72 | 1,536 |
| `requirements-dev.txt` | `DEV_TOOLING` | 134 | 10,084 |
| `requirements.txt` | `DEV_TOOLING` | 1,365 | 102,613 |
| `tsconfig.json` | `DEV_TOOLING` | 28 | 587 |
| `vitest.config.ts` | `DEV_TOOLING` | 22 | 825 |

</details>

### Subsystem: Context, Knowledge, Skills & Tools (`context_knowledge_skills`)
- **File Count:** 53
- **Lines of Code:** 10,840
- **Critical Files:** 53

<details>
<summary>Click to expand all 53 files in context_knowledge_skills</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `ai/context/__init__.py` | `ACTIVE_RUNTIME` | 119 | 2,836 |
| `ai/context/adapters/__init__.py` | `ACTIVE_RUNTIME` | 6 | 161 |
| `ai/context/adapters/knowledge_router_adapter.py` | `ACTIVE_RUNTIME` | 143 | 5,370 |
| `ai/context/assembly.py` | `ACTIVE_RUNTIME` | 139 | 4,863 |
| `ai/context/budgeting.py` | `ACTIVE_RUNTIME` | 319 | 12,663 |
| `ai/context/builder.py` | `ACTIVE_RUNTIME` | 222 | 8,801 |
| `ai/context/compression.py` | `ACTIVE_RUNTIME` | 108 | 3,936 |
| `ai/context/deduplication.py` | `ACTIVE_RUNTIME` | 161 | 7,611 |
| `ai/context/needs.py` | `ACTIVE_RUNTIME` | 182 | 7,960 |
| `ai/context/ranking.py` | `ACTIVE_RUNTIME` | 127 | 5,091 |
| `ai/context/retrieval.py` | `ACTIVE_RUNTIME` | 623 | 26,756 |
| `ai/context/types.py` | `ACTIVE_RUNTIME` | 341 | 15,806 |
| `ai/knowledge/__init__.py` | `ACTIVE_RUNTIME` | 87 | 2,372 |
| `ai/knowledge/catalog_service.py` | `ACTIVE_RUNTIME` | 121 | 4,116 |
| `ai/knowledge/contracts.py` | `ACTIVE_RUNTIME` | 151 | 7,927 |
| `ai/knowledge/indexer.py` | `ACTIVE_RUNTIME` | 187 | 7,818 |
| `ai/knowledge/loader.py` | `ACTIVE_RUNTIME` | 382 | 19,024 |
| `ai/knowledge/registry.py` | `ACTIVE_RUNTIME` | 135 | 5,696 |
| `ai/knowledge/retriever.py` | `ACTIVE_RUNTIME` | 540 | 23,395 |
| `ai/knowledge/router.py` | `ACTIVE_RUNTIME` | 125 | 4,746 |
| `ai/knowledge/semantic.py` | `ACTIVE_RUNTIME` | 302 | 12,138 |
| `ai/skills/__init__.py` | `ACTIVE_RUNTIME` | 71 | 1,815 |
| `ai/skills/context.py` | `ACTIVE_RUNTIME` | 129 | 4,563 |
| `ai/skills/contracts.py` | `ACTIVE_RUNTIME` | 90 | 4,752 |
| `ai/skills/loader.py` | `ACTIVE_RUNTIME` | 309 | 13,911 |
| `ai/skills/registry.py` | `ACTIVE_RUNTIME` | 115 | 4,486 |
| `ai/skills/router.py` | `ACTIVE_RUNTIME` | 204 | 8,835 |
| `ai/tools/__init__.py` | `ACTIVE_RUNTIME` | 135 | 3,449 |
| `ai/tools/adapters/__init__.py` | `ACTIVE_RUNTIME` | 43 | 1,334 |
| `ai/tools/adapters/acquisition.py` | `ACTIVE_RUNTIME` | 286 | 11,689 |
| `ai/tools/adapters/base.py` | `ACTIVE_RUNTIME` | 74 | 2,503 |
| `ai/tools/adapters/domain_service.py` | `ACTIVE_RUNTIME` | 274 | 11,003 |
| `ai/tools/adapters/image_processing.py` | `ACTIVE_RUNTIME` | 231 | 9,898 |
| `ai/tools/adapters/mcp.py` | `ACTIVE_RUNTIME` | 561 | 26,525 |
| `ai/tools/adapters/media_processing.py` | `ACTIVE_RUNTIME` | 437 | 21,563 |
| `ai/tools/adapters/native.py` | `ACTIVE_RUNTIME` | 71 | 2,503 |
| `ai/tools/adapters/registry.py` | `ACTIVE_RUNTIME` | 221 | 10,186 |
| `ai/tools/adapters/remote.py` | `ACTIVE_RUNTIME` | 131 | 5,427 |
| `ai/tools/adapters/worker.py` | `ACTIVE_RUNTIME` | 54 | 1,715 |
| `ai/tools/audit.py` | `ACTIVE_RUNTIME` | 124 | 5,120 |
| `ai/tools/authorization.py` | `ACTIVE_RUNTIME` | 121 | 5,147 |
| `ai/tools/contracts.py` | `ACTIVE_RUNTIME` | 288 | 15,037 |
| `ai/tools/dispatcher.py` | `ACTIVE_RUNTIME` | 261 | 10,275 |
| `ai/tools/domain/__init__.py` | `ACTIVE_RUNTIME` | 212 | 7,984 |
| `ai/tools/domain/assets.py` | `ACTIVE_RUNTIME` | 118 | 3,593 |
| `ai/tools/domain/blueprint.py` | `ACTIVE_RUNTIME` | 100 | 3,472 |
| `ai/tools/domain/projects.py` | `ACTIVE_RUNTIME` | 44 | 1,590 |
| `ai/tools/domain/qc.py` | `ACTIVE_RUNTIME` | 67 | 2,459 |
| `ai/tools/domain/runs.py` | `ACTIVE_RUNTIME` | 69 | 2,016 |
| `ai/tools/errors.py` | `ACTIVE_RUNTIME` | 371 | 14,177 |
| `ai/tools/gateway.py` | `ACTIVE_RUNTIME` | 688 | 32,412 |
| `ai/tools/registry.py` | `ACTIVE_RUNTIME` | 136 | 5,011 |
| `ai/tools/types.py` | `ACTIVE_RUNTIME` | 285 | 11,822 |

</details>

### Subsystem: Contracts & Pydantic Schemas (`contracts_schemas`)
- **File Count:** 310
- **Lines of Code:** 89,815
- **Critical Files:** 310

<details>
<summary>Click to expand all 310 files in contracts_schemas</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `ai/contracts/__init__.py` | `CONTRACT_SCHEMA` | 638 | 16,057 |
| `ai/contracts/activity.py` | `CONTRACT_SCHEMA` | 82 | 4,352 |
| `ai/contracts/audio.py` | `CONTRACT_SCHEMA` | 103 | 6,042 |
| `ai/contracts/base.py` | `CONTRACT_SCHEMA` | 94 | 3,565 |
| `ai/contracts/cache.py` | `CONTRACT_SCHEMA` | 132 | 5,925 |
| `ai/contracts/capability.py` | `CONTRACT_SCHEMA` | 548 | 24,400 |
| `ai/contracts/common.py` | `CONTRACT_SCHEMA` | 168 | 6,618 |
| `ai/contracts/creative/__init__.py` | `CONTRACT_SCHEMA` | 235 | 5,958 |
| `ai/contracts/creative/brief.py` | `CONTRACT_SCHEMA` | 138 | 7,607 |
| `ai/contracts/creative/conflict.py` | `CONTRACT_SCHEMA` | 95 | 5,218 |
| `ai/contracts/creative/cost.py` | `CONTRACT_SCHEMA` | 339 | 17,871 |
| `ai/contracts/creative/directors.py` | `CONTRACT_SCHEMA` | 77 | 5,821 |
| `ai/contracts/creative/feedback.py` | `CONTRACT_SCHEMA` | 220 | 12,286 |
| `ai/contracts/creative/narrative.py` | `CONTRACT_SCHEMA` | 70 | 3,696 |
| `ai/contracts/creative/plan.py` | `CONTRACT_SCHEMA` | 208 | 14,057 |
| `ai/contracts/creative/recipe.py` | `CONTRACT_SCHEMA` | 111 | 7,384 |
| `ai/contracts/creative/regression.py` | `CONTRACT_SCHEMA` | 254 | 11,210 |
| `ai/contracts/creative/skills_knowledge.py` | `CONTRACT_SCHEMA` | 174 | 7,027 |
| `ai/contracts/creative/taste.py` | `CONTRACT_SCHEMA` | 87 | 5,335 |
| `ai/contracts/creative/template_candidate.py` | `CONTRACT_SCHEMA` | 403 | 24,806 |
| `ai/contracts/errors.py` | `CONTRACT_SCHEMA` | 139 | 5,895 |
| `ai/contracts/evals.py` | `CONTRACT_SCHEMA` | 146 | 6,996 |
| `ai/contracts/media.py` | `CONTRACT_SCHEMA` | 334 | 19,513 |
| `ai/contracts/media_ops.py` | `CONTRACT_SCHEMA` | 901 | 54,372 |
| `ai/contracts/memory.py` | `CONTRACT_SCHEMA` | 110 | 4,576 |
| `ai/contracts/model.py` | `CONTRACT_SCHEMA` | 171 | 6,603 |
| `ai/contracts/observability.py` | `CONTRACT_SCHEMA` | 82 | 4,803 |
| `ai/contracts/prompt.py` | `CONTRACT_SCHEMA` | 143 | 6,089 |
| `ai/contracts/request.py` | `CONTRACT_SCHEMA` | 87 | 3,487 |
| `ai/contracts/response.py` | `CONTRACT_SCHEMA` | 60 | 2,672 |
| `ai/contracts/run.py` | `CONTRACT_SCHEMA` | 134 | 8,237 |
| `ai/contracts/specialized.py` | `CONTRACT_SCHEMA` | 246 | 13,931 |
| `ai/contracts/tools.py` | `CONTRACT_SCHEMA` | 111 | 4,239 |
| `ai/contracts/usage.py` | `CONTRACT_SCHEMA` | 71 | 3,387 |
| `ai/contracts/vision.py` | `CONTRACT_SCHEMA` | 179 | 10,645 |
| `contracts/SceneContent.ts` | `CONTRACT_SCHEMA` | 21 | 487 |
| `contracts/StyleSurface.ts` | `CONTRACT_SCHEMA` | 123 | 3,162 |
| `contracts/animations.ts` | `CONTRACT_SCHEMA` | 227 | 6,531 |
| `contracts/asset-resolver.ts` | `CONTRACT_SCHEMA` | 599 | 19,757 |
| `contracts/authoring.ts` | `CONTRACT_SCHEMA` | 327 | 11,951 |
| `contracts/blueprint.ts` | `CONTRACT_SCHEMA` | 593 | 20,765 |
| `contracts/brand.ts` | `CONTRACT_SCHEMA` | 64 | 2,098 |
| `contracts/canonical-video.ts` | `CONTRACT_SCHEMA` | 170 | 4,432 |
| `contracts/compositor.ts` | `CONTRACT_SCHEMA` | 508 | 18,117 |
| `contracts/editor-session.ts` | `CONTRACT_SCHEMA` | 1,145 | 38,188 |
| `contracts/effects.ts` | `CONTRACT_SCHEMA` | 420 | 13,518 |
| `contracts/evaluator.ts` | `CONTRACT_SCHEMA` | 553 | 20,549 |
| `contracts/fixtures/asset_resolution_golden.json` | `CONTRACT_SCHEMA` | 83 | 2,916 |
| `contracts/fonts.ts` | `CONTRACT_SCHEMA` | 66 | 1,924 |
| `contracts/generated/ai_contracts.ts` | `CONTRACT_SCHEMA` | 1,537 | 39,168 |
| `contracts/generated/creative_contracts.ts` | `CONTRACT_SCHEMA` | 930 | 27,740 |
| `contracts/index.ts` | `CONTRACT_SCHEMA` | 30 | 921 |
| `contracts/keyframes.ts` | `CONTRACT_SCHEMA` | 655 | 23,448 |
| `contracts/layers.ts` | `CONTRACT_SCHEMA` | 257 | 9,919 |
| `contracts/manifest.ts` | `CONTRACT_SCHEMA` | 113 | 3,429 |
| `contracts/mutations.ts` | `CONTRACT_SCHEMA` | 2,874 | 99,183 |
| `contracts/normalization.ts` | `CONTRACT_SCHEMA` | 643 | 21,618 |
| `contracts/override-validator.ts` | `CONTRACT_SCHEMA` | 57 | 1,908 |
| `contracts/positions.ts` | `CONTRACT_SCHEMA` | 82 | 2,509 |
| `contracts/preview-fidelity.ts` | `CONTRACT_SCHEMA` | 294 | 11,979 |
| `contracts/preview-proxy.ts` | `CONTRACT_SCHEMA` | 227 | 8,392 |
| `contracts/render-graph.ts` | `CONTRACT_SCHEMA` | 466 | 18,468 |
| `contracts/render-input.ts` | `CONTRACT_SCHEMA` | 353 | 14,321 |
| `contracts/renderer.ts` | `CONTRACT_SCHEMA` | 1,139 | 39,714 |
| `contracts/storage-service.ts` | `CONTRACT_SCHEMA` | 160 | 5,004 |
| `contracts/template-instantiator.ts` | `CONTRACT_SCHEMA` | 605 | 21,902 |
| `contracts/template-runtime-contract.json` | `CONTRACT_SCHEMA` | 1,348 | 43,312 |
| `contracts/template-schemas.ts` | `CONTRACT_SCHEMA` | 332 | 11,913 |
| `contracts/template-spec.ts` | `CONTRACT_SCHEMA` | 251 | 9,509 |
| `contracts/timeline.ts` | `CONTRACT_SCHEMA` | 264 | 11,196 |
| `contracts/waveform.ts` | `CONTRACT_SCHEMA` | 226 | 8,531 |
| `schemas/ai/ai_activity.schema.json` | `CONTRACT_SCHEMA` | 537 | 14,033 |
| `schemas/ai/ai_cache_entry.schema.json` | `CONTRACT_SCHEMA` | 395 | 10,203 |
| `schemas/ai/ai_contracts.schema.json` | `CONTRACT_SCHEMA` | 20,868 | 625,742 |
| `schemas/ai/ai_error.schema.json` | `CONTRACT_SCHEMA` | 80 | 2,090 |
| `schemas/ai/ai_request.schema.json` | `CONTRACT_SCHEMA` | 241 | 6,662 |
| `schemas/ai/ai_response.schema.json` | `CONTRACT_SCHEMA` | 428 | 11,663 |
| `schemas/ai/ai_run.schema.json` | `CONTRACT_SCHEMA` | 615 | 16,372 |
| `schemas/ai/ai_step.schema.json` | `CONTRACT_SCHEMA` | 723 | 18,603 |
| `schemas/ai/ai_trace.schema.json` | `CONTRACT_SCHEMA` | 390 | 10,085 |
| `schemas/ai/align_audio_metadata_input.schema.json` | `CONTRACT_SCHEMA` | 100 | 2,606 |
| `schemas/ai/align_audio_metadata_output.schema.json` | `CONTRACT_SCHEMA` | 175 | 4,676 |
| `schemas/ai/aligned_segment_item.schema.json` | `CONTRACT_SCHEMA` | 115 | 2,827 |
| `schemas/ai/aligned_word_item.schema.json` | `CONTRACT_SCHEMA` | 53 | 1,200 |
| `schemas/ai/analyze_loudness_input.schema.json` | `CONTRACT_SCHEMA` | 24 | 601 |
| `schemas/ai/analyze_loudness_output.schema.json` | `CONTRACT_SCHEMA` | 69 | 1,773 |
| `schemas/ai/audio_denoise_request.schema.json` | `CONTRACT_SCHEMA` | 32 | 844 |
| `schemas/ai/audio_denoise_result.schema.json` | `CONTRACT_SCHEMA` | 127 | 3,538 |
| `schemas/ai/audio_enhance_request.schema.json` | `CONTRACT_SCHEMA` | 31 | 824 |
| `schemas/ai/audio_enhance_result.schema.json` | `CONTRACT_SCHEMA` | 127 | 3,531 |
| `schemas/ai/audio_intelligence.schema.json` | `CONTRACT_SCHEMA` | 558 | 14,505 |
| `schemas/ai/audio_segment_item.schema.json` | `CONTRACT_SCHEMA` | 51 | 1,218 |
| `schemas/ai/auto_crop_image_request.schema.json` | `CONTRACT_SCHEMA` | 67 | 1,737 |
| `schemas/ai/auto_crop_image_result.schema.json` | `CONTRACT_SCHEMA` | 77 | 1,929 |
| `schemas/ai/auto_crop_input.schema.json` | `CONTRACT_SCHEMA` | 32 | 824 |
| `schemas/ai/auto_crop_output.schema.json` | `CONTRACT_SCHEMA` | 63 | 1,549 |
| `schemas/ai/background_removal_request.schema.json` | `CONTRACT_SCHEMA` | 30 | 814 |
| `schemas/ai/background_removal_result.schema.json` | `CONTRACT_SCHEMA` | 127 | 3,493 |
| `schemas/ai/benchmark_debt.schema.json` | `CONTRACT_SCHEMA` | 49 | 1,366 |
| `schemas/ai/cancel_job_input.schema.json` | `CONTRACT_SCHEMA` | 37 | 812 |
| `schemas/ai/cancel_job_output.schema.json` | `CONTRACT_SCHEMA` | 36 | 891 |
| `schemas/ai/capability_definition.schema.json` | `CONTRACT_SCHEMA` | 440 | 13,066 |
| `schemas/ai/capability_request.schema.json` | `CONTRACT_SCHEMA` | 494 | 13,568 |
| `schemas/ai/capability_result.schema.json` | `CONTRACT_SCHEMA` | 581 | 15,382 |
| `schemas/ai/change_video_speed_input.schema.json` | `CONTRACT_SCHEMA` | 38 | 1,035 |
| `schemas/ai/change_video_speed_output.schema.json` | `CONTRACT_SCHEMA` | 49 | 1,133 |
| `schemas/ai/check_cache_input.schema.json` | `CONTRACT_SCHEMA` | 31 | 770 |
| `schemas/ai/check_cache_output.schema.json` | `CONTRACT_SCHEMA` | 50 | 1,193 |
| `schemas/ai/concatenate_videos_input.schema.json` | `CONTRACT_SCHEMA` | 40 | 939 |
| `schemas/ai/concatenate_videos_output.schema.json` | `CONTRACT_SCHEMA` | 38 | 998 |
| `schemas/ai/convert_image_input.schema.json` | `CONTRACT_SCHEMA` | 58 | 1,478 |
| `schemas/ai/convert_image_output.schema.json` | `CONTRACT_SCHEMA` | 59 | 1,452 |
| `schemas/ai/convert_image_request.schema.json` | `CONTRACT_SCHEMA` | 58 | 1,478 |
| `schemas/ai/convert_image_result.schema.json` | `CONTRACT_SCHEMA` | 59 | 1,452 |
| `schemas/ai/cost_estimate.schema.json` | `CONTRACT_SCHEMA` | 89 | 2,133 |
| `schemas/ai/crop_image_ratio_request.schema.json` | `CONTRACT_SCHEMA` | 52 | 1,316 |
| `schemas/ai/crop_image_ratio_result.schema.json` | `CONTRACT_SCHEMA` | 59 | 1,442 |
| `schemas/ai/crop_ratio_input.schema.json` | `CONTRACT_SCHEMA` | 30 | 796 |
| `schemas/ai/crop_ratio_output.schema.json` | `CONTRACT_SCHEMA` | 44 | 1,037 |
| `schemas/ai/detect_black_frames_input.schema.json` | `CONTRACT_SCHEMA` | 40 | 1,093 |
| `schemas/ai/detect_black_frames_output.schema.json` | `CONTRACT_SCHEMA` | 45 | 1,267 |
| `schemas/ai/detect_silence_input.schema.json` | `CONTRACT_SCHEMA` | 38 | 1,005 |
| `schemas/ai/detect_silence_output.schema.json` | `CONTRACT_SCHEMA` | 93 | 2,614 |
| `schemas/ai/download_icon_input.schema.json` | `CONTRACT_SCHEMA` | 45 | 1,041 |
| `schemas/ai/download_icon_output.schema.json` | `CONTRACT_SCHEMA` | 37 | 881 |
| `schemas/ai/download_remote_media_input.schema.json` | `CONTRACT_SCHEMA` | 43 | 1,019 |
| `schemas/ai/download_remote_media_output.schema.json` | `CONTRACT_SCHEMA` | 45 | 1,112 |
| `schemas/ai/downloaded_asset_item.schema.json` | `CONTRACT_SCHEMA` | 45 | 1,122 |
| `schemas/ai/enforce_keyframes_input.schema.json` | `CONTRACT_SCHEMA` | 31 | 805 |
| `schemas/ai/enforce_keyframes_output.schema.json` | `CONTRACT_SCHEMA` | 31 | 804 |
| `schemas/ai/eval_dataset.schema.json` | `CONTRACT_SCHEMA` | 226 | 6,284 |
| `schemas/ai/eval_example.schema.json` | `CONTRACT_SCHEMA` | 85 | 2,056 |
| `schemas/ai/eval_result.schema.json` | `CONTRACT_SCHEMA` | 136 | 3,523 |
| `schemas/ai/extend_audio_input.schema.json` | `CONTRACT_SCHEMA` | 50 | 1,357 |
| `schemas/ai/extend_audio_output.schema.json` | `CONTRACT_SCHEMA` | 38 | 958 |
| `schemas/ai/extend_video_input.schema.json` | `CONTRACT_SCHEMA` | 37 | 972 |
| `schemas/ai/extend_video_output.schema.json` | `CONTRACT_SCHEMA` | 38 | 950 |
| `schemas/ai/extract_media_page_input.schema.json` | `CONTRACT_SCHEMA` | 30 | 761 |
| `schemas/ai/extract_media_page_output.schema.json` | `CONTRACT_SCHEMA` | 79 | 2,149 |
| `schemas/ai/get_job_status_input.schema.json` | `CONTRACT_SCHEMA` | 24 | 559 |
| `schemas/ai/get_job_status_output.schema.json` | `CONTRACT_SCHEMA` | 65 | 1,513 |
| `schemas/ai/icon_search_result_item.schema.json` | `CONTRACT_SCHEMA` | 44 | 995 |
| `schemas/ai/image_generation_request.schema.json` | `CONTRACT_SCHEMA` | 73 | 1,577 |
| `schemas/ai/image_generation_result.schema.json` | `CONTRACT_SCHEMA` | 141 | 3,771 |
| `schemas/ai/implementation_descriptor.schema.json` | `CONTRACT_SCHEMA` | 84 | 2,404 |
| `schemas/ai/inspect_media_input.schema.json` | `CONTRACT_SCHEMA` | 27 | 625 |
| `schemas/ai/inspect_media_output.schema.json` | `CONTRACT_SCHEMA` | 300 | 7,944 |
| `schemas/ai/lip_sync_request.schema.json` | `CONTRACT_SCHEMA` | 31 | 846 |
| `schemas/ai/lip_sync_result.schema.json` | `CONTRACT_SCHEMA` | 136 | 3,780 |
| `schemas/ai/media_intelligence.schema.json` | `CONTRACT_SCHEMA` | 1,980 | 54,593 |
| `schemas/ai/media_intelligence_ref.schema.json` | `CONTRACT_SCHEMA` | 51 | 1,470 |
| `schemas/ai/memory_query.schema.json` | `CONTRACT_SCHEMA` | 90 | 2,194 |
| `schemas/ai/memory_result.schema.json` | `CONTRACT_SCHEMA` | 172 | 4,709 |
| `schemas/ai/model_requirement.schema.json` | `CONTRACT_SCHEMA` | 307 | 8,469 |
| `schemas/ai/model_selection.schema.json` | `CONTRACT_SCHEMA` | 128 | 3,580 |
| `schemas/ai/mutate_asset_status_input.schema.json` | `CONTRACT_SCHEMA` | 44 | 1,030 |
| `schemas/ai/mutate_asset_status_output.schema.json` | `CONTRACT_SCHEMA` | 42 | 1,085 |
| `schemas/ai/normalize_audio_input.schema.json` | `CONTRACT_SCHEMA` | 54 | 1,433 |
| `schemas/ai/normalize_audio_output.schema.json` | `CONTRACT_SCHEMA` | 50 | 1,345 |
| `schemas/ai/normalize_loudness_input.schema.json` | `CONTRACT_SCHEMA` | 39 | 1,001 |
| `schemas/ai/normalize_loudness_output.schema.json` | `CONTRACT_SCHEMA` | 36 | 973 |
| `schemas/ai/optimize_image_input.schema.json` | `CONTRACT_SCHEMA` | 68 | 1,644 |
| `schemas/ai/optimize_image_output.schema.json` | `CONTRACT_SCHEMA` | 66 | 1,659 |
| `schemas/ai/optimize_image_request.schema.json` | `CONTRACT_SCHEMA` | 68 | 1,644 |
| `schemas/ai/optimize_image_result.schema.json` | `CONTRACT_SCHEMA` | 66 | 1,659 |
| `schemas/ai/person_segmentation_request.schema.json` | `CONTRACT_SCHEMA` | 38 | 1,021 |
| `schemas/ai/person_segmentation_result.schema.json` | `CONTRACT_SCHEMA` | 136 | 3,710 |
| `schemas/ai/prepare_image_asset_input.schema.json` | `CONTRACT_SCHEMA` | 108 | 2,676 |
| `schemas/ai/prepare_image_asset_output.schema.json` | `CONTRACT_SCHEMA` | 78 | 1,943 |
| `schemas/ai/prepare_image_asset_request.schema.json` | `CONTRACT_SCHEMA` | 108 | 2,676 |
| `schemas/ai/prepare_image_asset_result.schema.json` | `CONTRACT_SCHEMA` | 78 | 1,943 |
| `schemas/ai/prepare_vo_segments_input.schema.json` | `CONTRACT_SCHEMA` | 54 | 1,265 |
| `schemas/ai/prepare_vo_segments_output.schema.json` | `CONTRACT_SCHEMA` | 104 | 2,790 |
| `schemas/ai/prepared_vo_segment_item.schema.json` | `CONTRACT_SCHEMA` | 57 | 1,344 |
| `schemas/ai/probe_image_input.schema.json` | `CONTRACT_SCHEMA` | 30 | 804 |
| `schemas/ai/probe_image_output.schema.json` | `CONTRACT_SCHEMA` | 101 | 2,493 |
| `schemas/ai/probe_image_request.schema.json` | `CONTRACT_SCHEMA` | 30 | 804 |
| `schemas/ai/probe_image_result.schema.json` | `CONTRACT_SCHEMA` | 101 | 2,493 |
| `schemas/ai/prompt_contract.schema.json` | `CONTRACT_SCHEMA` | 171 | 4,348 |
| `schemas/ai/prompt_metadata.schema.json` | `CONTRACT_SCHEMA` | 70 | 1,496 |
| `schemas/ai/prompt_render_request.schema.json` | `CONTRACT_SCHEMA` | 55 | 1,249 |
| `schemas/ai/prompt_render_result.schema.json` | `CONTRACT_SCHEMA` | 69 | 1,690 |
| `schemas/ai/resize_image_request.schema.json` | `CONTRACT_SCHEMA` | 102 | 2,409 |
| `schemas/ai/resize_image_result.schema.json` | `CONTRACT_SCHEMA` | 52 | 1,268 |
| `schemas/ai/resize_video_input.schema.json` | `CONTRACT_SCHEMA` | 44 | 1,122 |
| `schemas/ai/resize_video_output.schema.json` | `CONTRACT_SCHEMA` | 38 | 885 |
| `schemas/ai/search_icons_input.schema.json` | `CONTRACT_SCHEMA` | 38 | 812 |
| `schemas/ai/search_icons_output.schema.json` | `CONTRACT_SCHEMA` | 77 | 1,914 |
| `schemas/ai/search_sound_effects_input.schema.json` | `CONTRACT_SCHEMA` | 50 | 1,090 |
| `schemas/ai/search_sound_effects_output.schema.json` | `CONTRACT_SCHEMA` | 158 | 3,888 |
| `schemas/ai/search_stock_audio_input.schema.json` | `CONTRACT_SCHEMA` | 32 | 717 |
| `schemas/ai/search_stock_audio_output.schema.json` | `CONTRACT_SCHEMA` | 158 | 3,882 |
| `schemas/ai/search_stock_images_input.schema.json` | `CONTRACT_SCHEMA` | 45 | 1,002 |
| `schemas/ai/search_stock_images_output.schema.json` | `CONTRACT_SCHEMA` | 158 | 3,894 |
| `schemas/ai/search_stock_videos_input.schema.json` | `CONTRACT_SCHEMA` | 45 | 1,003 |
| `schemas/ai/search_stock_videos_output.schema.json` | `CONTRACT_SCHEMA` | 158 | 3,886 |
| `schemas/ai/segment_speech_input.schema.json` | `CONTRACT_SCHEMA` | 220 | 5,731 |
| `schemas/ai/segment_speech_output.schema.json` | `CONTRACT_SCHEMA` | 85 | 2,230 |
| `schemas/ai/silence_interval_item.schema.json` | `CONTRACT_SCHEMA` | 31 | 771 |
| `schemas/ai/speech_intelligence.schema.json` | `CONTRACT_SCHEMA` | 417 | 11,046 |
| `schemas/ai/speech_manifest_input.schema.json` | `CONTRACT_SCHEMA` | 30 | 772 |
| `schemas/ai/speech_manifest_output.schema.json` | `CONTRACT_SCHEMA` | 45 | 1,208 |
| `schemas/ai/speech_text_segment_item.schema.json` | `CONTRACT_SCHEMA` | 79 | 1,864 |
| `schemas/ai/speech_timeline_input.schema.json` | `CONTRACT_SCHEMA` | 31 | 772 |
| `schemas/ai/speech_timeline_output.schema.json` | `CONTRACT_SCHEMA` | 38 | 999 |
| `schemas/ai/speech_to_text_input.schema.json` | `CONTRACT_SCHEMA` | 56 | 1,359 |
| `schemas/ai/split_speech_text_input.schema.json` | `CONTRACT_SCHEMA` | 50 | 1,277 |
| `schemas/ai/split_speech_text_output.schema.json` | `CONTRACT_SCHEMA` | 126 | 3,282 |
| `schemas/ai/stock_media_item.schema.json` | `CONTRACT_SCHEMA` | 118 | 2,497 |
| `schemas/ai/store_cache_input.schema.json` | `CONTRACT_SCHEMA` | 38 | 1,008 |
| `schemas/ai/store_cache_output.schema.json` | `CONTRACT_SCHEMA` | 44 | 1,112 |
| `schemas/ai/thumbnail_input.schema.json` | `CONTRACT_SCHEMA` | 60 | 1,520 |
| `schemas/ai/thumbnail_output.schema.json` | `CONTRACT_SCHEMA` | 52 | 1,261 |
| `schemas/ai/thumbnail_request.schema.json` | `CONTRACT_SCHEMA` | 60 | 1,520 |
| `schemas/ai/thumbnail_result.schema.json` | `CONTRACT_SCHEMA` | 52 | 1,261 |
| `schemas/ai/tool_call.schema.json` | `CONTRACT_SCHEMA` | 51 | 1,406 |
| `schemas/ai/tool_result.schema.json` | `CONTRACT_SCHEMA` | 160 | 4,359 |
| `schemas/ai/trace_span_record.schema.json` | `CONTRACT_SCHEMA` | 351 | 7,825 |
| `schemas/ai/trim_audio_input.schema.json` | `CONTRACT_SCHEMA` | 31 | 801 |
| `schemas/ai/trim_audio_output.schema.json` | `CONTRACT_SCHEMA` | 31 | 775 |
| `schemas/ai/trim_silence_input.schema.json` | `CONTRACT_SCHEMA` | 38 | 1,032 |
| `schemas/ai/trim_silence_output.schema.json` | `CONTRACT_SCHEMA` | 52 | 1,457 |
| `schemas/ai/trim_video_input.schema.json` | `CONTRACT_SCHEMA` | 38 | 975 |
| `schemas/ai/trim_video_output.schema.json` | `CONTRACT_SCHEMA` | 31 | 775 |
| `schemas/ai/tts_request.schema.json` | `CONTRACT_SCHEMA` | 73 | 1,579 |
| `schemas/ai/tts_result.schema.json` | `CONTRACT_SCHEMA` | 141 | 3,840 |
| `schemas/ai/upscale_image_input.schema.json` | `CONTRACT_SCHEMA` | 60 | 1,397 |
| `schemas/ai/upscale_image_output.schema.json` | `CONTRACT_SCHEMA` | 38 | 884 |
| `schemas/ai/upscale_request.schema.json` | `CONTRACT_SCHEMA` | 60 | 1,424 |
| `schemas/ai/upscale_result.schema.json` | `CONTRACT_SCHEMA` | 135 | 3,649 |
| `schemas/ai/usage_record.schema.json` | `CONTRACT_SCHEMA` | 158 | 3,722 |
| `schemas/ai/video_generation_request.schema.json` | `CONTRACT_SCHEMA` | 76 | 1,722 |
| `schemas/ai/video_generation_result.schema.json` | `CONTRACT_SCHEMA` | 155 | 4,117 |
| `schemas/ai/visual_intelligence.schema.json` | `CONTRACT_SCHEMA` | 755 | 20,964 |
| `schemas/ai/vocal_isolation_request.schema.json` | `CONTRACT_SCHEMA` | 30 | 832 |
| `schemas/ai/vocal_isolation_result.schema.json` | `CONTRACT_SCHEMA` | 147 | 3,898 |
| `schemas/blueprint.schema.json` | `CONTRACT_SCHEMA` | 578 | 16,499 |
| `schemas/brand.schema.json` | `CONTRACT_SCHEMA` | 63 | 2,232 |
| `schemas/creative/blueprint_compilation_result.schema.json` | `CONTRACT_SCHEMA` | 57 | 1,299 |
| `schemas/creative/candidate_gate_result.schema.json` | `CONTRACT_SCHEMA` | 66 | 1,643 |
| `schemas/creative/candidate_promotion_record.schema.json` | `CONTRACT_SCHEMA` | 143 | 4,107 |
| `schemas/creative/candidate_review_bundle.schema.json` | `CONTRACT_SCHEMA` | 144 | 4,169 |
| `schemas/creative/candidate_review_decision.schema.json` | `CONTRACT_SCHEMA` | 139 | 4,084 |
| `schemas/creative/candidate_validation_report.schema.json` | `CONTRACT_SCHEMA` | 271 | 7,498 |
| `schemas/creative/compose_component_ref.schema.json` | `CONTRACT_SCHEMA` | 39 | 1,053 |
| `schemas/creative/compose_evaluation_result.schema.json` | `CONTRACT_SCHEMA` | 192 | 5,560 |
| `schemas/creative/composition_layer.schema.json` | `CONTRACT_SCHEMA` | 33 | 873 |
| `schemas/creative/composition_plan.schema.json` | `CONTRACT_SCHEMA` | 128 | 3,447 |
| `schemas/creative/creative_brief.schema.json` | `CONTRACT_SCHEMA` | 423 | 12,050 |
| `schemas/creative/creative_case_grade.schema.json` | `CONTRACT_SCHEMA` | 142 | 3,697 |
| `schemas/creative/creative_conflict.schema.json` | `CONTRACT_SCHEMA` | 116 | 3,461 |
| `schemas/creative/creative_constraints.schema.json` | `CONTRACT_SCHEMA` | 116 | 2,893 |
| `schemas/creative/creative_contracts.schema.json` | `CONTRACT_SCHEMA` | 11,220 | 360,138 |
| `schemas/creative/creative_cost_audit_run.schema.json` | `CONTRACT_SCHEMA` | 223 | 6,391 |
| `schemas/creative/creative_eval_case.schema.json` | `CONTRACT_SCHEMA` | 349 | 9,268 |
| `schemas/creative/creative_eval_run.schema.json` | `CONTRACT_SCHEMA` | 191 | 5,099 |
| `schemas/creative/creative_feedback.schema.json` | `CONTRACT_SCHEMA` | 355 | 9,427 |
| `schemas/creative/creative_intent.schema.json` | `CONTRACT_SCHEMA` | 113 | 2,777 |
| `schemas/creative/creative_plan.schema.json` | `CONTRACT_SCHEMA` | 954 | 28,976 |
| `schemas/creative/creative_plan_validation_result.schema.json` | `CONTRACT_SCHEMA` | 40 | 991 |
| `schemas/creative/creative_project_cost_summary.schema.json` | `CONTRACT_SCHEMA` | 200 | 5,492 |
| `schemas/creative/creative_tier_decision.schema.json` | `CONTRACT_SCHEMA` | 455 | 13,274 |
| `schemas/creative/creative_usage_event.schema.json` | `CONTRACT_SCHEMA` | 309 | 7,193 |
| `schemas/creative/director_recommendation_bundle.schema.json` | `CONTRACT_SCHEMA` | 332 | 10,645 |
| `schemas/creative/effective_user_style.schema.json` | `CONTRACT_SCHEMA` | 293 | 7,395 |
| `schemas/creative/efficiency_finding.schema.json` | `CONTRACT_SCHEMA` | 113 | 2,912 |
| `schemas/creative/emotion_direction.schema.json` | `CONTRACT_SCHEMA` | 61 | 1,757 |
| `schemas/creative/feedback_classification.schema.json` | `CONTRACT_SCHEMA` | 206 | 5,423 |
| `schemas/creative/field_provenance.schema.json` | `CONTRACT_SCHEMA` | 54 | 1,290 |
| `schemas/creative/judge_calibration_record.schema.json` | `CONTRACT_SCHEMA` | 53 | 1,302 |
| `schemas/creative/knowledge_descriptor.schema.json` | `CONTRACT_SCHEMA` | 143 | 3,911 |
| `schemas/creative/motion_direction.schema.json` | `CONTRACT_SCHEMA` | 74 | 2,336 |
| `schemas/creative/narrative_beat.schema.json` | `CONTRACT_SCHEMA` | 80 | 2,103 |
| `schemas/creative/narrative_direction.schema.json` | `CONTRACT_SCHEMA` | 67 | 1,987 |
| `schemas/creative/narrative_plan.schema.json` | `CONTRACT_SCHEMA` | 209 | 5,990 |
| `schemas/creative/pairwise_grade_result.schema.json` | `CONTRACT_SCHEMA` | 43 | 1,100 |
| `schemas/creative/promotion_decision.schema.json` | `CONTRACT_SCHEMA` | 73 | 1,969 |
| `schemas/creative/promotion_manifest.schema.json` | `CONTRACT_SCHEMA` | 114 | 3,562 |
| `schemas/creative/recipe_definition.schema.json` | `CONTRACT_SCHEMA` | 395 | 10,805 |
| `schemas/creative/recipe_selection.schema.json` | `CONTRACT_SCHEMA` | 168 | 4,620 |
| `schemas/creative/recipe_stage.schema.json` | `CONTRACT_SCHEMA` | 126 | 3,500 |
| `schemas/creative/resolved_creative_guidance.schema.json` | `CONTRACT_SCHEMA` | 781 | 24,792 |
| `schemas/creative/resolved_template_decision.schema.json` | `CONTRACT_SCHEMA` | 33 | 825 |
| `schemas/creative/reuse_candidate_score.schema.json` | `CONTRACT_SCHEMA` | 52 | 1,450 |
| `schemas/creative/reuse_evaluation_result.schema.json` | `CONTRACT_SCHEMA` | 130 | 3,727 |
| `schemas/creative/scene_intent.schema.json` | `CONTRACT_SCHEMA` | 195 | 5,734 |
| `schemas/creative/sfx_direction.schema.json` | `CONTRACT_SCHEMA` | 75 | 1,938 |
| `schemas/creative/skill_definition.schema.json` | `CONTRACT_SCHEMA` | 211 | 5,930 |
| `schemas/creative/style_decision_trace.schema.json` | `CONTRACT_SCHEMA` | 108 | 2,660 |
| `schemas/creative/style_preference_provenance.schema.json` | `CONTRACT_SCHEMA` | 101 | 2,728 |
| `schemas/creative/taste_context.schema.json` | `CONTRACT_SCHEMA` | 928 | 27,432 |
| `schemas/creative/taste_decision.schema.json` | `CONTRACT_SCHEMA` | 76 | 2,226 |
| `schemas/creative/taste_rule.schema.json` | `CONTRACT_SCHEMA` | 120 | 3,489 |
| `schemas/creative/template_candidate.schema.json` | `CONTRACT_SCHEMA` | 290 | 8,352 |
| `schemas/creative/trace_assertion.schema.json` | `CONTRACT_SCHEMA` | 140 | 3,362 |
| `schemas/creative/trace_assertion_result.schema.json` | `CONTRACT_SCHEMA` | 34 | 806 |
| `schemas/creative/user_style_profile.schema.json` | `CONTRACT_SCHEMA` | 288 | 7,835 |
| `schemas/creative/validation_snapshot.schema.json` | `CONTRACT_SCHEMA` | 103 | 2,768 |
| `schemas/examples/prj_demo/blueprint.json` | `CONTRACT_SCHEMA` | 84 | 2,318 |
| `schemas/examples/prj_demo/brand.json` | `CONTRACT_SCHEMA` | 16 | 338 |
| `schemas/examples/prj_demo/manifest.json` | `CONTRACT_SCHEMA` | 78 | 1,869 |
| `schemas/examples/prj_demo/overrides.json` | `CONTRACT_SCHEMA` | 16 | 268 |
| `schemas/examples/prj_demo/project.json` | `CONTRACT_SCHEMA` | 15 | 378 |
| `schemas/examples/prj_demo/state.json` | `CONTRACT_SCHEMA` | 48 | 1,077 |
| `schemas/manifest.schema.json` | `CONTRACT_SCHEMA` | 79 | 2,861 |
| `schemas/manifest.v2.schema.json` | `CONTRACT_SCHEMA` | 106 | 3,847 |
| `schemas/overrides.schema.json` | `CONTRACT_SCHEMA` | 54 | 1,882 |
| `schemas/project.schema.json` | `CONTRACT_SCHEMA` | 114 | 3,654 |
| `schemas/state.schema.json` | `CONTRACT_SCHEMA` | 241 | 5,273 |
| `schemas/template_proposal_schema.json` | `CONTRACT_SCHEMA` | 94 | 3,065 |

</details>

### Subsystem: Developer & Maintenance Tooling (`dev_maintenance`)
- **File Count:** 145
- **Lines of Code:** 32,292
- **Critical Files:** 0

<details>
<summary>Click to expand all 145 files in dev_maintenance</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `scripts/archive/__init__.py` | `DEV_TOOLING` | 0 | 0 |
| `scripts/archive/classify_templates.py` | `DEV_TOOLING` | 226 | 8,551 |
| `scripts/archive/migrate_assets.py` | `DEV_TOOLING` | 86 | 2,854 |
| `scripts/archive/migrate_legacy_projects.py` | `DEV_TOOLING` | 108 | 3,730 |
| `scripts/archive/migrate_state.py` | `DEV_TOOLING` | 67 | 2,538 |
| `scripts/archive/phase13/baseline.ts` | `DEV_TOOLING` | 93 | 2,999 |
| `scripts/archive/phase13/coverage.ts` | `DEV_TOOLING` | 86 | 3,211 |
| `scripts/archive/phase13/prioritize.ts` | `DEV_TOOLING` | 78 | 2,684 |
| `scripts/archive/phase14/baseline.ts` | `DEV_TOOLING` | 46 | 1,482 |
| `scripts/archive/phase14/execution_bridge_audit.ts` | `DEV_TOOLING` | 106 | 4,007 |
| `scripts/archive/phase14/patch_candidates.ts` | `DEV_TOOLING` | 62 | 1,923 |
| `scripts/archive/phase14/prioritize.ts` | `DEV_TOOLING` | 40 | 1,428 |
| `scripts/archive/phase15/build_execution_cohorts.ts` | `DEV_TOOLING` | 72 | 2,845 |
| `scripts/archive/phase15/generate_sample_batch.ts` | `DEV_TOOLING` | 59 | 1,811 |
| `scripts/archive/phase15/validate_execution_contracts.ts` | `DEV_TOOLING` | 119 | 4,854 |
| `scripts/archive/phase15/validate_verification_integrity.ts` | `DEV_TOOLING` | 73 | 3,268 |
| `scripts/archive/phase16/build_16_3_coverage_report.ts` | `DEV_TOOLING` | 42 | 1,918 |
| `scripts/archive/phase16/build_blocked_inventory.ts` | `DEV_TOOLING` | 101 | 4,054 |
| `scripts/archive/phase16/build_phase_16_3_inventory.ts` | `DEV_TOOLING` | 71 | 2,942 |
| `scripts/archive/phase16/build_phase_16_4_analysis.ts` | `DEV_TOOLING` | 87 | 4,240 |
| `scripts/archive/phase16/build_phase_16_4_inventory.ts` | `DEV_TOOLING` | 45 | 1,676 |
| `scripts/archive/phase16/extract_proven_defaults.ts` | `DEV_TOOLING` | 101 | 4,601 |
| `scripts/archive/phase16/generate_16_3_runtime_batch.ts` | `DEV_TOOLING` | 62 | 1,714 |
| `scripts/archive/phase16/mine_adapter_families.ts` | `DEV_TOOLING` | 107 | 3,527 |
| `scripts/archive/phase16/rank_adapter_families.ts` | `DEV_TOOLING` | 57 | 2,117 |
| `scripts/archive/phase16/test_social_captions_adapter.ts` | `DEV_TOOLING` | 57 | 1,951 |
| `scripts/archive/phase16/validate_phase_16_2.ts` | `DEV_TOOLING` | 31 | 1,284 |
| `scripts/archive/phase16/validate_phase_16_3.ts` | `DEV_TOOLING` | 51 | 2,072 |
| `scripts/archive/smoke_crd019_templates.py` | `DEV_TOOLING` | 186 | 6,287 |
| `scripts/archive/smoke_crd020_temporal.py` | `DEV_TOOLING` | 251 | 9,337 |
| `scripts/archive/stitch_skill.py` | `DEV_TOOLING` | 88 | 5,588 |
| `scripts/assemble_m02_master_report.py` | `DEV_TOOLING` | 224 | 13,231 |
| `scripts/ci/ci_matrix.py` | `DEV_TOOLING` | 233 | 11,702 |
| `scripts/ci/run_required_checks.sh` | `DEV_TOOLING` | 250 | 7,720 |
| `scripts/ci_run_all.py` | `DEV_TOOLING` | 92 | 3,199 |
| `scripts/core/__init__.py` | `DEV_TOOLING` | 0 | 0 |
| `scripts/core/ai_cache_repository.py` | `DEV_TOOLING` | 525 | 22,698 |
| `scripts/core/ai_prompt_repository.py` | `DEV_TOOLING` | 245 | 9,383 |
| `scripts/core/ai_run_repository.py` | `DEV_TOOLING` | 1,219 | 48,872 |
| `scripts/core/ai_trace_repository.py` | `DEV_TOOLING` | 252 | 9,739 |
| `scripts/core/artifact_service.py` | `DEV_TOOLING` | 249 | 10,398 |
| `scripts/core/asset_cache.py` | `DEV_TOOLING` | 118 | 4,261 |
| `scripts/core/asset_lifecycle.py` | `DEV_TOOLING` | 142 | 5,596 |
| `scripts/core/asset_resolution.py` | `DEV_TOOLING` | 696 | 29,939 |
| `scripts/core/authoring_idempotency_repository.py` | `DEV_TOOLING` | 243 | 10,270 |
| `scripts/core/authority_matrix.py` | `DEV_TOOLING` | 636 | 31,559 |
| `scripts/core/blueprint_compiler.py` | `DEV_TOOLING` | 29 | 800 |
| `scripts/core/blueprint_errors.py` | `DEV_TOOLING` | 73 | 3,277 |
| `scripts/core/blueprint_loader.py` | `DEV_TOOLING` | 100 | 3,437 |
| `scripts/core/blueprint_migration.py` | `DEV_TOOLING` | 147 | 5,684 |
| `scripts/core/blueprint_model.py` | `DEV_TOOLING` | 157 | 6,158 |
| `scripts/core/blueprint_validator.py` | `DEV_TOOLING` | 161 | 7,405 |
| `scripts/core/budget_service.py` | `DEV_TOOLING` | 87 | 3,275 |
| `scripts/core/canonical_asset_repository.py` | `DEV_TOOLING` | 321 | 14,094 |
| `scripts/core/canonical_document_repository.py` | `DEV_TOOLING` | 393 | 16,555 |
| `scripts/core/database.py` | `DEV_TOOLING` | 812 | 31,802 |
| `scripts/core/dependency_graph.py` | `DEV_TOOLING` | 438 | 19,088 |
| `scripts/core/e2e_data_render.py` | `DEV_TOOLING` | 77 | 3,410 |
| `scripts/core/evidence_matrix.py` | `DEV_TOOLING` | 572 | 24,415 |
| `scripts/core/failure_injection.py` | `DEV_TOOLING` | 87 | 3,609 |
| `scripts/core/failure_model.py` | `DEV_TOOLING` | 589 | 29,348 |
| `scripts/core/idempotency_repository.py` | `DEV_TOOLING` | 214 | 9,721 |
| `scripts/core/idempotency_store.py` | `DEV_TOOLING` | 180 | 7,485 |
| `scripts/core/lifecycle_service.py` | `DEV_TOOLING` | 341 | 15,074 |
| `scripts/core/manifest_errors.py` | `DEV_TOOLING` | 67 | 2,577 |
| `scripts/core/manifest_loader.py` | `DEV_TOOLING` | 135 | 4,631 |
| `scripts/core/manifest_migration.py` | `DEV_TOOLING` | 262 | 9,198 |
| `scripts/core/manifest_model.py` | `DEV_TOOLING` | 220 | 7,357 |
| `scripts/core/manifest_validator.py` | `DEV_TOOLING` | 317 | 12,536 |
| `scripts/core/materializer.py` | `DEV_TOOLING` | 523 | 20,427 |
| `scripts/core/media_intelligence_repository.py` | `DEV_TOOLING` | 205 | 7,537 |
| `scripts/core/memory/__init__.py` | `DEV_TOOLING` | 9 | 285 |
| `scripts/core/memory/postgres_memory_repository.py` | `DEV_TOOLING` | 686 | 28,652 |
| `scripts/core/probe_planner.py` | `DEV_TOOLING` | 297 | 12,297 |
| `scripts/core/project_identity.py` | `DEV_TOOLING` | 128 | 4,870 |
| `scripts/core/recovery_engine.py` | `DEV_TOOLING` | 372 | 16,235 |
| `scripts/core/render_input.py` | `DEV_TOOLING` | 325 | 13,458 |
| `scripts/core/retry_policy.py` | `DEV_TOOLING` | 290 | 10,787 |
| `scripts/core/review_service.py` | `DEV_TOOLING` | 864 | 37,933 |
| `scripts/core/run_model.py` | `DEV_TOOLING` | 93 | 3,569 |
| `scripts/core/runtime_logger.py` | `DEV_TOOLING` | 235 | 9,194 |
| `scripts/core/session_manager.py` | `DEV_TOOLING` | 47 | 1,709 |
| `scripts/core/state_lock.py` | `DEV_TOOLING` | 98 | 3,275 |
| `scripts/core/state_model.py` | `DEV_TOOLING` | 344 | 14,982 |
| `scripts/core/state_store.py` | `DEV_TOOLING` | 558 | 24,112 |
| `scripts/core/storage/__init__.py` | `DEV_TOOLING` | 28 | 687 |
| `scripts/core/storage/storage_service.py` | `DEV_TOOLING` | 480 | 17,407 |
| `scripts/core/template_candidate_repository.py` | `DEV_TOOLING` | 871 | 38,865 |
| `scripts/core/template_contract.py` | `DEV_TOOLING` | 199 | 7,625 |
| `scripts/core/template_registry_publisher.py` | `DEV_TOOLING` | 596 | 28,845 |
| `scripts/core/tenant_model.py` | `DEV_TOOLING` | 135 | 5,244 |
| `scripts/execute_authoring_mutation.ts` | `DEV_TOOLING` | 226 | 7,365 |
| `scripts/generate_ai_contracts.py` | `DEV_TOOLING` | 2,066 | 56,726 |
| `scripts/generate_creative_contracts.py` | `DEV_TOOLING` | 1,232 | 37,715 |
| `scripts/governance/governance_audit.py` | `DEV_TOOLING` | 47 | 1,655 |
| `scripts/governance/simulate_ci_gate.ps1` | `DEV_TOOLING` | 0 | 2,877 |
| `scripts/maintenance/__init__.py` | `DEV_TOOLING` | 0 | 0 |
| `scripts/maintenance/auto_backup.py` | `DEV_TOOLING` | 32 | 1,191 |
| `scripts/maintenance/batch_builder.py` | `DEV_TOOLING` | 158 | 5,958 |
| `scripts/maintenance/check_orphans.py` | `DEV_TOOLING` | 36 | 1,439 |
| `scripts/maintenance/cleanup_assets.py` | `DEV_TOOLING` | 80 | 2,481 |
| `scripts/maintenance/generate_atlas_inventory.py` | `DEV_TOOLING` | 375 | 17,172 |
| `scripts/maintenance/generate_file_tree.py` | `DEV_TOOLING` | 166 | 9,693 |
| `scripts/maintenance/promote_template.py` | `DEV_TOOLING` | 127 | 5,577 |
| `scripts/maintenance/retier_docs.py` | `DEV_TOOLING` | 58 | 1,994 |
| `scripts/maintenance/scene_compiler.py` | `DEV_TOOLING` | 94 | 3,598 |
| `scripts/maintenance/setup_docker.py` | `DEV_TOOLING` | 26 | 945 |
| `scripts/maintenance/sync_templates.py` | `DEV_TOOLING` | 72 | 3,212 |
| `scripts/maintenance/template_router.py` | `DEV_TOOLING` | 88 | 3,077 |
| `scripts/maintenance/transcript_cleaner.py` | `DEV_TOOLING` | 160 | 6,602 |
| `scripts/maintenance/update_schema.py` | `DEV_TOOLING` | 23 | 741 |
| `scripts/metrics/__init__.py` | `DEV_TOOLING` | 0 | 0 |
| `scripts/metrics/benchmark_guards.py` | `DEV_TOOLING` | 33 | 992 |
| `scripts/metrics/health.py` | `DEV_TOOLING` | 71 | 2,603 |
| `scripts/metrics/metrics_collector.py` | `DEV_TOOLING` | 223 | 10,384 |
| `scripts/metrics/metrics_model.py` | `DEV_TOOLING` | 159 | 6,558 |
| `scripts/migration/tenant_project_migration.py` | `DEV_TOOLING` | 362 | 14,425 |
| `scripts/open_studio.py` | `DEV_TOOLING` | 137 | 5,685 |
| `scripts/remotion_interop/__init__.py` | `DEV_TOOLING` | 0 | 0 |
| `scripts/remotion_interop/analyze_adapter_families.ts` | `DEV_TOOLING` | 126 | 5,618 |
| `scripts/remotion_interop/build_video.ts` | `DEV_TOOLING` | 144 | 5,014 |
| `scripts/remotion_interop/certify_templates.ts` | `DEV_TOOLING` | 274 | 9,948 |
| `scripts/remotion_interop/enforce_contracts.ts` | `DEV_TOOLING` | 115 | 4,346 |
| `scripts/remotion_interop/infer_schemas_ast.ts` | `DEV_TOOLING` | 149 | 6,698 |
| `scripts/remotion_interop/tsconfig.json` | `DEV_TOOLING` | 13 | 300 |
| `scripts/render_via_adapter.ts` | `DEV_TOOLING` | 166 | 5,417 |
| `scripts/render_via_planner.ts` | `DEV_TOOLING` | 228 | 7,649 |
| `scripts/run_creative_cost_audit.py` | `DEV_TOOLING` | 499 | 18,782 |
| `scripts/run_creative_e2e.py` | `DEV_TOOLING` | 1,039 | 48,194 |
| `scripts/run_creative_regression.py` | `DEV_TOOLING` | 142 | 5,755 |
| `scripts/run_real_cost_performance_benchmark.py` | `DEV_TOOLING` | 235 | 9,896 |
| `scripts/scaffold_project.py` | `DEV_TOOLING` | 114 | 4,042 |
| `scripts/security/__init__.py` | `DEV_TOOLING` | 0 | 0 |
| `scripts/security/path_security.py` | `DEV_TOOLING` | 36 | 863 |
| `scripts/security/security.py` | `DEV_TOOLING` | 104 | 3,520 |
| `scripts/smoke_openrouter.py` | `DEV_TOOLING` | 171 | 6,656 |
| `scripts/testing/ai_test_accounting.py` | `DEV_TOOLING` | 352 | 15,516 |
| `scripts/testing/remotion_test_accounting.py` | `DEV_TOOLING` | 296 | 13,224 |
| `scripts/testing/s28_r15_soak_and_load_runner.py` | `DEV_TOOLING` | 674 | 29,613 |
| `scripts/verify/README.md` | `DEV_TOOLING` | 42 | 2,070 |
| `scripts/verify/contact-sheet.sh` | `DEV_TOOLING` | 17 | 868 |
| `scripts/verify/probe-mp4.sh` | `DEV_TOOLING` | 24 | 1,538 |
| `scripts/verify/seek-shot.sh` | `DEV_TOOLING` | 21 | 1,116 |
| `scripts/verify/verify_preview.py` | `DEV_TOOLING` | 263 | 9,490 |
| `scripts/worker.py` | `DEV_TOOLING` | 53 | 1,794 |

</details>

### Subsystem: Architecture Documentation & ADRs (`documentation_knowledge`)
- **File Count:** 298
- **Lines of Code:** 108,327
- **Critical Files:** 0

<details>
<summary>Click to expand all 298 files in documentation_knowledge</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `.github/pull_request_template.md` | `ARCHIVAL_DOC` | 48 | 985 |
| `BATCH_4_AGENTLESS_DEPENDENCY_ASSESSMENT.md` | `ARCHIVAL_DOC` | 119 | 11,962 |
| `BATCH_4_FINAL_ARCHITECTURAL_AUDIT.md` | `ARCHIVAL_DOC` | 99 | 8,951 |
| `BATCH_4_PRODUCT_E2E_VERIFICATION_REPORT.md` | `ARCHIVAL_DOC` | 164 | 12,684 |
| `BATCH_4_REMOTE_VERIFICATION_AND_OWNER_REVIEW.md` | `ARCHIVAL_DOC` | 315 | 27,597 |
| `README.md` | `ARCHIVAL_DOC` | 69 | 3,090 |
| `api/README.md` | `ARCHIVAL_DOC` | 56 | 1,615 |
| `docs/CI_RELEASE_GATES.md` | `ARCHIVAL_DOC` | 165 | 12,381 |
| `documentation/DEVELOPER_GUIDE.md` | `ARCHIVAL_DOC` | 39 | 1,619 |
| `documentation/EFFECTS_STATUS.md` | `ARCHIVAL_DOC` | 41 | 1,733 |
| `documentation/LIBRARY_STATUS.md` | `ARCHIVAL_DOC` | 104 | 5,767 |
| `documentation/PLUGIN_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 54 | 3,302 |
| `documentation/QUICK_START.md` | `ARCHIVAL_DOC` | 25 | 849 |
| `documentation/README.md` | `ARCHIVAL_DOC` | 83 | 6,717 |
| `documentation/USER_GUIDE.md` | `ARCHIVAL_DOC` | 26 | 1,696 |
| `documentation/architecture/ADR-004-ai-media-intelligence-platform.md` | `ARCHIVAL_DOC` | 164 | 11,489 |
| `documentation/architecture/ARCHITECTURE_TRUTH.md` | `ARCHIVAL_DOC` | 107 | 7,682 |
| `documentation/architecture/ARCHIVE_SCRIPTS_INVENTORY.md` | `ARCHIVAL_DOC` | 82 | 7,677 |
| `documentation/architecture/BLUEPRINT_V2_SPEC.md` | `ARCHIVAL_DOC` | 155 | 9,279 |
| `documentation/architecture/MANIFEST_V2_SPEC.md` | `ARCHIVAL_DOC` | 93 | 4,970 |
| `documentation/architecture/PROJECT_STRUCTURE.md` | `ARCHIVAL_DOC` | 3,615 | 175,755 |
| `documentation/architecture/S27.9-tool-registry-and-authorization.md` | `ARCHIVAL_DOC` | 107 | 5,281 |
| `documentation/architecture/S28-creative-intelligence-foundation.md` | `ARCHIVAL_DOC` | 148 | 13,108 |
| `documentation/architecture/TRUST_MODEL.md` | `ARCHIVAL_DOC` | 403 | 26,606 |
| `documentation/architecture/ai-contract-evolution-policy.md` | `ARCHIVAL_DOC` | 75 | 3,818 |
| `documentation/architecture/atlas/01_SYSTEM_OVERVIEW.md` | `ARCHIVAL_DOC` | 181 | 14,758 |
| `documentation/architecture/atlas/02_SUBSYSTEM_ATLAS.md` | `ARCHIVAL_DOC` | 462 | 28,531 |
| `documentation/architecture/atlas/03_FILE_INVENTORY.json` | `ARCHIVAL_DOC` | 26,302 | 891,611 |
| `documentation/architecture/atlas/03_FILE_INVENTORY.md` | `ARCHIVAL_DOC` | 3,890 | 442,365 |
| `documentation/architecture/atlas/04_EXECUTION_GRAPHS.md` | `ARCHIVAL_DOC` | 365 | 14,818 |
| `documentation/architecture/atlas/05_TROUBLESHOOTING_GUIDE.md` | `ARCHIVAL_DOC` | 195 | 9,990 |
| `documentation/architecture/atlas/06_LEARNING_ROADMAP.md` | `ARCHIVAL_DOC` | 186 | 10,720 |
| `documentation/architecture/decisions/ADR-001-single-host-api-worker.md` | `ARCHIVAL_DOC` | 114 | 8,888 |
| `documentation/architecture/decisions/ADR-002-principal-and-authorization-model.md` | `ARCHIVAL_DOC` | 123 | 8,906 |
| `documentation/architecture/decisions/ADR-003-multi-tenant-saas-foundation.md` | `ARCHIVAL_DOC` | 71 | 4,051 |
| `documentation/architecture/decisions/ADR-004-ai-media-intelligence-platform.md` | `ARCHIVAL_DOC` | 164 | 11,489 |
| `documentation/archive/ARCHITECTURE_v1.md` | `ARCHIVAL_DOC` | 100 | 3,296 |
| `documentation/archive/SYSTEM_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 104 | 5,017 |
| `documentation/archive/SYSTEM_OVERVIEW.md` | `ARCHIVAL_DOC` | 42 | 2,328 |
| `documentation/archive/WORKSPACE_COMPREHENSIVE_GUIDE.md` | `ARCHIVAL_DOC` | 1,286 | 153,118 |
| `documentation/archive/WORKSPACE_PIPELINE_EXPLAINED.md` | `ARCHIVAL_DOC` | 310 | 28,769 |
| `documentation/archive/project_overview.md` | `ARCHIVAL_DOC` | 2,476 | 157,440 |
| `documentation/audits/AUDIT_REPORT.md` | `ARCHIVAL_DOC` | 60 | 4,604 |
| `documentation/audits/CONFLICTS.md` | `ARCHIVAL_DOC` | 19 | 2,746 |
| `documentation/audits/DECISIONS.md` | `ARCHIVAL_DOC` | 23 | 2,486 |
| `documentation/audits/EDGE_CASES_REPORT.md` | `ARCHIVAL_DOC` | 76 | 6,929 |
| `documentation/audits/FINAL_AUDIT_REPORT.md` | `ARCHIVAL_DOC` | 46 | 4,183 |
| `documentation/audits/FINAL_CHECKLIST.md` | `ARCHIVAL_DOC` | 28 | 2,513 |
| `documentation/audits/HEALTH.md` | `ARCHIVAL_DOC` | 25 | 1,826 |
| `documentation/audits/INTEGRATION_TEST_REPORT.md` | `ARCHIVAL_DOC` | 9 | 1,011 |
| `documentation/audits/INVENTORY.md` | `ARCHIVAL_DOC` | 61 | 3,286 |
| `documentation/audits/PRE_S25_FULL_VERIFICATION_REPORT.md` | `ARCHIVAL_DOC` | 501 | 30,440 |
| `documentation/audits/PROJECT_AUDIT_REPORT.md` | `ARCHIVAL_DOC` | 138 | 13,816 |
| `documentation/audits/PROJECT_RECONNAISSANCE.md` | `ARCHIVAL_DOC` | 305 | 15,507 |
| `documentation/audits/S27-ai-baseline-inventory.md` | `ARCHIVAL_DOC` | 171 | 17,768 |
| `documentation/audits/S28-02-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 340 | 29,083 |
| `documentation/audits/S28-02A-HYBRID-RETRIEVAL-DELTA-REPORT.md` | `ARCHIVAL_DOC` | 176 | 13,046 |
| `documentation/audits/S28-03-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 253 | 17,559 |
| `documentation/audits/S28-03A-EXIT-GATE-EVIDENCE-DELTA-REPORT.md` | `ARCHIVAL_DOC` | 305 | 22,073 |
| `documentation/audits/S28-04-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 221 | 14,340 |
| `documentation/audits/S28-04A-FINAL-EVIDENCE-DELTA-REPORT.md` | `ARCHIVAL_DOC` | 335 | 22,126 |
| `documentation/audits/S28-05-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 334 | 22,278 |
| `documentation/audits/S28-06-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 283 | 23,586 |
| `documentation/audits/S28-06A-FINAL-EVIDENCE-DELTA-REPORT.md` | `ARCHIVAL_DOC` | 185 | 16,948 |
| `documentation/audits/S28-07A-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 191 | 13,112 |
| `documentation/audits/S28-07B-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 254 | 16,454 |
| `documentation/audits/S28-07C-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 223 | 12,503 |
| `documentation/audits/S28-07D-EXECUTION-EVIDENCE-REPORT.md` | `ARCHIVAL_DOC` | 295 | 15,144 |
| `documentation/audits/SYSTEM_HEALTH_REPORT.md` | `ARCHIVAL_DOC` | 74 | 7,123 |
| `documentation/audits/TEMPLATE_DISCOVERY.md` | `ARCHIVAL_DOC` | 462 | 44,423 |
| `documentation/audits/TOOL_USAGE_AUDIT.md` | `ARCHIVAL_DOC` | 37 | 1,869 |
| `documentation/audits/actual_templates_list.txt` | `ARCHIVAL_DOC` | 104 | 3,823 |
| `documentation/audits/audit_pack.txt` | `ARCHIVAL_DOC` | 1,472 | 52,637 |
| `documentation/audits/benchmark_real_performance_results.json` | `ARCHIVAL_DOC` | 19 | 737 |
| `documentation/audits/creative_cost_audit.json` | `ARCHIVAL_DOC` | 100 | 3,121 |
| `documentation/audits/creative_regression_run.json` | `ARCHIVAL_DOC` | 129 | 2,608 |
| `documentation/audits/s28_02_eval_report.json` | `ARCHIVAL_DOC` | 435 | 13,013 |
| `documentation/audits/s28_03_intent_eval_report.json` | `ARCHIVAL_DOC` | 20 | 479 |
| `documentation/audits/s28_03_recipe_eval_report.json` | `ARCHIVAL_DOC` | 8 | 162 |
| `documentation/audits/s28_03a_recipe_compliance_report.json` | `ARCHIVAL_DOC` | 370 | 12,744 |
| `documentation/audits/s28_04_creative_eval_report.json` | `ARCHIVAL_DOC` | 254 | 7,611 |
| `documentation/audits/s28_05_planner_eval_report.json` | `ARCHIVAL_DOC` | 138 | 4,230 |
| `documentation/audits/s28_06_eval_report.json` | `ARCHIVAL_DOC` | 299 | 9,445 |
| `documentation/audits/s28_full_creative_e2e_run.json` | `ARCHIVAL_DOC` | 281 | 8,954 |
| `documentation/audits/s28_legacy_creative_inventory.json` | `ARCHIVAL_DOC` | 1,022 | 48,390 |
| `documentation/audits/s28_legacy_creative_inventory.md` | `ARCHIVAL_DOC` | 154 | 26,196 |
| `documentation/governance/ARCHITECTURE_CHANGE_CONTROL.md` | `ARCHIVAL_DOC` | 36 | 1,403 |
| `documentation/governance/CHANGE_POLICY.md` | `ARCHIVAL_DOC` | 44 | 1,676 |
| `documentation/governance/DEFECT_POLICY.md` | `ARCHIVAL_DOC` | 35 | 1,485 |
| `documentation/governance/DEPENDENCY_POLICY.md` | `ARCHIVAL_DOC` | 21 | 1,476 |
| `documentation/governance/required-checks.md` | `ARCHIVAL_DOC` | 36 | 2,938 |
| `documentation/guides/DATA_DRIVEN_MIGRATION.md` | `ARCHIVAL_DOC` | 26 | 2,988 |
| `documentation/guides/SECURITY_PATCH_NOTES.md` | `ARCHIVAL_DOC` | 154 | 11,566 |
| `documentation/guides/UPGRADE_NOTES.md` | `ARCHIVAL_DOC` | 33 | 3,300 |
| `documentation/remediation/S00_BASELINE_REPORT.md` | `ARCHIVAL_DOC` | 324 | 46,262 |
| `documentation/remediation/S25_FAULT_INJECTION_REPORT.md` | `ARCHIVAL_DOC` | 103 | 11,428 |
| `documentation/remediation/S25_FINAL_ARCHITECTURE_REAUDIT.md` | `ARCHIVAL_DOC` | 128 | 9,250 |
| `documentation/remediation/S25_VERIFICATION_MATRIX.md` | `ARCHIVAL_DOC` | 58 | 11,440 |
| `documentation/remediation/S26_GOVERNANCE_CLOSURE_REPORT.md` | `ARCHIVAL_DOC` | 197 | 11,330 |
| `documentation/remediation/S26_PRODUCTION_GATE.md` | `ARCHIVAL_DOC` | 53 | 6,356 |
| `documentation/remediation/S26_REQUIRED_CHECKS_MATRIX.md` | `ARCHIVAL_DOC` | 78 | 5,691 |
| `documentation/remediation/pr_001_authentication_hardening/PR_001_COMPLETE_REPORT.txt` | `ARCHIVAL_DOC` | 332 | 20,882 |
| `documentation/remediation/pr_001_authentication_hardening/PR_001_IMPLEMENTATION_REPORT.md` | `ARCHIVAL_DOC` | 87 | 8,235 |
| `documentation/remediation/pr_001_authentication_hardening/PR_001_REVIEW_AND_ROLLBACK.md` | `ARCHIVAL_DOC` | 89 | 4,952 |
| `documentation/remediation/pr_001_authentication_hardening/PR_001_TEST_EVIDENCE.md` | `ARCHIVAL_DOC` | 124 | 6,497 |
| `documentation/remediation/pr_003_ai_runtime_vertical_slice/PR_003_IMPLEMENTATION_AND_TEST_REPORT.md` | `ARCHIVAL_DOC` | 276 | 17,151 |
| `documentation/s28/evidence/S28-01_REPORT.md` | `ARCHIVAL_DOC` | 154 | 26,196 |
| `documentation/s28/evidence/S28-02_REPORT.md` | `ARCHIVAL_DOC` | 340 | 29,083 |
| `documentation/s28/evidence/S28-03_REPORT.md` | `ARCHIVAL_DOC` | 253 | 17,559 |
| `documentation/s28/evidence/S28-04_REPORT.md` | `ARCHIVAL_DOC` | 221 | 14,340 |
| `documentation/s28/evidence/S28-05_REPORT.md` | `ARCHIVAL_DOC` | 334 | 22,278 |
| `documentation/s28/evidence/S28-06_REPORT.md` | `ARCHIVAL_DOC` | 283 | 23,586 |
| `documentation/s28/evidence/S28-07A_REPORT.md` | `ARCHIVAL_DOC` | 191 | 13,112 |
| `documentation/s28/evidence/S28-07B_REPORT.md` | `ARCHIVAL_DOC` | 254 | 16,454 |
| `documentation/s28/evidence/S28-07C_REPORT.md` | `ARCHIVAL_DOC` | 223 | 12,826 |
| `documentation/s28/evidence/S28-07D_REPORT.md` | `ARCHIVAL_DOC` | 295 | 15,125 |
| `documentation/s28/evidence/S28-07E_REPORT.md` | `ARCHIVAL_DOC` | 311 | 17,136 |
| `documentation/s28/evidence/S28-07F_REPORT.md` | `ARCHIVAL_DOC` | 262 | 15,586 |
| `documentation/s28/evidence/S28-07_FINAL_REPORT.md` | `ARCHIVAL_DOC` | 191 | 11,695 |
| `documentation/s28/evidence/S28-08A_REPORT.md` | `ARCHIVAL_DOC` | 294 | 20,450 |
| `documentation/s28/evidence/S28-08B_REPORT.md` | `ARCHIVAL_DOC` | 300 | 20,103 |
| `documentation/s28/evidence/S28-08C_REPORT.md` | `ARCHIVAL_DOC` | 567 | 33,368 |
| `documentation/s28/evidence/S28-08D_REPORT.md` | `ARCHIVAL_DOC` | 499 | 43,553 |
| `documentation/s28/evidence/S28-08E_REPORT.md` | `ARCHIVAL_DOC` | 209 | 15,694 |
| `documentation/s28/evidence/S28_FINAL_REPORT.md` | `ARCHIVAL_DOC` | 244 | 18,341 |
| `documentation/s28/evidence/S28_LEGACY_RETIREMENT.md` | `ARCHIVAL_DOC` | 222 | 31,276 |
| `documentation/s28/evidence/testbeds/creative_datasets_s28_06.py` | `ARCHIVAL_DOC` | 441 | 21,385 |
| `documentation/s28/evidence/testbeds/creative_evals_s28_05.py` | `ARCHIVAL_DOC` | 429 | 18,313 |
| `documentation/s28/evidence/testbeds/creative_evals_s28_06.py` | `ARCHIVAL_DOC` | 382 | 14,699 |
| `documentation/s28h/AI_AUTHORITY_MATRIX.md` | `ARCHIVAL_DOC` | 85 | 12,027 |
| `documentation/s28h/AI_OVERLAP_FINDINGS.md` | `ARCHIVAL_DOC` | 277 | 20,074 |
| `documentation/s28h/AI_PACKAGE_DEPENDENCY_GRAPH.md` | `ARCHIVAL_DOC` | 165 | 9,831 |
| `documentation/s28h/AI_PACKAGE_INVENTORY.md` | `ARCHIVAL_DOC` | 931 | 55,876 |
| `documentation/s28h/AI_RESTRUCTURE_PROPOSAL.md` | `ARCHIVAL_DOC` | 145 | 9,851 |
| `documentation/s28h/evidence/S28-H01_REPORT.md` | `ARCHIVAL_DOC` | 147 | 9,038 |
| `documentation/s28h/evidence/S28-H02_REPORT.md` | `ARCHIVAL_DOC` | 230 | 17,747 |
| `documentation/s28h/evidence/S28-H03_REPORT.md` | `ARCHIVAL_DOC` | 231 | 16,804 |
| `documentation/s28m/CAPABILITY_AUTHORITY_MATRIX.md` | `ARCHIVAL_DOC` | 69 | 10,757 |
| `documentation/s28m/CAPABILITY_CATALOG.json` | `ARCHIVAL_DOC` | 2,282 | 91,544 |
| `documentation/s28m/CAPABILITY_PARITY_MATRIX.json` | `ARCHIVAL_DOC` | 1,034 | 36,394 |
| `documentation/s28m/CAPABILITY_ROUTING_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 221 | 11,148 |
| `documentation/s28m/CAPABILITY_RUNTIME_MATRIX.md` | `ARCHIVAL_DOC` | 117 | 17,741 |
| `documentation/s28m/CAPABILITY_TAXONOMY.md` | `ARCHIVAL_DOC` | 280 | 21,346 |
| `documentation/s28m/EMBEDDED_MODEL_INVENTORY.json` | `ARCHIVAL_DOC` | 159 | 8,165 |
| `documentation/s28m/FAULT_INJECTION_MATRIX.json` | `ARCHIVAL_DOC` | 146 | 7,876 |
| `documentation/s28m/FINAL_ARCHITECTURE_AUDIT.json` | `ARCHIVAL_DOC` | 290 | 12,542 |
| `documentation/s28m/FINAL_ARCHITECTURE_SEARCH.md` | `ARCHIVAL_DOC` | 153 | 8,944 |
| `documentation/s28m/FINAL_CAPABILITY_MATRIX.json` | `ARCHIVAL_DOC` | 747 | 31,164 |
| `documentation/s28m/LEGACY_TOOL_MIGRATION_MAP.json` | `ARCHIVAL_DOC` | 1,332 | 47,671 |
| `documentation/s28m/MCP_COMPATIBILITY_MATRIX.json` | `ARCHIVAL_DOC` | 494 | 23,020 |
| `documentation/s28m/MCP_DEPENDENCY_GRAPH.md` | `ARCHIVAL_DOC` | 242 | 12,706 |
| `documentation/s28m/MCP_REALITY_INVENTORY.json` | `ARCHIVAL_DOC` | 475 | 17,037 |
| `documentation/s28m/MCP_TOOL_MATRIX.md` | `ARCHIVAL_DOC` | 655 | 45,650 |
| `documentation/s28m/PERFORMANCE_BASELINE.json` | `ARCHIVAL_DOC` | 80 | 2,308 |
| `documentation/s28m/PRODUCT_E2E_MATRIX.json` | `ARCHIVAL_DOC` | 667 | 21,846 |
| `documentation/s28m/S28-M02_MASTER_REPORT.md` | `ARCHIVAL_DOC` | 1,921 | 138,101 |
| `documentation/s28m/S28-M_FINAL_REPORT.md` | `ARCHIVAL_DOC` | 257 | 14,203 |
| `documentation/s28m/STT_MODEL_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 185 | 8,418 |
| `documentation/s28m/STT_PARITY_MATRIX.md` | `ARCHIVAL_DOC` | 105 | 10,106 |
| `documentation/s28m/evidence/S28-M01_REPORT.md` | `ARCHIVAL_DOC` | 345 | 21,266 |
| `documentation/s28m/evidence/S28-M02.1_REPORT.md` | `ARCHIVAL_DOC` | 264 | 24,261 |
| `documentation/s28m/evidence/S28-M02_REPORT.md` | `ARCHIVAL_DOC` | 316 | 25,985 |
| `documentation/s28m/evidence/S28-M03_REPORT.md` | `ARCHIVAL_DOC` | 143 | 9,204 |
| `documentation/s28m/evidence/S28-M03_VERIFICATION_CLOSURE.md` | `ARCHIVAL_DOC` | 387 | 23,243 |
| `documentation/s28m/evidence/S28-M04.1_REPORT.md` | `ARCHIVAL_DOC` | 194 | 11,516 |
| `documentation/s28m/evidence/S28-M04_REPORT.md` | `ARCHIVAL_DOC` | 121 | 9,151 |
| `documentation/s28m/evidence/S28-M04_VERIFICATION_CLOSURE.md` | `ARCHIVAL_DOC` | 205 | 11,115 |
| `documentation/s28m/evidence/S28-M05-C_CLOSURE_REPORT.md` | `ARCHIVAL_DOC` | 211 | 17,881 |
| `documentation/s28m/evidence/S28-M05_REPORT.md` | `ARCHIVAL_DOC` | 167 | 17,374 |
| `documentation/s28m/evidence/S28-M06_REPORT.md` | `ARCHIVAL_DOC` | 163 | 16,976 |
| `documentation/s28m/evidence/S28-M07_REPORT.md` | `ARCHIVAL_DOC` | 175 | 17,373 |
| `documentation/s28m/evidence/S28-M08_REPORT.md` | `ARCHIVAL_DOC` | 248 | 20,460 |
| `documentation/s28m/evidence/S28-M09_REPORT.md` | `ARCHIVAL_DOC` | 313 | 21,476 |
| `documentation/s28m/evidence/S28-M10_REPORT.md` | `ARCHIVAL_DOC` | 256 | 20,412 |
| `documentation/s28m/evidence/S28-M11_REPORT.md` | `ARCHIVAL_DOC` | 139 | 10,018 |
| `documentation/s28m/evidence/S28-M_FINAL_EVIDENCE_CLOSURE.md` | `ARCHIVAL_DOC` | 137 | 9,180 |
| `documentation/s28r/AI_MUTATION_MODEL.md` | `ARCHIVAL_DOC` | 111 | 5,848 |
| `documentation/s28r/AI_USER_EDITING_RULES.md` | `ARCHIVAL_DOC` | 69 | 3,734 |
| `documentation/s28r/ALTERNATIVE_RENDERER_ADAPTER.md` | `ARCHIVAL_DOC` | 130 | 7,167 |
| `documentation/s28r/AUDIO_PREVIEW_RUNTIME.md` | `ARCHIVAL_DOC` | 108 | 5,660 |
| `documentation/s28r/AUDIO_SYNC_MODEL.md` | `ARCHIVAL_DOC` | 113 | 5,272 |
| `documentation/s28r/AUTHORITY_MATRIX.md` | `ARCHIVAL_DOC` | 183 | 19,038 |
| `documentation/s28r/BROWSER_LIVE_PREVIEW_RUNTIME.md` | `ARCHIVAL_DOC` | 121 | 7,207 |
| `documentation/s28r/CANONICAL_MUTATION_MODEL.md` | `ARCHIVAL_DOC` | 133 | 8,445 |
| `documentation/s28r/CANONICAL_NORMALIZATION.md` | `ARCHIVAL_DOC` | 184 | 8,271 |
| `documentation/s28r/CANONICAL_TIMELINE_MODEL.md` | `ARCHIVAL_DOC` | 128 | 6,937 |
| `documentation/s28r/CANONICAL_VIDEO_CONTRACT.md` | `ARCHIVAL_DOC` | 223 | 10,875 |
| `documentation/s28r/CONTRACT_DEPENDENCY_RULES.md` | `ARCHIVAL_DOC` | 151 | 7,475 |
| `documentation/s28r/CREATIVEPLAN_TO_EDITABLE_DOCUMENT.md` | `ARCHIVAL_DOC` | 85 | 4,408 |
| `documentation/s28r/CURRENT_PREVIEW_FLOW.md` | `ARCHIVAL_DOC` | 69 | 5,829 |
| `documentation/s28r/CURRENT_RENDER_FLOW.md` | `ARCHIVAL_DOC` | 98 | 7,186 |
| `documentation/s28r/EDITOR_REVISION_MODEL.md` | `ARCHIVAL_DOC` | 154 | 6,833 |
| `documentation/s28r/ENGINE_NEUTRAL_TEMPLATE_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 120 | 6,178 |
| `documentation/s28r/FRAME_EVALUATION_MODEL.md` | `ARCHIVAL_DOC` | 76 | 2,965 |
| `documentation/s28r/FUTURE_ARCHITECTURE_GUARDS.md` | `ARCHIVAL_DOC` | 102 | 4,418 |
| `documentation/s28r/INTERMEDIATE_ARTIFACT_MODEL.md` | `ARCHIVAL_DOC` | 92 | 4,362 |
| `documentation/s28r/KEYFRAME_ANIMATION_MODEL.md` | `ARCHIVAL_DOC` | 89 | 4,742 |
| `documentation/s28r/LAYER_MODEL.md` | `ARCHIVAL_DOC` | 129 | 4,606 |
| `documentation/s28r/MASTER_COMPOSITOR_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 93 | 6,949 |
| `documentation/s28r/MULTI_ENGINE_EXECUTION.md` | `ARCHIVAL_DOC` | 73 | 3,581 |
| `documentation/s28r/MUTATION_INVALIDATION_MODEL.md` | `ARCHIVAL_DOC` | 112 | 4,854 |
| `documentation/s28r/OUTPUT_NORMALIZATION_MODEL.md` | `ARCHIVAL_DOC` | 92 | 4,224 |
| `documentation/s28r/PREVIEW_CACHE_INVALIDATION.md` | `ARCHIVAL_DOC` | 133 | 6,318 |
| `documentation/s28r/PREVIEW_FIDELITY_MODEL.md` | `ARCHIVAL_DOC` | 142 | 8,146 |
| `documentation/s28r/PREVIEW_PROXY_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 164 | 9,668 |
| `documentation/s28r/R02_MIGRATION_MAP.md` | `ARCHIVAL_DOC` | 97 | 9,481 |
| `documentation/s28r/R03_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 25 | 2,609 |
| `documentation/s28r/R04_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 36 | 3,255 |
| `documentation/s28r/R07B_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 99 | 8,804 |
| `documentation/s28r/R08_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 46 | 3,685 |
| `documentation/s28r/R09_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 104 | 6,604 |
| `documentation/s28r/R10_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 90 | 6,854 |
| `documentation/s28r/R11_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 46 | 3,845 |
| `documentation/s28r/R12_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 47 | 4,250 |
| `documentation/s28r/R13_COMPATIBILITY_MAP.md` | `ARCHIVAL_DOC` | 41 | 3,191 |
| `documentation/s28r/REMOTION_COUPLING_INVENTORY.json` | `ARCHIVAL_DOC` | 613 | 31,406 |
| `documentation/s28r/REMOTION_LOCKIN_SCORECARD.md` | `ARCHIVAL_DOC` | 51 | 5,334 |
| `documentation/s28r/REMOTION_RENDERER_ADAPTER.md` | `ARCHIVAL_DOC` | 151 | 8,781 |
| `documentation/s28r/RENDERER_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 127 | 7,208 |
| `documentation/s28r/RENDERER_CAPABILITY_MODEL.md` | `ARCHIVAL_DOC` | 110 | 7,017 |
| `documentation/s28r/RENDERER_REGISTRY_MODEL.md` | `ARCHIVAL_DOC` | 93 | 3,493 |
| `documentation/s28r/RENDER_EDITOR_DEPENDENCY_GRAPH.md` | `ARCHIVAL_DOC` | 174 | 8,108 |
| `documentation/s28r/RENDER_GRAPH_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 133 | 8,531 |
| `documentation/s28r/RENDER_PLANNER_MODEL.md` | `ARCHIVAL_DOC` | 83 | 4,560 |
| `documentation/s28r/RENDER_PLANNING_POLICY.md` | `ARCHIVAL_DOC` | 94 | 3,464 |
| `documentation/s28r/S28-R14_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 182 | 12,753 |
| `documentation/s28r/S28-R14_REPORT.md` | `ARCHIVAL_DOC` | 184 | 17,392 |
| `documentation/s28r/S28-R15_EVIDENCE_PART_1_2.md` | `ARCHIVAL_DOC` | 134 | 18,409 |
| `documentation/s28r/S28-R15_REPORT.md` | `ARCHIVAL_DOC` | 159 | 10,886 |
| `documentation/s28r/S28-R_ARCHITECTURE_BASELINE.md` | `ARCHIVAL_DOC` | 169 | 11,515 |
| `documentation/s28r/S28-R_FINAL_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 84 | 4,345 |
| `documentation/s28r/S28-R_FINAL_REPORT.md` | `ARCHIVAL_DOC` | 220 | 12,441 |
| `documentation/s28r/TEMPLATE_INVENTORY_S28_R05.json` | `ARCHIVAL_DOC` | 6,646 | 192,502 |
| `documentation/s28r/TEMPLATE_RUNTIME_MATRIX.md` | `ARCHIVAL_DOC` | 109 | 7,888 |
| `documentation/s28r/TIMEBASE_AND_DURATION_SEMANTICS.md` | `ARCHIVAL_DOC` | 61 | 3,277 |
| `documentation/s28r/UNDO_REDO_MODEL.md` | `ARCHIVAL_DOC` | 171 | 8,228 |
| `documentation/s28r/UNIFIED_AUTHORING_ARCHITECTURE.md` | `ARCHIVAL_DOC` | 127 | 9,421 |
| `documentation/s28r/WAVEFORM_MODEL.md` | `ARCHIVAL_DOC` | 90 | 3,688 |
| `documentation/s28r/evidence/R15_BASELINE.md` | `ARCHIVAL_DOC` | 40 | 2,555 |
| `documentation/s28r/evidence/R15_FAULT_MATRIX.md` | `ARCHIVAL_DOC` | 24 | 5,103 |
| `documentation/s28r/evidence/R15_FINAL_AUDIT.md` | `ARCHIVAL_DOC` | 76 | 7,620 |
| `documentation/s28r/evidence/R15_LOAD_SOAK_RESULTS.md` | `ARCHIVAL_DOC` | 86 | 8,343 |
| `documentation/s28r/evidence/R15_MIGRATION_PARITY_MATRIX.md` | `ARCHIVAL_DOC` | 44 | 3,500 |
| `documentation/s28r/evidence/S28-R01_REPORT.md` | `ARCHIVAL_DOC` | 256 | 21,475 |
| `documentation/s28r/evidence/S28-R02_REPORT.md` | `ARCHIVAL_DOC` | 204 | 13,068 |
| `documentation/s28r/evidence/S28-R03_REPORT.md` | `ARCHIVAL_DOC` | 197 | 12,640 |
| `documentation/s28r/evidence/S28-R04-PART1_REPORT.md` | `ARCHIVAL_DOC` | 136 | 8,579 |
| `documentation/s28r/evidence/S28-R04_REPORT.md` | `ARCHIVAL_DOC` | 137 | 9,427 |
| `documentation/s28r/evidence/S28-R05_REPORT.md` | `ARCHIVAL_DOC` | 314 | 19,493 |
| `documentation/s28r/evidence/S28-R06_REPORT.md` | `ARCHIVAL_DOC` | 211 | 12,079 |
| `documentation/s28r/evidence/S28-R07B_REPORT.md` | `ARCHIVAL_DOC` | 160 | 11,457 |
| `documentation/s28r/evidence/S28-R07_REPORT.md` | `ARCHIVAL_DOC` | 185 | 11,514 |
| `documentation/s28r/evidence/S28-R08_REPORT.md` | `ARCHIVAL_DOC` | 170 | 11,853 |
| `documentation/s28r/evidence/S28-R09_REPORT.md` | `ARCHIVAL_DOC` | 110 | 8,262 |
| `documentation/s28r/evidence/S28-R10_REPORT.md` | `ARCHIVAL_DOC` | 153 | 8,649 |
| `documentation/s28r/evidence/S28-R11_REPORT.md` | `ARCHIVAL_DOC` | 119 | 8,856 |
| `documentation/s28r/evidence/S28-R12_REPORT.md` | `ARCHIVAL_DOC` | 104 | 7,166 |
| `documentation/s28r/evidence/S28-R13_REPORT.md` | `ARCHIVAL_DOC` | 105 | 7,956 |
| `documentation/s28r/evidence/S28-R14_REPORT.md` | `ARCHIVAL_DOC` | 170 | 15,483 |
| `documentation/s28r/evidence/soak_telemetry_30m.json` | `ARCHIVAL_DOC` | 529 | 14,150 |
| `documentation/tools/breakdown.py` | `ARCHIVAL_DOC` | 38 | 1,724 |
| `documentation/tools/build_massive_report.py` | `ARCHIVAL_DOC` | 146 | 14,066 |
| `documentation/tools/generate_overview.py` | `ARCHIVAL_DOC` | 105 | 3,480 |
| `documentation/tools/print_orphans.py` | `ARCHIVAL_DOC` | 38 | 1,733 |
| `references/1_playbooks/ffmpeg_recipes.md` | `ARCHIVAL_DOC` | 426 | 13,859 |
| `references/1_playbooks/hook_playbook_article_sprint.md` | `ARCHIVAL_DOC` | 272 | 23,691 |
| `references/1_playbooks/living_canvas.md` | `ARCHIVAL_DOC` | 683 | 39,218 |
| `references/1_playbooks/motion_collage.md` | `ARCHIVAL_DOC` | 234 | 11,594 |
| `references/1_playbooks/review_video.md` | `ARCHIVAL_DOC` | 155 | 10,947 |
| `references/1_playbooks/tabletop_explainer.md` | `ARCHIVAL_DOC` | 111 | 8,093 |
| `references/1_playbooks/video_copy.md` | `ARCHIVAL_DOC` | 376 | 21,222 |
| `references/2_sops/hyperrealistic_image.md` | `ARCHIVAL_DOC` | 395 | 25,415 |
| `references/2_sops/plan_template.md` | `ARCHIVAL_DOC` | 95 | 4,305 |
| `references/2_sops/seedance_avatar.md` | `ARCHIVAL_DOC` | 97 | 9,809 |
| `references/2_sops/spoken_vo_humanizer.md` | `ARCHIVAL_DOC` | 88 | 10,301 |
| `references/2_sops/template_proposal.md` | `ARCHIVAL_DOC` | 141 | 4,157 |
| `references/3_engineering/remotion_guide.md` | `ARCHIVAL_DOC` | 142 | 7,064 |
| `references/4_taste_engine/choreography.md` | `ARCHIVAL_DOC` | 100 | 3,415 |
| `references/4_taste_engine/context-adaptation.md` | `ARCHIVAL_DOC` | 90 | 3,436 |
| `references/4_taste_engine/core-philosophy.md` | `ARCHIVAL_DOC` | 60 | 2,204 |
| `references/4_taste_engine/decision-framework.md` | `ARCHIVAL_DOC` | 98 | 3,203 |
| `references/4_taste_engine/disney-principles.md` | `ARCHIVAL_DOC` | 109 | 3,586 |
| `references/4_taste_engine/emotion-mapping.md` | `ARCHIVAL_DOC` | 78 | 3,235 |
| `references/4_taste_engine/motion-personality.md` | `ARCHIVAL_DOC` | 115 | 4,470 |
| `references/4_taste_engine/narrative-structure.md` | `ARCHIVAL_DOC` | 69 | 2,756 |
| `references/4_taste_engine/sfx_binding_matrix.md` | `ARCHIVAL_DOC` | 103 | 5,932 |
| `references/4_taste_engine/user-signature-style.md` | `ARCHIVAL_DOC` | 84 | 5,079 |
| `references/README.md` | `ARCHIVAL_DOC` | 445 | 14,574 |
| `references/ROUTER.md` | `ARCHIVAL_DOC` | 240 | 20,809 |
| `registry/README.md` | `ARCHIVAL_DOC` | 28 | 1,649 |
| `التعلم/الاصلاح/Master_Remediation_Ledger_motion_محدث_S24_5.xlsx` | `ARCHIVAL_DOC` | 0 | 43,242 |
| `التعلم/الاصلاح/اخطاء.md` | `ARCHIVAL_DOC` | 163 | 12,105 |
| `التعلم/الاصلاح/الاخطاء_محدثة_بعد_S24_5.md` | `ARCHIVAL_DOC` | 1,290 | 55,943 |
| `التعلم/الاصلاح/خارطة_طريق_الإصلاح_حتى_الجاهزية_للإنتاج_محدثة_بعد_S24_5.md` | `ARCHIVAL_DOC` | 316 | 39,617 |
| `التعلم/الاصلاح/خطة_الS27.md` | `ARCHIVAL_DOC` | 1,493 | 34,825 |
| `التعلم/التقارير/CODE_VERIFIED_PIPELINE_AND_STATE_MACHINE.md` | `ARCHIVAL_DOC` | 928 | 72,405 |
| `التعلم/التقارير/CODE_VERIFIED_RENDERING_SUBSYSTEM.md` | `ARCHIVAL_DOC` | 1,067 | 81,612 |
| `التعلم/التقارير/LEVEL 0 — System Overview.md` | `ARCHIVAL_DOC` | 305 | 22,846 |

</details>

### Subsystem: Durable Execution & Worker Engine (`durable_execution`)
- **File Count:** 6
- **Lines of Code:** 3,093
- **Critical Files:** 6

<details>
<summary>Click to expand all 6 files in durable_execution</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `api/services/pipeline_service.py` | `ACTIVE_RUNTIME` | 389 | 16,873 |
| `api/services/run_service.py` | `ACTIVE_RUNTIME` | 292 | 12,679 |
| `scripts/core/project_lock.py` | `ACTIVE_RUNTIME` | 249 | 11,331 |
| `scripts/core/run_repository.py` | `ACTIVE_RUNTIME` | 852 | 37,546 |
| `scripts/core/worker.py` | `ACTIVE_RUNTIME` | 766 | 35,554 |
| `scripts/pipeline.py` | `ACTIVE_RUNTIME` | 545 | 27,782 |

</details>

### Subsystem: HTTP Transport & Ingestion (`http_transport`)
- **File Count:** 16
- **Lines of Code:** 1,803
- **Critical Files:** 16

<details>
<summary>Click to expand all 16 files in http_transport</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `api/main.py` | `ACTIVE_RUNTIME` | 92 | 4,434 |
| `api/routers/__init__.py` | `ACTIVE_RUNTIME` | 4 | 152 |
| `api/routers/artifacts.py` | `ACTIVE_RUNTIME` | 144 | 5,149 |
| `api/routers/assets.py` | `ACTIVE_RUNTIME` | 89 | 2,942 |
| `api/routers/authoring.py` | `ACTIVE_RUNTIME` | 290 | 11,114 |
| `api/routers/blueprint.py` | `ACTIVE_RUNTIME` | 91 | 3,661 |
| `api/routers/brand.py` | `ACTIVE_RUNTIME` | 59 | 2,230 |
| `api/routers/candidate_promotions.py` | `ACTIVE_RUNTIME` | 147 | 6,385 |
| `api/routers/candidate_reviews.py` | `ACTIVE_RUNTIME` | 242 | 10,761 |
| `api/routers/capabilities.py` | `ACTIVE_RUNTIME` | 58 | 2,114 |
| `api/routers/gates.py` | `ACTIVE_RUNTIME` | 79 | 3,015 |
| `api/routers/health.py` | `ACTIVE_RUNTIME` | 62 | 1,851 |
| `api/routers/outputs.py` | `ACTIVE_RUNTIME` | 76 | 2,582 |
| `api/routers/projects.py` | `ACTIVE_RUNTIME` | 120 | 4,591 |
| `api/routers/render.py` | `ACTIVE_RUNTIME` | 55 | 1,933 |
| `api/routers/runs.py` | `ACTIVE_RUNTIME` | 195 | 7,300 |

</details>

### Subsystem: Supporting Assets & Data (`miscellaneous`)
- **File Count:** 346
- **Lines of Code:** 84,099
- **Critical Files:** 0

<details>
<summary>Click to expand all 346 files in miscellaneous</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `.blueprint_lock.json` | `SUPPORTING` | 12 | 250 |
| `.dockerignore` | `SUPPORTING` | 0 | 818 |
| `.githooks/pre-commit` | `SUPPORTING` | 0 | 906 |
| `.githooks/pre-push` | `SUPPORTING` | 0 | 257 |
| `.github/workflows/real-e2e-nightly.yml` | `SUPPORTING` | 269 | 10,939 |
| `.github/workflows/remediation-ci.yml` | `SUPPORTING` | 500 | 15,591 |
| `.gitmodules` | `SUPPORTING` | 0 | 171 |
| `.trivyignore` | `SUPPORTING` | 0 | 124 |
| `PR_001_COMPLETE_REPORT.txt` | `SUPPORTING` | 332 | 20,882 |
| `ai/__init__.py` | `SUPPORTING` | 20 | 692 |
| `ai/acquisition/__init__.py` | `SUPPORTING` | 58 | 1,484 |
| `ai/acquisition/contracts.py` | `SUPPORTING` | 141 | 9,377 |
| `ai/acquisition/dedupe.py` | `SUPPORTING` | 87 | 3,291 |
| `ai/acquisition/errors.py` | `SUPPORTING` | 174 | 7,377 |
| `ai/acquisition/filtering.py` | `SUPPORTING` | 119 | 4,919 |
| `ai/acquisition/providers/__init__.py` | `SUPPORTING` | 17 | 493 |
| `ai/acquisition/providers/base.py` | `SUPPORTING` | 61 | 1,849 |
| `ai/acquisition/providers/freesound.py` | `SUPPORTING` | 218 | 9,203 |
| `ai/acquisition/providers/iconify.py` | `SUPPORTING` | 211 | 8,508 |
| `ai/acquisition/providers/pexels.py` | `SUPPORTING` | 262 | 11,746 |
| `ai/acquisition/providers/pixabay.py` | `SUPPORTING` | 294 | 12,964 |
| `ai/acquisition/ranking.py` | `SUPPORTING` | 159 | 6,194 |
| `ai/acquisition/safe_downloader.py` | `SUPPORTING` | 388 | 17,032 |
| `ai/acquisition/service.py` | `SUPPORTING` | 616 | 26,870 |
| `ai/audio/__init__.py` | `SUPPORTING` | 37 | 755 |
| `ai/audio/benchmark/__init__.py` | `SUPPORTING` | 48 | 1,313 |
| `ai/audio/benchmark/fixtures.py` | `SUPPORTING` | 144 | 5,449 |
| `ai/audio/benchmark/manifest.py` | `SUPPORTING` | 129 | 4,095 |
| `ai/audio/benchmark/metrics.py` | `SUPPORTING` | 21 | 621 |
| `ai/audio/benchmark/runner.py` | `SUPPORTING` | 83 | 3,478 |
| `ai/audio/dsp.py` | `SUPPORTING` | 355 | 12,921 |
| `ai/audio/modes.py` | `SUPPORTING` | 335 | 16,852 |
| `ai/audio/pipeline.py` | `SUPPORTING` | 173 | 7,231 |
| `ai/batch/__init__.py` | `SUPPORTING` | 26 | 598 |
| `ai/batch/policy.py` | `SUPPORTING` | 82 | 3,083 |
| `ai/batch/service.py` | `SUPPORTING` | 281 | 11,886 |
| `ai/budget/__init__.py` | `SUPPORTING` | 79 | 2,148 |
| `ai/budget/accounting.py` | `SUPPORTING` | 110 | 4,114 |
| `ai/budget/estimator.py` | `SUPPORTING` | 98 | 4,065 |
| `ai/budget/policy.py` | `SUPPORTING` | 108 | 4,055 |
| `ai/budget/repository.py` | `SUPPORTING` | 247 | 9,866 |
| `ai/budget/reservation.py` | `SUPPORTING` | 257 | 11,508 |
| `ai/budget/service.py` | `SUPPORTING` | 504 | 22,060 |
| `ai/budget/types.py` | `SUPPORTING` | 242 | 12,786 |
| `ai/cache/__init__.py` | `SUPPORTING` | 67 | 1,746 |
| `ai/cache/errors.py` | `SUPPORTING` | 46 | 1,329 |
| `ai/cache/key.py` | `SUPPORTING` | 121 | 4,476 |
| `ai/cache/policy.py` | `SUPPORTING` | 50 | 1,671 |
| `ai/cache/repository.py` | `SUPPORTING` | 139 | 4,792 |
| `ai/cache/service.py` | `SUPPORTING` | 655 | 30,942 |
| `ai/candidates/__init__.py` | `SUPPORTING` | 118 | 3,532 |
| `ai/candidates/errors.py` | `SUPPORTING` | 9 | 269 |
| `ai/candidates/gates/__init__.py` | `SUPPORTING` | 9 | 266 |
| `ai/candidates/gates/aspect_gate.py` | `SUPPORTING` | 9 | 302 |
| `ai/candidates/gates/ast_runner.py` | `SUPPORTING` | 9 | 299 |
| `ai/candidates/gates/base.py` | `SUPPORTING` | 9 | 281 |
| `ai/candidates/gates/candidate_qc_gate.py` | `SUPPORTING` | 9 | 320 |
| `ai/candidates/gates/contract_gate.py` | `SUPPORTING` | 9 | 308 |
| `ai/candidates/gates/dependency_gate.py` | `SUPPORTING` | 9 | 314 |
| `ai/candidates/gates/probe_gate.py` | `SUPPORTING` | 9 | 299 |
| `ai/candidates/gates/render_smoke_gate.py` | `SUPPORTING` | 9 | 320 |
| `ai/candidates/gates/runtime_contract_gate.py` | `SUPPORTING` | 9 | 332 |
| `ai/candidates/gates/security_gate.py` | `SUPPORTING` | 9 | 308 |
| `ai/candidates/gates/static_code_gate.py` | `SUPPORTING` | 9 | 317 |
| `ai/candidates/gates/template_schema_gate.py` | `SUPPORTING` | 9 | 329 |
| `ai/candidates/gates/typescript_gate.py` | `SUPPORTING` | 9 | 314 |
| `ai/candidates/hashing.py` | `SUPPORTING` | 9 | 272 |
| `ai/candidates/policies.py` | `SUPPORTING` | 9 | 275 |
| `ai/candidates/promotion_service.py` | `SUPPORTING` | 9 | 302 |
| `ai/candidates/repository.py` | `SUPPORTING` | 9 | 281 |
| `ai/candidates/review_service.py` | `SUPPORTING` | 9 | 293 |
| `ai/candidates/runtime_runner.py` | `SUPPORTING` | 9 | 293 |
| `ai/candidates/service.py` | `SUPPORTING` | 9 | 272 |
| `ai/candidates/validation_service.py` | `SUPPORTING` | 9 | 305 |
| `ai/capabilities/__init__.py` | `SUPPORTING` | 43 | 1,067 |
| `ai/capabilities/catalog.py` | `SUPPORTING` | 110 | 4,529 |
| `ai/capabilities/definitions.py` | `SUPPORTING` | 494 | 25,192 |
| `ai/capabilities/registry.py` | `SUPPORTING` | 172 | 6,490 |
| `ai/capabilities/types.py` | `SUPPORTING` | 94 | 4,324 |
| `ai/conflict/__init__.py` | `SUPPORTING` | 11 | 206 |
| `ai/conflict/resolver.py` | `SUPPORTING` | 198 | 10,059 |
| `ai/cost/__init__.py` | `SUPPORTING` | 41 | 968 |
| `ai/cost/accounting.py` | `SUPPORTING` | 143 | 5,705 |
| `ai/cost/analyzer.py` | `SUPPORTING` | 485 | 23,543 |
| `ai/cost/baseline.py` | `SUPPORTING` | 97 | 3,825 |
| `ai/cost/collector.py` | `SUPPORTING` | 355 | 14,448 |
| `ai/cost/errors.py` | `SUPPORTING` | 22 | 615 |
| `ai/directors/__init__.py` | `SUPPORTING` | 19 | 542 |
| `ai/directors/bundle.py` | `SUPPORTING` | 55 | 2,222 |
| `ai/directors/emotion_director.py` | `SUPPORTING` | 73 | 2,996 |
| `ai/directors/motion_director.py` | `SUPPORTING` | 139 | 5,502 |
| `ai/directors/narrative_director.py` | `SUPPORTING` | 92 | 3,992 |
| `ai/directors/sfx_director.py` | `SUPPORTING` | 153 | 6,587 |
| `ai/evals/__init__.py` | `SUPPORTING` | 68 | 1,834 |
| `ai/evals/creative_datasets.py` | `SUPPORTING` | 255 | 13,649 |
| `ai/evals/creative_evals_s28_04.py` | `SUPPORTING` | 556 | 25,476 |
| `ai/evals/datasets.py` | `SUPPORTING` | 209 | 8,035 |
| `ai/evals/deferred.py` | `SUPPORTING` | 55 | 2,202 |
| `ai/evals/evaluators.py` | `SUPPORTING` | 152 | 5,677 |
| `ai/evals/gate.py` | `SUPPORTING` | 96 | 3,457 |
| `ai/evals/promotion.py` | `SUPPORTING` | 119 | 4,535 |
| `ai/evals/runner.py` | `SUPPORTING` | 107 | 4,095 |
| `ai/feedback/__init__.py` | `SUPPORTING` | 23 | 484 |
| `ai/feedback/classifier.py` | `SUPPORTING` | 211 | 12,266 |
| `ai/feedback/service.py` | `SUPPORTING` | 192 | 7,864 |
| `ai/image_processing/__init__.py` | `SUPPORTING` | 105 | 2,942 |
| `ai/image_processing/adapter.py` | `SUPPORTING` | 391 | 15,521 |
| `ai/image_processing/cache.py` | `SUPPORTING` | 121 | 4,890 |
| `ai/image_processing/contracts.py` | `SUPPORTING` | 285 | 17,226 |
| `ai/image_processing/errors.py` | `SUPPORTING` | 161 | 6,737 |
| `ai/image_processing/security.py` | `SUPPORTING` | 156 | 5,875 |
| `ai/image_processing/service.py` | `SUPPORTING` | 505 | 20,494 |
| `ai/image_processing/validator.py` | `SUPPORTING` | 86 | 2,846 |
| `ai/intent/__init__.py` | `SUPPORTING` | 25 | 612 |
| `ai/intent/brief_builder.py` | `SUPPORTING` | 110 | 4,253 |
| `ai/intent/contracts.py` | `SUPPORTING` | 87 | 4,167 |
| `ai/intent/evaluator.py` | `SUPPORTING` | 246 | 11,371 |
| `ai/intent/parser.py` | `SUPPORTING` | 517 | 26,985 |
| `ai/mcp/__init__.py` | `SUPPORTING` | 176 | 4,582 |
| `ai/mcp/adapters/__init__.py` | `SUPPORTING` | 50 | 1,279 |
| `ai/mcp/adapters/audio.py` | `SUPPORTING` | 153 | 5,445 |
| `ai/mcp/adapters/base.py` | `SUPPORTING` | 214 | 7,658 |
| `ai/mcp/adapters/image.py` | `SUPPORTING` | 141 | 4,886 |
| `ai/mcp/adapters/parity.py` | `SUPPORTING` | 78 | 2,357 |
| `ai/mcp/adapters/video.py` | `SUPPORTING` | 159 | 5,497 |
| `ai/mcp/audit.py` | `SUPPORTING` | 89 | 3,328 |
| `ai/mcp/catalog.py` | `SUPPORTING` | 336 | 13,198 |
| `ai/mcp/compatibility/__init__.py` | `SUPPORTING` | 45 | 1,302 |
| `ai/mcp/compatibility/contracts.py` | `SUPPORTING` | 75 | 3,812 |
| `ai/mcp/compatibility/facade.py` | `SUPPORTING` | 256 | 10,557 |
| `ai/mcp/compatibility/mappers.py` | `SUPPORTING` | 364 | 16,818 |
| `ai/mcp/compatibility/registry.py` | `SUPPORTING` | 556 | 25,895 |
| `ai/mcp/compatibility/server.py` | `SUPPORTING` | 133 | 4,502 |
| `ai/mcp/contracts.py` | `SUPPORTING` | 260 | 13,660 |
| `ai/mcp/errors.py` | `SUPPORTING` | 129 | 4,812 |
| `ai/mcp/policy.py` | `SUPPORTING` | 211 | 7,957 |
| `ai/media/__init__.py` | `SUPPORTING` | 20 | 694 |
| `ai/media/repository.py` | `SUPPORTING` | 84 | 2,580 |
| `ai/media/service.py` | `SUPPORTING` | 509 | 22,676 |
| `ai/media/technical_probe.py` | `SUPPORTING` | 139 | 5,225 |
| `ai/media/validation.py` | `SUPPORTING` | 164 | 7,614 |
| `ai/media_processing/__init__.py` | `SUPPORTING` | 142 | 4,008 |
| `ai/media_processing/adapter.py` | `SUPPORTING` | 544 | 18,266 |
| `ai/media_processing/contracts.py` | `SUPPORTING` | 551 | 25,814 |
| `ai/media_processing/errors.py` | `SUPPORTING` | 187 | 7,106 |
| `ai/media_processing/security.py` | `SUPPORTING` | 181 | 6,314 |
| `ai/media_processing/service.py` | `SUPPORTING` | 1,083 | 50,660 |
| `ai/media_processing/staging.py` | `SUPPORTING` | 167 | 6,123 |
| `ai/media_processing/validator.py` | `SUPPORTING` | 232 | 9,020 |
| `ai/memory/__init__.py` | `SUPPORTING` | 74 | 1,991 |
| `ai/memory/deduplication.py` | `SUPPORTING` | 102 | 4,026 |
| `ai/memory/embeddings.py` | `SUPPORTING` | 102 | 3,559 |
| `ai/memory/facade.py` | `SUPPORTING` | 174 | 6,579 |
| `ai/memory/models.py` | `SUPPORTING` | 267 | 11,745 |
| `ai/memory/normalization.py` | `SUPPORTING` | 115 | 4,240 |
| `ai/memory/policy.py` | `SUPPORTING` | 352 | 17,523 |
| `ai/memory/repository.py` | `SUPPORTING` | 385 | 15,798 |
| `ai/memory/service.py` | `SUPPORTING` | 394 | 16,006 |
| `ai/memory/types.py` | `SUPPORTING` | 64 | 1,709 |
| `ai/models/__init__.py` | `SUPPORTING` | 35 | 738 |
| `ai/models/definitions.py` | `SUPPORTING` | 427 | 14,071 |
| `ai/models/registry.py` | `SUPPORTING` | 168 | 6,106 |
| `ai/models/types.py` | `SUPPORTING` | 62 | 3,599 |
| `ai/observability/__init__.py` | `SUPPORTING` | 31 | 909 |
| `ai/observability/metrics.py` | `SUPPORTING` | 182 | 7,809 |
| `ai/observability/redaction.py` | `SUPPORTING` | 155 | 7,297 |
| `ai/observability/repository.py` | `SUPPORTING` | 61 | 1,923 |
| `ai/observability/tracer.py` | `SUPPORTING` | 306 | 11,370 |
| `ai/planning/__init__.py` | `SUPPORTING` | 56 | 1,808 |
| `ai/planning/asset_preparation.py` | `SUPPORTING` | 487 | 20,660 |
| `ai/planning/compiler.py` | `SUPPORTING` | 442 | 18,406 |
| `ai/planning/compose_engine.py` | `SUPPORTING` | 434 | 18,142 |
| `ai/planning/creative_planner.py` | `SUPPORTING` | 374 | 16,972 |
| `ai/planning/errors.py` | `SUPPORTING` | 100 | 3,050 |
| `ai/planning/reuse_engine.py` | `SUPPORTING` | 652 | 30,794 |
| `ai/planning/tier_policy.py` | `SUPPORTING` | 235 | 10,803 |
| `ai/planning/validator.py` | `SUPPORTING` | 222 | 11,903 |
| `ai/prompts/__init__.py` | `SUPPORTING` | 13 | 276 |
| `ai/prompts/repository.py` | `SUPPORTING` | 67 | 2,144 |
| `ai/prompts/service.py` | `SUPPORTING` | 270 | 11,354 |
| `ai/providers/__init__.py` | `SUPPORTING` | 39 | 1,056 |
| `ai/providers/base.py` | `SUPPORTING` | 75 | 2,991 |
| `ai/providers/definitions.py` | `SUPPORTING` | 99 | 4,121 |
| `ai/providers/fake.py` | `SUPPORTING` | 255 | 9,573 |
| `ai/providers/openrouter.py` | `SUPPORTING` | 535 | 24,818 |
| `ai/providers/registry.py` | `SUPPORTING` | 93 | 3,086 |
| `ai/regression/__init__.py` | `SUPPORTING` | 95 | 2,752 |
| `ai/regression/contracts.py` | `SUPPORTING` | 41 | 942 |
| `ai/regression/datasets.py` | `SUPPORTING` | 824 | 34,952 |
| `ai/regression/retrieval_grader.py` | `SUPPORTING` | 134 | 3,946 |
| `ai/regression/rubric_grader.py` | `SUPPORTING` | 455 | 17,918 |
| `ai/regression/runner.py` | `SUPPORTING` | 917 | 43,726 |
| `ai/regression/trace_grader.py` | `SUPPORTING` | 376 | 14,906 |
| `ai/routing/__init__.py` | `SUPPORTING` | 65 | 1,734 |
| `ai/routing/capability_router.py` | `SUPPORTING` | 168 | 6,823 |
| `ai/routing/constraints.py` | `SUPPORTING` | 161 | 8,238 |
| `ai/routing/cost.py` | `SUPPORTING` | 67 | 2,576 |
| `ai/routing/escalation.py` | `SUPPORTING` | 72 | 2,711 |
| `ai/routing/fallback.py` | `SUPPORTING` | 126 | 5,013 |
| `ai/routing/policy.py` | `SUPPORTING` | 118 | 4,832 |
| `ai/routing/router.py` | `SUPPORTING` | 709 | 30,791 |
| `ai/routing/scoring.py` | `SUPPORTING` | 136 | 5,127 |
| `ai/routing/types.py` | `SUPPORTING` | 120 | 6,098 |
| `ai/security/__init__.py` | `SUPPORTING` | 25 | 657 |
| `ai/security/bounds.py` | `SUPPORTING` | 62 | 2,551 |
| `ai/security/policies.py` | `SUPPORTING` | 92 | 3,679 |
| `ai/security/scrubber.py` | `SUPPORTING` | 67 | 2,923 |
| `ai/security/ssrf.py` | `SUPPORTING` | 97 | 3,630 |
| `ai/specialized/__init__.py` | `SUPPORTING` | 45 | 1,317 |
| `ai/specialized/adapters.py` | `SUPPORTING` | 398 | 15,153 |
| `ai/specialized/errors.py` | `SUPPORTING` | 44 | 1,300 |
| `ai/specialized/interfaces.py` | `SUPPORTING` | 110 | 3,089 |
| `ai/specialized/service.py` | `SUPPORTING` | 498 | 21,382 |
| `ai/speech/__init__.py` | `SUPPORTING` | 101 | 2,675 |
| `ai/speech/adapter.py` | `SUPPORTING` | 470 | 20,393 |
| `ai/speech/benchmark/__init__.py` | `SUPPORTING` | 47 | 1,277 |
| `ai/speech/benchmark/corpus_manifest.py` | `SUPPORTING` | 230 | 12,280 |
| `ai/speech/benchmark/metrics.py` | `SUPPORTING` | 265 | 10,260 |
| `ai/speech/benchmark/runner.py` | `SUPPORTING` | 224 | 10,154 |
| `ai/speech/cache.py` | `SUPPORTING` | 94 | 3,459 |
| `ai/speech/lifecycle.py` | `SUPPORTING` | 320 | 12,083 |
| `ai/speech/local_provider.py` | `SUPPORTING` | 429 | 17,557 |
| `ai/speech/manifest.py` | `SUPPORTING` | 264 | 11,247 |
| `ai/speech/preparation.py` | `SUPPORTING` | 460 | 18,070 |
| `ai/speech/reconciliation.py` | `SUPPORTING` | 259 | 9,304 |
| `ai/speech/storage_resolver.py` | `SUPPORTING` | 196 | 8,465 |
| `ai/speech/stt_provider.py` | `SUPPORTING` | 406 | 19,080 |
| `ai/speech/timeline.py` | `SUPPORTING` | 238 | 10,276 |
| `ai/style/__init__.py` | `SUPPORTING` | 13 | 249 |
| `ai/style/resolver.py` | `SUPPORTING` | 427 | 18,230 |
| `ai/vision/__init__.py` | `SUPPORTING` | 39 | 852 |
| `ai/vision/adaptive_resolution.py` | `SUPPORTING` | 79 | 2,988 |
| `ai/vision/benchmark/__init__.py` | `SUPPORTING` | 32 | 852 |
| `ai/vision/benchmark/manifest.py` | `SUPPORTING` | 173 | 5,625 |
| `ai/vision/benchmark/metrics.py` | `SUPPORTING` | 63 | 1,968 |
| `ai/vision/benchmark/runner.py` | `SUPPORTING` | 57 | 2,189 |
| `ai/vision/keyframe_extractor.py` | `SUPPORTING` | 161 | 6,158 |
| `ai/vision/object_person.py` | `SUPPORTING` | 154 | 5,646 |
| `ai/vision/ocr.py` | `SUPPORTING` | 85 | 3,073 |
| `ai/vision/pipeline.py` | `SUPPORTING` | 280 | 12,380 |
| `ai/vision/shot_detection.py` | `SUPPORTING` | 123 | 4,303 |
| `api/__init__.py` | `SUPPORTING` | 4 | 152 |
| `api/core/auth.py` | `SUPPORTING` | 485 | 19,907 |
| `api/core/config.py` | `SUPPORTING` | 168 | 7,165 |
| `api/core/errors.py` | `SUPPORTING` | 280 | 10,256 |
| `api/schemas/__init__.py` | `SUPPORTING` | 22 | 696 |
| `api/schemas/artifact.py` | `SUPPORTING` | 34 | 846 |
| `api/schemas/asset.py` | `SUPPORTING` | 32 | 890 |
| `api/schemas/blueprint.py` | `SUPPORTING` | 6 | 207 |
| `api/schemas/capability.py` | `SUPPORTING` | 46 | 2,502 |
| `api/schemas/creative.py` | `SUPPORTING` | 65 | 3,512 |
| `api/schemas/gate.py` | `SUPPORTING` | 22 | 514 |
| `api/schemas/lifecycle.py` | `SUPPORTING` | 23 | 972 |
| `api/schemas/project.py` | `SUPPORTING` | 17 | 535 |
| `api/schemas/responses.py` | `SUPPORTING` | 13 | 359 |
| `api/schemas/run.py` | `SUPPORTING` | 98 | 3,419 |
| `api/websocket.py` | `SUPPORTING` | 31 | 1,367 |
| `assets/cache/.gitkeep` | `SUPPORTING` | 0 | 0 |
| `assets/incoming/.gitkeep` | `SUPPORTING` | 0 | 0 |
| `assets/incoming/tests/background_music.mp3` | `SUPPORTING` | 0 | 386,194 |
| `assets/incoming/tests/dialogue_two_speakers.wav` | `SUPPORTING` | 0 | 266,924 |
| `assets/incoming/tests/human_vo_01.txt` | `SUPPORTING` | 1 | 60 |
| `assets/incoming/tests/human_vo_01.wav` | `SUPPORTING` | 0 | 689,298 |
| `assets/incoming/tests/msa_bgm.wav` | `SUPPORTING` | 0 | 331,710 |
| `assets/incoming/tests/msa_clean_female.wav` | `SUPPORTING` | 0 | 218,924 |
| `assets/incoming/tests/msa_clean_male.wav` | `SUPPORTING` | 0 | 180,524 |
| `assets/incoming/tests/msa_fast.wav` | `SUPPORTING` | 0 | 180,524 |
| `assets/processing/.gitkeep` | `SUPPORTING` | 0 | 0 |
| `assets/ready/.gitkeep` | `SUPPORTING` | 0 | 0 |
| `authoring/creative-adapter.ts` | `SUPPORTING` | 200 | 6,081 |
| `authoring/index.ts` | `SUPPORTING` | 11 | 417 |
| `authoring/intent-planner.ts` | `SUPPORTING` | 839 | 28,127 |
| `authoring/template-adapter.ts` | `SUPPORTING` | 90 | 3,013 |
| `authoring/unified-authoring-session.ts` | `SUPPORTING` | 266 | 9,213 |
| `canvas/canvas-renderer-adapter.ts` | `SUPPORTING` | 661 | 21,607 |
| `canvas/index.ts` | `SUPPORTING` | 1 | 44 |
| `compositor/audio-normalizer.ts` | `SUPPORTING` | 343 | 11,269 |
| `compositor/index.ts` | `SUPPORTING` | 11 | 409 |
| `compositor/master-compositor.ts` | `SUPPORTING` | 350 | 12,237 |
| `compositor/output-normalizer.ts` | `SUPPORTING` | 246 | 7,726 |
| `compositor/probe.ts` | `SUPPORTING` | 215 | 6,959 |
| `compositor/qc-adapter.ts` | `SUPPORTING` | 182 | 6,350 |
| `compositor/timeline-assembler.ts` | `SUPPORTING` | 270 | 7,323 |
| `config/violations_config.json` | `SUPPORTING` | 167 | 8,158 |
| `config/violations_config.schema.json` | `SUPPORTING` | 101 | 3,331 |
| `data/.gitkeep` | `SUPPORTING` | 0 | 0 |
| `hooks.json` | `SUPPORTING` | 49 | 1,098 |
| `package-lock.json` | `SUPPORTING` | 7,837 | 287,898 |
| `planner/cache-evaluator.ts` | `SUPPORTING` | 196 | 6,107 |
| `planner/cost-estimator.ts` | `SUPPORTING` | 90 | 3,046 |
| `planner/index.ts` | `SUPPORTING` | 11 | 413 |
| `planner/planning-policy.ts` | `SUPPORTING` | 162 | 5,127 |
| `planner/production-render-graph-executor.ts` | `SUPPORTING` | 752 | 24,525 |
| `planner/render-graph-executor.ts` | `SUPPORTING` | 427 | 14,715 |
| `planner/render-planner.ts` | `SUPPORTING` | 543 | 17,338 |
| `preview/audio/audio-preview-runtime.ts` | `SUPPORTING` | 591 | 20,135 |
| `preview/audio/audio-types.ts` | `SUPPORTING` | 85 | 2,802 |
| `preview/audio/index.ts` | `SUPPORTING` | 8 | 326 |
| `preview/audio/waveform-analyzer.ts` | `SUPPORTING` | 104 | 3,072 |
| `preview/audio/web-audio-adapter.ts` | `SUPPORTING` | 276 | 8,813 |
| `preview/capabilities.ts` | `SUPPORTING` | 154 | 5,864 |
| `preview/components/LivePreviewPlayer.tsx` | `SUPPORTING` | 247 | 7,267 |
| `preview/dom-driver.ts` | `SUPPORTING` | 215 | 8,212 |
| `preview/index.ts` | `SUPPORTING` | 12 | 400 |
| `preview/preview-runtime.ts` | `SUPPORTING` | 560 | 19,139 |
| `preview/proxy/index.ts` | `SUPPORTING` | 8 | 279 |
| `preview/proxy/production-preview-coordinator.ts` | `SUPPORTING` | 157 | 5,419 |
| `preview/proxy/proxy-cache.ts` | `SUPPORTING` | 359 | 11,189 |
| `preview/proxy/proxy-coordinator.ts` | `SUPPORTING` | 433 | 13,580 |
| `preview/types.ts` | `SUPPORTING` | 115 | 3,696 |
| `preview/visual-frame.ts` | `SUPPORTING` | 385 | 14,158 |
| `projects/.gitkeep` | `SUPPORTING` | 0 | 1 |
| `public/media/bot.svg` | `SUPPORTING` | 0 | 1,319 |
| `public/media/brain.svg` | `SUPPORTING` | 0 | 996 |
| `public/media/code.svg` | `SUPPORTING` | 0 | 248 |
| `public/media/icon_cpu.svg` | `SUPPORTING` | 0 | 4,220 |
| `public/media/icon_satellite.svg` | `SUPPORTING` | 0 | 2,080 |
| `public/media/instagram.svg` | `SUPPORTING` | 0 | 2,109 |
| `public/media/meteor.svg` | `SUPPORTING` | 0 | 1,206 |
| `public/media/moon.svg` | `SUPPORTING` | 0 | 1,114 |
| `public/media/smartphone_lucide.svg` | `SUPPORTING` | 0 | 269 |
| `public/media/space_shuttle.svg` | `SUPPORTING` | 0 | 2,523 |
| `public/media/success.svg` | `SUPPORTING` | 0 | 291 |
| `public/media/tiktok.svg` | `SUPPORTING` | 0 | 1,802 |
| `public/media/twitter.svg` | `SUPPORTING` | 0 | 787 |
| `public/media/youtube.svg` | `SUPPORTING` | 0 | 513 |
| `registry/auto-generated-entries.ts` | `SUPPORTING` | 489 | 24,374 |
| `registry/docs-extractor.ts` | `SUPPORTING` | 105 | 3,436 |
| `registry/docs-worklist.json` | `SUPPORTING` | 706 | 21,874 |
| `registry/effects-catalog.ts` | `SUPPORTING` | 318 | 9,990 |
| `registry/effects-runtime.ts` | `SUPPORTING` | 52 | 1,613 |
| `registry/engine-classification.json` | `SUPPORTING` | 266 | 9,625 |
| `registry/ids.json` | `SUPPORTING` | 88 | 1,684 |
| `registry/semantic-registry.ts` | `SUPPORTING` | 149 | 5,526 |
| `registry/template-aliases.ts` | `SUPPORTING` | 197 | 9,122 |
| `registry/template-migration-manifest.json` | `SUPPORTING` | 1,935 | 84,953 |
| `registry/template-registry-data.json` | `SUPPORTING` | 3,996 | 103,700 |
| `registry/template-registry.tsx` | `SUPPORTING` | 293 | 13,990 |
| `registry/template-specs-data.json` | `SUPPORTING` | 12,184 | 334,682 |
| `registry/thumbs/.gitkeep` | `SUPPORTING` | 0 | 15 |
| `registry/tier-map.json` | `SUPPORTING` | 224 | 9,002 |
| `registry/types.ts` | `SUPPORTING` | 66 | 3,127 |
| `remotion/index.ts` | `SUPPORTING` | 5 | 152 |
| `remotion/remotion-renderer-adapter.ts` | `SUPPORTING` | 556 | 17,365 |
| `skills-lock.json` | `SUPPORTING` | 17 | 480 |
| `uv.lock` | `SUPPORTING` | 0 | 418,505 |

</details>

### Subsystem: Quality Control & Automated Gates (`quality_control`)
- **File Count:** 28
- **Lines of Code:** 4,953
- **Critical Files:** 28

<details>
<summary>Click to expand all 28 files in quality_control</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `scripts/gates/__init__.py` | `ACTIVE_RUNTIME` | 0 | 0 |
| `scripts/gates/asset_gate.py` | `ACTIVE_RUNTIME` | 109 | 4,674 |
| `scripts/gates/code_template_gate.py` | `ACTIVE_RUNTIME` | 267 | 14,674 |
| `scripts/gates/final_qc.py` | `ACTIVE_RUNTIME` | 833 | 33,893 |
| `scripts/gates/motion_validator.py` | `ACTIVE_RUNTIME` | 380 | 18,122 |
| `scripts/gates/plan_gate.py` | `ACTIVE_RUNTIME` | 251 | 10,584 |
| `scripts/gates/probe_qc.py` | `ACTIVE_RUNTIME` | 741 | 30,320 |
| `scripts/gates/smart_qc.py` | `ACTIVE_RUNTIME` | 229 | 8,708 |
| `scripts/gates/taste_gate.py` | `ACTIVE_RUNTIME` | 140 | 6,637 |
| `scripts/gates/validate_blueprint.py` | `ACTIVE_RUNTIME` | 191 | 8,967 |
| `scripts/gates/vo_quality_check.py` | `ACTIVE_RUNTIME` | 60 | 2,175 |
| `scripts/validators/__init__.py` | `ACTIVE_RUNTIME` | 0 | 0 |
| `scripts/validators/audit_imports.py` | `ACTIVE_RUNTIME` | 56 | 2,299 |
| `scripts/validators/audit_skill.py` | `ACTIVE_RUNTIME` | 146 | 6,829 |
| `scripts/validators/candidate_ast_worker.cjs` | `ACTIVE_RUNTIME` | 0 | 11,819 |
| `scripts/validators/candidate_runtime_runner.py` | `ACTIVE_RUNTIME` | 343 | 12,863 |
| `scripts/validators/check_dependencies_lock.py` | `ACTIVE_RUNTIME` | 63 | 2,000 |
| `scripts/validators/check_ground_truth_sync.py` | `ACTIVE_RUNTIME` | 54 | 1,916 |
| `scripts/validators/check_secrets.py` | `ACTIVE_RUNTIME` | 96 | 3,532 |
| `scripts/validators/custom_code_validator.py` | `ACTIVE_RUNTIME` | 184 | 6,688 |
| `scripts/validators/inspect_template.py` | `ACTIVE_RUNTIME` | 80 | 2,758 |
| `scripts/validators/spec_validator.py` | `ACTIVE_RUNTIME` | 99 | 3,879 |
| `scripts/validators/template_lint.py` | `ACTIVE_RUNTIME` | 84 | 4,151 |
| `scripts/validators/template_proposal_validator.py` | `ACTIVE_RUNTIME` | 224 | 8,913 |
| `scripts/validators/validate_schemas.py` | `ACTIVE_RUNTIME` | 140 | 4,675 |
| `scripts/validators/validate_template.py` | `ACTIVE_RUNTIME` | 44 | 1,537 |
| `scripts/validators/verify_links.py` | `ACTIVE_RUNTIME` | 77 | 3,033 |
| `scripts/validators/verify_media_layer.py` | `ACTIVE_RUNTIME` | 62 | 3,521 |

</details>

### Subsystem: Remotion & FFmpeg Video Renderer (`rendering_engine`)
- **File Count:** 504
- **Lines of Code:** 61,762
- **Critical Files:** 478

<details>
<summary>Click to expand all 504 files in rendering_engine</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `remotion-app/README.md` | `ACTIVE_RUNTIME` | 39 | 947 |
| `remotion-app/build_caption_props.py` | `ACTIVE_RUNTIME` | 87 | 2,514 |
| `remotion-app/card_stack.json` | `ACTIVE_RUNTIME` | 25 | 3,639 |
| `remotion-app/carousel.json` | `ACTIVE_RUNTIME` | 24 | 3,401 |
| `remotion-app/components.json` | `ACTIVE_RUNTIME` | 22 | 518 |
| `remotion-app/dependency_tree.json` | `ACTIVE_RUNTIME` | 8 | 199 |
| `remotion-app/package-lock.json` | `ACTIVE_RUNTIME` | 7,746 | 342,505 |
| `remotion-app/package.json` | `ACTIVE_RUNTIME` | 45 | 1,508 |
| `remotion-app/public/logo.svg` | `ACTIVE_RUNTIME` | 0 | 5,669 |
| `remotion-app/public/media/icons/bookmark.svg` | `ACTIVE_RUNTIME` | 0 | 834 |
| `remotion-app/public/media/icons/bot.svg` | `ACTIVE_RUNTIME` | 0 | 1,319 |
| `remotion-app/public/media/icons/brain.svg` | `ACTIVE_RUNTIME` | 0 | 996 |
| `remotion-app/public/media/icons/calculator.svg` | `ACTIVE_RUNTIME` | 0 | 2,130 |
| `remotion-app/public/media/icons/code.svg` | `ACTIVE_RUNTIME` | 0 | 248 |
| `remotion-app/public/media/icons/database.svg` | `ACTIVE_RUNTIME` | 0 | 1,751 |
| `remotion-app/public/media/icons/laptop.svg` | `ACTIVE_RUNTIME` | 0 | 1,538 |
| `remotion-app/public/media/icons/moon.svg` | `ACTIVE_RUNTIME` | 0 | 1,114 |
| `remotion-app/public/media/icons/python.svg` | `ACTIVE_RUNTIME` | 0 | 1,316 |
| `remotion-app/public/media/icons/repeat.svg` | `ACTIVE_RUNTIME` | 0 | 1,180 |
| `remotion-app/public/media/icons/success.svg` | `ACTIVE_RUNTIME` | 0 | 291 |
| `remotion-app/public/media/icons/telegram.svg` | `ACTIVE_RUNTIME` | 0 | 739 |
| `remotion-app/public/render-props.json` | `ACTIVE_RUNTIME` | 19 | 562 |
| `remotion-app/public/warning.svg` | `ACTIVE_RUNTIME` | 0 | 1,180 |
| `remotion-app/remotion-ui.json` | `ACTIVE_RUNTIME` | 17 | 410 |
| `remotion-app/remotion.config.ts` | `ACTIVE_RUNTIME` | 82 | 3,430 |
| `remotion-app/skills-lock.json` | `ACTIVE_RUNTIME` | 17 | 497 |
| `remotion-app/src/BlueprintVideo.tsx` | `ACTIVE_RUNTIME` | 282 | 11,805 |
| `remotion-app/src/BrandContext.tsx` | `ACTIVE_RUNTIME` | 35 | 1,028 |
| `remotion-app/src/CanonicalVideo.tsx` | `ACTIVE_RUNTIME` | 464 | 16,746 |
| `remotion-app/src/CursorInteractionContext.tsx` | `ACTIVE_RUNTIME` | 5 | 229 |
| `remotion-app/src/Root.tsx` | `ACTIVE_RUNTIME` | 142 | 4,623 |
| `remotion-app/src/Showcase.tsx` | `ACTIVE_RUNTIME` | 66 | 3,557 |
| `remotion-app/src/TemplateGallery.tsx` | `ACTIVE_RUNTIME` | 99 | 3,541 |
| `remotion-app/src/animations.ts` | `ACTIVE_RUNTIME` | 121 | 4,454 |
| `remotion-app/src/captionLayout.ts` | `ACTIVE_RUNTIME` | 61 | 1,439 |
| `remotion-app/src/compositions/ai-composer-showcase/index.tsx` | `ACTIVE_RUNTIME` | 323 | 10,205 |
| `remotion-app/src/compositions/ai-generation-canvas/index.tsx` | `ACTIVE_RUNTIME` | 683 | 21,619 |
| `remotion-app/src/compositions/bento-pan/index.tsx` | `ACTIVE_RUNTIME` | 224 | 8,600 |
| `remotion-app/src/compositions/browser-flow/index.tsx` | `ACTIVE_RUNTIME` | 57 | 2,260 |
| `remotion-app/src/compositions/creator-reel/index.tsx` | `ACTIVE_RUNTIME` | 175 | 5,561 |
| `remotion-app/src/compositions/dashboard-populate/index.tsx` | `ACTIVE_RUNTIME` | 87 | 2,800 |
| `remotion-app/src/compositions/data-story/index.tsx` | `ACTIVE_RUNTIME` | 212 | 7,463 |
| `remotion-app/src/compositions/deploy-reveal/index.tsx` | `ACTIVE_RUNTIME` | 265 | 8,059 |
| `remotion-app/src/compositions/ecosystem-orbit/index.tsx` | `ACTIVE_RUNTIME` | 274 | 9,596 |
| `remotion-app/src/compositions/hero-device-assemble/index.tsx` | `ACTIVE_RUNTIME` | 474 | 13,841 |
| `remotion-app/src/compositions/hero-loop/index.tsx` | `ACTIVE_RUNTIME` | 828 | 25,786 |
| `remotion-app/src/compositions/image-expand/index.tsx` | `ACTIVE_RUNTIME` | 206 | 7,065 |
| `remotion-app/src/compositions/intro/index.tsx` | `ACTIVE_RUNTIME` | 168 | 4,824 |
| `remotion-app/src/compositions/landing-code-showcase/index.tsx` | `ACTIVE_RUNTIME` | 32 | 1,249 |
| `remotion-app/src/compositions/live-code-split/index.tsx` | `ACTIVE_RUNTIME` | 365 | 10,524 |
| `remotion-app/src/compositions/podcast-clip/index.tsx` | `ACTIVE_RUNTIME` | 299 | 9,551 |
| `remotion-app/src/compositions/pricing-focus/index.tsx` | `ACTIVE_RUNTIME` | 284 | 10,106 |
| `remotion-app/src/compositions/showcase/index.tsx` | `ACTIVE_RUNTIME` | 106 | 3,363 |
| `remotion-app/src/compositions/social-clip/index.tsx` | `ACTIVE_RUNTIME` | 101 | 3,261 |
| `remotion-app/src/compositions/tool-menu-slide/index.tsx` | `ACTIVE_RUNTIME` | 331 | 10,975 |
| `remotion-app/src/compositions/tutorial-clip/index.tsx` | `ACTIVE_RUNTIME` | 150 | 5,501 |
| `remotion-app/src/engine/audio/AudioManager.tsx` | `ACTIVE_RUNTIME` | 63 | 1,740 |
| `remotion-app/src/engine/audio/index.ts` | `ACTIVE_RUNTIME` | 8 | 215 |
| `remotion-app/src/engine/audio/resolveCues.ts` | `ACTIVE_RUNTIME` | 65 | 1,848 |
| `remotion-app/src/engine/audio/types.ts` | `ACTIVE_RUNTIME` | 27 | 489 |
| `remotion-app/src/engine/camera/AutoZoom.tsx` | `ACTIVE_RUNTIME` | 85 | 2,574 |
| `remotion-app/src/engine/camera/CameraRig.tsx` | `ACTIVE_RUNTIME` | 43 | 1,167 |
| `remotion-app/src/engine/camera/index.ts` | `ACTIVE_RUNTIME` | 11 | 370 |
| `remotion-app/src/engine/camera/interpolate.ts` | `ACTIVE_RUNTIME` | 48 | 1,428 |
| `remotion-app/src/engine/camera/resolveTimeline.ts` | `ACTIVE_RUNTIME` | 38 | 1,062 |
| `remotion-app/src/engine/camera/types.ts` | `ACTIVE_RUNTIME` | 26 | 469 |
| `remotion-app/src/engine/choreography/filterCursorPath.ts` | `ACTIVE_RUNTIME` | 18 | 573 |
| `remotion-app/src/engine/choreography/index.ts` | `ACTIVE_RUNTIME` | 4 | 220 |
| `remotion-app/src/engine/choreography/mapCursorPath.ts` | `ACTIVE_RUNTIME` | 93 | 2,861 |
| `remotion-app/src/engine/choreography/resolveWindowPose.ts` | `ACTIVE_RUNTIME` | 94 | 2,956 |
| `remotion-app/src/engine/cursor/Cursor.tsx` | `ACTIVE_RUNTIME` | 313 | 9,525 |
| `remotion-app/src/engine/cursor/CursorSprite.tsx` | `ACTIVE_RUNTIME` | 111 | 4,791 |
| `remotion-app/src/engine/cursor/arc.ts` | `ACTIVE_RUNTIME` | 124 | 3,291 |
| `remotion-app/src/engine/cursor/index.ts` | `ACTIVE_RUNTIME` | 17 | 570 |
| `remotion-app/src/engine/cursor/resolveAnchor.ts` | `ACTIVE_RUNTIME` | 52 | 1,432 |
| `remotion-app/src/engine/cursor/types.ts` | `ACTIVE_RUNTIME` | 67 | 1,438 |
| `remotion-app/src/engine/fonts.ts` | `ACTIVE_RUNTIME` | 9 | 327 |
| `remotion-app/src/engine/index.ts` | `ACTIVE_RUNTIME` | 96 | 1,650 |
| `remotion-app/src/engine/layout/LayoutContext.tsx` | `ACTIVE_RUNTIME` | 45 | 1,349 |
| `remotion-app/src/engine/layout/LayoutWindow.tsx` | `ACTIVE_RUNTIME` | 76 | 1,590 |
| `remotion-app/src/engine/layout/index.ts` | `ACTIVE_RUNTIME` | 13 | 379 |
| `remotion-app/src/engine/layout/types.ts` | `ACTIVE_RUNTIME` | 46 | 921 |
| `remotion-app/src/engine/layout/useWindowRect.ts` | `ACTIVE_RUNTIME` | 7 | 227 |
| `remotion-app/src/engine/layout/zones.ts` | `ACTIVE_RUNTIME` | 142 | 4,189 |
| `remotion-app/src/engine/primitives/CountUp.tsx` | `ACTIVE_RUNTIME` | 88 | 2,035 |
| `remotion-app/src/engine/primitives/EndCard.tsx` | `ACTIVE_RUNTIME` | 113 | 3,079 |
| `remotion-app/src/engine/primitives/Enter.tsx` | `ACTIVE_RUNTIME` | 69 | 1,827 |
| `remotion-app/src/engine/primitives/Exit.tsx` | `ACTIVE_RUNTIME` | 69 | 1,816 |
| `remotion-app/src/engine/primitives/Headline.tsx` | `ACTIVE_RUNTIME` | 277 | 8,474 |
| `remotion-app/src/engine/primitives/Highlight.tsx` | `ACTIVE_RUNTIME` | 102 | 2,582 |
| `remotion-app/src/engine/primitives/Pulse.tsx` | `ACTIVE_RUNTIME` | 66 | 1,426 |
| `remotion-app/src/engine/primitives/ScenePush.tsx` | `ACTIVE_RUNTIME` | 75 | 2,297 |
| `remotion-app/src/engine/primitives/Stagger.tsx` | `ACTIVE_RUNTIME` | 78 | 1,874 |
| `remotion-app/src/engine/primitives/TrafficLights.tsx` | `ACTIVE_RUNTIME` | 29 | 645 |
| `remotion-app/src/engine/primitives/TypeWriter.tsx` | `ACTIVE_RUNTIME` | 72 | 1,661 |
| `remotion-app/src/engine/primitives/Wallpaper.tsx` | `ACTIVE_RUNTIME` | 38 | 929 |
| `remotion-app/src/engine/primitives/Window.tsx` | `ACTIVE_RUNTIME` | 114 | 3,078 |
| `remotion-app/src/engine/primitives/app-ui/AppFromDescriptor.tsx` | `ACTIVE_RUNTIME` | 180 | 5,339 |
| `remotion-app/src/engine/primitives/app-ui/AppShell.tsx` | `ACTIVE_RUNTIME` | 71 | 1,830 |
| `remotion-app/src/engine/primitives/app-ui/Avatar.tsx` | `ACTIVE_RUNTIME` | 41 | 829 |
| `remotion-app/src/engine/primitives/app-ui/Badge.tsx` | `ACTIVE_RUNTIME` | 35 | 665 |
| `remotion-app/src/engine/primitives/app-ui/Button.tsx` | `ACTIVE_RUNTIME` | 85 | 2,310 |
| `remotion-app/src/engine/primitives/app-ui/DataTable.tsx` | `ACTIVE_RUNTIME` | 111 | 3,170 |
| `remotion-app/src/engine/primitives/app-ui/ListItems.tsx` | `ACTIVE_RUNTIME` | 59 | 1,575 |
| `remotion-app/src/engine/primitives/app-ui/MessageList.tsx` | `ACTIVE_RUNTIME` | 109 | 3,562 |
| `remotion-app/src/engine/primitives/app-ui/NotificationToast.tsx` | `ACTIVE_RUNTIME` | 74 | 2,086 |
| `remotion-app/src/engine/primitives/app-ui/Panel.tsx` | `ACTIVE_RUNTIME` | 75 | 1,622 |
| `remotion-app/src/engine/primitives/app-ui/PanelGrid.tsx` | `ACTIVE_RUNTIME` | 33 | 686 |
| `remotion-app/src/engine/primitives/app-ui/Placeholder.tsx` | `ACTIVE_RUNTIME` | 40 | 884 |
| `remotion-app/src/engine/primitives/app-ui/SearchBar.tsx` | `ACTIVE_RUNTIME` | 51 | 1,240 |
| `remotion-app/src/engine/primitives/app-ui/SidebarNav.tsx` | `ACTIVE_RUNTIME` | 120 | 3,368 |
| `remotion-app/src/engine/primitives/app-ui/StatCard.tsx` | `ACTIVE_RUNTIME` | 50 | 1,269 |
| `remotion-app/src/engine/primitives/app-ui/TabBar.tsx` | `ACTIVE_RUNTIME` | 82 | 2,011 |
| `remotion-app/src/engine/primitives/app-ui/TopNav.tsx` | `ACTIVE_RUNTIME` | 33 | 801 |
| `remotion-app/src/engine/primitives/app-ui/index.ts` | `ACTIVE_RUNTIME` | 47 | 1,762 |
| `remotion-app/src/engine/primitives/index.ts` | `ACTIVE_RUNTIME` | 24 | 1,191 |
| `remotion-app/src/engine/scenes/ChaosDesktop.tsx` | `ACTIVE_RUNTIME` | 249 | 10,605 |
| `remotion-app/src/engine/scenes/Closer.tsx` | `ACTIVE_RUNTIME` | 66 | 1,724 |
| `remotion-app/src/engine/scenes/DynamicWindows.tsx` | `ACTIVE_RUNTIME` | 66 | 1,968 |
| `remotion-app/src/engine/scenes/FeatureShowcase.tsx` | `ACTIVE_RUNTIME` | 130 | 5,478 |
| `remotion-app/src/engine/scenes/HeadlineResolution.tsx` | `ACTIVE_RUNTIME` | 25 | 821 |
| `remotion-app/src/engine/scenes/ProductReveal.tsx` | `ACTIVE_RUNTIME` | 179 | 7,225 |
| `remotion-app/src/engine/scenes/index.ts` | `ACTIVE_RUNTIME` | 5 | 248 |
| `remotion-app/src/engine/schema.ts` | `ACTIVE_RUNTIME` | 484 | 18,656 |
| `remotion-app/src/engine/tokens.ts` | `ACTIVE_RUNTIME` | 56 | 1,418 |
| `remotion-app/src/engine/types.ts` | `ACTIVE_RUNTIME` | 68 | 1,520 |
| `remotion-app/src/engine/ui-state/UIStateProvider.tsx` | `ACTIVE_RUNTIME` | 24 | 754 |
| `remotion-app/src/engine/ui-state/generatePressKeyframes.ts` | `ACTIVE_RUNTIME` | 25 | 676 |
| `remotion-app/src/engine/ui-state/index.ts` | `ACTIVE_RUNTIME` | 4 | 221 |
| `remotion-app/src/engine/ui-state/types.ts` | `ACTIVE_RUNTIME` | 39 | 879 |
| `remotion-app/src/fonts.ts` | `ACTIVE_RUNTIME` | 43 | 2,039 |
| `remotion-app/src/index.ts` | `ACTIVE_RUNTIME` | 5 | 172 |
| `remotion-app/src/lib/onda/canvas-schemas.ts` | `ACTIVE_RUNTIME` | 83 | 2,362 |
| `remotion-app/src/lib/onda/canvas.tsx` | `ACTIVE_RUNTIME` | 129 | 4,941 |
| `remotion-app/src/lib/onda/choreography.ts` | `ACTIVE_RUNTIME` | 416 | 13,492 |
| `remotion-app/src/lib/onda/easing.ts` | `ACTIVE_RUNTIME` | 27 | 1,014 |
| `remotion-app/src/lib/onda/elevation.ts` | `ACTIVE_RUNTIME` | 58 | 2,026 |
| `remotion-app/src/lib/onda/hooks.ts` | `ACTIVE_RUNTIME` | 242 | 8,514 |
| `remotion-app/src/lib/onda/motion.ts` | `ACTIVE_RUNTIME` | 114 | 4,183 |
| `remotion-app/src/lib/onda/primitives/Camera.tsx` | `ACTIVE_RUNTIME` | 74 | 2,657 |
| `remotion-app/src/lib/onda/primitives/Glow.tsx` | `ACTIVE_RUNTIME` | 44 | 1,229 |
| `remotion-app/src/lib/onda/primitives/GridField.tsx` | `ACTIVE_RUNTIME` | 46 | 1,475 |
| `remotion-app/src/lib/onda/primitives/Surface.tsx` | `ACTIVE_RUNTIME` | 81 | 2,587 |
| `remotion-app/src/lib/onda/primitives/index.ts` | `ACTIVE_RUNTIME` | 10 | 509 |
| `remotion-app/src/lib/onda/random.ts` | `ACTIVE_RUNTIME` | 26 | 899 |
| `remotion-app/src/lib/onda/timing.ts` | `ACTIVE_RUNTIME` | 103 | 3,650 |
| `remotion-app/src/lib/onda/tokens.ts` | `ACTIVE_RUNTIME` | 110 | 4,290 |
| `remotion-app/src/lib/remocn-ui/color.ts` | `ACTIVE_RUNTIME` | 87 | 2,430 |
| `remotion-app/src/lib/remocn-ui/index.ts` | `ACTIVE_RUNTIME` | 27 | 641 |
| `remotion-app/src/lib/remocn-ui/motion.ts` | `ACTIVE_RUNTIME` | 17 | 561 |
| `remotion-app/src/lib/remocn-ui/theme.ts` | `ACTIVE_RUNTIME` | 108 | 3,007 |
| `remotion-app/src/lib/remocn-ui/timeline.ts` | `ACTIVE_RUNTIME` | 96 | 2,767 |
| `remotion-app/src/lib/remocn-ui/types.ts` | `ACTIVE_RUNTIME` | 5 | 105 |
| `remotion-app/src/lib/snap-cn-ui/color.ts` | `ACTIVE_RUNTIME` | 101 | 3,047 |
| `remotion-app/src/lib/snap-cn-ui/fonts.ts` | `ACTIVE_RUNTIME` | 79 | 3,380 |
| `remotion-app/src/lib/snap-cn-ui/index.ts` | `ACTIVE_RUNTIME` | 29 | 714 |
| `remotion-app/src/lib/snap-cn-ui/motion.ts` | `ACTIVE_RUNTIME` | 17 | 561 |
| `remotion-app/src/lib/snap-cn-ui/theme.ts` | `ACTIVE_RUNTIME` | 151 | 5,274 |
| `remotion-app/src/lib/snap-cn-ui/timeline.ts` | `ACTIVE_RUNTIME` | 101 | 3,012 |
| `remotion-app/src/lib/snap-cn-ui/types.ts` | `ACTIVE_RUNTIME` | 5 | 105 |
| `remotion-app/src/loadProjectData.ts` | `ACTIVE_RUNTIME` | 63 | 2,350 |
| `remotion-app/src/merge.ts` | `ACTIVE_RUNTIME` | 66 | 2,298 |
| `remotion-app/src/remotion/hooks/use-stagger.ts` | `ACTIVE_RUNTIME` | 15 | 369 |
| `remotion-app/src/remotion/lib/ai-composer-utils.tsx` | `ACTIVE_RUNTIME` | 252 | 6,634 |
| `remotion-app/src/remotion/lib/audio-viz-utils.ts` | `ACTIVE_RUNTIME` | 528 | 16,397 |
| `remotion-app/src/remotion/lib/caption-utils.ts` | `ACTIVE_RUNTIME` | 279 | 9,011 |
| `remotion-app/src/remotion/lib/chart-utils.ts` | `ACTIVE_RUNTIME` | 265 | 8,324 |
| `remotion-app/src/remotion/lib/code-syntax.tsx` | `ACTIVE_RUNTIME` | 313 | 7,808 |
| `remotion-app/src/remotion/lib/displacement-presentation.tsx` | `ACTIVE_RUNTIME` | 213 | 7,961 |
| `remotion-app/src/remotion/lib/displacement-transition.ts` | `ACTIVE_RUNTIME` | 267 | 10,202 |
| `remotion-app/src/remotion/lib/gpu.ts` | `ACTIVE_RUNTIME` | 230 | 7,581 |
| `remotion-app/src/remotion/lib/layout.ts` | `ACTIVE_RUNTIME` | 95 | 2,697 |
| `remotion-app/src/remotion/lib/map-utils.ts` | `ACTIVE_RUNTIME` | 187 | 4,974 |
| `remotion-app/src/remotion/lib/media-utils.ts` | `ACTIVE_RUNTIME` | 63 | 1,363 |
| `remotion-app/src/remotion/lib/motion-primitive.ts` | `ACTIVE_RUNTIME` | 245 | 7,956 |
| `remotion-app/src/remotion/lib/motion-tokens.ts` | `ACTIVE_RUNTIME` | 51 | 1,643 |
| `remotion-app/src/remotion/lib/motion-wrapper.tsx` | `ACTIVE_RUNTIME` | 37 | 988 |
| `remotion-app/src/remotion/lib/path-morph.ts` | `ACTIVE_RUNTIME` | 261 | 9,037 |
| `remotion-app/src/remotion/lib/path-utils.ts` | `ACTIVE_RUNTIME` | 184 | 5,494 |
| `remotion-app/src/remotion/lib/sample-media.ts` | `ACTIVE_RUNTIME` | 77 | 4,231 |
| `remotion-app/src/remotion/lib/springs.ts` | `ACTIVE_RUNTIME` | 22 | 431 |
| `remotion-app/src/remotion/lib/text-emphasis.ts` | `ACTIVE_RUNTIME` | 74 | 2,432 |
| `remotion-app/src/remotion/lib/text-fit-utils.ts` | `ACTIVE_RUNTIME` | 24 | 691 |
| `remotion-app/src/remotion/lib/text-split.ts` | `ACTIVE_RUNTIME` | 455 | 14,390 |
| `remotion-app/src/remotion/lib/timing.ts` | `ACTIVE_RUNTIME` | 63 | 1,569 |
| `remotion-app/src/remotion/lib/transition-timing.ts` | `ACTIVE_RUNTIME` | 142 | 5,141 |
| `remotion-app/src/remotion/primitives/audio-pulse.tsx` | `ACTIVE_RUNTIME` | 118 | 4,057 |
| `remotion-app/src/remotion/primitives/audiogram-bars.tsx` | `ACTIVE_RUNTIME` | 203 | 5,825 |
| `remotion-app/src/remotion/primitives/caption-highlight.tsx` | `ACTIVE_RUNTIME` | 124 | 3,873 |
| `remotion-app/src/remotion/primitives/counter.tsx` | `ACTIVE_RUNTIME` | 404 | 13,289 |
| `remotion-app/src/remotion/primitives/directional-wipe.tsx` | `ACTIVE_RUNTIME` | 135 | 4,175 |
| `remotion-app/src/remotion/primitives/fade-in.tsx` | `ACTIVE_RUNTIME` | 42 | 1,154 |
| `remotion-app/src/remotion/primitives/fade-out.tsx` | `ACTIVE_RUNTIME` | 58 | 1,704 |
| `remotion-app/src/remotion/primitives/karaoke-captions.tsx` | `ACTIVE_RUNTIME` | 167 | 5,303 |
| `remotion-app/src/remotion/primitives/line-chart-draw.tsx` | `ACTIVE_RUNTIME` | 311 | 10,246 |
| `remotion-app/src/remotion/primitives/map-markers.tsx` | `ACTIVE_RUNTIME` | 195 | 5,444 |
| `remotion-app/src/remotion/primitives/map-route.tsx` | `ACTIVE_RUNTIME` | 229 | 6,126 |
| `remotion-app/src/remotion/primitives/multi-device-lineup.tsx` | `ACTIVE_RUNTIME` | 274 | 9,024 |
| `remotion-app/src/remotion/primitives/path-draw.tsx` | `ACTIVE_RUNTIME` | 146 | 4,749 |
| `remotion-app/src/remotion/primitives/slide-up.tsx` | `ACTIVE_RUNTIME` | 82 | 2,327 |
| `remotion-app/src/remotion/primitives/spring-in.tsx` | `ACTIVE_RUNTIME` | 66 | 1,855 |
| `remotion-app/src/remotion/primitives/stagger-children.tsx` | `ACTIVE_RUNTIME` | 126 | 4,029 |
| `remotion-app/src/remotion/primitives/transition-fade.tsx` | `ACTIVE_RUNTIME` | 89 | 2,745 |
| `remotion-app/src/remotion/primitives/transition-slide.tsx` | `ACTIVE_RUNTIME` | 37 | 1,008 |
| `remotion-app/src/remotion/primitives/transition-wipe.tsx` | `ACTIVE_RUNTIME` | 36 | 936 |
| `remotion-app/src/remotion/primitives/typewriter.tsx` | `ACTIVE_RUNTIME` | 399 | 11,234 |
| `remotion-app/src/remotion/primitives/waveform-line.tsx` | `ACTIVE_RUNTIME` | 297 | 8,992 |
| `remotion-app/src/remotion/scenes/animated-bar-chart/index.tsx` | `ACTIVE_RUNTIME` | 413 | 13,928 |
| `remotion-app/src/remotion/scenes/audiogram-scene/index.tsx` | `ACTIVE_RUNTIME` | 134 | 4,091 |
| `remotion-app/src/remotion/scenes/auto-fit-title/index.tsx` | `ACTIVE_RUNTIME` | 213 | 6,548 |
| `remotion-app/src/remotion/scenes/b-roll-stack/index.tsx` | `ACTIVE_RUNTIME` | 360 | 12,142 |
| `remotion-app/src/remotion/scenes/calendar-month-fill/index.tsx` | `ACTIVE_RUNTIME` | 339 | 11,409 |
| `remotion-app/src/remotion/scenes/callout-spotlight/index.tsx` | `ACTIVE_RUNTIME` | 322 | 10,237 |
| `remotion-app/src/remotion/scenes/caption-bumper/index.tsx` | `ACTIVE_RUNTIME` | 227 | 7,168 |
| `remotion-app/src/remotion/scenes/caption-scene/index.tsx` | `ACTIVE_RUNTIME` | 373 | 10,646 |
| `remotion-app/src/remotion/scenes/changelog-entry/index.tsx` | `ACTIVE_RUNTIME` | 291 | 9,310 |
| `remotion-app/src/remotion/scenes/chat-gpt/index.tsx` | `ACTIVE_RUNTIME` | 556 | 14,727 |
| `remotion-app/src/remotion/scenes/chat-to-preview/index.tsx` | `ACTIVE_RUNTIME` | 809 | 26,905 |
| `remotion-app/src/remotion/scenes/claude-chat/index.tsx` | `ACTIVE_RUNTIME` | 437 | 11,958 |
| `remotion-app/src/remotion/scenes/claude-code/index.tsx` | `ACTIVE_RUNTIME` | 344 | 10,498 |
| `remotion-app/src/remotion/scenes/code-accordion/index.tsx` | `ACTIVE_RUNTIME` | 457 | 14,928 |
| `remotion-app/src/remotion/scenes/code-diff-wipe/index.tsx` | `ACTIVE_RUNTIME` | 475 | 15,420 |
| `remotion-app/src/remotion/scenes/code-reveal/index.tsx` | `ACTIVE_RUNTIME` | 494 | 16,755 |
| `remotion-app/src/remotion/scenes/comment-callout/index.tsx` | `ACTIVE_RUNTIME` | 517 | 16,666 |
| `remotion-app/src/remotion/scenes/commit-graph/index.tsx` | `ACTIVE_RUNTIME` | 372 | 13,036 |
| `remotion-app/src/remotion/scenes/comparison-table/index.tsx` | `ACTIVE_RUNTIME` | 358 | 12,053 |
| `remotion-app/src/remotion/scenes/countdown-timer/index.tsx` | `ACTIVE_RUNTIME` | 223 | 6,703 |
| `remotion-app/src/remotion/scenes/data-flow-pipes/index.tsx` | `ACTIVE_RUNTIME` | 458 | 15,196 |
| `remotion-app/src/remotion/scenes/device-mockup-zoom/index.tsx` | `ACTIVE_RUNTIME` | 950 | 27,884 |
| `remotion-app/src/remotion/scenes/drag-drop-flow/index.tsx` | `ACTIVE_RUNTIME` | 665 | 21,153 |
| `remotion-app/src/remotion/scenes/end-card/index.tsx` | `ACTIVE_RUNTIME` | 364 | 11,366 |
| `remotion-app/src/remotion/scenes/faq-accordion/index.tsx` | `ACTIVE_RUNTIME` | 307 | 10,644 |
| `remotion-app/src/remotion/scenes/feature-list/index.tsx` | `ACTIVE_RUNTIME` | 290 | 9,165 |
| `remotion-app/src/remotion/scenes/file-tree-reveal/index.tsx` | `ACTIVE_RUNTIME` | 402 | 13,834 |
| `remotion-app/src/remotion/scenes/form-fill-sequence/index.tsx` | `ACTIVE_RUNTIME` | 388 | 13,752 |
| `remotion-app/src/remotion/scenes/hook-card/index.tsx` | `ACTIVE_RUNTIME` | 385 | 13,450 |
| `remotion-app/src/remotion/scenes/kanban-move/index.tsx` | `ACTIVE_RUNTIME` | 418 | 14,859 |
| `remotion-app/src/remotion/scenes/logo-reveal/index.tsx` | `ACTIVE_RUNTIME` | 221 | 6,497 |
| `remotion-app/src/remotion/scenes/logo-wall/index.tsx` | `ACTIVE_RUNTIME` | 265 | 9,167 |
| `remotion-app/src/remotion/scenes/lower-third/index.tsx` | `ACTIVE_RUNTIME` | 215 | 7,161 |
| `remotion-app/src/remotion/scenes/map-flight/index.tsx` | `ACTIVE_RUNTIME` | 243 | 6,729 |
| `remotion-app/src/remotion/scenes/media-frame/index.tsx` | `ACTIVE_RUNTIME` | 282 | 8,926 |
| `remotion-app/src/remotion/scenes/media-sequence/index.tsx` | `ACTIVE_RUNTIME` | 169 | 5,862 |
| `remotion-app/src/remotion/scenes/metric-ticker/index.tsx` | `ACTIVE_RUNTIME` | 307 | 10,599 |
| `remotion-app/src/remotion/scenes/news-ticker-bar/index.tsx` | `ACTIVE_RUNTIME` | 256 | 8,023 |
| `remotion-app/src/remotion/scenes/notification-stack/index.tsx` | `ACTIVE_RUNTIME` | 362 | 12,714 |
| `remotion-app/src/remotion/scenes/opencode/index.tsx` | `ACTIVE_RUNTIME` | 232 | 6,891 |
| `remotion-app/src/remotion/scenes/org-chart-build/index.tsx` | `ACTIVE_RUNTIME` | 387 | 13,661 |
| `remotion-app/src/remotion/scenes/poll-overlay/index.tsx` | `ACTIVE_RUNTIME` | 320 | 11,293 |
| `remotion-app/src/remotion/scenes/pricing-card/index.tsx` | `ACTIVE_RUNTIME` | 394 | 12,923 |
| `remotion-app/src/remotion/scenes/quiz-question/index.tsx` | `ACTIVE_RUNTIME` | 302 | 10,542 |
| `remotion-app/src/remotion/scenes/quote-card/index.tsx` | `ACTIVE_RUNTIME` | 373 | 11,818 |
| `remotion-app/src/remotion/scenes/reaction-burst/index.tsx` | `ACTIVE_RUNTIME` | 185 | 6,629 |
| `remotion-app/src/remotion/scenes/roadmap-lanes/index.tsx` | `ACTIVE_RUNTIME` | 355 | 12,168 |
| `remotion-app/src/remotion/scenes/search-results-populate/index.tsx` | `ACTIVE_RUNTIME` | 417 | 14,994 |
| `remotion-app/src/remotion/scenes/split-screen/index.tsx` | `ACTIVE_RUNTIME` | 314 | 10,075 |
| `remotion-app/src/remotion/scenes/sports-scorebug/index.tsx` | `ACTIVE_RUNTIME` | 320 | 9,626 |
| `remotion-app/src/remotion/scenes/stat-card/index.tsx` | `ACTIVE_RUNTIME` | 309 | 9,819 |
| `remotion-app/src/remotion/scenes/tab-switch-panel/index.tsx` | `ACTIVE_RUNTIME` | 431 | 15,094 |
| `remotion-app/src/remotion/scenes/talking-head-layout/index.tsx` | `ACTIVE_RUNTIME` | 505 | 17,920 |
| `remotion-app/src/remotion/scenes/team-grid/index.tsx` | `ACTIVE_RUNTIME` | 287 | 9,163 |
| `remotion-app/src/remotion/scenes/terminal-simulator/index.tsx` | `ACTIVE_RUNTIME` | 720 | 21,822 |
| `remotion-app/src/remotion/scenes/timeline-steps/index.tsx` | `ACTIVE_RUNTIME` | 430 | 14,357 |
| `remotion-app/src/remotion/scenes/title-card/index.tsx` | `ACTIVE_RUNTIME` | 316 | 9,980 |
| `remotion-app/src/remotion/scenes/v0/index.tsx` | `ACTIVE_RUNTIME` | 434 | 12,573 |
| `remotion-app/src/remotion/scenes/weather-card/index.tsx` | `ACTIVE_RUNTIME` | 453 | 14,502 |
| `remotion-app/src/remotion/scenes/zoom-pan-frame/index.tsx` | `ACTIVE_RUNTIME` | 190 | 5,909 |
| `remotion-app/src/rtl.css` | `ACTIVE_RUNTIME` | 0 | 267 |
| `remotion-app/src/templates/brand-resolver.ts` | `ACTIVE_RUNTIME` | 32 | 1,330 |
| `remotion-app/src/templates/custom/LevelOneScene.tsx` | `ACTIVE_RUNTIME` | 38 | 1,239 |
| `remotion-app/src/templates/custom/LevelZeroBox.tsx` | `ACTIVE_RUNTIME` | 33 | 1,035 |
| `remotion-app/src/templates/effects/BookFlipTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 836 |
| `remotion-app/src/templates/effects/ClockWipeTransition.tsx` | `ACTIVE_RUNTIME` | 23 | 936 |
| `remotion-app/src/templates/effects/CrossZoomTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 840 |
| `remotion-app/src/templates/effects/CrosswarpTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 839 |
| `remotion-app/src/templates/effects/DissolveTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 835 |
| `remotion-app/src/templates/effects/DreamyZoomTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 844 |
| `remotion-app/src/templates/effects/FadeTransition.tsx` | `ACTIVE_RUNTIME` | 21 | 886 |
| `remotion-app/src/templates/effects/FilmBurnTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 836 |
| `remotion-app/src/templates/effects/FlipTransition.tsx` | `ACTIVE_RUNTIME` | 22 | 895 |
| `remotion-app/src/templates/effects/IrisTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 819 |
| `remotion-app/src/templates/effects/LinearBlurTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 844 |
| `remotion-app/src/templates/effects/PushCutTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 832 |
| `remotion-app/src/templates/effects/RippleTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 827 |
| `remotion-app/src/templates/effects/SlideTransition.tsx` | `ACTIVE_RUNTIME` | 21 | 894 |
| `remotion-app/src/templates/effects/SwapTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 819 |
| `remotion-app/src/templates/effects/WipeTransition.tsx` | `ACTIVE_RUNTIME` | 21 | 890 |
| `remotion-app/src/templates/effects/ZoomBlurTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 836 |
| `remotion-app/src/templates/effects/ZoomInOutTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 841 |
| `remotion-app/src/templates/effects/engine-bridge.tsx` | `ACTIVE_RUNTIME` | 31 | 1,154 |
| `remotion-app/src/templates/elements/AnimatedBarChartWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 523 |
| `remotion-app/src/templates/elements/AnimatedCounterWrapper.tsx` | `ACTIVE_RUNTIME` | 33 | 1,124 |
| `remotion-app/src/templates/elements/AnimatedTextWrapper.tsx` | `ACTIVE_RUNTIME` | 30 | 998 |
| `remotion-app/src/templates/elements/AutoFitTitleWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 507 |
| `remotion-app/src/templates/elements/BRollStackWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 536 |
| `remotion-app/src/templates/elements/BentoPanWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 409 |
| `remotion-app/src/templates/elements/CalendarMonthFillWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 449 |
| `remotion-app/src/templates/elements/CalloutSpotlightWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 522 |
| `remotion-app/src/templates/elements/CaptionBumperWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 465 |
| `remotion-app/src/templates/elements/ChangelogEntryWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 436 |
| `remotion-app/src/templates/elements/ChatToPreviewWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 529 |
| `remotion-app/src/templates/elements/CodeAccordionWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 466 |
| `remotion-app/src/templates/elements/CodeBlockWrapper.tsx` | `ACTIVE_RUNTIME` | 25 | 871 |
| `remotion-app/src/templates/elements/CodeDiffWipeWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 463 |
| `remotion-app/src/templates/elements/CodeRevealWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 454 |
| `remotion-app/src/templates/elements/CommentCalloutWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 436 |
| `remotion-app/src/templates/elements/CommitGraphWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 424 |
| `remotion-app/src/templates/elements/ComparisonTableWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 474 |
| `remotion-app/src/templates/elements/CountdownTimerWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 470 |
| `remotion-app/src/templates/elements/DashboardPopulateWrapper.tsx` | `ACTIVE_RUNTIME` | 32 | 1,167 |
| `remotion-app/src/templates/elements/DeployRevealWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 425 |
| `remotion-app/src/templates/elements/DeviceMockupZoomWrapper.tsx` | `ACTIVE_RUNTIME` | 32 | 1,574 |
| `remotion-app/src/templates/elements/EndCardWrapper.tsx` | `ACTIVE_RUNTIME` | 16 | 615 |
| `remotion-app/src/templates/elements/FaqAccordionWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 543 |
| `remotion-app/src/templates/elements/FeatureListWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 458 |
| `remotion-app/src/templates/elements/FileTreeRevealWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 471 |
| `remotion-app/src/templates/elements/GradientWrapper.tsx` | `ACTIVE_RUNTIME` | 18 | 603 |
| `remotion-app/src/templates/elements/HookCardWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 455 |
| `remotion-app/src/templates/elements/ImageExpandWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 499 |
| `remotion-app/src/templates/elements/KanbanMoveWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 420 |
| `remotion-app/src/templates/elements/LogoRevealWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 420 |
| `remotion-app/src/templates/elements/LogoWallWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 446 |
| `remotion-app/src/templates/elements/LowerThirdWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 498 |
| `remotion-app/src/templates/elements/MapFlightWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 416 |
| `remotion-app/src/templates/elements/MatrixRainWrapper.tsx` | `ACTIVE_RUNTIME` | 20 | 1,081 |
| `remotion-app/src/templates/elements/MediaFrameWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 454 |
| `remotion-app/src/templates/elements/MetricTickerWrapper.tsx` | `ACTIVE_RUNTIME` | 19 | 760 |
| `remotion-app/src/templates/elements/NewsTickerBarWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 433 |
| `remotion-app/src/templates/elements/NotificationStackWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 448 |
| `remotion-app/src/templates/elements/OrgChartBuildWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 467 |
| `remotion-app/src/templates/elements/ParticleSystemWrapper.tsx` | `ACTIVE_RUNTIME` | 22 | 1,254 |
| `remotion-app/src/templates/elements/PodcastClipWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 499 |
| `remotion-app/src/templates/elements/PollOverlayWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 424 |
| `remotion-app/src/templates/elements/PricingCardWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 424 |
| `remotion-app/src/templates/elements/PricingFocusWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 425 |
| `remotion-app/src/templates/elements/QuizQuestionWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 428 |
| `remotion-app/src/templates/elements/QuoteCardWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 416 |
| `remotion-app/src/templates/elements/ReactionBurstWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 432 |
| `remotion-app/src/templates/elements/RoadmapLanesWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 462 |
| `remotion-app/src/templates/elements/Scene3DWrapper.tsx` | `ACTIVE_RUNTIME` | 17 | 619 |
| `remotion-app/src/templates/elements/ScrollingImagesWrapper.tsx` | `ACTIVE_RUNTIME` | 29 | 1,077 |
| `remotion-app/src/templates/elements/SearchResultsPopulateWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 465 |
| `remotion-app/src/templates/elements/SocialClipWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 417 |
| `remotion-app/src/templates/elements/SportsScorebugWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 436 |
| `remotion-app/src/templates/elements/StaggeredMotionWrapper.tsx` | `ACTIVE_RUNTIME` | 33 | 1,260 |
| `remotion-app/src/templates/elements/StatCardWrapper.tsx` | `ACTIVE_RUNTIME` | 19 | 750 |
| `remotion-app/src/templates/elements/THEMESWrapper.tsx` | `ACTIVE_RUNTIME` | 8 | 278 |
| `remotion-app/src/templates/elements/TabSwitchPanelWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 437 |
| `remotion-app/src/templates/elements/TerminalSimulatorWrapper.tsx` | `ACTIVE_RUNTIME` | 22 | 830 |
| `remotion-app/src/templates/elements/TimelineStepsWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 466 |
| `remotion-app/src/templates/elements/TitleCardWrapper.tsx` | `ACTIVE_RUNTIME` | 15 | 784 |
| `remotion-app/src/templates/elements/TutorialClipWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 503 |
| `remotion-app/src/templates/elements/TypeWriterWrapper.tsx` | `ACTIVE_RUNTIME` | 25 | 897 |
| `remotion-app/src/templates/elements/WeatherCardWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 424 |
| `remotion-app/src/templates/elements/ZoomPanFrameWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 463 |
| `remotion-app/src/templates/scenes/AiComposerShowcaseWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 450 |
| `remotion-app/src/templates/scenes/AiGenerationCanvasWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 450 |
| `remotion-app/src/templates/scenes/AudiogramSceneWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 514 |
| `remotion-app/src/templates/scenes/BrowserFlowWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 494 |
| `remotion-app/src/templates/scenes/CaptionSceneWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 462 |
| `remotion-app/src/templates/scenes/CreatorReelWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 421 |
| `remotion-app/src/templates/scenes/DataFlowPipesWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 433 |
| `remotion-app/src/templates/scenes/DataStoryWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 491 |
| `remotion-app/src/templates/scenes/DragDropFlowWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 463 |
| `remotion-app/src/templates/scenes/EcosystemOrbitWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 433 |
| `remotion-app/src/templates/scenes/FormFillSequenceWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 523 |
| `remotion-app/src/templates/scenes/HeroDeviceAssembleWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 528 |
| `remotion-app/src/templates/scenes/HeroLoopWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 409 |
| `remotion-app/src/templates/scenes/IntroWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 474 |
| `remotion-app/src/templates/scenes/LandingCodeShowcaseWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 454 |
| `remotion-app/src/templates/scenes/LiveCodeSplitWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 430 |
| `remotion-app/src/templates/scenes/MediaSequenceWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 512 |
| `remotion-app/src/templates/scenes/ShowcaseWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 486 |
| `remotion-app/src/templates/scenes/SplitScreenWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 458 |
| `remotion-app/src/templates/scenes/TalkingHeadLayoutWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 527 |
| `remotion-app/src/templates/scenes/TeamGridWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 490 |
| `remotion-app/src/templates/scenes/ToolMenuSlideWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 430 |
| `remotion-app/src/types/ai_contracts.ts` | `ACTIVE_RUNTIME` | 1,537 | 40,705 |
| `remotion-app/src/types/creative_contracts.ts` | `ACTIVE_RUNTIME` | 930 | 27,740 |
| `remotion-app/src/types/state.ts` | `ACTIVE_RUNTIME` | 60 | 1,619 |
| `remotion-app/tsconfig.json` | `ACTIVE_RUNTIME` | 81 | 1,998 |
| `scripts/generators/__init__.py` | `ACTIVE_RUNTIME` | 0 | 0 |
| `scripts/generators/build_asset_index.py` | `ACTIVE_RUNTIME` | 91 | 3,346 |
| `scripts/generators/build_catalog.py` | `ACTIVE_RUNTIME` | 57 | 1,935 |
| `scripts/generators/build_ground_truth.py` | `ACTIVE_RUNTIME` | 298 | 15,239 |
| `scripts/generators/generate_drift_matrix.py` | `ACTIVE_RUNTIME` | 103 | 4,076 |
| `scripts/generators/generate_matrix.ts` | `ACTIVE_RUNTIME` | 52 | 2,228 |
| `scripts/generators/generate_plan.py` | `ACTIVE_RUNTIME` | 80 | 3,158 |
| `scripts/generators/generate_registry.ts` | `ACTIVE_RUNTIME` | 456 | 19,427 |
| `scripts/generators/generate_s28_legacy_inventory.py` | `ACTIVE_RUNTIME` | 305 | 30,881 |
| `scripts/generators/generate_schema.ts` | `ACTIVE_RUNTIME` | 32 | 1,500 |
| `scripts/generators/generate_template_aliases.py` | `ACTIVE_RUNTIME` | 50 | 1,669 |
| `scripts/generators/generate_template_contract.py` | `ACTIVE_RUNTIME` | 256 | 10,394 |
| `scripts/generators/materialize_project.py` | `ACTIVE_RUNTIME` | 89 | 3,611 |
| `scripts/render_project.py` | `ACTIVE_RUNTIME` | 289 | 12,941 |
| `templates/brand-resolver.ts` | `ACTIVE_RUNTIME` | 32 | 1,330 |
| `templates/custom/LevelOneScene.tsx` | `ACTIVE_RUNTIME` | 38 | 1,239 |
| `templates/custom/LevelZeroBox.tsx` | `ACTIVE_RUNTIME` | 33 | 1,035 |
| `templates/effects/BookFlipTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 836 |
| `templates/effects/ClockWipeTransition.tsx` | `ACTIVE_RUNTIME` | 23 | 936 |
| `templates/effects/CrossZoomTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 840 |
| `templates/effects/CrosswarpTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 839 |
| `templates/effects/DissolveTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 835 |
| `templates/effects/DreamyZoomTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 844 |
| `templates/effects/FadeTransition.tsx` | `ACTIVE_RUNTIME` | 21 | 886 |
| `templates/effects/FilmBurnTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 836 |
| `templates/effects/FlipTransition.tsx` | `ACTIVE_RUNTIME` | 22 | 895 |
| `templates/effects/IrisTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 819 |
| `templates/effects/LinearBlurTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 844 |
| `templates/effects/PushCutTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 832 |
| `templates/effects/RippleTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 827 |
| `templates/effects/SlideTransition.tsx` | `ACTIVE_RUNTIME` | 21 | 894 |
| `templates/effects/SwapTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 819 |
| `templates/effects/WipeTransition.tsx` | `ACTIVE_RUNTIME` | 21 | 890 |
| `templates/effects/ZoomBlurTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 836 |
| `templates/effects/ZoomInOutTransition.tsx` | `ACTIVE_RUNTIME` | 20 | 841 |
| `templates/effects/engine-bridge.tsx` | `ACTIVE_RUNTIME` | 31 | 1,154 |
| `templates/elements/AnimatedBarChartWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 523 |
| `templates/elements/AnimatedCounterWrapper.tsx` | `ACTIVE_RUNTIME` | 33 | 1,124 |
| `templates/elements/AnimatedTextWrapper.tsx` | `ACTIVE_RUNTIME` | 30 | 998 |
| `templates/elements/AutoFitTitleWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 507 |
| `templates/elements/BRollStackWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 536 |
| `templates/elements/BentoPanWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 409 |
| `templates/elements/CalendarMonthFillWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 449 |
| `templates/elements/CalloutSpotlightWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 522 |
| `templates/elements/CaptionBumperWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 465 |
| `templates/elements/ChangelogEntryWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 436 |
| `templates/elements/ChatToPreviewWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 529 |
| `templates/elements/CodeAccordionWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 466 |
| `templates/elements/CodeBlockWrapper.tsx` | `ACTIVE_RUNTIME` | 25 | 871 |
| `templates/elements/CodeDiffWipeWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 463 |
| `templates/elements/CodeRevealWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 454 |
| `templates/elements/CommentCalloutWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 436 |
| `templates/elements/CommitGraphWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 424 |
| `templates/elements/ComparisonTableWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 474 |
| `templates/elements/CountdownTimerWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 470 |
| `templates/elements/DashboardPopulateWrapper.tsx` | `ACTIVE_RUNTIME` | 32 | 1,167 |
| `templates/elements/DeployRevealWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 425 |
| `templates/elements/DeviceMockupZoomWrapper.tsx` | `ACTIVE_RUNTIME` | 32 | 1,574 |
| `templates/elements/EndCardWrapper.tsx` | `ACTIVE_RUNTIME` | 16 | 615 |
| `templates/elements/FaqAccordionWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 543 |
| `templates/elements/FeatureListWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 458 |
| `templates/elements/FileTreeRevealWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 471 |
| `templates/elements/GradientWrapper.tsx` | `ACTIVE_RUNTIME` | 18 | 603 |
| `templates/elements/HookCardWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 455 |
| `templates/elements/ImageExpandWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 499 |
| `templates/elements/KanbanMoveWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 420 |
| `templates/elements/LogoRevealWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 420 |
| `templates/elements/LogoWallWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 446 |
| `templates/elements/LowerThirdWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 498 |
| `templates/elements/MapFlightWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 416 |
| `templates/elements/MatrixRainWrapper.tsx` | `ACTIVE_RUNTIME` | 20 | 1,081 |
| `templates/elements/MediaFrameWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 454 |
| `templates/elements/MetricTickerWrapper.tsx` | `ACTIVE_RUNTIME` | 19 | 760 |
| `templates/elements/NewsTickerBarWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 433 |
| `templates/elements/NotificationStackWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 448 |
| `templates/elements/OrgChartBuildWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 467 |
| `templates/elements/ParticleSystemWrapper.tsx` | `ACTIVE_RUNTIME` | 22 | 1,254 |
| `templates/elements/PodcastClipWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 499 |
| `templates/elements/PollOverlayWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 424 |
| `templates/elements/PricingCardWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 424 |
| `templates/elements/PricingFocusWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 425 |
| `templates/elements/QuizQuestionWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 428 |
| `templates/elements/QuoteCardWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 416 |
| `templates/elements/ReactionBurstWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 432 |
| `templates/elements/RoadmapLanesWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 462 |
| `templates/elements/Scene3DWrapper.tsx` | `ACTIVE_RUNTIME` | 17 | 619 |
| `templates/elements/ScrollingImagesWrapper.tsx` | `ACTIVE_RUNTIME` | 29 | 1,077 |
| `templates/elements/SearchResultsPopulateWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 465 |
| `templates/elements/SocialClipWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 417 |
| `templates/elements/SportsScorebugWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 436 |
| `templates/elements/StaggeredMotionWrapper.tsx` | `ACTIVE_RUNTIME` | 33 | 1,260 |
| `templates/elements/StatCardWrapper.tsx` | `ACTIVE_RUNTIME` | 19 | 750 |
| `templates/elements/THEMESWrapper.tsx` | `ACTIVE_RUNTIME` | 8 | 278 |
| `templates/elements/TabSwitchPanelWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 437 |
| `templates/elements/TerminalSimulatorWrapper.tsx` | `ACTIVE_RUNTIME` | 22 | 830 |
| `templates/elements/TimelineStepsWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 466 |
| `templates/elements/TitleCardWrapper.tsx` | `ACTIVE_RUNTIME` | 15 | 784 |
| `templates/elements/TutorialClipWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 503 |
| `templates/elements/TypeWriterWrapper.tsx` | `ACTIVE_RUNTIME` | 25 | 897 |
| `templates/elements/WeatherCardWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 424 |
| `templates/elements/ZoomPanFrameWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 463 |
| `templates/scenes/AiComposerShowcaseWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 450 |
| `templates/scenes/AiGenerationCanvasWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 450 |
| `templates/scenes/AudiogramSceneWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 514 |
| `templates/scenes/BrowserFlowWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 494 |
| `templates/scenes/CaptionSceneWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 462 |
| `templates/scenes/CreatorReelWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 421 |
| `templates/scenes/DataFlowPipesWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 433 |
| `templates/scenes/DataStoryWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 491 |
| `templates/scenes/DragDropFlowWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 463 |
| `templates/scenes/EcosystemOrbitWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 433 |
| `templates/scenes/FormFillSequenceWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 523 |
| `templates/scenes/HeroDeviceAssembleWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 528 |
| `templates/scenes/HeroLoopWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 409 |
| `templates/scenes/IntroWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 474 |
| `templates/scenes/LandingCodeShowcaseWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 454 |
| `templates/scenes/LiveCodeSplitWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 430 |
| `templates/scenes/MediaSequenceWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 512 |
| `templates/scenes/ShowcaseWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 486 |
| `templates/scenes/SplitScreenWrapper.tsx` | `ACTIVE_RUNTIME` | 19 | 772 |
| `templates/scenes/TalkingHeadLayoutWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 527 |
| `templates/scenes/TeamGridWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 490 |
| `templates/scenes/ToolMenuSlideWrapper.tsx` | `ACTIVE_RUNTIME` | 12 | 430 |

</details>

### Subsystem: Review, Governance & Approvals (`review_governance`)
- **File Count:** 25
- **Lines of Code:** 5,313
- **Critical Files:** 25

<details>
<summary>Click to expand all 25 files in review_governance</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `creative_governance/__init__.py` | `ACTIVE_RUNTIME` | 9 | 293 |
| `creative_governance/candidates/__init__.py` | `ACTIVE_RUNTIME` | 114 | 3,387 |
| `creative_governance/candidates/errors.py` | `ACTIVE_RUNTIME` | 98 | 2,977 |
| `creative_governance/candidates/gates/__init__.py` | `ACTIVE_RUNTIME` | 37 | 1,486 |
| `creative_governance/candidates/gates/aspect_gate.py` | `ACTIVE_RUNTIME` | 169 | 6,484 |
| `creative_governance/candidates/gates/ast_runner.py` | `ACTIVE_RUNTIME` | 75 | 2,251 |
| `creative_governance/candidates/gates/base.py` | `ACTIVE_RUNTIME` | 70 | 1,815 |
| `creative_governance/candidates/gates/candidate_qc_gate.py` | `ACTIVE_RUNTIME` | 190 | 8,243 |
| `creative_governance/candidates/gates/contract_gate.py` | `ACTIVE_RUNTIME` | 203 | 9,272 |
| `creative_governance/candidates/gates/dependency_gate.py` | `ACTIVE_RUNTIME` | 199 | 8,207 |
| `creative_governance/candidates/gates/probe_gate.py` | `ACTIVE_RUNTIME` | 151 | 5,980 |
| `creative_governance/candidates/gates/render_smoke_gate.py` | `ACTIVE_RUNTIME` | 119 | 4,479 |
| `creative_governance/candidates/gates/runtime_contract_gate.py` | `ACTIVE_RUNTIME` | 106 | 3,985 |
| `creative_governance/candidates/gates/security_gate.py` | `ACTIVE_RUNTIME` | 114 | 5,234 |
| `creative_governance/candidates/gates/static_code_gate.py` | `ACTIVE_RUNTIME` | 172 | 7,664 |
| `creative_governance/candidates/gates/template_schema_gate.py` | `ACTIVE_RUNTIME` | 170 | 7,474 |
| `creative_governance/candidates/gates/typescript_gate.py` | `ACTIVE_RUNTIME` | 100 | 4,149 |
| `creative_governance/candidates/hashing.py` | `ACTIVE_RUNTIME` | 133 | 5,509 |
| `creative_governance/candidates/policies.py` | `ACTIVE_RUNTIME` | 225 | 8,346 |
| `creative_governance/candidates/promotion_service.py` | `ACTIVE_RUNTIME` | 527 | 25,726 |
| `creative_governance/candidates/repository.py` | `ACTIVE_RUNTIME` | 398 | 17,812 |
| `creative_governance/candidates/review_service.py` | `ACTIVE_RUNTIME` | 738 | 33,689 |
| `creative_governance/candidates/runtime_runner.py` | `ACTIVE_RUNTIME` | 18 | 543 |
| `creative_governance/candidates/service.py` | `ACTIVE_RUNTIME` | 520 | 23,345 |
| `creative_governance/candidates/validation_service.py` | `ACTIVE_RUNTIME` | 658 | 27,685 |

</details>

### Subsystem: Storage & Artifact Distribution (`storage_distribution`)
- **File Count:** 1
- **Lines of Code:** 387
- **Critical Files:** 1

<details>
<summary>Click to expand all 1 files in storage_distribution</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `api/services/asset_service.py` | `ACTIVE_RUNTIME` | 387 | 14,041 |

</details>

### Subsystem: Test Suites & E2E Verification (`tests_verification`)
- **File Count:** 628
- **Lines of Code:** 127,489
- **Critical Files:** 0

<details>
<summary>Click to expand all 628 files in tests_verification</summary>

| Relative File Path | Role | Lines | Size (Bytes) |
| :--- | :--- | :--- | :--- |
| `remotion-app/src/__tests__/merge.test.ts` | `TEST_SUITE` | 56 | 1,666 |
| `scripts/tests/compiler.test.ts` | `TEST_SUITE` | 108 | 3,613 |
| `scripts/tests/orchestration.test.ts` | `TEST_SUITE` | 136 | 3,533 |
| `scripts/tests/phase11.test.ts` | `TEST_SUITE` | 146 | 6,265 |
| `scripts/tests/phase12.test.ts` | `TEST_SUITE` | 164 | 6,067 |
| `scripts/tests/registry.test.ts` | `TEST_SUITE` | 222 | 8,402 |
| `tests/ai/acquisition/__init__.py` | `TEST_SUITE` | 3 | 62 |
| `tests/ai/acquisition/test_contracts_and_normalization.py` | `TEST_SUITE` | 404 | 17,658 |
| `tests/ai/acquisition/test_dedupe_and_cache.py` | `TEST_SUITE` | 557 | 26,052 |
| `tests/ai/acquisition/test_e2e_acquisition_pipeline.py` | `TEST_SUITE` | 195 | 8,273 |
| `tests/ai/acquisition/test_filtering_and_ranking.py` | `TEST_SUITE` | 226 | 9,369 |
| `tests/ai/acquisition/test_legacy_parity.py` | `TEST_SUITE` | 200 | 8,543 |
| `tests/ai/acquisition/test_live_smoke.py` | `TEST_SUITE` | 123 | 4,749 |
| `tests/ai/acquisition/test_provider_fault_tolerance.py` | `TEST_SUITE` | 111 | 4,208 |
| `tests/ai/acquisition/test_safe_downloader_and_security.py` | `TEST_SUITE` | 236 | 10,870 |
| `tests/ai/acquisition/test_tool_gateway_acquisition.py` | `TEST_SUITE` | 508 | 23,018 |
| `tests/ai/audio/test_audio_benchmark.py` | `TEST_SUITE` | 66 | 2,425 |
| `tests/ai/audio/test_audio_mode_engine.py` | `TEST_SUITE` | 220 | 10,398 |
| `tests/ai/audio/test_audio_pipeline.py` | `TEST_SUITE` | 137 | 4,673 |
| `tests/ai/audio/test_dsp_analysis.py` | `TEST_SUITE` | 112 | 3,994 |
| `tests/ai/audio_modernization/test_architecture_guards.py` | `TEST_SUITE` | 161 | 7,425 |
| `tests/ai/audio_modernization/test_audio_analysis.py` | `TEST_SUITE` | 237 | 9,609 |
| `tests/ai/audio_modernization/test_audio_contracts.py` | `TEST_SUITE` | 248 | 8,035 |
| `tests/ai/audio_modernization/test_fault_injection.py` | `TEST_SUITE` | 184 | 7,580 |
| `tests/ai/audio_modernization/test_parity_matrix.py` | `TEST_SUITE` | 349 | 13,759 |
| `tests/ai/audio_modernization/test_security.py` | `TEST_SUITE` | 188 | 7,511 |
| `tests/ai/audio_modernization/test_speech_preparation.py` | `TEST_SUITE` | 144 | 5,986 |
| `tests/ai/audio_modernization/test_tenant_isolation.py` | `TEST_SUITE` | 103 | 4,056 |
| `tests/ai/audio_modernization/test_voiceover_manifest_and_timeline.py` | `TEST_SUITE` | 232 | 8,602 |
| `tests/ai/audit/test_s27_final_architecture_audit.py` | `TEST_SUITE` | 244 | 10,137 |
| `tests/ai/audit/test_s28_inventory.py` | `TEST_SUITE` | 123 | 4,650 |
| `tests/ai/audit/test_s28_m11_final_architecture_audit.py` | `TEST_SUITE` | 247 | 12,706 |
| `tests/ai/batch/test_batch_execution.py` | `TEST_SUITE` | 164 | 6,251 |
| `tests/ai/benchmark/test_cost_and_performance_benchmark.py` | `TEST_SUITE` | 354 | 13,660 |
| `tests/ai/budget/test_accounting.py` | `TEST_SUITE` | 118 | 4,506 |
| `tests/ai/budget/test_architecture_guards.py` | `TEST_SUITE` | 100 | 4,957 |
| `tests/ai/budget/test_concurrency.py` | `TEST_SUITE` | 225 | 8,865 |
| `tests/ai/budget/test_estimator.py` | `TEST_SUITE` | 103 | 4,134 |
| `tests/ai/budget/test_idempotency.py` | `TEST_SUITE` | 158 | 5,694 |
| `tests/ai/budget/test_invariants.py` | `TEST_SUITE` | 148 | 5,456 |
| `tests/ai/budget/test_release.py` | `TEST_SUITE` | 127 | 4,478 |
| `tests/ai/budget/test_reservation.py` | `TEST_SUITE` | 210 | 7,356 |
| `tests/ai/budget/test_scopes.py` | `TEST_SUITE` | 166 | 5,775 |
| `tests/ai/budget/test_settlement.py` | `TEST_SUITE` | 271 | 10,662 |
| `tests/ai/cache/test_architecture_guards.py` | `TEST_SUITE` | 162 | 7,399 |
| `tests/ai/cache/test_cache_architecture_and_boundaries.py` | `TEST_SUITE` | 275 | 10,583 |
| `tests/ai/cache/test_cache_key.py` | `TEST_SUITE` | 190 | 7,032 |
| `tests/ai/cache/test_cache_policy.py` | `TEST_SUITE` | 44 | 2,170 |
| `tests/ai/cache/test_cache_repository.py` | `TEST_SUITE` | 260 | 8,971 |
| `tests/ai/cache/test_cache_service.py` | `TEST_SUITE` | 166 | 6,544 |
| `tests/ai/cache/test_concurrency_coalescing.py` | `TEST_SUITE` | 243 | 9,310 |
| `tests/ai/cache/test_crash_recovery.py` | `TEST_SUITE` | 111 | 4,299 |
| `tests/ai/cache/test_crash_recovery_coalesced.py` | `TEST_SUITE` | 604 | 24,463 |
| `tests/ai/cache/test_durable_activity_integration.py` | `TEST_SUITE` | 308 | 11,391 |
| `tests/ai/cache/test_poisoning_and_invalidation.py` | `TEST_SUITE` | 254 | 9,875 |
| `tests/ai/cache/test_tenant_isolation.py` | `TEST_SUITE` | 140 | 5,647 |
| `tests/ai/candidates/conftest.py` | `TEST_SUITE` | 54 | 1,909 |
| `tests/ai/candidates/test_candidate_adversarial_closure.py` | `TEST_SUITE` | 703 | 32,349 |
| `tests/ai/candidates/test_candidate_architecture_guards.py` | `TEST_SUITE` | 379 | 15,695 |
| `tests/ai/candidates/test_candidate_concurrency.py` | `TEST_SUITE` | 106 | 3,895 |
| `tests/ai/candidates/test_candidate_contracts.py` | `TEST_SUITE` | 152 | 5,969 |
| `tests/ai/candidates/test_candidate_hashing.py` | `TEST_SUITE` | 110 | 3,814 |
| `tests/ai/candidates/test_candidate_lifecycle_e2e.py` | `TEST_SUITE` | 990 | 45,180 |
| `tests/ai/candidates/test_candidate_promotion_service.py` | `TEST_SUITE` | 844 | 36,544 |
| `tests/ai/candidates/test_candidate_registry_isolation.py` | `TEST_SUITE` | 375 | 15,825 |
| `tests/ai/candidates/test_candidate_review_workflow.py` | `TEST_SUITE` | 680 | 32,536 |
| `tests/ai/candidates/test_candidate_runtime_validation.py` | `TEST_SUITE` | 857 | 36,139 |
| `tests/ai/candidates/test_candidate_service.py` | `TEST_SUITE` | 181 | 6,645 |
| `tests/ai/candidates/test_candidate_static_validation.py` | `TEST_SUITE` | 625 | 26,186 |
| `tests/ai/candidates/test_candidate_storage.py` | `TEST_SUITE` | 129 | 5,142 |
| `tests/ai/candidates/test_candidate_tenant_isolation.py` | `TEST_SUITE` | 132 | 4,902 |
| `tests/ai/candidates/test_candidate_validation_tenant_isolation.py` | `TEST_SUITE` | 152 | 5,438 |
| `tests/ai/capabilities/test_capability_registry.py` | `TEST_SUITE` | 211 | 8,832 |
| `tests/ai/conflict/test_conflict_resolver.py` | `TEST_SUITE` | 263 | 10,436 |
| `tests/ai/context/conftest.py` | `TEST_SUITE` | 85 | 2,874 |
| `tests/ai/context/test_architecture_guards.py` | `TEST_SUITE` | 336 | 15,169 |
| `tests/ai/context/test_budgeting.py` | `TEST_SUITE` | 142 | 5,343 |
| `tests/ai/context/test_builder.py` | `TEST_SUITE` | 161 | 5,768 |
| `tests/ai/context/test_compression.py` | `TEST_SUITE` | 96 | 3,766 |
| `tests/ai/context/test_conflicts.py` | `TEST_SUITE` | 101 | 3,942 |
| `tests/ai/context/test_deduplication.py` | `TEST_SUITE` | 91 | 3,000 |
| `tests/ai/context/test_determinism.py` | `TEST_SUITE` | 197 | 7,272 |
| `tests/ai/context/test_irrelevant_memory.py` | `TEST_SUITE` | 112 | 3,979 |
| `tests/ai/context/test_knowledge_router_adapter.py` | `TEST_SUITE` | 135 | 5,242 |
| `tests/ai/context/test_needs.py` | `TEST_SUITE` | 136 | 5,054 |
| `tests/ai/context/test_ranking.py` | `TEST_SUITE` | 175 | 5,940 |
| `tests/ai/context/test_retrieval.py` | `TEST_SUITE` | 215 | 8,307 |
| `tests/ai/context/test_tenant_isolation.py` | `TEST_SUITE` | 161 | 6,100 |
| `tests/ai/context/test_token_safety.py` | `TEST_SUITE` | 286 | 10,785 |
| `tests/ai/contracts/fixtures.py` | `TEST_SUITE` | 376 | 14,360 |
| `tests/ai/contracts/fixtures/creative_contract_fixtures.json` | `TEST_SUITE` | 423 | 16,036 |
| `tests/ai/contracts/test_capability_taxonomy_and_contracts.py` | `TEST_SUITE` | 506 | 24,232 |
| `tests/ai/contracts/test_contracts_invalid.py` | `TEST_SUITE` | 116 | 4,428 |
| `tests/ai/contracts/test_contracts_valid.py` | `TEST_SUITE` | 283 | 10,626 |
| `tests/ai/contracts/test_creative_contracts.py` | `TEST_SUITE` | 248 | 9,531 |
| `tests/ai/contracts/test_generator_sync.py` | `TEST_SUITE` | 53 | 2,154 |
| `tests/ai/contracts/test_no_dict_any.py` | `TEST_SUITE` | 96 | 4,136 |
| `tests/ai/contracts/test_provider_bypass_guards.py` | `TEST_SUITE` | 166 | 7,357 |
| `tests/ai/contracts/test_provider_neutrality.py` | `TEST_SUITE` | 94 | 4,005 |
| `tests/ai/contracts/test_schema_parity.py` | `TEST_SUITE` | 98 | 3,927 |
| `tests/ai/contracts/test_semantic_invariants.py` | `TEST_SUITE` | 182 | 8,415 |
| `tests/ai/cost/test_architecture_guards.py` | `TEST_SUITE` | 148 | 5,080 |
| `tests/ai/cost/test_cost_attribution_and_summary.py` | `TEST_SUITE` | 232 | 8,538 |
| `tests/ai/cost/test_cost_semantics_closeout.py` | `TEST_SUITE` | 273 | 10,900 |
| `tests/ai/cost/test_efficiency_analyzer.py` | `TEST_SUITE` | 247 | 8,883 |
| `tests/ai/cost/test_regression_integration.py` | `TEST_SUITE` | 125 | 4,591 |
| `tests/ai/cost/test_tenant_isolation.py` | `TEST_SUITE` | 136 | 5,069 |
| `tests/ai/cost/test_token_accounting.py` | `TEST_SUITE` | 121 | 4,633 |
| `tests/ai/cost/test_usage_event_contracts.py` | `TEST_SUITE` | 202 | 7,474 |
| `tests/ai/directors/test_creative_directors.py` | `TEST_SUITE` | 264 | 9,238 |
| `tests/ai/e2e/test_full_creative_e2e_matrix.py` | `TEST_SUITE` | 952 | 39,600 |
| `tests/ai/e2e/test_multi_tenant_production_e2e.py` | `TEST_SUITE` | 413 | 17,713 |
| `tests/ai/e2e/test_real_service_e2e_closeout.py` | `TEST_SUITE` | 740 | 34,608 |
| `tests/ai/e2e/test_s28_m11_product_e2e_matrix.py` | `TEST_SUITE` | 1,317 | 56,444 |
| `tests/ai/e2e/test_s28_m_automatic_stock_preparation.py` | `TEST_SUITE` | 515 | 21,942 |
| `tests/ai/evals/datasets/intent_dataset.json` | `TEST_SUITE` | 241 | 8,269 |
| `tests/ai/evals/datasets/recipe_selection_matrix.json` | `TEST_SUITE` | 133 | 7,039 |
| `tests/ai/evals/test_creative_evals.py` | `TEST_SUITE` | 46 | 2,253 |
| `tests/ai/evals/test_creative_evals_s28_04.py` | `TEST_SUITE` | 61 | 2,341 |
| `tests/ai/evals/test_eval_platform.py` | `TEST_SUITE` | 310 | 11,743 |
| `tests/ai/evals/test_knowledge_and_skill_evals.py` | `TEST_SUITE` | 296 | 11,744 |
| `tests/ai/fault_injection/__init__.py` | `TEST_SUITE` | 21 | 420 |
| `tests/ai/fault_injection/contracts.py` | `TEST_SUITE` | 85 | 2,918 |
| `tests/ai/fault_injection/harness.py` | `TEST_SUITE` | 115 | 4,464 |
| `tests/ai/fault_injection/test_cascades_and_recovery.py` | `TEST_SUITE` | 395 | 17,076 |
| `tests/ai/fault_injection/test_full_fault_injection.py` | `TEST_SUITE` | 547 | 23,753 |
| `tests/ai/fault_injection/test_s28_m10_fault_injection.py` | `TEST_SUITE` | 337 | 13,520 |
| `tests/ai/fault_injection/test_system_fault_injection.py` | `TEST_SUITE` | 579 | 24,957 |
| `tests/ai/feedback/test_feedback_classification.py` | `TEST_SUITE` | 210 | 8,571 |
| `tests/ai/feedback/test_feedback_learning_service.py` | `TEST_SUITE` | 221 | 9,489 |
| `tests/ai/feedback/test_feedback_tenant_isolation.py` | `TEST_SUITE` | 256 | 10,100 |
| `tests/ai/image_modernization/__init__.py` | `TEST_SUITE` | 5 | 150 |
| `tests/ai/image_modernization/conftest.py` | `TEST_SUITE` | 108 | 3,267 |
| `tests/ai/image_modernization/test_adapter_and_gateway.py` | `TEST_SUITE` | 162 | 5,694 |
| `tests/ai/image_modernization/test_architecture_guards.py` | `TEST_SUITE` | 111 | 4,214 |
| `tests/ai/image_modernization/test_fault_injection.py` | `TEST_SUITE` | 148 | 5,871 |
| `tests/ai/image_modernization/test_image_cache.py` | `TEST_SUITE` | 237 | 9,844 |
| `tests/ai/image_modernization/test_image_contracts.py` | `TEST_SUITE` | 117 | 4,264 |
| `tests/ai/image_modernization/test_image_security.py` | `TEST_SUITE` | 111 | 4,144 |
| `tests/ai/image_modernization/test_image_service.py` | `TEST_SUITE` | 209 | 7,654 |
| `tests/ai/image_modernization/test_parity_matrix.py` | `TEST_SUITE` | 107 | 4,267 |
| `tests/ai/integration/test_knowledge_skill_integration.py` | `TEST_SUITE` | 330 | 13,072 |
| `tests/ai/integration/test_s28_03_e2e_pipeline.py` | `TEST_SUITE` | 139 | 5,632 |
| `tests/ai/integration/test_s28_04_integration.py` | `TEST_SUITE` | 167 | 6,721 |
| `tests/ai/intent/test_intent_parser.py` | `TEST_SUITE` | 104 | 5,175 |
| `tests/ai/knowledge/test_catalog_initialization_readiness.py` | `TEST_SUITE` | 58 | 2,176 |
| `tests/ai/knowledge/test_knowledge_platform.py` | `TEST_SUITE` | 485 | 18,441 |
| `tests/ai/mcp/__init__.py` | `TEST_SUITE` | 1 | 29 |
| `tests/ai/mcp/test_architecture_guards.py` | `TEST_SUITE` | 207 | 10,031 |
| `tests/ai/mcp/test_behavior_parity.py` | `TEST_SUITE` | 167 | 6,120 |
| `tests/ai/mcp/test_development_agent_preservation.py` | `TEST_SUITE` | 121 | 4,578 |
| `tests/ai/mcp/test_mcp_catalog.py` | `TEST_SUITE` | 113 | 5,305 |
| `tests/ai/mcp/test_mcp_compatibility_facade.py` | `TEST_SUITE` | 427 | 15,344 |
| `tests/ai/mcp/test_mcp_contracts.py` | `TEST_SUITE` | 93 | 3,123 |
| `tests/ai/mcp/test_mcp_security_adversarial.py` | `TEST_SUITE` | 398 | 15,581 |
| `tests/ai/media_intelligence/test_architecture_guards.py` | `TEST_SUITE` | 162 | 7,162 |
| `tests/ai/media_intelligence/test_media_contracts.py` | `TEST_SUITE` | 183 | 6,012 |
| `tests/ai/media_intelligence/test_media_service.py` | `TEST_SUITE` | 263 | 8,996 |
| `tests/ai/media_intelligence/test_technical_probe.py` | `TEST_SUITE` | 79 | 2,748 |
| `tests/ai/media_processing/__init__.py` | `TEST_SUITE` | 1 | 37 |
| `tests/ai/media_processing/conftest.py` | `TEST_SUITE` | 89 | 3,250 |
| `tests/ai/media_processing/test_adapter.py` | `TEST_SUITE` | 149 | 4,494 |
| `tests/ai/media_processing/test_architecture_guards.py` | `TEST_SUITE` | 65 | 2,909 |
| `tests/ai/media_processing/test_contracts.py` | `TEST_SUITE` | 240 | 6,920 |
| `tests/ai/media_processing/test_fault_injection.py` | `TEST_SUITE` | 82 | 2,873 |
| `tests/ai/media_processing/test_parity_matrix.py` | `TEST_SUITE` | 230 | 8,357 |
| `tests/ai/media_processing/test_security.py` | `TEST_SUITE` | 134 | 4,404 |
| `tests/ai/media_processing/test_service.py` | `TEST_SUITE` | 247 | 7,276 |
| `tests/ai/media_processing/test_validator.py` | `TEST_SUITE` | 106 | 3,416 |
| `tests/ai/memory/test_100_messages.py` | `TEST_SUITE` | 251 | 10,276 |
| `tests/ai/memory/test_architecture_guards.py` | `TEST_SUITE` | 156 | 7,709 |
| `tests/ai/memory/test_embeddings.py` | `TEST_SUITE` | 61 | 2,338 |
| `tests/ai/memory/test_in_memory_repository.py` | `TEST_SUITE` | 281 | 11,081 |
| `tests/ai/memory/test_large_artifacts.py` | `TEST_SUITE` | 74 | 3,164 |
| `tests/ai/memory/test_models.py` | `TEST_SUITE` | 203 | 7,932 |
| `tests/ai/memory/test_normalization.py` | `TEST_SUITE` | 63 | 3,131 |
| `tests/ai/memory/test_postgres_memory_repository.py` | `TEST_SUITE` | 365 | 14,198 |
| `tests/ai/memory/test_project_memory_boundary.py` | `TEST_SUITE` | 105 | 4,019 |
| `tests/ai/memory/test_serialization.py` | `TEST_SUITE` | 324 | 13,923 |
| `tests/ai/memory/test_tenant_isolation.py` | `TEST_SUITE` | 182 | 7,130 |
| `tests/ai/memory/test_write_policy.py` | `TEST_SUITE` | 311 | 13,313 |
| `tests/ai/migration/test_legacy_migration.py` | `TEST_SUITE` | 113 | 4,439 |
| `tests/ai/models/test_models.py` | `TEST_SUITE` | 225 | 8,734 |
| `tests/ai/narrative/test_narrative_metrics.py` | `TEST_SUITE` | 118 | 5,424 |
| `tests/ai/narrative/test_narrative_planner.py` | `TEST_SUITE` | 182 | 6,472 |
| `tests/ai/observability/test_metrics.py` | `TEST_SUITE` | 106 | 4,673 |
| `tests/ai/observability/test_redaction.py` | `TEST_SUITE` | 124 | 5,105 |
| `tests/ai/observability/test_tracer.py` | `TEST_SUITE` | 162 | 6,944 |
| `tests/ai/orchestration/test_architecture_guards.py` | `TEST_SUITE` | 117 | 5,772 |
| `tests/ai/orchestration/test_cancellation.py` | `TEST_SUITE` | 93 | 3,793 |
| `tests/ai/orchestration/test_crash_recovery.py` | `TEST_SUITE` | 1,287 | 53,808 |
| `tests/ai/orchestration/test_dag.py` | `TEST_SUITE` | 182 | 5,658 |
| `tests/ai/orchestration/test_dag_execution_and_dependencies.py` | `TEST_SUITE` | 192 | 7,858 |
| `tests/ai/orchestration/test_failure_propagation_and_retries.py` | `TEST_SUITE` | 151 | 6,097 |
| `tests/ai/orchestration/test_repository_persistence.py` | `TEST_SUITE` | 135 | 4,476 |
| `tests/ai/orchestration/test_restart_foundation_proof.py` | `TEST_SUITE` | 118 | 5,381 |
| `tests/ai/orchestration/test_state_machines.py` | `TEST_SUITE` | 132 | 5,866 |
| `tests/ai/orchestration/test_tenant_isolation.py` | `TEST_SUITE` | 83 | 3,284 |
| `tests/ai/orchestration/test_worker_claims_and_leases.py` | `TEST_SUITE` | 291 | 9,876 |
| `tests/ai/parity/test_full_capability_parity.py` | `TEST_SUITE` | 223 | 9,273 |
| `tests/ai/parity/test_m09_residual_disposition.py` | `TEST_SUITE` | 442 | 18,849 |
| `tests/ai/performance/test_s28_m10_performance_baseline.py` | `TEST_SUITE` | 350 | 12,780 |
| `tests/ai/planning/conftest.py` | `TEST_SUITE` | 165 | 5,228 |
| `tests/ai/planning/test_blueprint_compiler.py` | `TEST_SUITE` | 251 | 9,845 |
| `tests/ai/planning/test_compiler_negative.py` | `TEST_SUITE` | 275 | 10,868 |
| `tests/ai/planning/test_compose_engine.py` | `TEST_SUITE` | 245 | 9,054 |
| `tests/ai/planning/test_creative_plan_validator.py` | `TEST_SUITE` | 218 | 9,337 |
| `tests/ai/planning/test_creative_planner.py` | `TEST_SUITE` | 260 | 9,636 |
| `tests/ai/planning/test_planner_personalization.py` | `TEST_SUITE` | 219 | 8,572 |
| `tests/ai/planning/test_planning_architecture_guards.py` | `TEST_SUITE` | 152 | 6,895 |
| `tests/ai/planning/test_reuse_engine.py` | `TEST_SUITE` | 297 | 12,438 |
| `tests/ai/planning/test_s28_05_e2e_integration.py` | `TEST_SUITE` | 294 | 10,872 |
| `tests/ai/planning/test_s28_06_integration.py` | `TEST_SUITE` | 398 | 15,609 |
| `tests/ai/planning/test_tier_policy.py` | `TEST_SUITE` | 274 | 11,553 |
| `tests/ai/prompts/test_prompt_cache.py` | `TEST_SUITE` | 108 | 4,490 |
| `tests/ai/prompts/test_prompt_registry.py` | `TEST_SUITE` | 295 | 10,767 |
| `tests/ai/providers/test_openrouter.py` | `TEST_SUITE` | 479 | 21,373 |
| `tests/ai/providers/test_providers.py` | `TEST_SUITE` | 222 | 9,358 |
| `tests/ai/recipes/test_hard_eligibility_gate_proof.py` | `TEST_SUITE` | 114 | 4,945 |
| `tests/ai/recipes/test_recipe_compliance_audit.py` | `TEST_SUITE` | 117 | 4,974 |
| `tests/ai/recipes/test_recipe_registry.py` | `TEST_SUITE` | 100 | 3,721 |
| `tests/ai/recipes/test_recipe_selector.py` | `TEST_SUITE` | 134 | 5,186 |
| `tests/ai/regression/test_all_eval_categories.py` | `TEST_SUITE` | 51 | 1,918 |
| `tests/ai/regression/test_deliberately_bad_detection.py` | `TEST_SUITE` | 87 | 3,734 |
| `tests/ai/regression/test_personalization_regression.py` | `TEST_SUITE` | 57 | 2,688 |
| `tests/ai/regression/test_regression_contracts.py` | `TEST_SUITE` | 148 | 4,751 |
| `tests/ai/regression/test_regression_runner.py` | `TEST_SUITE` | 72 | 2,967 |
| `tests/ai/regression/test_retrieval_metrics.py` | `TEST_SUITE` | 104 | 3,607 |
| `tests/ai/regression/test_rubric_and_calibration.py` | `TEST_SUITE` | 129 | 4,804 |
| `tests/ai/regression/test_s28_08b_architecture_guards.py` | `TEST_SUITE` | 100 | 3,784 |
| `tests/ai/regression/test_trace_grader.py` | `TEST_SUITE` | 185 | 6,680 |
| `tests/ai/routing/test_capability_router.py` | `TEST_SUITE` | 226 | 9,064 |
| `tests/ai/routing/test_constraints.py` | `TEST_SUITE` | 275 | 11,568 |
| `tests/ai/routing/test_determinism.py` | `TEST_SUITE` | 117 | 4,365 |
| `tests/ai/routing/test_escalation.py` | `TEST_SUITE` | 119 | 5,126 |
| `tests/ai/routing/test_fallback.py` | `TEST_SUITE` | 172 | 7,025 |
| `tests/ai/routing/test_provider_neutrality.py` | `TEST_SUITE` | 80 | 2,993 |
| `tests/ai/routing/test_router.py` | `TEST_SUITE` | 112 | 4,101 |
| `tests/ai/routing/test_scoring.py` | `TEST_SUITE` | 156 | 6,176 |
| `tests/ai/routing/test_simulation.py` | `TEST_SUITE` | 361 | 15,385 |
| `tests/ai/security/test_ai_security.py` | `TEST_SUITE` | 223 | 9,057 |
| `tests/ai/security/test_knowledge_skill_security.py` | `TEST_SUITE` | 261 | 8,813 |
| `tests/ai/security/test_s28_03_architecture_guards.py` | `TEST_SUITE` | 78 | 3,378 |
| `tests/ai/security/test_s28_m10_security_campaign.py` | `TEST_SUITE` | 341 | 13,180 |
| `tests/ai/skills/test_skill_platform.py` | `TEST_SUITE` | 224 | 8,426 |
| `tests/ai/specialized/test_durability_and_cache.py` | `TEST_SUITE` | 135 | 5,431 |
| `tests/ai/specialized/test_failure_handling.py` | `TEST_SUITE` | 84 | 3,734 |
| `tests/ai/specialized/test_provider_swap.py` | `TEST_SUITE` | 95 | 3,875 |
| `tests/ai/specialized/test_routing_and_budget.py` | `TEST_SUITE` | 133 | 5,476 |
| `tests/ai/specialized/test_specialized_contracts.py` | `TEST_SUITE` | 172 | 6,227 |
| `tests/ai/specialized/test_tenant_isolation.py` | `TEST_SUITE` | 89 | 3,436 |
| `tests/ai/speech/test_benchmark_harness.py` | `TEST_SUITE` | 149 | 5,325 |
| `tests/ai/speech/test_benchmark_metrics.py` | `TEST_SUITE` | 137 | 5,263 |
| `tests/ai/speech/test_language_and_code_switching.py` | `TEST_SUITE` | 108 | 3,816 |
| `tests/ai/speech/test_provider_swap.py` | `TEST_SUITE` | 98 | 3,738 |
| `tests/ai/speech/test_real_human_speech_validation.py` | `TEST_SUITE` | 72 | 3,075 |
| `tests/ai/speech/test_reconciliation.py` | `TEST_SUITE` | 141 | 5,226 |
| `tests/ai/speech/test_semantic_validators.py` | `TEST_SUITE` | 80 | 2,556 |
| `tests/ai/speech/test_speech_canonicalization.py` | `TEST_SUITE` | 96 | 3,562 |
| `tests/ai/speech/test_stt_cache_and_artifacts.py` | `TEST_SUITE` | 298 | 11,262 |
| `tests/ai/speech/test_stt_canonical_integration.py` | `TEST_SUITE` | 159 | 6,499 |
| `tests/ai/speech/test_stt_parity_matrix.py` | `TEST_SUITE` | 225 | 9,340 |
| `tests/ai/speech/test_stt_provider_interface.py` | `TEST_SUITE` | 257 | 10,152 |
| `tests/ai/speech/test_stt_tenant_and_security.py` | `TEST_SUITE` | 252 | 10,508 |
| `tests/ai/style/test_current_request_wins.py` | `TEST_SUITE` | 266 | 10,152 |
| `tests/ai/style/test_style_resolver_precedence.py` | `TEST_SUITE` | 291 | 11,528 |
| `tests/ai/style/test_user_style_profile.py` | `TEST_SUITE` | 202 | 8,493 |
| `tests/ai/taste/test_taste_engine.py` | `TEST_SUITE` | 217 | 8,622 |
| `tests/ai/taste/test_taste_registry.py` | `TEST_SUITE` | 86 | 3,149 |
| `tests/ai/test_ai14_cross_cutting.py` | `TEST_SUITE` | 205 | 7,840 |
| `tests/ai/test_ai14_final_integration_proof.py` | `TEST_SUITE` | 431 | 19,833 |
| `tests/ai/test_ai_architecture_guards.py` | `TEST_SUITE` | 437 | 19,284 |
| `tests/ai/test_creative_architecture_guards.py` | `TEST_SUITE` | 699 | 28,872 |
| `tests/ai/test_provider_neutrality_architecture.py` | `TEST_SUITE` | 74 | 2,753 |
| `tests/ai/test_s28_08a_architecture_guards.py` | `TEST_SUITE` | 221 | 9,750 |
| `tests/ai/test_s28_h02_remediation.py` | `TEST_SUITE` | 308 | 14,351 |
| `tests/ai/test_s28_h03_remediation.py` | `TEST_SUITE` | 226 | 11,722 |
| `tests/ai/tools/test_architecture_guards.py` | `TEST_SUITE` | 257 | 12,442 |
| `tests/ai/tools/test_authorization.py` | `TEST_SUITE` | 225 | 7,815 |
| `tests/ai/tools/test_context_builder_integration.py` | `TEST_SUITE` | 111 | 3,865 |
| `tests/ai/tools/test_contracts.py` | `TEST_SUITE` | 271 | 9,474 |
| `tests/ai/tools/test_dispatcher.py` | `TEST_SUITE` | 285 | 9,587 |
| `tests/ai/tools/test_domain_adapters.py` | `TEST_SUITE` | 273 | 11,109 |
| `tests/ai/tools/test_e2e_tool_integration.py` | `TEST_SUITE` | 173 | 5,721 |
| `tests/ai/tools/test_registry.py` | `TEST_SUITE` | 200 | 6,708 |
| `tests/ai/tools/test_security_adversarial.py` | `TEST_SUITE` | 452 | 15,494 |
| `tests/ai/tools/test_tool_gateway.py` | `TEST_SUITE` | 666 | 26,719 |
| `tests/ai/vision/test_adaptive_resolution.py` | `TEST_SUITE` | 33 | 1,225 |
| `tests/ai/vision/test_keyframe_selection.py` | `TEST_SUITE` | 76 | 2,521 |
| `tests/ai/vision/test_object_person.py` | `TEST_SUITE` | 59 | 2,292 |
| `tests/ai/vision/test_ocr.py` | `TEST_SUITE` | 92 | 2,939 |
| `tests/ai/vision/test_shot_detection.py` | `TEST_SUITE` | 100 | 2,992 |
| `tests/ai/vision/test_vision_benchmark.py` | `TEST_SUITE` | 67 | 2,634 |
| `tests/ai/vision/test_vision_pipeline.py` | `TEST_SUITE` | 145 | 5,034 |
| `tests/api/test_candidate_promotions_router.py` | `TEST_SUITE` | 492 | 21,627 |
| `tests/api/test_candidate_reviews_router.py` | `TEST_SUITE` | 271 | 10,572 |
| `tests/api/test_client_without_filesystem.py` | `TEST_SUITE` | 227 | 9,788 |
| `tests/api/test_gates.py` | `TEST_SUITE` | 93 | 3,917 |
| `tests/api/test_health_readiness.py` | `TEST_SUITE` | 93 | 3,399 |
| `tests/api/test_lifecycle_bypass_prevention.py` | `TEST_SUITE` | 88 | 3,144 |
| `tests/api/test_pipeline_service.py` | `TEST_SUITE` | 133 | 5,259 |
| `tests/api/test_project_creation.py` | `TEST_SUITE` | 32 | 1,121 |
| `tests/api/test_projects.py` | `TEST_SUITE` | 154 | 5,422 |
| `tests/api/test_render.py` | `TEST_SUITE` | 50 | 1,924 |
| `tests/api/test_tenant_endpoints.py` | `TEST_SUITE` | 196 | 8,406 |
| `tests/architecture/test_adapter_layer_rules.py` | `TEST_SUITE` | 44 | 1,864 |
| `tests/architecture/test_agent_governance_parity.py` | `TEST_SUITE` | 38 | 1,518 |
| `tests/architecture/test_architecture_guards.py` | `TEST_SUITE` | 115 | 5,615 |
| `tests/architecture/test_archive_hygiene.py` | `TEST_SUITE` | 53 | 2,105 |
| `tests/architecture/test_contract_authority_matrix.py` | `TEST_SUITE` | 168 | 7,069 |
| `tests/architecture/test_gate_facade_guard.py` | `TEST_SUITE` | 156 | 6,986 |
| `tests/architecture/test_import_restrictions.py` | `TEST_SUITE` | 37 | 1,524 |
| `tests/architecture/test_lifecycle_authority_guard.py` | `TEST_SUITE` | 106 | 4,737 |
| `tests/architecture/test_no_parallel_pipeline.py` | `TEST_SUITE` | 56 | 2,299 |
| `tests/architecture/test_platform_portability.py` | `TEST_SUITE` | 36 | 1,453 |
| `tests/architecture/test_plugin_architecture_boundary.py` | `TEST_SUITE` | 79 | 5,478 |
| `tests/architecture/test_quarantine_isolation.py` | `TEST_SUITE` | 39 | 1,557 |
| `tests/architecture/test_review_authority_guard.py` | `TEST_SUITE` | 90 | 3,468 |
| `tests/architecture/test_s14_architecture_guard.py` | `TEST_SUITE` | 96 | 3,689 |
| `tests/architecture/test_s15_architecture_guard.py` | `TEST_SUITE` | 131 | 6,022 |
| `tests/architecture/test_s17_architecture_guard.py` | `TEST_SUITE` | 102 | 5,094 |
| `tests/architecture/test_s18_architecture_guard.py` | `TEST_SUITE` | 101 | 4,591 |
| `tests/architecture/test_s19_architecture_guard.py` | `TEST_SUITE` | 107 | 4,984 |
| `tests/architecture/test_s20_architecture_guard.py` | `TEST_SUITE` | 91 | 5,366 |
| `tests/architecture/test_s21_architecture_guards.py` | `TEST_SUITE` | 89 | 3,545 |
| `tests/architecture/test_s22_architecture_guards.py` | `TEST_SUITE` | 117 | 5,436 |
| `tests/architecture/test_s23_architecture_guards.py` | `TEST_SUITE` | 120 | 4,848 |
| `tests/architecture/test_s24_5_architecture_guards.py` | `TEST_SUITE` | 136 | 6,214 |
| `tests/architecture/test_s24_architecture_guards.py` | `TEST_SUITE` | 134 | 6,235 |
| `tests/architecture/test_s28_r02_architecture_guards.py` | `TEST_SUITE` | 112 | 4,731 |
| `tests/architecture/test_s28_r02_architecture_guards.test.ts` | `TEST_SUITE` | 206 | 9,737 |
| `tests/architecture/test_s28_r03_architecture_guards.test.ts` | `TEST_SUITE` | 61 | 2,460 |
| `tests/architecture/test_s28_r04_architecture_guards.test.ts` | `TEST_SUITE` | 75 | 3,236 |
| `tests/architecture/test_s28_r05_architecture_guards.test.ts` | `TEST_SUITE` | 138 | 6,405 |
| `tests/architecture/test_s28_r06_architecture_guards.test.ts` | `TEST_SUITE` | 98 | 4,067 |
| `tests/architecture/test_s28_r07_architecture_guards.test.ts` | `TEST_SUITE` | 108 | 4,788 |
| `tests/architecture/test_s28_r07b_architecture_guards.test.ts` | `TEST_SUITE` | 119 | 5,430 |
| `tests/architecture/test_s28_r08_architecture_guards.py` | `TEST_SUITE` | 54 | 2,200 |
| `tests/architecture/test_s28_r08_architecture_guards.test.ts` | `TEST_SUITE` | 112 | 5,008 |
| `tests/architecture/test_s28_r09_architecture_guards.py` | `TEST_SUITE` | 58 | 2,485 |
| `tests/architecture/test_s28_r09_architecture_guards.test.ts` | `TEST_SUITE` | 117 | 5,228 |
| `tests/architecture/test_s28_r10_architecture_guards.py` | `TEST_SUITE` | 68 | 2,971 |
| `tests/architecture/test_s28_r10_architecture_guards.test.ts` | `TEST_SUITE` | 111 | 4,875 |
| `tests/architecture/test_s28_r11_architecture_guards.py` | `TEST_SUITE` | 89 | 3,916 |
| `tests/architecture/test_s28_r11_architecture_guards.test.ts` | `TEST_SUITE` | 122 | 5,682 |
| `tests/architecture/test_s28_r12_architecture_guards.py` | `TEST_SUITE` | 94 | 3,877 |
| `tests/architecture/test_s28_r12_architecture_guards.test.ts` | `TEST_SUITE` | 124 | 6,249 |
| `tests/architecture/test_s28_r13_architecture_guards.py` | `TEST_SUITE` | 65 | 3,186 |
| `tests/architecture/test_s28_r13_architecture_guards.test.ts` | `TEST_SUITE` | 127 | 6,247 |
| `tests/architecture/test_s28_r14_architecture_guards.py` | `TEST_SUITE` | 141 | 7,060 |
| `tests/architecture/test_s28_r14_architecture_guards.test.ts` | `TEST_SUITE` | 134 | 7,091 |
| `tests/architecture/test_s28_r15_architecture_guards.py` | `TEST_SUITE` | 108 | 5,042 |
| `tests/architecture/test_s28_r15_architecture_guards.test.ts` | `TEST_SUITE` | 79 | 3,668 |
| `tests/architecture/test_state_file_integrity.py` | `TEST_SUITE` | 70 | 3,416 |
| `tests/architecture/test_state_transaction_guard.py` | `TEST_SUITE` | 152 | 5,785 |
| `tests/archive/test_migrate_legacy.py` | `TEST_SUITE` | 72 | 2,712 |
| `tests/ci/test_ci_parity.py` | `TEST_SUITE` | 258 | 12,049 |
| `tests/conftest.py` | `TEST_SUITE` | 248 | 9,321 |
| `tests/contracts/test_pipeline_service_contract.py` | `TEST_SUITE` | 82 | 3,281 |
| `tests/contracts/test_state_schema.py` | `TEST_SUITE` | 50 | 1,603 |
| `tests/core/test_asset_resolution.py` | `TEST_SUITE` | 337 | 15,028 |
| `tests/core/test_cross_tenant_asset_resolution.py` | `TEST_SUITE` | 155 | 5,768 |
| `tests/core/test_evidence_matrix.py` | `TEST_SUITE` | 385 | 16,969 |
| `tests/core/test_failure_classification.py` | `TEST_SUITE` | 70 | 2,811 |
| `tests/core/test_lifecycle_service.py` | `TEST_SUITE` | 167 | 6,180 |
| `tests/core/test_project_identity_matrix.py` | `TEST_SUITE` | 152 | 5,475 |
| `tests/core/test_recovery_rollback.py` | `TEST_SUITE` | 262 | 11,062 |
| `tests/core/test_runtime_logger.py` | `TEST_SUITE` | 81 | 3,241 |
| `tests/core/test_s07_5_hardening.py` | `TEST_SUITE` | 380 | 15,590 |
| `tests/core/test_s08_failure_retry.py` | `TEST_SUITE` | 574 | 21,351 |
| `tests/core/test_s09_review_service.py` | `TEST_SUITE` | 382 | 15,672 |
| `tests/core/test_s10_dependency_graph.py` | `TEST_SUITE` | 587 | 24,034 |
| `tests/core/test_s11_manifest_v2_acceptance.py` | `TEST_SUITE` | 287 | 12,319 |
| `tests/core/test_s12_blueprint_canonical_acceptance.py` | `TEST_SUITE` | 265 | 11,528 |
| `tests/core/test_s12_cross_language_parity.py` | `TEST_SUITE` | 87 | 4,582 |
| `tests/core/test_s13_transactional_materializer.py` | `TEST_SUITE` | 1,047 | 47,172 |
| `tests/core/test_s17_render_input.py` | `TEST_SUITE` | 282 | 11,335 |
| `tests/core/test_s18_probe_qc.py` | `TEST_SUITE` | 768 | 28,256 |
| `tests/core/test_s28_r14_production_integration.py` | `TEST_SUITE` | 1,282 | 48,715 |
| `tests/core/test_s28_r15_destruction_and_fault.py` | `TEST_SUITE` | 843 | 35,033 |
| `tests/core/test_s28_r15_postgres_and_s3_closure.py` | `TEST_SUITE` | 411 | 17,362 |
| `tests/core/test_safe_retry.py` | `TEST_SUITE` | 156 | 5,756 |
| `tests/core/test_security_scaffolding.py` | `TEST_SUITE` | 296 | 12,569 |
| `tests/core/test_state_store_cas.py` | `TEST_SUITE` | 623 | 24,374 |
| `tests/core/test_state_store_tenant_cas.py` | `TEST_SUITE` | 74 | 2,770 |
| `tests/core/test_storage_service.py` | `TEST_SUITE` | 141 | 4,331 |
| `tests/core/test_template_candidate_repository.py` | `TEST_SUITE` | 277 | 9,755 |
| `tests/core/test_template_contract.py` | `TEST_SUITE` | 311 | 12,827 |
| `tests/core/test_tenant_database.py` | `TEST_SUITE` | 129 | 5,296 |
| `tests/core/test_tenant_project_migration.py` | `TEST_SUITE` | 131 | 5,683 |
| `tests/core/test_trace_identity.py` | `TEST_SUITE` | 151 | 6,023 |
| `tests/core/test_version_compatibility_matrix.py` | `TEST_SUITE` | 58 | 1,908 |
| `tests/core/test_worker_ephemeral_workspace.py` | `TEST_SUITE` | 259 | 9,505 |
| `tests/documentation/test_agents_md_accuracy.py` | `TEST_SUITE` | 87 | 4,904 |
| `tests/documentation/test_architecture_truth.py` | `TEST_SUITE` | 51 | 2,881 |
| `tests/documentation/test_references_validity.py` | `TEST_SUITE` | 65 | 3,097 |
| `tests/e2e/test_pipeline_integration.py` | `TEST_SUITE` | 210 | 8,393 |
| `tests/e2e/test_process_loopback_smoke.py` | `TEST_SUITE` | 342 | 15,965 |
| `tests/e2e/test_product_http_to_mp4_e2e.py` | `TEST_SUITE` | 514 | 22,241 |
| `tests/e2e/test_saas_multi_tenant_e2e.py` | `TEST_SUITE` | 438 | 18,286 |
| `tests/e2e/test_unified_pipeline.py` | `TEST_SUITE` | 19 | 703 |
| `tests/e2e/true_e2e_suite.py` | `TEST_SUITE` | 303 | 11,283 |
| `tests/factories/canonical_factory.py` | `TEST_SUITE` | 312 | 10,215 |
| `tests/fault_injection/__init__.py` | `TEST_SUITE` | 3 | 95 |
| `tests/fault_injection/test_fi_01_db_outage_transition.py` | `TEST_SUITE` | 147 | 5,551 |
| `tests/fault_injection/test_fi_02_lease_fencing.py` | `TEST_SUITE` | 152 | 6,131 |
| `tests/fault_injection/test_fi_03_worker_hard_death.py` | `TEST_SUITE` | 265 | 9,939 |
| `tests/fault_injection/test_fi_04_api_hard_death.py` | `TEST_SUITE` | 152 | 5,609 |
| `tests/fault_injection/test_fi_05_storage_outage.py` | `TEST_SUITE` | 212 | 7,636 |
| `tests/fault_injection/test_fi_06_partial_upload.py` | `TEST_SUITE` | 162 | 5,756 |
| `tests/fault_injection/test_fi_07_db_storage_disagreement.py` | `TEST_SUITE` | 218 | 7,895 |
| `tests/fault_injection/test_fi_08_multiprocess_cas.py` | `TEST_SUITE` | 117 | 4,337 |
| `tests/fault_injection/test_fi_09_idempotency.py` | `TEST_SUITE` | 210 | 7,365 |
| `tests/fault_injection/test_fi_10_cross_tenant_access.py` | `TEST_SUITE` | 259 | 9,897 |
| `tests/fault_injection/test_fi_11_cross_tenant_indirect_ref.py` | `TEST_SUITE` | 190 | 7,321 |
| `tests/fault_injection/test_fi_12_rbac_matrix.py` | `TEST_SUITE` | 245 | 9,739 |
| `tests/fault_injection/test_fi_13_tenant_spoofing.py` | `TEST_SUITE` | 147 | 5,805 |
| `tests/fault_injection/test_fi_14_ephemeral_cleanup.py` | `TEST_SUITE` | 164 | 5,508 |
| `tests/fault_injection/test_fi_15_ephemeral_loss.py` | `TEST_SUITE` | 153 | 5,501 |
| `tests/fault_injection/test_fi_16_migration_rebuild.py` | `TEST_SUITE` | 122 | 4,885 |
| `tests/fault_injection/test_fi_17_readiness_truthfulness.py` | `TEST_SUITE` | 156 | 5,737 |
| `tests/fault_injection/test_fi_18_event_stream_reconnect.py` | `TEST_SUITE` | 167 | 6,138 |
| `tests/fault_injection/test_fi_19_cancellation_execution.py` | `TEST_SUITE` | 175 | 5,965 |
| `tests/fault_injection/test_fi_20_e2e_destructive.py` | `TEST_SUITE` | 202 | 8,167 |
| `tests/fixtures/blueprint/invalid_aspect_ratio_blueprint.json` | `TEST_SUITE` | 14 | 281 |
| `tests/fixtures/blueprint/invalid_audio_asset_kind_blueprint.json` | `TEST_SUITE` | 19 | 353 |
| `tests/fixtures/blueprint/invalid_audio_volume_blueprint.json` | `TEST_SUITE` | 20 | 373 |
| `tests/fixtures/blueprint/invalid_duration_frames_blueprint.json` | `TEST_SUITE` | 14 | 271 |
| `tests/fixtures/blueprint/invalid_fps_blueprint.json` | `TEST_SUITE` | 14 | 268 |
| `tests/fixtures/blueprint/invalid_project_id_blueprint.json` | `TEST_SUITE` | 14 | 297 |
| `tests/fixtures/blueprint/invalid_start_frame_blueprint.json` | `TEST_SUITE` | 14 | 271 |
| `tests/fixtures/blueprint/invalid_transition_type_blueprint.json` | `TEST_SUITE` | 18 | 380 |
| `tests/fixtures/blueprint/invalid_version_blueprint.json` | `TEST_SUITE` | 14 | 268 |
| `tests/fixtures/blueprint/legacy_v1_blueprint.json` | `TEST_SUITE` | 27 | 563 |
| `tests/fixtures/blueprint/missing_required_fields_blueprint.json` | `TEST_SUITE` | 4 | 52 |
| `tests/fixtures/blueprint/valid_audio_plan_blueprint.json` | `TEST_SUITE` | 39 | 802 |
| `tests/fixtures/blueprint/valid_minimal_blueprint.json` | `TEST_SUITE` | 14 | 270 |
| `tests/fixtures/blueprint/valid_multi_scene_blueprint.json` | `TEST_SUITE` | 37 | 829 |
| `tests/fixtures/canonical/01_simple_text_scene.json` | `TEST_SUITE` | 20 | 459 |
| `tests/fixtures/canonical/02_image_scene.json` | `TEST_SUITE` | 18 | 396 |
| `tests/fixtures/canonical/03_video_scene.json` | `TEST_SUITE` | 17 | 347 |
| `tests/fixtures/canonical/04_audio_plan.json` | `TEST_SUITE` | 38 | 776 |
| `tests/fixtures/canonical/05_multi_scenes_effects_transitions.json` | `TEST_SUITE` | 47 | 1,002 |
| `tests/fixtures/canonical/06_overrides_and_brand.json` | `TEST_SUITE` | 18 | 387 |
| `tests/fixtures/canonical/07_aspect_1_1_non_30fps.json` | `TEST_SUITE` | 14 | 284 |
| `tests/fixtures/canonical/08_aspect_9_16.json` | `TEST_SUITE` | 14 | 284 |
| `tests/fixtures/canonical/09_timeline_basic.json` | `TEST_SUITE` | 28 | 609 |
| `tests/fixtures/canonical/10_layer_stack.json` | `TEST_SUITE` | 73 | 2,176 |
| `tests/fixtures/canonical/11_keyframes_linear.json` | `TEST_SUITE` | 54 | 1,704 |
| `tests/fixtures/canonical/12_keyframes_easing.json` | `TEST_SUITE` | 52 | 1,763 |
| `tests/fixtures/canonical/13_keyframes_spring.json` | `TEST_SUITE` | 50 | 1,498 |
| `tests/fixtures/canonical/14_nested_groups.json` | `TEST_SUITE` | 70 | 2,061 |
| `tests/fixtures/canonical/15_cross_scene_audio.json` | `TEST_SUITE` | 48 | 1,094 |
| `tests/fixtures/canonical/16_transition_overlap.json` | `TEST_SUITE` | 28 | 700 |
| `tests/fixtures/canonical/17_60fps_animation.json` | `TEST_SUITE` | 44 | 1,386 |
| `tests/fixtures/clean_room_project/00_answers.md` | `TEST_SUITE` | 41 | 3,310 |
| `tests/fixtures/clean_room_project/assets/ready/audio/cyber_synth_bgm_norm.wav` | `TEST_SUITE` | 0 | 15,837,774 |
| `tests/fixtures/clean_room_project/assets/ready/audio/digital_norm.wav` | `TEST_SUITE` | 0 | 193,614 |
| `tests/fixtures/clean_room_project/assets/ready/audio/keyboard_norm.wav` | `TEST_SUITE` | 0 | 1,419,342 |
| `tests/fixtures/clean_room_project/assets/ready/audio/notification_norm.wav` | `TEST_SUITE` | 0 | 322,638 |
| `tests/fixtures/clean_room_project/assets/ready/audio/pop_norm.wav` | `TEST_SUITE` | 0 | 186,358 |
| `tests/fixtures/clean_room_project/assets/ready/audio/swoosh_norm.wav` | `TEST_SUITE` | 0 | 364,110 |
| `tests/fixtures/clean_room_project/assets/ready/audio/whoosh_norm.wav` | `TEST_SUITE` | 0 | 212,046 |
| `tests/fixtures/clean_room_project/assets/ready/icons/brain.svg` | `TEST_SUITE` | 0 | 996 |
| `tests/fixtures/clean_room_project/assets/ready/icons/code.svg` | `TEST_SUITE` | 0 | 248 |
| `tests/fixtures/clean_room_project/assets/ready/icons/cpu.svg` | `TEST_SUITE` | 0 | 4,220 |
| `tests/fixtures/clean_room_project/assets/ready/icons/rocket_cartoon.svg` | `TEST_SUITE` | 0 | 2,132 |
| `tests/fixtures/clean_room_project/assets/ready/icons/smartphone_lucide.svg` | `TEST_SUITE` | 0 | 269 |
| `tests/fixtures/clean_room_project/assets/ready/icons/success.svg` | `TEST_SUITE` | 0 | 291 |
| `tests/fixtures/clean_room_project/assets/ready/vo_norm.wav` | `TEST_SUITE` | 0 | 1,573,566 |
| `tests/fixtures/manifest/duplicate_id_manifest.json` | `TEST_SUITE` | 23 | 617 |
| `tests/fixtures/manifest/invalid_kind_manifest.json` | `TEST_SUITE` | 15 | 393 |
| `tests/fixtures/manifest/invalid_provenance_manifest.json` | `TEST_SUITE` | 15 | 377 |
| `tests/fixtures/manifest/invalid_status_manifest.json` | `TEST_SUITE` | 14 | 336 |
| `tests/fixtures/manifest/legacy_v1_ambiguous_manifest.json` | `TEST_SUITE` | 3 | 30 |
| `tests/fixtures/manifest/legacy_v1_valid_manifest.json` | `TEST_SUITE` | 42 | 989 |
| `tests/fixtures/manifest/project_id_mismatch_manifest.json` | `TEST_SUITE` | 6 | 131 |
| `tests/fixtures/manifest/unsupported_version_manifest.json` | `TEST_SUITE` | 6 | 133 |
| `tests/fixtures/manifest/valid_manifest_v2.json` | `TEST_SUITE` | 51 | 1,426 |
| `tests/fixtures/stt_parity/01_arabic_clean.wav` | `TEST_SUITE` | 0 | 689,298 |
| `tests/fixtures/stt_parity/02_english_clean.wav` | `TEST_SUITE` | 0 | 219,126 |
| `tests/fixtures/stt_parity/03_mixed_ar_en.wav` | `TEST_SUITE` | 0 | 205,234 |
| `tests/fixtures/stt_parity/04_speech_with_noise.wav` | `TEST_SUITE` | 0 | 976,974 |
| `tests/fixtures/stt_parity/05_speech_with_music.wav` | `TEST_SUITE` | 0 | 331,710 |
| `tests/fixtures/stt_parity/06_silence.wav` | `TEST_SUITE` | 0 | 96,078 |
| `tests/fixtures/stt_parity/07_corrupt_audio.wav` | `TEST_SUITE` | 0 | 71 |
| `tests/fixtures/stt_parity/08_long_audio.wav` | `TEST_SUITE` | 0 | 1,573,566 |
| `tests/gates/test_datastory_gate_contract.py` | `TEST_SUITE` | 121 | 4,271 |
| `tests/generators/test_asset_resolution.py` | `TEST_SUITE` | 179 | 6,576 |
| `tests/generators/test_scaffold.py` | `TEST_SUITE` | 44 | 1,672 |
| `tests/golden_scenarios/test_concurrent_requests.py` | `TEST_SUITE` | 62 | 2,997 |
| `tests/golden_scenarios/test_failure_recovery.py` | `TEST_SUITE` | 40 | 1,666 |
| `tests/golden_scenarios/test_happy_path.py` | `TEST_SUITE` | 44 | 2,106 |
| `tests/golden_scenarios/test_migration_from_legacy.py` | `TEST_SUITE` | 51 | 2,104 |
| `tests/integration/test_b1_context_knowledge_creative_proposal.py` | `TEST_SUITE` | 488 | 19,293 |
| `tests/integration/test_b2_capability_gateway_integration.py` | `TEST_SUITE` | 489 | 18,492 |
| `tests/integration/test_pr003_ai_runtime_vertical_slice.py` | `TEST_SUITE` | 526 | 18,808 |
| `tests/integration/test_pr003_provenance_verification.py` | `TEST_SUITE` | 754 | 34,177 |
| `tests/integration/test_pr003_render_runtime_closure.py` | `TEST_SUITE` | 588 | 23,125 |
| `tests/integration/test_pr004_state_consistency.py` | `TEST_SUITE` | 703 | 29,463 |
| `tests/integration/test_pr005_process_hard_death_recovery.py` | `TEST_SUITE` | 664 | 26,359 |
| `tests/integration/test_pr005_run_blueprint_provenance.py` | `TEST_SUITE` | 808 | 30,603 |
| `tests/metrics/test_metrics.py` | `TEST_SUITE` | 99 | 3,855 |
| `tests/performance/test_api_response_times.py` | `TEST_SUITE` | 49 | 1,689 |
| `tests/performance/test_pipeline_performance.py` | `TEST_SUITE` | 54 | 2,118 |
| `tests/remediation/reproductions/conftest.py` | `TEST_SUITE` | 38 | 2,161 |
| `tests/remediation/reproductions/test_asset_009_path_traversal.py` | `TEST_SUITE` | 66 | 2,736 |
| `tests/remediation/reproductions/test_conc_001_lost_update.py` | `TEST_SUITE` | 60 | 2,736 |
| `tests/remediation/reproductions/test_gate_001_facade_reproductions.py` | `TEST_SUITE` | 201 | 9,057 |
| `tests/remediation/reproductions/test_led_005_artifact_records_erasure.py` | `TEST_SUITE` | 49 | 2,419 |
| `tests/remediation/reproductions/test_led_008_corrupt_state.py` | `TEST_SUITE` | 42 | 1,874 |
| `tests/remediation/reproductions/test_led_019_approval_bypass.py` | `TEST_SUITE` | 27 | 1,418 |
| `tests/remediation/reproductions/test_led_022_skip_strict_qc.py` | `TEST_SUITE` | 24 | 1,222 |
| `tests/remediation/reproductions/test_led_054_props_divergence.py` | `TEST_SUITE` | 35 | 1,852 |
| `tests/remediation/reproductions/test_led_088_authority_duplication.py` | `TEST_SUITE` | 30 | 1,222 |
| `tests/remediation/reproductions/test_led_090_downstream_invalidation.py` | `TEST_SUITE` | 75 | 3,088 |
| `tests/remediation/reproductions/test_rec_001_recovery_empty_evidence.py` | `TEST_SUITE` | 41 | 1,885 |
| `tests/remediation/reproductions/test_s11_manifest_v2_reproductions.py` | `TEST_SUITE` | 188 | 7,435 |
| `tests/remediation/reproductions/test_s11_remediation_proof.py` | `TEST_SUITE` | 180 | 7,040 |
| `tests/remediation/reproductions/test_s12_blueprint_remediation_proof.py` | `TEST_SUITE` | 122 | 4,751 |
| `tests/remediation/reproductions/test_s12_blueprint_reproductions.py` | `TEST_SUITE` | 128 | 4,612 |
| `tests/remediation/reproductions/test_s13_remediation_proof.py` | `TEST_SUITE` | 276 | 11,816 |
| `tests/remediation/reproductions/test_s13_reproductions.py` | `TEST_SUITE` | 315 | 13,009 |
| `tests/remediation/reproductions/test_s14_remediation_proof.py` | `TEST_SUITE` | 229 | 10,958 |
| `tests/remediation/reproductions/test_s14_reproductions.py` | `TEST_SUITE` | 74 | 3,028 |
| `tests/remediation/reproductions/test_s15_remediation_proof.py` | `TEST_SUITE` | 176 | 7,394 |
| `tests/remediation/reproductions/test_s15_reproductions.py` | `TEST_SUITE` | 139 | 5,399 |
| `tests/remediation/reproductions/test_s16_remediation_proof.py` | `TEST_SUITE` | 111 | 4,050 |
| `tests/remediation/reproductions/test_s17_remediation_proof.py` | `TEST_SUITE` | 71 | 3,193 |
| `tests/remediation/reproductions/test_s18_remediation_proof.py` | `TEST_SUITE` | 265 | 10,811 |
| `tests/remediation/reproductions/test_s18_reproductions.py` | `TEST_SUITE` | 105 | 5,290 |
| `tests/remediation/reproductions/test_s19_remediation_proof.py` | `TEST_SUITE` | 488 | 21,657 |
| `tests/remediation/reproductions/test_s19_reproductions.py` | `TEST_SUITE` | 82 | 3,761 |
| `tests/remediation/reproductions/test_s20_remediation_proof.py` | `TEST_SUITE` | 147 | 7,171 |
| `tests/remediation/reproductions/test_s20_reproductions.py` | `TEST_SUITE` | 82 | 3,986 |
| `tests/remediation/reproductions/test_s21_remediation_proof.py` | `TEST_SUITE` | 372 | 15,419 |
| `tests/remediation/reproductions/test_s21_reproductions.py` | `TEST_SUITE` | 165 | 7,175 |
| `tests/remediation/reproductions/test_s22_remediation_proof.py` | `TEST_SUITE` | 638 | 29,907 |
| `tests/remediation/reproductions/test_s22_reproductions.py` | `TEST_SUITE` | 334 | 14,761 |
| `tests/remediation/reproductions/test_s23_remediation_proof.py` | `TEST_SUITE` | 325 | 12,983 |
| `tests/remediation/reproductions/test_s23_reproductions.py` | `TEST_SUITE` | 193 | 8,825 |
| `tests/remediation/reproductions/test_s24_remediation_proof.py` | `TEST_SUITE` | 152 | 9,855 |
| `tests/remediation/reproductions/test_s24_reproductions.py` | `TEST_SUITE` | 103 | 4,666 |
| `tests/remediation/reproductions/test_state_001_lifecycle_bypass.py` | `TEST_SUITE` | 44 | 2,098 |
| `tests/remediation/s02_acceptance/conftest.py` | `TEST_SUITE` | 7 | 207 |
| `tests/remediation/s02_acceptance/test_acc_001_unauthenticated_sensitive_request.py` | `TEST_SUITE` | 27 | 1,132 |
| `tests/remediation/s02_acceptance/test_acc_002_approved_by_untrusted.py` | `TEST_SUITE` | 53 | 2,244 |
| `tests/remediation/s02_acceptance/test_acc_003_project_scope_isolation.py` | `TEST_SUITE` | 45 | 1,948 |
| `tests/remediation/s02_acceptance/test_acc_004_non_reviewer_approval.py` | `TEST_SUITE` | 55 | 2,149 |
| `tests/remediation/s02_acceptance/test_acc_005_path_traversal.py` | `TEST_SUITE` | 72 | 2,814 |
| `tests/remediation/s02_acceptance/test_acc_006_symlink_escape.py` | `TEST_SUITE` | 81 | 3,192 |
| `tests/remediation/s02_acceptance/test_acc_007_docker_subcommand_validation.py` | `TEST_SUITE` | 29 | 1,304 |
| `tests/remediation/s02_acceptance/test_acc_008_dangerous_subprocess_flags.py` | `TEST_SUITE` | 33 | 1,506 |
| `tests/remediation/s02_acceptance/test_acc_009_skip_strict_qc_production.py` | `TEST_SUITE` | 57 | 2,186 |
| `tests/remediation/s02_acceptance/test_acc_010_agy_is_managed_approval.py` | `TEST_SUITE` | 65 | 2,722 |
| `tests/remediation/s02_acceptance/test_acc_011_python_interpreter_contract.py` | `TEST_SUITE` | 35 | 1,592 |
| `tests/remotion/ai_contracts_parity.test.ts` | `TEST_SUITE` | 247 | 8,901 |
| `tests/remotion/asset_resolution.test.ts` | `TEST_SUITE` | 238 | 9,304 |
| `tests/remotion/blueprint.test.ts` | `TEST_SUITE` | 196 | 8,645 |
| `tests/remotion/capability_contracts_parity.test.ts` | `TEST_SUITE` | 245 | 9,810 |
| `tests/remotion/conformance.test.ts` | `TEST_SUITE` | 264 | 11,346 |
| `tests/remotion/contracts.test.ts` | `TEST_SUITE` | 79 | 3,312 |
| `tests/remotion/creative_contracts_parity.test.ts` | `TEST_SUITE` | 793 | 33,716 |
| `tests/remotion/datastory_contract.test.ts` | `TEST_SUITE` | 121 | 4,833 |
| `tests/remotion/effects.test.ts` | `TEST_SUITE` | 163 | 6,811 |
| `tests/remotion/manifest.test.ts` | `TEST_SUITE` | 104 | 4,341 |
| `tests/remotion/merge.test.ts` | `TEST_SUITE` | 139 | 6,169 |
| `tests/remotion/registry.test.ts` | `TEST_SUITE` | 104 | 4,604 |
| `tests/remotion/s16_pre_mount_gate.test.ts` | `TEST_SUITE` | 670 | 26,964 |
| `tests/remotion/s16_reproductions.test.ts` | `TEST_SUITE` | 210 | 9,533 |
| `tests/remotion/s17_render_input_parity.test.ts` | `TEST_SUITE` | 132 | 4,651 |
| `tests/remotion/s28_06_render_smoke.test.ts` | `TEST_SUITE` | 281 | 8,521 |
| `tests/remotion/s28_r02_canonical_parity.test.ts` | `TEST_SUITE` | 167 | 6,315 |
| `tests/remotion/s28_r02_red_tests.test.ts` | `TEST_SUITE` | 188 | 10,917 |
| `tests/remotion/s28_r03_canonical_parity.test.ts` | `TEST_SUITE` | 426 | 20,444 |
| `tests/remotion/s28_r03_red_tests.test.ts` | `TEST_SUITE` | 408 | 21,256 |
| `tests/remotion/s28_r04_editor_performance.test.ts` | `TEST_SUITE` | 173 | 6,308 |
| `tests/remotion/s28_r04_editor_session.test.ts` | `TEST_SUITE` | 576 | 21,027 |
| `tests/remotion/s28_r04_mutations_core.test.ts` | `TEST_SUITE` | 705 | 28,902 |
| `tests/remotion/s28_r04_subprocess_isolation.test.ts` | `TEST_SUITE` | 331 | 12,602 |
| `tests/remotion/s28_r05_red_tests.test.ts` | `TEST_SUITE` | 180 | 7,906 |
| `tests/remotion/s28_r05_subprocess_isolation.test.ts` | `TEST_SUITE` | 144 | 5,945 |
| `tests/remotion/s28_r05_template_migration.test.ts` | `TEST_SUITE` | 315 | 11,985 |
| `tests/remotion/s28_r05_template_spec.test.ts` | `TEST_SUITE` | 336 | 11,137 |
| `tests/remotion/s28_r06_preview_core.test.ts` | `TEST_SUITE` | 421 | 15,571 |
| `tests/remotion/s28_r06_preview_performance.test.ts` | `TEST_SUITE` | 187 | 9,151 |
| `tests/remotion/s28_r06_templates_and_mutations.test.ts` | `TEST_SUITE` | 547 | 21,258 |
| `tests/remotion/s28_r07_audio_core.test.ts` | `TEST_SUITE` | 404 | 15,996 |
| `tests/remotion/s28_r07_audio_performance.test.ts` | `TEST_SUITE` | 238 | 12,275 |
| `tests/remotion/s28_r07_critical_integration.test.ts` | `TEST_SUITE` | 158 | 6,234 |
| `tests/remotion/s28_r07_waveform.test.ts` | `TEST_SUITE` | 226 | 9,904 |
| `tests/remotion/s28_r07b_critical_integration.test.ts` | `TEST_SUITE` | 304 | 12,093 |
| `tests/remotion/s28_r07b_performance.test.ts` | `TEST_SUITE` | 216 | 8,883 |
| `tests/remotion/s28_r07b_preview_fidelity_and_proxy.test.ts` | `TEST_SUITE` | 710 | 24,604 |
| `tests/remotion/s28_r08_renderer_core.test.ts` | `TEST_SUITE` | 652 | 22,260 |
| `tests/remotion/s28_r09_remotion_adapter.test.ts` | `TEST_SUITE` | 893 | 34,710 |
| `tests/remotion/s28_r10_canvas_adapter.test.ts` | `TEST_SUITE` | 613 | 22,058 |
| `tests/remotion/s28_r11_master_compositor.test.ts` | `TEST_SUITE` | 932 | 34,222 |
| `tests/remotion/s28_r12_render_planner.test.ts` | `TEST_SUITE` | 758 | 33,040 |
| `tests/remotion/s28_r13_unified_authoring.test.ts` | `TEST_SUITE` | 906 | 39,191 |
| `tests/remotion/s28_r14_production_integration.test.ts` | `TEST_SUITE` | 1,469 | 57,878 |
| `tests/remotion/s28_r15_destruction_and_load.test.ts` | `TEST_SUITE` | 1,372 | 58,335 |
| `tests/remotion/s28_r15_part3_final_campaigns.test.ts` | `TEST_SUITE` | 462 | 19,008 |
| `tests/remotion/template_contract_parity.test.ts` | `TEST_SUITE` | 135 | 5,660 |
| `tests/remotion/template_runtime_resolution.test.ts` | `TEST_SUITE` | 140 | 5,524 |
| `tests/remotion/zod_v3_v4_parity.test.ts` | `TEST_SUITE` | 281 | 9,540 |
| `tests/security/test_guardian.py` | `TEST_SUITE` | 78 | 3,113 |
| `tests/security/test_guardrails.py` | `TEST_SUITE` | 68 | 2,944 |
| `tests/security/test_mcp_security.py` | `TEST_SUITE` | 35 | 1,513 |
| `tests/security/test_path_traversal.py` | `TEST_SUITE` | 86 | 3,158 |
| `tests/security/test_pr001_authentication_hardening.py` | `TEST_SUITE` | 710 | 28,526 |
| `tests/security/test_pr002_integration_gate.py` | `TEST_SUITE` | 530 | 23,839 |
| `tests/security/test_pr002_tenant_isolation.py` | `TEST_SUITE` | 579 | 24,207 |
| `tests/security/test_project_lock_and_credential_isolation.py` | `TEST_SUITE` | 522 | 24,233 |
| `tests/security/test_race_conditions.py` | `TEST_SUITE` | 85 | 4,476 |
| `tests/security/test_s02_negative_enforcement.py` | `TEST_SUITE` | 626 | 24,676 |
| `tests/security/test_security_path_traversal.py` | `TEST_SUITE` | 44 | 1,712 |
| `tests/security/test_subprocess_security.py` | `TEST_SUITE` | 88 | 3,970 |
| `tests/security/test_tenant_authorization.py` | `TEST_SUITE` | 111 | 4,641 |
| `tests/security/test_tenant_path_isolation.py` | `TEST_SUITE` | 468 | 19,257 |
| `tests/snapshots/command_guard_block_curl.json` | `TEST_SUITE` | 5 | 416 |
| `tests/snapshots/command_guard_block_npm_studio.json` | `TEST_SUITE` | 5 | 314 |
| `tests/snapshots/test_snapshots.py` | `TEST_SUITE` | 144 | 6,541 |
| `tests/snapshots/write_guard_block_absolute_path.json` | `TEST_SUITE` | 5 | 327 |
| `tests/snapshots/write_guard_block_studio_approved.json` | `TEST_SUITE` | 5 | 306 |
| `tests/snapshots/write_guard_block_timings.json` | `TEST_SUITE` | 5 | 305 |
| `tests/validators/test_schemas_validation.py` | `TEST_SUITE` | 296 | 13,215 |
| `tests/validators/test_template_registry_consistency.py` | `TEST_SUITE` | 97 | 3,762 |

</details>

