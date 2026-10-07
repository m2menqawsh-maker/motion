"""
ai/planning/reuse_engine.py
===========================
Authoritative REUSE Engine for S28-06 (Part A).

Sole Authority:
- Canonical Template Registry (contracts/template-runtime-contract.json and registry/template-registry-data.json)
  is the sole reusable-template authority.
- The REUSE Engine can: READ, FILTER, RANK, VALIDATE.
- The REUSE Engine CANNOT: REGISTER, PROMOTE, MUTATE, DELETE.
- Any template not in the Canonical Registry CANNOT be selected as REUSE.

Pipeline:
SceneIntent / Need
↓
Hard Compatibility Filters (Aspect, Content Family, Props, Media, AudioMode, Status)
↓
Eligible Registered Templates
↓
Metadata + Semantic Ranking (Style, Motion, Content, Duration, Media)
↓
Ranked Candidates
↓
Suitability Evaluation (Fit score >= threshold, full requirements coverage)
↓
Structured Audit Evidence (ReuseEvaluationResult)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import (
    ReuseCandidateScore,
    ReuseEvaluationResult,
    SceneIntent,
)
from scripts.core.template_contract import (
    TemplateRegistryContract,
    get_template_contract,
)

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_DATA_PATH = ROOT / "registry" / "template-registry-data.json"
CATALOG_PATH = ROOT / "ground-truth" / "template_catalog.json"


class TemplateMetadataRecord:
    """Consolidated read-only metadata snapshot for a registered template."""

    def __init__(
        self,
        canonical_id: str,
        category: str,
        component_name: str,
        default_duration_frames: int,
        runtime_available: bool,
        aliases: List[str],
        label: Dict[str, str],
        description: Dict[str, str],
        schema: Dict[str, Any],
        defaults: Dict[str, Any],
        supported_aspects: List[str],
        use_cases: List[str],
        intents: List[str],
        moods: List[str],
        capabilities: List[str],
        family: str,
        quality: str,
    ) -> None:
        self.canonical_id = canonical_id
        self.category = category
        self.component_name = component_name
        self.default_duration_frames = default_duration_frames
        self.runtime_available = runtime_available
        self.aliases = aliases
        self.label = label
        self.description = description
        self.schema = schema
        self.defaults = defaults
        self.supported_aspects = supported_aspects
        self.use_cases = use_cases
        self.intents = intents
        self.moods = moods
        self.capabilities = capabilities
        self.family = family
        self.quality = quality


class SemanticScorer:
    """Provider-neutral semantic scoring interface (Section 51)."""

    def compute_similarity(self, query: str, document: str) -> float:
        """Computes similarity score between 0.0 and 1.0."""
        raise NotImplementedError


class DeterministicLexicalSemanticScorer(SemanticScorer):
    """Deterministic, provider-neutral lexical/token similarity scorer."""

    def compute_similarity(self, query: str, document: str) -> float:
        if not query or not document:
            return 0.0
        q_tokens = set(re.findall(r"\w+", query.lower()))
        d_tokens = set(re.findall(r"\w+", document.lower()))
        if not q_tokens or not d_tokens:
            return 0.0
        intersection = q_tokens.intersection(d_tokens)
        query_coverage = len(intersection) / len(q_tokens)
        jaccard = len(intersection) / len(q_tokens.union(d_tokens))
        return round(0.7 * query_coverage + 0.3 * jaccard, 4)


class ReuseEngine:
    """
    Authoritative REUSE Engine searching solely within the Canonical Template Registry.
    Guarantees strict read-only interaction, hard compatibility filtering before ranking,
    and deterministic structured audit evidence generation.
    """

    DEFAULT_SUITABILITY_THRESHOLD: float = 0.70

    def __init__(
        self,
        template_contract: Optional[TemplateRegistryContract] = None,
        registry_data_path: Path = REGISTRY_DATA_PATH,
        catalog_path: Path = CATALOG_PATH,
        semantic_scorer: Optional[SemanticScorer] = None,
        suitability_threshold: float = DEFAULT_SUITABILITY_THRESHOLD,
    ) -> None:
        self.contract = template_contract or get_template_contract()
        self.registry_data_path = registry_data_path
        self.catalog_path = catalog_path
        self.semantic_scorer = semantic_scorer or DeterministicLexicalSemanticScorer()
        self.suitability_threshold = suitability_threshold
        self._template_metadata: Dict[str, TemplateMetadataRecord] = {}
        self._load_registry_metadata()

    def reload(self) -> None:
        """Reloads registry metadata and contract cache deterministically."""
        self.contract = get_template_contract(contract_path=self.contract.contract_path, reload=True)
        self._template_metadata.clear()
        self._load_registry_metadata()

    def _load_registry_metadata(self) -> None:
        """Loads rich template metadata, strictly validating against canonical registry IDs."""
        raw_reg = {}
        if self.registry_data_path.exists():
            try:
                raw_reg = json.loads(self.registry_data_path.read_text(encoding="utf-8")).get("templates", {})
            except Exception:
                raw_reg = {}

        raw_catalog = []
        if self.catalog_path.exists():
            try:
                raw_catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            except Exception:
                raw_catalog = []

        cat_by_id: Dict[str, Dict[str, Any]] = {}
        for item in raw_catalog:
            if isinstance(item, dict) and "id" in item:
                cat_by_id[item["id"]] = item

        # Build records strictly for canonical IDs in the contract
        for cid in self.contract.list_canonical_ids():
            entry = self.contract.get_entry(cid)
            if not entry:
                continue

            reg_data = raw_reg.get(cid, {})
            cat_data = cat_by_id.get(cid, {})

            # Schema and defaults
            schema = reg_data.get("schema", {})
            defaults = reg_data.get("defaults", {})
            label = reg_data.get("label", {"en": entry.component_name, "ar": entry.component_name})
            desc = reg_data.get("description", {"en": "", "ar": ""})

            # Aspects from catalog (default: 16:9, 9:16, 1:1)
            supported_aspects = cat_data.get("supported_aspects", ["16:9", "9:16", "1:1"])
            use_cases = cat_data.get("use_cases", [])
            intents = cat_data.get("intents", [])
            moods = cat_data.get("moods", [])
            capabilities = cat_data.get("capabilities", [])
            family = cat_data.get("family", entry.category)
            quality = cat_data.get("quality", "B")

            # Rich domain inference if catalog lists empty arrays
            derived_intents, derived_caps, derived_moods = self._infer_template_semantics(
                cid=cid,
                component_name=entry.component_name,
                category=entry.category,
                schema=schema,
            )
            if not intents:
                intents = derived_intents
            if not capabilities:
                capabilities = derived_caps
            if not moods:
                moods = derived_moods

            self._template_metadata[cid] = TemplateMetadataRecord(
                canonical_id=cid,
                category=entry.category,
                component_name=entry.component_name,
                default_duration_frames=entry.default_duration_frames,
                runtime_available=entry.runtime_available,
                aliases=entry.aliases,
                label=label,
                description=desc,
                schema=schema,
                defaults=defaults,
                supported_aspects=supported_aspects,
                use_cases=use_cases,
                intents=intents,
                moods=moods,
                capabilities=capabilities,
                family=family,
                quality=quality,
            )

    def _infer_template_semantics(
        self, cid: str, component_name: str, category: str, schema: Dict[str, Any]
    ) -> Tuple[List[str], List[str], List[str]]:
        """Infers domain intents, capabilities, and moods from template identity and schema."""
        intents: List[str] = []
        caps: List[str] = list(schema.keys())
        moods: List[str] = ["Cinematic", "Energetic"]
        name = f"{cid} {component_name}".lower()
        tokens = set(re.findall(r"[a-z0-9]+", name))

        if tokens.intersection({"stat", "counter", "metric", "ticker", "stats", "metrics"}):
            intents.extend(["proof", "statistic", "solution", "metric", "numbers", "kpi"])
            caps.extend(["numbers", "metric", "counter", "title", "data", "proof"])
            moods.extend(["Technical", "Energetic", "Clean", "Corporate"])
        elif tokens.intersection({"hook", "intro", "title", "banner", "headline"}):
            intents.extend(["hook", "intro", "problem", "title", "headline"])
            caps.extend(["headline", "hook", "title", "attention"])
            moods.extend(["Cinematic", "Energetic", "Bold", "Punchy"])
        elif tokens.intersection({"code", "terminal", "deploy", "commit", "syntax", "diff"}):
            intents.extend(["code_demo", "mechanism", "proof", "demonstration", "technical_explanation"])
            caps.extend(["code", "syntax", "terminal", "diff", "programming", "code_block"])
            moods.extend(["Technical", "Precise", "Focused", "Modern"])
        elif tokens.intersection({"chart", "graph", "bar", "pie", "timeseries"}):
            intents.extend(["chart", "comparison", "proof", "data_story", "growth", "statistic"])
            caps.extend(["chart", "graph", "visualization", "data", "comparison"])
            moods.extend(["Technical", "Corporate", "Analytical"])
        elif tokens.intersection({"table", "comparison", "matrix"}):
            intents.extend(["comparison", "proof", "table", "evaluation"])
            caps.extend(["table", "comparison", "matrix", "data"])
            moods.extend(["Technical", "Corporate", "Analytical"])
        elif tokens.intersection({"end", "cta", "outro"}) or "endcard" in name or "end-card" in cid:
            intents.extend(["cta", "outro", "payoff", "action", "subscribe"])
            caps.extend(["call_to_action", "button", "link", "summary"])
            moods.extend(["Energetic", "Direct", "Friendly"])
        elif tokens.intersection({"calendar", "month", "schedule", "date"}):
            intents.extend(["calendar", "schedule", "event", "timeline", "date"])
            caps.extend(["calendar", "date", "schedule"])
            moods.extend(["Organized", "Clean", "Corporate"])
        elif tokens.intersection({"talking", "head", "creator", "speaker", "presenter"}):
            intents.extend(["talking_head", "personal_narrative", "vlog", "presenter"])
            caps.extend(["speaker", "presenter", "face", "talking_head"])
            moods.extend(["Thoughtful", "Conversational", "Authentic"])
        elif tokens.intersection({"audiogram", "podcast", "wave", "spectrum"}):
            intents.extend(["audiogram", "speech_audiogram", "podcast_clip", "sound_wave"])
            caps.extend(["audio_spectrum", "waveform", "captions", "speech"])
            moods.extend(["Conversational", "Authentic", "Dynamic"])
        elif tokens.intersection({"device", "mockup", "browser", "mobile", "laptop", "phone"}):
            intents.extend(["product_demo", "device_mockup", "showcase", "mechanism", "action"])
            caps.extend(["device", "mobile", "desktop", "laptop", "mockup", "browser"])
            moods.extend(["Cinematic", "Premium", "Sleek"])
        elif tokens.intersection({"split", "versus", "vs"}):
            intents.extend(["comparison", "split_screen", "before_after", "dual", "proof"])
            caps.extend(["split", "side_by_side", "comparison"])
            moods.extend(["Analytical", "Cinematic", "Energetic"])
        elif tokens.intersection({"faq", "accordion"}):
            intents.extend(["objection_handling", "faq", "solution", "qa"])
            caps.extend(["accordion", "qa", "text"])
            moods.extend(["Thoughtful", "Helpful"])
        elif tokens.intersection({"bento", "showcase", "feature", "kanban", "timeline", "pipe", "pipes", "flow"}):
            intents.extend(["feature_walkthrough", "overview", "showcase", "solution", "mechanism"])
            caps.extend(["grid", "cards", "pan", "features", "timeline", "data_flow"])
            moods.extend(["Modern", "Cinematic", "Clean"])
        else:
            intents.append(category)

        return list(dict.fromkeys(intents)), list(dict.fromkeys(caps)), list(dict.fromkeys(moods))

    def evaluate_template_hard_compatibility(
        self,
        template: TemplateMetadataRecord,
        scene_intent: SceneIntent,
        aspect_ratio: str = "9:16",
        audio_mode: Optional[AudioMode] = None,
        expected_family: Optional[str] = None,
        required_props: Optional[List[str]] = None,
        required_media: Optional[List[str]] = None,
        forbidden_capabilities: Optional[List[str]] = None,
        template_aspect_overrides: Optional[Dict[str, List[str]]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Executes strict hard compatibility filters (Sections 10-15).
        Returns (is_eligible, failure_reasons).
        """
        failures: List[str] = []

        # 1. Status & Runtime Availability (Section 15)
        if not template.runtime_available or not self.contract.is_valid(template.canonical_id):
            failures.append(f"Template '{template.canonical_id}' is retired, disabled, or not runtime available.")

        # 2. Aspect Ratio Compatibility (Section 11)
        aspects = template.supported_aspects
        if template_aspect_overrides and template.canonical_id in template_aspect_overrides:
            aspects = template_aspect_overrides[template.canonical_id]
        if aspect_ratio and aspect_ratio not in aspects:
            failures.append(
                f"Aspect ratio mismatch: requested '{aspect_ratio}' is not in supported aspects {aspects}."
            )

        # 3. Audio Mode Compatibility (Section 63)
        active_audio_mode = audio_mode or AudioMode.VO_MUSIC
        if active_audio_mode in (AudioMode.MUSIC_ONLY, AudioMode.SILENT):
            # 3a. If the scene intent itself explicitly requires spoken speech or audiogram
            intent_label_lower = scene_intent.intent_label.lower()
            if any(ind in intent_label_lower for ind in ("audiogram", "podcast", "talking_head", "speech")):
                failures.append(
                    f"AudioMode '{active_audio_mode.value}' forbids spoken voiceover/audiogram intent '{scene_intent.intent_label}'."
                )
            if scene_intent.template_requirements:
                if any(req.lower() in ("audio_spectrum", "waveform", "speech", "speaker", "captions") for req in scene_intent.template_requirements):
                    failures.append(
                        f"AudioMode '{active_audio_mode.value}' forbids speech/audiogram template requirements."
                    )
            # 3b. Templates strictly requiring spoken speech or speech spectrum are forbidden
            spoken_indicators = ("audiogram", "podcast", "talking_head", "talking-head", "voiceover", "speech", "interview", "audio_spectrum", "waveform")
            if any(
                ind in template.canonical_id.lower()
                or ind in template.family.lower()
                or ind in template.category.lower()
                or any(ind in cap.lower() for cap in template.capabilities)
                for ind in spoken_indicators
            ):
                failures.append(
                    f"AudioMode '{active_audio_mode.value}' forbids spoken voiceover required by '{template.canonical_id}'."
                )

        # 4. Family Compatibility (Section 12 / S28-06A)
        if expected_family:
            expected_fam_norm = expected_family.lower().replace("-", "").replace("_", "").replace("wrapper", "")
            actual_fam_norm = template.family.lower().replace("-", "").replace("_", "").replace("wrapper", "")
            if expected_fam_norm not in actual_fam_norm and actual_fam_norm not in expected_fam_norm:
                failures.append(
                    f"Template family '{template.family}' does not match expected family '{expected_family}'."
                )

        # 5. Content / Visual Job Compatibility (Section 12)
        # Check explicit template_requirements from SceneIntent
        if scene_intent.template_requirements:
            for req in scene_intent.template_requirements:
                req_lower = req.lower().replace("-", "_")
                # Must match template capabilities, schema keys, or category
                has_req = any(
                    req_lower in cap.lower().replace("-", "_")
                    for cap in template.capabilities + list(template.schema.keys()) + [template.category, template.family]
                )
                if not has_req:
                    failures.append(f"Template does not satisfy required template capability: '{req}'.")

        # Incompatible content exclusions
        intent_label = scene_intent.intent_label.lower()
        if any(m in intent_label for m in ("music_montage", "montage", "music_video")):
            if any(th in template.canonical_id.lower() or th in template.family.lower() for th in ("talking_head", "talkinghead", "creator_reel", "creatorreel", "interview", "podcast")):
                failures.append("Talking-head/interview template is strictly incompatible with music montage intent.")
        elif "talking_head" in intent_label or "presenter" in intent_label:
            if not any(th in template.canonical_id.lower() or th in template.family.lower() for th in ("talking_head", "talkinghead", "creator_reel", "creatorreel", "speaker", "presenter")):
                failures.append(f"Template '{template.canonical_id}' does not support talking-head/presenter layout.")

        # 5. Props Compatibility (Section 13)
        if required_props:
            schema_keys = set(template.schema.keys())
            for prop in required_props:
                if prop not in schema_keys:
                    failures.append(f"Required property '{prop}' is unsupported by template schema.")

        # 6. Media Compatibility (Section 14)
        if required_media:
            schema_text = json.dumps(template.schema).lower()
            for media in required_media:
                media_lower = media.lower()
                if "video" in media_lower:
                    if "video" not in schema_text and "media" not in schema_text:
                        failures.append(f"Required video media capability is unsupported by template schema.")
                elif "image" in media_lower:
                    if "image" not in schema_text and "media" not in schema_text:
                        failures.append(f"Required image media capability is unsupported by template schema.")

        # 7. Forbidden Capabilities (Safety & Recipe boundaries)
        if forbidden_capabilities:
            for cap in forbidden_capabilities:
                if cap in template.capabilities:
                    failures.append(f"Template contains forbidden capability '{cap}'.")

        return len(failures) == 0, failures

    def compute_template_fit_score(
        self,
        template: TemplateMetadataRecord,
        scene_intent: SceneIntent,
        fps: int = 30,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Computes weighted metadata and semantic ranking score (Section 16).
        Returns (overall_fit_score, score_breakdown).
        """
        # 1. Content & Intent Fit (Weight: 0.35)
        content_score = 0.0
        intent_lower = scene_intent.intent_label.lower()
        visual_job_lower = scene_intent.primary_visual_job.lower()

        # Direct intent match
        if any(intent_lower in i.lower() for i in template.intents):
            content_score += 0.5
        elif any(intent_lower in u.lower() for u in template.use_cases):
            content_score += 0.4

        # Visual job match
        if any(visual_job_lower in c.lower() for c in template.capabilities):
            content_score += 0.3
        elif any(visual_job_lower in d.lower() for d in template.description.values()):
            content_score += 0.2

        # Semantic query match with label / description
        semantic_query = f"{scene_intent.intent_label} {scene_intent.primary_visual_job} {scene_intent.mood}"
        doc_text = f"{template.canonical_id} {template.label.get('en', '')} {template.description.get('en', '')} {' '.join(template.intents)} {' '.join(template.capabilities)}"
        lex_sim = self.semantic_scorer.compute_similarity(semantic_query, doc_text)
        content_score += 0.2 * min(1.0, lex_sim * 2.0)

        # Explicit template_requirements boost
        if scene_intent.template_requirements:
            req_matches = 0
            for req in scene_intent.template_requirements:
                r_lower = req.lower().replace("-", "_")
                if (
                    any(r_lower in cap.lower().replace("-", "_") for cap in template.capabilities)
                    or r_lower in template.canonical_id.lower().replace("-", "_")
                    or r_lower in template.component_name.lower().replace("-", "_")
                ):
                    req_matches += 1
            if req_matches > 0:
                content_score += 0.25 * (req_matches / len(scene_intent.template_requirements))

        content_score = min(1.0, content_score)

        # 2. Motion Personality Fit (Weight: 0.20)
        motion_score = 0.0
        target_motion = scene_intent.motion_personality.lower()
        if any(target_motion in m.lower() for m in template.moods):
            motion_score = 1.0
        elif target_motion in ("cinematic", "smooth") and template.category in ("composition", "effect"):
            motion_score = 0.8
        elif target_motion in ("energetic", "punchy") and ("pulse" in template.canonical_id or "ticker" in template.canonical_id):
            motion_score = 0.9
        else:
            motion_score = 0.6

        # 3. Style & Mood Fit (Weight: 0.15)
        style_score = 0.0
        target_mood = scene_intent.mood.lower()
        if any(target_mood in m.lower() for m in template.moods):
            style_score = 1.0
        elif self.semantic_scorer.compute_similarity(target_mood, " ".join(template.moods)) > 0:
            style_score = 0.8
        else:
            style_score = 0.6

        # 4. Duration Fit (Weight: 0.15)
        target_frames = scene_intent.estimated_duration_sec * fps
        actual_frames = template.default_duration_frames
        ratio = min(target_frames, actual_frames) / max(target_frames, actual_frames) if max(target_frames, actual_frames) > 0 else 0.5
        duration_score = max(0.2, min(1.0, ratio))

        # 5. Media Fit (Weight: 0.15)
        media_score = 0.8
        if scene_intent.asset_requirements:
            schema_keys = set(template.schema.keys())
            matched_assets = 0
            for req in scene_intent.asset_requirements:
                if any(k in req.lower() for k in schema_keys) or any(req.lower() in k for k in schema_keys):
                    matched_assets += 1
            if matched_assets > 0:
                media_score = min(1.0, 0.5 + (0.5 * (matched_assets / len(scene_intent.asset_requirements))))

        # Weighted aggregate
        fit_score = round(
            0.35 * content_score +
            0.20 * motion_score +
            0.15 * style_score +
            0.15 * duration_score +
            0.15 * media_score,
            4,
        )

        breakdown = {
            "content_fit": round(content_score, 4),
            "motion_fit": round(motion_score, 4),
            "style_fit": round(style_score, 4),
            "duration_fit": round(duration_score, 4),
            "media_fit": round(media_score, 4),
        }

        return fit_score, breakdown

    def evaluate(
        self,
        scene_intent: SceneIntent,
        aspect_ratio: str = "9:16",
        audio_mode: Optional[AudioMode] = None,
        expected_family: Optional[str] = None,
        required_props: Optional[List[str]] = None,
        required_media: Optional[List[str]] = None,
        forbidden_capabilities: Optional[List[str]] = None,
        fps: int = 30,
        template_aspect_overrides: Optional[Dict[str, List[str]]] = None,
        force_unregistered_id_for_testing: Optional[str] = None,
    ) -> ReuseEvaluationResult:
        """
        Executes full REUSE retrieval pipeline and suitability evaluation (Sections 8-22).
        Fails closed on non-canonical templates.
        """
        candidates_checked: List[str] = []
        eligible_candidates: List[str] = []
        ranked_scores: List[ReuseCandidateScore] = []
        rejection_reasons: Dict[str, List[str]] = {}

        # Canonical inventory
        all_canonical_ids = self.contract.list_canonical_ids()
        candidates_checked.extend(all_canonical_ids)

        if force_unregistered_id_for_testing:
            candidates_checked.append(force_unregistered_id_for_testing)
            rejection_reasons[force_unregistered_id_for_testing] = [
                f"Template '{force_unregistered_id_for_testing}' is not in the Canonical Template Registry."
            ]

        # 1. Hard Compatibility Filtering (Run strictly before ranking)
        for cid in all_canonical_ids:
            record = self._template_metadata.get(cid)
            if not record:
                rejection_reasons[cid] = ["Missing template metadata record."]
                continue

            is_eligible, failures = self.evaluate_template_hard_compatibility(
                template=record,
                scene_intent=scene_intent,
                aspect_ratio=aspect_ratio,
                audio_mode=audio_mode,
                expected_family=expected_family,
                required_props=required_props,
                required_media=required_media,
                forbidden_capabilities=forbidden_capabilities,
                template_aspect_overrides=template_aspect_overrides,
            )

            if is_eligible:
                eligible_candidates.append(cid)
            else:
                rejection_reasons[cid] = failures

        # 2. Ranking over eligible candidates only
        for cid in eligible_candidates:
            record = self._template_metadata[cid]
            fit_score, breakdown = self.compute_template_fit_score(
                template=record,
                scene_intent=scene_intent,
                fps=fps,
            )
            is_sufficient = fit_score >= self.suitability_threshold
            ranked_scores.append(
                ReuseCandidateScore(
                    template_id=cid,
                    eligible=True,
                    hard_filter_failures=[],
                    fit_score=fit_score,
                    score_breakdown=breakdown,
                    sufficient=is_sufficient,
                )
            )

        # Record rejected candidates in ranked_scores for complete auditability
        for cid, failures in rejection_reasons.items():
            if cid in eligible_candidates:
                continue
            ranked_scores.append(
                ReuseCandidateScore(
                    template_id=cid,
                    eligible=False,
                    hard_filter_failures=failures,
                    fit_score=0.0,
                    score_breakdown={},
                    sufficient=False,
                )
            )

        # Deterministic sorting: eligible descending by fit_score, then canonical_id
        ranked_scores.sort(key=lambda s: (-int(s.eligible), -s.fit_score, s.template_id))

        # 3. Suitability Decision
        selected_candidate: Optional[str] = None
        sufficiency = False
        rationale: str

        if eligible_candidates and ranked_scores and ranked_scores[0].eligible:
            best_candidate = ranked_scores[0]
            if best_candidate.fit_score >= self.suitability_threshold:
                selected_candidate = best_candidate.template_id
                sufficiency = True
                rationale = (
                    f"REUSE sufficient: canonical registered template '{selected_candidate}' "
                    f"passed all hard compatibility filters with fit score {best_candidate.fit_score:.2f} "
                    f"(>= threshold {self.suitability_threshold:.2f})."
                )
            else:
                sufficiency = False
                rationale = (
                    f"REUSE insufficient: best eligible template '{best_candidate.template_id}' "
                    f"scored {best_candidate.fit_score:.2f}, below suitability threshold {self.suitability_threshold:.2f}."
                )
        else:
            sufficiency = False
            rationale = (
                f"REUSE insufficient: zero registered templates passed hard compatibility filters "
                f"for need '{scene_intent.intent_label}'."
            )

        need_desc = f"{scene_intent.intent_label} ({scene_intent.primary_visual_job}, aspect={aspect_ratio})"

        return ReuseEvaluationResult(
            need_description=need_desc,
            candidates_checked=candidates_checked,
            eligible_candidates=eligible_candidates,
            ranked_candidates=ranked_scores,
            selected_candidate=selected_candidate,
            rejection_reasons=rejection_reasons,
            sufficiency=sufficiency,
            rationale=rationale,
        )
