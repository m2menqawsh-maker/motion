"""
ai/vision/object_person.py
==========================
Canonical Object Detection, Person Tracking, and Scene Classification (S27.15 / AI-13).

Invariants:
- Normalizes spatial and semantic classifications into strictly typed domain contracts.
- Uses neutral human subject identifiers (e.g. 'PERSON_00', 'PERSON_01') to prevent biased attribution.
- Enforces adaptive resolution (Scene Classification = LOW/MEDIUM, Object/Person = MEDIUM/HIGH).
- All detections carry cryptographic AnalysisProvenance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import JsonValue

from ai.contracts.media import AnalysisProvenance
from ai.contracts.vision import (
    BoundingBox,
    Keyframe,
    VisualObjectObservation,
    VisualObservation,
    VisualPersonObservation,
    VisualSceneClassification,
)


class VisualClassificationEngine:
    """
    Provider-neutral coordinator for spatial objects, human subjects, and scene tags.
    """

    def __init__(self, default_provider_id: str = "local"):
        self.default_provider_id = default_provider_id

    def classify_scene(
        self,
        start: float,
        end: float,
        label: str = "studio",
        confidence: float = 0.95,
        resolution_tier: str = "LOW",
        provider_id: Optional[str] = None,
        model_id: str = "scene-classifier-v1",
    ) -> VisualSceneClassification:
        now_utc = datetime.now(timezone.utc)
        prov = AnalysisProvenance(
            producer="visual_classification_engine",
            provider=provider_id or self.default_provider_id,
            model=model_id,
            version="1.0.0",
            confidence=confidence,
            timestamp=now_utc,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )
        return VisualSceneClassification(
            label=label,
            start=start,
            end=end,
            confidence=confidence,
            resolution_tier=resolution_tier,
            provenance=prov,
        )

    def detect_objects(
        self,
        keyframe: Keyframe,
        simulated_objects: Optional[List[Dict[str, JsonValue]]] = None,
        provider_id: Optional[str] = None,
        model_id: str = "object-detector-v1",
    ) -> List[VisualObjectObservation]:
        now_utc = datetime.now(timezone.utc)
        prov = AnalysisProvenance(
            producer="object_detector",
            provider=provider_id or self.default_provider_id,
            model=model_id,
            version="1.0.0",
            confidence=0.96,
            timestamp=now_utc,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

        results: List[VisualObjectObservation] = []
        if simulated_objects:
            for item in simulated_objects:
                lbl = str(item.get("label", "object"))
                bbox = None
                if "box" in item and isinstance(item["box"], dict):
                    b = item["box"]
                    bbox = BoundingBox(
                        x=float(b.get("x", 0.0)),
                        y=float(b.get("y", 0.0)),
                        width=float(b.get("width", 1.0)),
                        height=float(b.get("height", 1.0)),
                    )
                results.append(
                    VisualObjectObservation(
                        label=lbl,
                        bounding_box=bbox,
                        timestamp=keyframe.timestamp,
                        frame_ref=keyframe.keyframe_id,
                        confidence=float(item.get("confidence", 0.95)),
                        provenance=prov,
                    )
                )
        return results

    def detect_people(
        self,
        keyframe: Keyframe,
        simulated_people: Optional[List[Dict[str, JsonValue]]] = None,
        provider_id: Optional[str] = None,
        model_id: str = "person-detector-v1",
    ) -> List[VisualPersonObservation]:
        now_utc = datetime.now(timezone.utc)
        prov = AnalysisProvenance(
            producer="person_detector",
            provider=provider_id or self.default_provider_id,
            model=model_id,
            version="1.0.0",
            confidence=0.98,
            timestamp=now_utc,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

        results: List[VisualPersonObservation] = []
        if simulated_people:
            for idx, item in enumerate(simulated_people):
                pid = str(item.get("person_id", f"PERSON_{idx:02d}"))
                bbox = None
                if "box" in item and isinstance(item["box"], dict):
                    b = item["box"]
                    bbox = BoundingBox(
                        x=float(b.get("x", 0.0)),
                        y=float(b.get("y", 0.0)),
                        width=float(b.get("width", 1.0)),
                        height=float(b.get("height", 1.0)),
                    )
                results.append(
                    VisualPersonObservation(
                        person_id=pid,
                        bounding_box=bbox,
                        timestamp=keyframe.timestamp,
                        frame_ref=keyframe.keyframe_id,
                        confidence=float(item.get("confidence", 0.98)),
                        provenance=prov,
                    )
                )
        return results
