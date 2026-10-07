# AI Contract Evolution & Backward Compatibility Policy (S27.1)

## Metadata
- **Status:** APPROVED (S27.1 Contract Authority)
- **Authority:** Pydantic (`ai/contracts/*.py`)
- **Downstream Targets:** JSON Schema (`schemas/ai/*.json`), TypeScript (`contracts/generated/ai_contracts.ts`, `remotion-app/src/types/ai_contracts.ts`)
- **Scope:** All AI subsystem boundary contracts.

---

## 1. Authority Hierarchy
Per ADR-004 DEC-06.2, the single machine-readable source of truth is:
```text
Python Pydantic Contracts (ai/contracts/*.py)
                    ↓ (Export)
JSON Schema Definitions (schemas/ai/*.schema.json)
                    ↓ (Code Generation)
TypeScript Interfaces (contracts/generated/ai_contracts.ts)
```
Duplicate manual definition of contracts in TypeScript or schema files is strictly prohibited.
All artifacts are verified in CI using `python scripts/generate_ai_contracts.py --check`.

---

## 2. Strict Ingress Boundaries
All boundary contracts inherit from `AIContractModel` with:
- `extra = "forbid"`: Unexpected keys from external models or untrusted callers are immediately rejected.
- `strict = True`: Implicit type coercions that can obscure model hallucinations or type drift are forbidden.
- `frozen = True`: Boundary payloads are immutable value objects.
- `TzAwareDatetime`: All timestamps must explicitly provide timezone offsets (e.g., UTC `Z`).
- `Decimal`: Monetary amounts must use exact Decimal representation. Floating-point authority is banned.

---

## 3. Versioning Semantics (SemVer)
Contracts carry a `contract_version` field adhering to Semantic Versioning (`MAJOR.MINOR.PATCH`):

1. **PATCH bump (`1.0.0` -> `1.0.1`):**
   - Non-breaking clarifications in field descriptions, documentation, or regex tightening that does not invalidate previously valid payloads.
   - Internal validator bug fixes.

2. **MINOR bump (`1.0.0` -> `1.1.0`):**
   - Backward-compatible additions:
     - Adding a new optional field (with a default value of `None` or an empty collection).
     - Expanding an enum with a new variant (see Enum Expansion Policy below).
     - Loosening an overly restrictive optional constraint.

3. **MAJOR bump (`1.0.0` -> `2.0.0`):**
   - Breaking changes:
     - Removing a field or renaming an existing field.
     - Changing the type of an existing field.
     - Making an existing optional field mandatory.
     - Removing or renaming an enum variant.
     - Altering semantic invariant constraints (e.g. changing bounds).

---

## 4. Enum Expansion Policy
- AI subsystem enums (`CapabilityType`, `AIErrorCode`, `ExecutionClass`, `QualityTarget`, etc.) are closed, strictly checked vocabularies.
- Unknown enum strings fail schema validation immediately.
- Adding a new variant to an enum constitutes a **MINOR** version increment.
- Consumers (such as switch statements in TypeScript or Python match/case) MUST include a default fallback or error handler for unexpected variants when communicating across distributed version boundaries.

---

## 5. Required Field Policy
- Fields that represent foundational tenant identity, operational targets, or security context are mandatory (`request_id`, `workspace_id`, `actor_id`, `capability`, `created_at`, `status`).
- All newly introduced fields in subsequent iterations MUST be optional with sensible defaults to preserve backward compatibility with existing serialized payloads.
- Making any optional field required requires a deprecation period and a MAJOR version bump.

---

## 6. Deprecation Policy
- Deprecated fields must be annotated in Pydantic with `deprecated=True` or documentation docstrings.
- Deprecated fields must remain functional for at least one minor release cycle before removal in the next major version.
