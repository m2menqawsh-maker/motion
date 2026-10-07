"""
ai/intent/parser.py
===================
Authoritative Intent Parser transforming raw user requests and contextual inputs
into structured creative intent with epistemic provenance (S28-03).

Guarantees:
- Robust multi-language support (Arabic, English, mixed Arabic-English).
- Every significant field carries explicit epistemic provenance:
  • EXPLICIT: Directly asserted by user in the prompt.
  • INFERRED: Deduce from assets, media intelligence, or technical metadata.
  • DEFAULTED: Standard fallback applied when absent from input.
  • UNKNOWN: Insufficient evidence available to establish with certainty.
- Strictly separates defaults from explicit facts (uncertain information never becomes fact).
- Contradiction Detection: Detects conflicting requirements (e.g. silent + voiceover)
  and flags them in detected_contradictions without silent arbitrary resolution.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from ai.contracts.common import CapabilityType
from ai.contracts.creative.brief import AudioMode, FieldProvenance, ProvenanceType
from ai.contracts.media import MediaIntelligence
from ai.intent.contracts import IntentParseResult


class IntentParser:
    """
    Parses unstructured user requests in Arabic, English, or mixed language into
    typed IntentParseResult records accompanied by explicit epistemic provenance.
    """

    def parse(
        self,
        user_request: str,
        project_state: Optional[Dict[str, Any]] = None,
        available_assets: Optional[List[Any]] = None,
        media_intelligence: Optional[Union[MediaIntelligence, List[MediaIntelligence]]] = None,
        workspace_constraints: Optional[Dict[str, Any]] = None,
    ) -> IntentParseResult:
        """Parses user prompt and context into a typed intent representation."""
        request_text = user_request.strip()

        # 1. Detect language
        detected_lang = self._detect_language(request_text)

        # 2. Detect contradictions
        contradictions = self._detect_contradictions(request_text)

        # 3. Extract entities with per-field epistemic provenance
        provenances: Dict[str, FieldProvenance] = {}

        video_type, prov_video = self._extract_video_type(request_text, available_assets, media_intelligence)
        provenances["video_type"] = prov_video

        platforms, prov_platform = self._extract_platforms(request_text, available_assets, workspace_constraints)
        provenances["platform"] = prov_platform

        audio_mode, prov_audio = self._extract_audio_mode(request_text, available_assets, media_intelligence)
        provenances["audio_mode"] = prov_audio

        target_dur, min_dur, max_dur, prov_dur = self._extract_duration(request_text, available_assets, media_intelligence)
        provenances["duration"] = prov_dur

        pace, prov_pace = self._extract_pace(request_text, video_type)
        provenances["pace"] = prov_pace

        style, prov_style = self._extract_style(request_text)
        provenances["style"] = prov_style

        brand_colors, prov_colors = self._extract_brand_colors(request_text, workspace_constraints)
        if brand_colors:
            provenances["brand_colors"] = prov_colors

        # Language provenance
        provenances["language"] = FieldProvenance(
            source_type=ProvenanceType.EXPLICIT if any(k in request_text.lower() for k in ["عربي", "arabic", "english", "انجليزي"]) else ProvenanceType.INFERRED,
            rationale=f"Detected from input script characteristics as {detected_lang}",
            raw_reference=None,
        )

        # Goal and tone synthesis
        goal = self._synthesize_goal(request_text, video_type, detected_lang)
        tone = self._synthesize_tone(request_text, pace, style)
        key_takeaway = self._extract_key_takeaway(request_text)
        cta = self._extract_cta(request_text)

        return IntentParseResult(
            user_request_raw=request_text,
            detected_language=detected_lang,
            goal=goal,
            video_type=video_type,
            target_platforms=platforms,
            audio_mode=audio_mode,
            target_duration_seconds=target_dur,
            min_duration_seconds=min_dur,
            max_duration_seconds=max_dur,
            style=style,
            pace=pace,
            tone=tone,
            brand_colors=brand_colors,
            key_takeaway=key_takeaway,
            call_to_action=cta,
            field_provenance=provenances,
            detected_contradictions=contradictions,
        )

    def _detect_language(self, text: str) -> str:
        """Detects whether text is Arabic, English, or Mixed based on script proportions."""
        arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
        latin_chars = len(re.findall(r"[a-zA-Z]", text))

        if arabic_chars > 0 and latin_chars > 0:
            total_letters = arabic_chars + latin_chars
            latin_ratio = latin_chars / total_letters
            if 0.20 <= latin_ratio <= 0.80:
                return "MIXED"
            return "AR" if arabic_chars > latin_chars else "EN"
        if arabic_chars > 0:
            return "AR"
        return "EN"

    def _detect_contradictions(self, text: str) -> List[str]:
        """Detects explicit contradictory requirements in the user prompt."""
        contradictions = []
        lowered = text.lower()

        # Contradiction: Silent / No sound vs Voiceover
        has_silent = bool(
            re.search(r"\b(صامت|silent|muted|no audio|without sound|بدون أي صوت|بلا أي صوت)\b", text, re.IGNORECASE)
            or (
                re.search(r"\b(بدون صوت|بلا صوت)\b", text, re.IGNORECASE)
                and not re.search(r"(?:بدون|بلا)\s+صوت\s+(?:متحدث|تعليق)", text, re.IGNORECASE)
                and not re.search(r"\b(موسيقى|music|bgm)\b", text, re.IGNORECASE)
            )
        )
        has_vo = bool(
            re.search(r"\b(تعليق صوتي|مع تعليق|voiceover|voice over|vo|اعمل voiceover|سجل صوت|narration)\b", text, re.IGNORECASE)
        )
        if has_silent and has_vo:
            contradictions.append(
                "Contradiction detected: Request specifies silent/no audio while simultaneously requesting voiceover or spoken narration."
            )

        # Contradiction: No music vs Music requested
        has_no_music = bool(
            re.search(r"\b(بدون موسيقى|بلا موسيقى|no music|without music|no bgm)\b", text, re.IGNORECASE)
        )
        text_without_no_music = re.sub(r"\b(بدون موسيقى|بلا موسيقى|no music|without music|no bgm)\b[^\s]*", "", text, flags=re.IGNORECASE)
        has_music = bool(
            re.search(r"\b(موسيقى|music|bgm)\b", text_without_no_music, re.IGNORECASE)
        )
        if has_no_music and has_music:
            contradictions.append(
                "Contradiction detected: Request specifies no music while simultaneously requesting background music/BGM."
            )

        # Contradiction: Short duration vs Long duration conflicting assertions
        durations = re.findall(r"(\d+)\s*(?:ثانية|seconds?|sec|s\b)", text, re.IGNORECASE)
        if len(durations) >= 2:
            unique_durs = sorted(list(set(int(d) for d in durations)))
            if len(unique_durs) > 1 and max(unique_durs) >= min(unique_durs) * 2:
                contradictions.append(
                    f"Contradiction detected: Multiple conflicting duration numbers specified: {unique_durs}s"
                )

        return contradictions

    def _extract_video_type(
        self,
        text: str,
        assets: Optional[List[Any]],
        media_intel: Optional[Union[MediaIntelligence, List[MediaIntelligence]]],
    ) -> Tuple[Optional[str], FieldProvenance]:
        """Extracts video type category and records epistemic provenance."""
        lowered = text.lower()

        patterns = [
            (r"\b(saas|سارس|منتج saas|برنامج|تطبيق|screencast|software demo|منصة|استعراض برنامج)\b", "SAAS_DEMO"),
            (r"\b(منتاج|مونتاج|montage|ريل سريع|منتاج إعلاني|dynamic montage)\b", "DYNAMIC_MONTAGE"),
            (r"\b(أفاتار|avatar|شخصية افتراضية|مقدم افتراضي|avatar explainer)\b", "AVATAR_EXPLAINER"),
            (r"\b(talking head|متحدث|حديث الكاميرا|مؤسس الشركة|مقابلة)\b", "TALKING_HEAD"),
            (r"\b(مقال|article sprint|article to video|شورت مقال)\b", "ARTICLE_SPRINT"),
            (r"\b(repurpose|تقطيع بودكاست|longform|بودكاست|podcast clip)\b", "LONGFORM_REPURPOSE"),
            (r"\b(مراجعة منافس|review conquest|مقارنة)\b", "REVIEW_CONQUEST"),
            (r"\b(tabletop|هرمي|متعدد المستويات|طبقات)\b", "TABLETOP_EXPLAINER"),
            (r"\b(شرح|explainer|فيديو شرح|توضيحي|living canvas)\b", "EXPLAINER"),
            (r"\b(إعلان|ad|social ad|ترويج|ugc)\b", "PRODUCT_AD"),
            (r"\b(موشن جرافيك|motion graphics|انيميشن)\b", "MOTION_GRAPHICS"),
        ]

        for pat, vtype in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return vtype, FieldProvenance(
                    source_type=ProvenanceType.EXPLICIT,
                    rationale=f"Matched explicit user phrase: '{match.group(0)}'",
                    raw_reference=match.group(0),
                )

        # Infer from available assets or media intelligence if provided
        if media_intel:
            intels = media_intel if isinstance(media_intel, list) else [media_intel]
            for intel in intels:
                if intel.speech and intel.speech.has_speech and intel.visual and intel.visual.faces_detected > 0:
                    return "TALKING_HEAD", FieldProvenance(
                        source_type=ProvenanceType.INFERRED,
                        rationale="Inferred from MediaIntelligence: asset contains detected face with spoken audio",
                        raw_reference="MediaIntelligence(faces_detected > 0, has_speech=True)",
                    )

        # If assets contain video
        if assets:
            for a in assets:
                filename = getattr(a, "filename", str(a)).lower()
                if "screen" in filename or "demo" in filename:
                    return "SAAS_DEMO", FieldProvenance(
                        source_type=ProvenanceType.INFERRED,
                        rationale=f"Inferred from asset filename '{filename}'",
                        raw_reference=filename,
                    )

        # Truly vague or generic request: return UNKNOWN
        return None, FieldProvenance(
            source_type=ProvenanceType.UNKNOWN,
            rationale="No explicit video type specified in prompt and no informative context assets provided",
            raw_reference=None,
        )

    def _extract_platforms(
        self,
        text: str,
        assets: Optional[List[Any]],
        constraints: Optional[Dict[str, Any]],
    ) -> Tuple[List[str], FieldProvenance]:
        """Extracts target social or distribution platforms."""
        patterns = [
            (r"\b(ريل|ريلز|reels?|انستغرام|انستقرام|instagram)\b", "instagram_reels"),
            (r"\b(تيك توك|تيكتوك|tiktok)\b", "tiktok"),
            (r"\b(شورتس|shorts?|يوتيوب شورتس|youtube shorts)\b", "youtube_shorts"),
            (r"\b(لينكد ان|لينكدإن|linkedin)\b", "linkedin"),
            (r"\b(يوتيوب|youtube)\b", "youtube"),
        ]

        matched = []
        raw_refs = []
        for pat, plat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                matched.append(plat)
                raw_refs.append(m.group(0))

        if matched:
            return sorted(list(set(matched))), FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale=f"Matched explicit platform references: {raw_refs}",
                raw_reference=", ".join(raw_refs),
            )

        # Check workspace constraints
        if constraints and "target_platforms" in constraints:
            plat_list = constraints["target_platforms"]
            return plat_list, FieldProvenance(
                source_type=ProvenanceType.INFERRED,
                rationale="Derived from workspace default target platforms constraint",
                raw_reference="workspace_constraints.target_platforms",
            )

        # Standard defaulted short-form social platforms
        return ["instagram_reels", "tiktok", "youtube_shorts"], FieldProvenance(
            source_type=ProvenanceType.DEFAULTED,
            rationale="Defaulted to standard short-form vertical platforms (reels, tiktok, shorts)",
            raw_reference=None,
        )

    def _extract_audio_mode(
        self,
        text: str,
        assets: Optional[List[Any]],
        media_intel: Optional[Union[MediaIntelligence, List[MediaIntelligence]]],
    ) -> Tuple[AudioMode, FieldProvenance]:
        """Determines the governing AudioMode and records epistemic provenance."""
        # 1. Explicit Music-only requests (takes precedence over generic "no voice" mentions)
        if re.search(r"\b(بدون تعليق صوتي بس موسيقى|بدون صوت متحدث بس موسيقى|بس موسيقى فقط|بس موسيقى|موسيقى فقط|موسيقي فقط|music only|bgm only|no voiceover|بدون تعليق صوتي|بدون vo)\b", text, re.IGNORECASE):
            match = re.search(r"\b(بدون تعليق صوتي بس موسيقى|بدون صوت متحدث بس موسيقى|بس موسيقى فقط|بس موسيقى|موسيقى فقط|موسيقي فقط|music only|bgm only|no voiceover|بدون تعليق صوتي|بدون vo)\b", text, re.IGNORECASE)
            return AudioMode.MUSIC_ONLY, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale="User explicitly requested music-only mode without voiceover/speech",
                raw_reference=match.group(0) if match else "music only",
            )

        # 2. Explicit Silent requests
        if re.search(r"\b(صامت|silent|muted|no audio|without sound|بدون أي صوت|بلا أي صوت)\b", text, re.IGNORECASE) or (
            re.search(r"\b(بدون صوت|بلا صوت)\b", text, re.IGNORECASE)
            and not re.search(r"(?:بدون|بلا)\s+صوت\s+(?:متحدث|تعليق)", text, re.IGNORECASE)
            and not re.search(r"\b(موسيقى|music|bgm)\b", text, re.IGNORECASE)
        ):
            match = re.search(r"\b(صامت|silent|muted|no audio|without sound|بدون أي صوت|بلا أي صوت|بدون صوت|بلا صوت)\b", text, re.IGNORECASE)
            return AudioMode.SILENT, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale="User explicitly requested silent video without audio track",
                raw_reference=match.group(0) if match else "silent",
            )

        # 3. Explicit Voiceover-only requests
        if re.search(r"\b(تعليق صوتي فقط|بدون موسيقى|voiceover only|vo only|no music|no bgm)\b", text, re.IGNORECASE):
            match = re.search(r"\b(تعليق صوتي فقط|بدون موسيقى|voiceover only|vo only|no music|no bgm)\b", text, re.IGNORECASE)
            return AudioMode.VO_ONLY, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale="User explicitly requested voiceover only without background music",
                raw_reference=match.group(0) if match else "vo only",
            )

        # 4. Explicit Source Audio with Music requests
        if (
            re.search(r"(?:(?:ال)?صوت\s+(?:ال)?أصلي|source\s+audio|original\s+audio|(?:ال)?صوت\s+المسجل).+?(?:مع\s+موسيقى|with\s+music|and\s+music|in\s+the\s+background|bgm)", text, re.IGNORECASE)
            or re.search(r"\b((?:ال)?صوت\s+(?:ال)?أصلي\s+مع\s+موسيقى|source\s+audio\s+with\s+music|native\s+audio\s+and\s+bgm)\b", text, re.IGNORECASE)
        ):
            match = re.search(r"(?:(?:ال)?صوت\s+(?:ال)?أصلي|source\s+audio|original\s+audio|(?:ال)?صوت\s+المسجل).+?(?:مع\s+موسيقى|with\s+music|and\s+music|in\s+the\s+background|bgm)", text, re.IGNORECASE) or re.search(r"\b((?:ال)?صوت\s+(?:ال)?أصلي\s+مع\s+موسيقى|source\s+audio\s+with\s+music|native\s+audio\s+and\s+bgm)\b", text, re.IGNORECASE)
            return AudioMode.SOURCE_AUDIO_MUSIC, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale="User explicitly requested native source audio preserved with added music bed",
                raw_reference=match.group(0) if match else "source_audio_music",
            )

        # 5. Explicit Source Audio requests (native audio preserved)
        if re.search(r"\b((?:ال)?صوت\s+(?:ال)?أصلي|original\s+audio|source\s+audio|(?:ال)?صوت\s+المسجل|(?:ال)?صوت\s+الفيديو)\b", text, re.IGNORECASE):
            match = re.search(r"\b((?:ال)?صوت\s+(?:ال)?أصلي|original\s+audio|source\s+audio|(?:ال)?صوت\s+المسجل|(?:ال)?صوت\s+الفيديو)\b", text, re.IGNORECASE)
            return AudioMode.SOURCE_AUDIO, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale="User explicitly requested preserving native source audio",
                raw_reference=match.group(0) if match else "source_audio",
            )

        # 6. Explicit VO + Music requests
        if re.search(r"\b(تعليق صوتي وموسيقى|vo and music|voiceover with music|voiceover and music|صوت وموسيقى)\b", text, re.IGNORECASE):
            match = re.search(r"\b(تعليق صوتي وموسيقى|vo and music|voiceover with music|voiceover and music|صوت وموسيقى)\b", text, re.IGNORECASE)
            return AudioMode.VO_MUSIC, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale="User explicitly requested dual-track voiceover and background music",
                raw_reference=match.group(0) if match else "vo_music",
            )

        # Contextual inference from MediaIntelligence
        if media_intel:
            intels = media_intel if isinstance(media_intel, list) else [media_intel]
            for intel in intels:
                if intel.speech and intel.speech.has_speech:
                    return AudioMode.SOURCE_AUDIO_MUSIC, FieldProvenance(
                        source_type=ProvenanceType.INFERRED,
                        rationale="Inferred SOURCE_AUDIO_MUSIC because source asset contains recognized speech track",
                        raw_reference="MediaIntelligence.speech.has_speech=True",
                    )

        # Standard platform default
        return AudioMode.VO_MUSIC, FieldProvenance(
            source_type=ProvenanceType.DEFAULTED,
            rationale="Defaulted to standard commercial audio presentation (voiceover with ducked background music)",
            raw_reference=None,
        )

    def _extract_duration(
        self,
        text: str,
        assets: Optional[List[Any]],
        media_intel: Optional[Union[MediaIntelligence, List[MediaIntelligence]]],
    ) -> Tuple[float, float, float, FieldProvenance]:
        """Extracts duration bounds and target duration in seconds."""
        # Match explicit numbers with second indicators
        m = re.search(r"(\d+)\s*(?:ثانية|seconds?|sec|s\b)", text, re.IGNORECASE)
        if m:
            dur = float(m.group(1))
            min_d = max(5.0, dur * 0.8)
            max_d = dur * 1.2
            return dur, min_d, max_d, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale=f"Matched explicit duration in prompt: {dur}s",
                raw_reference=m.group(0),
            )

        if "دقيقة" in text or "minute" in text.lower():
            return 60.0, 45.0, 75.0, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale="Matched explicit 1 minute indicator",
                raw_reference="دقيقة / minute",
            )

        # Inferred from MediaIntelligence duration if source video exists
        if media_intel:
            intels = media_intel if isinstance(media_intel, list) else [media_intel]
            for intel in intels:
                if intel.technical and intel.technical.duration_seconds and intel.technical.duration_seconds > 0:
                    asset_dur = round(intel.technical.duration_seconds, 1)
                    return asset_dur, max(5.0, asset_dur * 0.8), asset_dur * 1.2, FieldProvenance(
                        source_type=ProvenanceType.INFERRED,
                        rationale=f"Inferred duration from source asset length ({asset_dur}s)",
                        raw_reference=f"MediaIntelligence.technical.duration_seconds={asset_dur}",
                    )

        # Standard default for short-form
        return 30.0, 15.0, 60.0, FieldProvenance(
            source_type=ProvenanceType.DEFAULTED,
            rationale="Defaulted to standard 30s target duration for short-form video",
            raw_reference=None,
        )

    def _extract_pace(self, text: str, video_type: Optional[str]) -> Tuple[str, FieldProvenance]:
        """Extracts pacing profile."""
        fast_match = re.search(r"\b(سريع|fast|energetic|ديناميكي|حماسي|خاطف)\b", text, re.IGNORECASE)
        if fast_match:
            return "FAST", FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale=f"Matched fast pacing keyword: '{fast_match.group(0)}'",
                raw_reference=fast_match.group(0),
            )

        slow_match = re.search(r"\b(هادئ|calm|بطيء|slow|متزن)\b", text, re.IGNORECASE)
        if slow_match:
            return "SLOW", FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale=f"Matched slow pacing keyword: '{slow_match.group(0)}'",
                raw_reference=slow_match.group(0),
            )

        if video_type in ("DYNAMIC_MONTAGE", "ARTICLE_SPRINT"):
            return "FAST", FieldProvenance(
                source_type=ProvenanceType.INFERRED,
                rationale=f"Inferred FAST pacing from video type '{video_type}'",
                raw_reference=video_type,
            )

        return "MODERATE", FieldProvenance(
            source_type=ProvenanceType.DEFAULTED,
            rationale="Defaulted to MODERATE standard pacing profile",
            raw_reference=None,
        )

    def _extract_style(self, text: str) -> Tuple[str, FieldProvenance]:
        """Extracts creative style."""
        patterns = [
            (r"\b(clean|ستايل clean|نظيف|ستايل بسيط|minimal)\b", "CLEAN"),
            (r"\b(سينمائي|cinematic|فخم|luxury)\b", "CINEMATIC"),
            (r"\b(جريء|bold|حركي|punchy)\b", "BOLD"),
            (r"\b(تقني|technical|دقيق)\b", "TECHNICAL"),
            (r"\b(عصري|modern)\b", "MODERN"),
        ]

        for pat, style in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return style, FieldProvenance(
                    source_type=ProvenanceType.EXPLICIT,
                    rationale=f"Matched style keyword: '{m.group(0)}'",
                    raw_reference=m.group(0),
                )

        return "CLEAN", FieldProvenance(
            source_type=ProvenanceType.DEFAULTED,
            rationale="Defaulted to CLEAN signature design style",
            raw_reference=None,
        )

    def _extract_brand_colors(
        self,
        text: str,
        constraints: Optional[Dict[str, Any]],
    ) -> Tuple[List[str], FieldProvenance]:
        """Extracts hex color codes from text or workspace constraints."""
        hex_matches = re.findall(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b", text)
        if hex_matches:
            return hex_matches, FieldProvenance(
                source_type=ProvenanceType.EXPLICIT,
                rationale=f"Extracted hex colors from prompt: {hex_matches}",
                raw_reference=", ".join(hex_matches),
            )

        if constraints and "brand_colors" in constraints:
            return constraints["brand_colors"], FieldProvenance(
                source_type=ProvenanceType.INFERRED,
                rationale="Loaded brand colors from workspace constraints profile",
                raw_reference="workspace_constraints.brand_colors",
            )

        return [], FieldProvenance(
            source_type=ProvenanceType.UNKNOWN,
            rationale="No brand colors specified or configured",
            raw_reference=None,
        )

    def _synthesize_goal(self, text: str, vtype: Optional[str], lang: str) -> str:
        if vtype == "SAAS_DEMO":
            return "Showcase SaaS software value and core user workflow concisely."
        if vtype == "DYNAMIC_MONTAGE":
            return "Deliver an energetic high-impact social media montage."
        if vtype == "AVATAR_EXPLAINER":
            return "Explain value proposition through synthesized digital presenter."
        if vtype == "TALKING_HEAD":
            return "Present speaker message clearly with synchronized captioning."
        return f"Produce video engaging target audience in {lang}."

    def _synthesize_tone(self, text: str, pace: str, style: str) -> str:
        if style == "CINEMATIC":
            return "cinematic and refined"
        if pace == "FAST":
            return "energetic and punchy"
        return "professional and engaging"

    def _extract_key_takeaway(self, text: str) -> str:
        # Simple extraction or summary
        return text[:120] if len(text) > 120 else text

    def _extract_cta(self, text: str) -> Optional[str]:
        m = re.search(r"(?:cta|دعوة|اشترك|حمل|جرب|sign up|try it|download|visit)\s*:?\s*([^.\n]+)", text, re.IGNORECASE)
        return m.group(0).strip() if m else None
