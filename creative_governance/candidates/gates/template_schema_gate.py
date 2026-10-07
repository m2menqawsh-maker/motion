"""
creative_governance/candidates/gates/template_schema_gate.py
===========================================
Template Schema Gate for TemplateCandidate Static Validation (S28-07B).

Validates that candidate template_schema adheres to canonical schema structure
and that candidate fixtures strictly validate against the declared schema.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import jsonschema

from creative_governance.candidates.gates.base import StaticGate
from creative_governance.candidates.policies import ValidationFailureCode
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext

SUPPORTED_SCHEMA_TYPES = {"string", "number", "integer", "boolean", "object", "array", "null"}


class TemplateSchemaGate(StaticGate):
    """
    Validates structural correctness of candidate props schema and verifies
    that sample fixtures strictly satisfy schema constraints.
    """

    @property
    def gate_id(self) -> str:
        return "template_schema_gate"

    def run(
        self,
        candidate: TemplateCandidate,
        tenant_context: TenantContext,
        ast_analysis: Optional[Dict[str, Any]] = None,
    ) -> CandidateGateResult:
        schema = candidate.template_schema
        fixtures = candidate.fixtures

        # 1. Structural Schema Validity
        if not isinstance(schema, dict) or not schema:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_SCHEMA_STRUCTURE,
                summary="Candidate template_schema must be a non-empty dictionary.",
                machine_details={"schema": schema},
            )

        try:
            jsonschema.Draft7Validator.check_schema(schema)
        except jsonschema.exceptions.SchemaError as e:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_SCHEMA_STRUCTURE,
                summary=f"Candidate template_schema is not a valid JSON Schema: {e.message}",
                machine_details={"schema_error": str(e)},
            )
        except Exception as e:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.CORRUPTED_SCHEMA,
                summary=f"Candidate template_schema could not be evaluated: {str(e)}",
                machine_details={"error": str(e)},
            )

        # 2. Enforce object shape & supported property types
        schema_type = schema.get("type")
        if schema_type != "object":
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_SCHEMA_STRUCTURE,
                summary=f"Template candidate schema top-level type must be 'object', got '{schema_type}'.",
                machine_details={"top_level_type": schema_type},
            )

        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_SCHEMA_STRUCTURE,
                summary="Template candidate schema 'properties' must be an object dictionary.",
                machine_details={"properties": properties},
            )

        for prop_name, prop_def in properties.items():
            if isinstance(prop_def, dict):
                p_type = prop_def.get("type")
                if p_type:
                    if isinstance(p_type, str) and p_type not in SUPPORTED_SCHEMA_TYPES:
                        return CandidateGateResult(
                            gate_id=self.gate_id,
                            status=GateStatus.FAIL,
                            failure_code=ValidationFailureCode.UNSUPPORTED_PROPERTY_TYPE,
                            summary=(
                                f"Property '{prop_name}' specifies unsupported type '{p_type}'. "
                                f"Supported types: {sorted(list(SUPPORTED_SCHEMA_TYPES))}."
                            ),
                            machine_details={"property": prop_name, "type": p_type},
                        )

        # 3. Check Required Properties defined in properties
        required_props = schema.get("required", [])
        if isinstance(required_props, list):
            for req in required_props:
                if req not in properties:
                    return CandidateGateResult(
                        gate_id=self.gate_id,
                        status=GateStatus.FAIL,
                        failure_code=ValidationFailureCode.INVALID_REQUIRED_PROPERTIES,
                        summary=f"Required property '{req}' is not declared in schema 'properties'.",
                        machine_details={"missing_required_property": req},
                    )

        # 4. Fixtures presence
        if not isinstance(fixtures, dict) or not fixtures:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.EMPTY_FIXTURES,
                summary="Candidate fixtures must be a non-empty dictionary representing valid props.",
                machine_details={"fixtures": fixtures},
            )

        # 5. Validate Fixture Against Schema
        try:
            validator = jsonschema.Draft7Validator(schema)
            errors = list(validator.iter_errors(fixtures))
            if errors:
                first_err = errors[0]
                field_path = ".".join(str(p) for p in first_err.absolute_path) or "root"
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.FIXTURE_SCHEMA_MISMATCH,
                    summary=f"Fixture validation failed at '{field_path}': {first_err.message}",
                    machine_details={
                        "field_path": field_path,
                        "error_message": first_err.message,
                        "total_errors": len(errors),
                    },
                )
        except Exception as e:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.ERROR,
                failure_code=ValidationFailureCode.VALIDATOR_EXECUTION_ERROR,
                summary=f"Schema validator error while evaluating fixtures: {str(e)}",
                machine_details={"error": str(e)},
            )

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary="Candidate template_schema is valid and fixtures satisfy all schema constraints.",
            machine_details={
                "properties_count": len(properties),
                "required_count": len(required_props),
            },
        )
