"""
ai/taste/registry.py
====================
Authoritative Registry for Creative Taste Rules (S28-04).

Guarantees:
- Taste Rule = Creative principle influencing decisions (Taste ≠ QC).
- Full provenance traceability: Every rule answers "Where did it come from?" via source_knowledge_ids.
- Strict enforcement degrees: MUST, SHOULD, PREFER, AVOID.
- Zero runtime authority: Taste cannot mutate lifecycle, approve QC, authorize tools, or write canonical templates.
- Pre-populated with verified principles derived from references/4_taste_engine/.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple
from ai.contracts.creative.taste import TasteRule, TasteRuleSeverity
from ai.taste.contracts import DuplicateTasteRuleError, InvalidTasteRuleError, TasteRuleNotFoundError


class TasteRuleRegistry:
    """
    Registry indexing and serving canonical creative TasteRules.
    """

    def __init__(self, seed_defaults: bool = True) -> None:
        # Key: (rule_id, version) -> TasteRule
        self._rules: Dict[Tuple[str, str], TasteRule] = {}
        # Key: rule_id -> latest TasteRule
        self._latest: Dict[str, TasteRule] = {}

        if seed_defaults:
            self._load_canonical_rules()

    def register(self, rule: TasteRule, allow_overwrite: bool = True) -> None:
        """Registers a TasteRule, verifying provenance and uniqueness."""
        if not rule.rule_id:
            raise InvalidTasteRuleError("TasteRule must specify a non-empty rule_id.")
        if not rule.citation_source:
            raise InvalidTasteRuleError(f"TasteRule '{rule.rule_id}' missing citation_source for provenance.")
        if not rule.source_knowledge_ids:
            raise InvalidTasteRuleError(f"TasteRule '{rule.rule_id}' missing source_knowledge_ids for provenance.")

        key = (rule.rule_id, rule.version)
        if key in self._rules and not allow_overwrite:
            raise DuplicateTasteRuleError(f"TasteRule '{rule.rule_id}' v{rule.version} already registered.")

        self._rules[key] = rule
        existing = self._latest.get(rule.rule_id)
        if existing is None or rule.version >= existing.version:
            self._latest[rule.rule_id] = rule

    def get(self, rule_id: str, version: Optional[str] = None) -> Optional[TasteRule]:
        """Retrieves a rule by ID and optional version."""
        if version is not None:
            return self._rules.get((rule_id, version))
        return self._latest.get(rule_id)

    def list_all(self) -> List[TasteRule]:
        """Returns all latest registered TasteRules sorted by priority descending."""
        return sorted(self._latest.values(), key=lambda r: r.priority, reverse=True)

    def list_by_category(self, category: str) -> List[TasteRule]:
        """Filters rules by category."""
        return [r for r in self.list_all() if r.category == category]

    def _load_canonical_rules(self) -> None:
        """Seeds canonical taste rules derived from references/4_taste_engine/."""
        seeds = [
            # 1. Avoid Constant Motion / Visual Rest
            TasteRule(
                rule_id="taste_avoid_constant_motion",
                category="choreography",
                name="Avoid Constant Motion",
                description="Prevent visual exhaustion by ensuring complex scenes have static rest periods and hierarchy.",
                rationale="When every element animates simultaneously, viewer attention is fragmented and message recall drops.",
                citation_source="references/4_taste_engine/user-signature-style.md#L54",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"scene_density": "high", "duration_sec_gt": 3.0},
                recommendation="Use motion hierarchy (Hero 100%, Supporting 30-50%, Ambient 10%) with deliberate resting pauses.",
                priority=90,
                exceptions=["explosive_celebration_burst", "100ms_glitch_accent"],
                source_knowledge_ids=["know_taste_signature_style", "know_taste_motion_personality"],
                parameters={"max_concurrent_moving_elements": 2, "min_rest_period_ms": 200},
            ),
            # 2. Double Variance
            TasteRule(
                rule_id="taste_double_variance",
                category="visual_grammar",
                name="Double Variance Rule",
                description="Consecutive visual framing units must never repeat identical styles or layout structures.",
                rationale="Visual rhythm requires unpredictable contrast to sustain attention over short-form videos.",
                citation_source="references/4_taste_engine/user-signature-style.md#L18",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"consecutive_units": True},
                recommendation="Two consecutive shots inside a scene must not carry the same frame style; consecutive scenes must not open with the same style.",
                priority=85,
                exceptions=["single_shot_minimal_scene"],
                source_knowledge_ids=["know_taste_signature_style"],
                parameters={"forbidden_repetition_distance": 2},
            ),
            # 3. Beat Density
            TasteRule(
                rule_id="taste_beat_density",
                category="rhythm",
                name="Beat Density per Sentence",
                description="Scale shot cuts and visual density directly according to sentence duration and energy.",
                rationale="Matches visual cutting tempo to spoken thought units (Scene = Sentence, Shot = Beat).",
                citation_source="references/4_taste_engine/user-signature-style.md#L13",
                severity=TasteRuleSeverity.SHOULD,
                version="1.0.0",
                applies_when={"spoken_voiceover": True},
                recommendation="Duration < 2.5s -> 1 shot; 2.5-5s -> 2 shots; 5-8s -> 2-3 shots; > 8s -> 3-4 shots.",
                priority=80,
                exceptions=["ambient_montage", "silent_mode"],
                source_knowledge_ids=["know_taste_signature_style"],
                parameters={"thresholds": {"short": 2.5, "medium": 5.0, "long": 8.0}},
            ),
            # 4. Kinetic RTL Tracking
            TasteRule(
                rule_id="taste_kinetic_rtl_tracking",
                category="typography",
                name="Kinetic RTL Tracking",
                description="For Arabic typography, text reveals Right-to-Left with the camera dynamically chasing the active word.",
                rationale="Natural reading flow in RTL languages requires focus to move rightward to leftward; sliding from fixed edges breaks readability.",
                citation_source="references/4_taste_engine/user-signature-style.md#L21",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"language": "ar"},
                recommendation="Reveal text Right-to-Left and lock camera tracking onto the current active word index.",
                priority=85,
                exceptions=["static_table_display"],
                source_knowledge_ids=["know_taste_signature_style"],
                parameters={"reveal_direction": "rtl", "camera_tracking": True},
            ),
            # 5. Word-Chase Zoom
            TasteRule(
                rule_id="taste_word_chase_zoom",
                category="camera",
                name="Word-Chase Zoom",
                description="Execute a punchy camera zoom diving directly into the emphasized key word.",
                rationale="Physically propels the viewer into the core proposition, punctuating the turning point.",
                citation_source="references/4_taste_engine/user-signature-style.md#L24",
                severity=TasteRuleSeverity.PREFER,
                version="1.0.0",
                applies_when={"has_emphasis_keyword": True},
                recommendation="Scale 1.25-1.4 over 250-400ms (ease-out-expo) diving into key word index.",
                priority=70,
                exceptions=["calm_luxury_minimal"],
                source_knowledge_ids=["know_taste_signature_style"],
                parameters={"scale_min": 1.25, "scale_max": 1.4, "duration_ms": 350},
            ),
            # 6. Emphasis Grammar
            TasteRule(
                rule_id="taste_emphasis_grammar",
                category="gesture",
                name="Emphasis Grammar",
                description="Every spoken statement must carry at least one visual gesture on the critical word, without repeating gestures consecutively.",
                rationale="Visual gestures anchor auditory keywords into long-term visual memory.",
                citation_source="references/4_taste_engine/user-signature-style.md#L27",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"has_spoken_sentence": True},
                recommendation="Assign Neon Ring for numbers/promises, Marker Underline for summaries, Highlighter BG for rules, Strikethrough for negation.",
                priority=80,
                exceptions=["dramatic_pause"],
                source_knowledge_ids=["know_taste_signature_style"],
                parameters={"allowed_gestures": ["Neon Ring", "Marker Underline", "Highlighter BG", "Strikethrough", "Flash Cut"]},
            ),
            # 7. Gestural SFX Sync
            TasteRule(
                rule_id="taste_gestural_sfx_sync",
                category="sound_design",
                name="Gestural SFX Synchronization",
                description="Every visual emphasis gesture must possess a tightly bound sound effect cue unless audio mode is SILENT.",
                rationale="Synesthetic audio-visual binding makes graphics feel tactile and impactful.",
                citation_source="references/4_taste_engine/user-signature-style.md#L51",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"has_visual_gesture": True, "audio_mode_not": "SILENT"},
                recommendation="Bind visual gesture to primary/alternate SFX: Neon Ring->chime-soft, Underline->swish-metal, Flash->dramatic-boom.",
                priority=95,
                exceptions=["audio_mode_silent", "dramatic_pause"],
                source_knowledge_ids=["know_taste_sfx_matrix", "know_taste_signature_style"],
                parameters={"sync_offset_ms": 0},
            ),
            # 8. Visual Rest
            TasteRule(
                rule_id="taste_visual_rest",
                category="pacing",
                name="Visual Rest After Climax",
                description="Provide visual breathing room after high-velocity sequences.",
                rationale="Continuous stimulation induces cognitive fatigue; contrast between fast and slow creates cinematic pacing.",
                citation_source="references/4_taste_engine/user-signature-style.md#L54",
                severity=TasteRuleSeverity.SHOULD,
                version="1.0.0",
                applies_when={"dense_scenes_count_gte": 2},
                recommendation="After two dense scenes, introduce a calmer shot with dynamic typography and slow subtle zoom.",
                priority=75,
                exceptions=["15s_ultra_fast_sprint"],
                source_knowledge_ids=["know_taste_signature_style"],
                parameters={"rest_duration_sec_min": 2.5},
            ),
            # 9. Color Discipline
            TasteRule(
                rule_id="taste_color_discipline",
                category="color",
                name="Color Discipline",
                description="Enforce dark base background with 2-3 neon accents strictly derived from the brand palette.",
                rationale="Unconstrained color palettes make videos look chaotic; a disciplined palette communicates brand sophistication.",
                citation_source="references/4_taste_engine/user-signature-style.md#L48",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"has_palette": True},
                recommendation="Anchor canvas in dark base, apply 2-3 accents from brand colors, zero arbitrary off-palette hues.",
                priority=85,
                exceptions=[],
                source_knowledge_ids=["know_taste_signature_style"],
                parameters={"max_accents": 3},
            ),
            # 10. Motion Personality Curves
            TasteRule(
                rule_id="taste_motion_personality_curves",
                category="motion_physics",
                name="Motion Personality Curves",
                description="Adhere strictly to official easing curves and duration palettes matching the chosen archetype.",
                rationale="Consistent physics creates a recognizable, coherent brand motion identity.",
                citation_source="references/4_taste_engine/motion-personality.md#L79",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"has_motion_personality": True},
                recommendation="Playful (ease-out-back, 150-300ms); Premium ((0.4,0,0.2,1), 350-600ms); Corporate ((0.2,0,0,1), 200-400ms); Energetic (ease-out-expo, 100-250ms).",
                priority=85,
                exceptions=[],
                source_knowledge_ids=["know_taste_motion_personality", "know_taste_disney"],
                parameters={"archetypes": ["Playful", "Premium", "Corporate", "Energetic"]},
            ),
            # 11. Audio Restraint
            TasteRule(
                rule_id="taste_audio_restraint",
                category="sound_design",
                name="Audio Restraint (Anti-Spam)",
                description="Avoid SFX pollution; placing sound effects on every single word or frame is strictly forbidden.",
                rationale="Overuse of sound effects degrades perceived quality and drowns out voiceover clarity.",
                citation_source="references/4_taste_engine/user-signature-style.md#L82",
                severity=TasteRuleSeverity.AVOID,
                version="1.0.0",
                applies_when={"sfx_density": "excessive"},
                recommendation="Reserve prominent SFX for major transitions, dramatic turning points, and key gestures.",
                priority=90,
                exceptions=["typewriter_effect"],
                source_knowledge_ids=["know_taste_signature_style"],
                parameters={"max_sfx_per_second": 1.5},
            ),
            # 12. Rollercoaster Pacing
            TasteRule(
                rule_id="taste_rollercoaster_pacing",
                category="pacing",
                name="The Rollercoaster Effect",
                description="Never make all scenes or beats the exact same duration.",
                rationale="Uniform duration creates a monotonous mechanical cadence.",
                citation_source="references/4_taste_engine/motion-personality.md#L97",
                severity=TasteRuleSeverity.SHOULD,
                version="1.0.0",
                applies_when={"multi_beat": True},
                recommendation="Alternate snappier beats (2-3s) for fast facts with breathing beats (4-6s) for profound statements.",
                priority=70,
                exceptions=["uniform_countdown_timer"],
                source_knowledge_ids=["know_taste_motion_personality"],
                parameters={"min_duration_variance_sec": 1.0},
            ),
            # 13. Context Mobile Scaling
            TasteRule(
                rule_id="taste_context_mobile_scaling",
                category="context_adaptation",
                name="Mobile Context Scaling",
                description="When targeting mobile vertical (9:16), reduce displacement, simplify multi-column stagger, and accelerate timing.",
                rationale="Small screens have higher perceived motion intensity and tighter cognitive viewports.",
                citation_source="references/4_taste_engine/context-adaptation.md#L11",
                severity=TasteRuleSeverity.SHOULD,
                version="1.0.0",
                applies_when={"platform": "mobile"},
                recommendation="Apply 0.8x duration multiplier, prefer opacity+transform, reduce stagger by 30%, avoid 3D parallax.",
                priority=75,
                exceptions=["desktop_16_9"],
                source_knowledge_ids=["know_taste_motion_personality"],
                parameters={"duration_multiplier": 0.8, "stagger_reduction": 0.3},
            ),
            # 14. Accessibility Reduced Motion
            TasteRule(
                rule_id="taste_accessibility_reduced_motion",
                category="accessibility",
                name="Accessibility: Reduced Motion",
                description="Eliminate spatial displacement and spring oscillations when reduced motion is requested.",
                rationale="Protects users with vestibular disorders from motion sickness or disorientation.",
                citation_source="references/4_taste_engine/context-adaptation.md#L25",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"prefers_reduced_motion": True},
                recommendation="Replace slide and zoom with subtle opacity fades; eliminate spring overshoot; reduce total duration by 50%.",
                priority=95,
                exceptions=[],
                source_knowledge_ids=["know_taste_motion_personality"],
                parameters={"enable_fade_only": True},
            ),
            # 15. Silent Audio Mode Enforcement
            TasteRule(
                rule_id="taste_silent_audio_mode",
                category="sound_design",
                name="Silent Audio Mode Invariant",
                description="In SILENT audio mode, zero sound effects or audio playback are permitted.",
                rationale="User explicit requirement for silent video overrides all soft sound recommendations.",
                citation_source="references/4_taste_engine/sfx_binding_matrix.md#L11",
                severity=TasteRuleSeverity.MUST,
                version="1.0.0",
                applies_when={"audio_mode": "SILENT"},
                recommendation="Suppress all audio gestures, mute sound design cues, and waive gestural audio binding.",
                priority=100,
                exceptions=[],
                source_knowledge_ids=["know_taste_sfx_matrix"],
                parameters={"audio_disabled": True},
            ),
        ]

        for r in seeds:
            self.register(r)
