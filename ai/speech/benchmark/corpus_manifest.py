"""
ai/speech/benchmark/corpus_manifest.py
======================================
Structured Project Speech Benchmark Corpus Manifest (S27.14).

Invariants:
- Ground-truth reference datasets specifically tailored to the project domain.
- Distinguishes between:
  1. REQUIRED_FOR_CURRENT_PRODUCT_GATE (Core video voiceovers: MSA, Male/Female, Fast Promo, Music Bed, Diarization if enabled)
  2. OPTIONAL_COVERAGE (Dialectal expansions like Palestinian Arabic, noisy cafe stress-tests, code-switching)
- Models being evaluated NEVER generate ground-truth for themselves.
- If real audio files or annotations are incomplete, recorded as INSUFFICIENT DATA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class CorpusRequirementLevel(str, Enum):
    """Categorizes whether a benchmark sample is mandatory for the current production gate or optional."""
    REQUIRED_FOR_CURRENT_PRODUCT_GATE = "REQUIRED_FOR_CURRENT_PRODUCT_GATE"
    OPTIONAL_COVERAGE = "OPTIONAL_COVERAGE"


@dataclass(frozen=True)
class BenchmarkReferenceSegment:
    start_sec: float
    end_sec: float
    text: str
    speaker_id: str


@dataclass(frozen=True)
class BenchmarkSample:
    sample_id: str
    title: str
    language_category: str  # 'ar_msa', 'ar_palestinian', 'en', 'code_switch_ar_en'
    audio_characteristics: List[str]
    reference_transcript: str
    reference_language: str
    duration_seconds: float
    requirement_level: str = CorpusRequirementLevel.REQUIRED_FOR_CURRENT_PRODUCT_GATE.value
    reference_segments: List[BenchmarkReferenceSegment] = field(default_factory=list)
    reference_speakers: List[str] = field(default_factory=list)
    has_real_audio_file: bool = False
    notes: Optional[str] = None


# Authoritative Project Benchmark Manifest
PROJECT_SPEECH_BENCHMARK_CORPUS: List[BenchmarkSample] = [
    # 1. Arabic MSA — Clean Studio Male Voice (REQUIRED)
    BenchmarkSample(
        sample_id="corpus_ar_msa_001",
        title="Arabic MSA Technical Script (Clean Studio Male)",
        language_category="ar_msa",
        audio_characteristics=["male", "studio", "clean"],
        reference_transcript="الموبايل الذي تحمله في يدك أقوى بآلاف المرات من الحواسيب التي هبطت بها ناسا على القمر",
        reference_language="ar",
        duration_seconds=6.5,
        requirement_level=CorpusRequirementLevel.REQUIRED_FOR_CURRENT_PRODUCT_GATE.value,
        reference_segments=[
            BenchmarkReferenceSegment(0.0, 3.2, "الموبايل الذي تحمله في يدك أقوى بآلاف المرات", "SPEAKER_00"),
            BenchmarkReferenceSegment(3.3, 6.5, "من الحواسيب التي هبطت بها ناسا على القمر", "SPEAKER_00"),
        ],
        reference_speakers=["SPEAKER_00"],
        has_real_audio_file=False,
        notes="Core voiceover scenario: clean studio male narration in Modern Standard Arabic.",
    ),

    # 2. Palestinian Arabic Dialect (OPTIONAL COVERAGE)
    BenchmarkSample(
        sample_id="corpus_ar_palestinian_001",
        title="Palestinian Arabic Dialect (Authentic Narrative)",
        language_category="ar_palestinian",
        audio_characteristics=["male", "dialect", "colloquial"],
        reference_transcript="الموبايل الي بايدك هادا فيه شغلات ما بتخطر على بالك وسرعته بتعادل شغل يوم كامل",
        reference_language="ar",
        duration_seconds=5.8,
        requirement_level=CorpusRequirementLevel.OPTIONAL_COVERAGE.value,
        reference_segments=[
            BenchmarkReferenceSegment(0.0, 2.8, "الموبايل الي بايدك هادا فيه شغلات ما بتخطر على بالك", "SPEAKER_00"),
            BenchmarkReferenceSegment(2.9, 5.8, "وسرعته بتعادل شغل يوم كامل", "SPEAKER_00"),
        ],
        reference_speakers=["SPEAKER_00"],
        has_real_audio_file=False,
        notes="Palestinian dialect sample; classified as OPTIONAL_COVERAGE. No product requirement or ADR mandates Palestinian Arabic as a blocking production gate.",
    ),

    # 3. Arabic-English Code-Switching (OPTIONAL COVERAGE)
    BenchmarkSample(
        sample_id="corpus_code_switch_001",
        title="Arabic-English Code Switching (Tech Podcast)",
        language_category="code_switch_ar_en",
        audio_characteristics=["male", "code_switch", "tech_terms"],
        reference_transcript="عملنا render للفيديو الجديد على Remotion وطلعت الـ performance ممتازة جدا",
        reference_language="ar",
        duration_seconds=4.8,
        requirement_level=CorpusRequirementLevel.OPTIONAL_COVERAGE.value,
        reference_segments=[
            BenchmarkReferenceSegment(0.0, 2.4, "عملنا render للفيديو الجديد على Remotion", "SPEAKER_00"),
            BenchmarkReferenceSegment(2.5, 4.8, "وطلعت الـ performance ممتازة جدا", "SPEAKER_00"),
        ],
        reference_speakers=["SPEAKER_00"],
        has_real_audio_file=False,
        notes="Arabic-English technical code-switching; classified as OPTIONAL_COVERAGE for tech vocabulary expansion.",
    ),

    # 4. Fast Speech — High-Pacing Promo Ad (REQUIRED)
    BenchmarkSample(
        sample_id="corpus_fast_speech_001",
        title="Fast Speech Promotional Pacing",
        language_category="ar_msa",
        audio_characteristics=["female", "fast_speech", "commercial"],
        reference_transcript="اشترك الآن ولا تفوت الفرصة العرض متاح لفترة محدودة فقط احصل على خصمك اليوم",
        reference_language="ar",
        duration_seconds=3.2,
        requirement_level=CorpusRequirementLevel.REQUIRED_FOR_CURRENT_PRODUCT_GATE.value,
        reference_segments=[
            BenchmarkReferenceSegment(0.0, 1.6, "اشترك الآن ولا تفوت الفرصة العرض متاح لفترة محدودة فقط", "SPEAKER_00"),
            BenchmarkReferenceSegment(1.7, 3.2, "احصل على خصمك اليوم", "SPEAKER_00"),
        ],
        reference_speakers=["SPEAKER_00"],
        has_real_audio_file=False,
        notes="Fast promotional speech pacing; mandatory for video promo ads (Reels, TikTok, Shorts).",
    ),

    # 5. Noisy Speech — Ambient Street / Cafe Recording (OPTIONAL COVERAGE)
    BenchmarkSample(
        sample_id="corpus_noisy_speech_001",
        title="Noisy Acoustic Environment (Cafe Ambience)",
        language_category="ar_msa",
        audio_characteristics=["male", "noisy", "background_chatter"],
        reference_transcript="نحن نسجل هذا المقطع في مكان مزدحم لاختبار قدرة النموذج على عزل الضجيج",
        reference_language="ar",
        duration_seconds=5.0,
        requirement_level=CorpusRequirementLevel.OPTIONAL_COVERAGE.value,
        reference_segments=[
            BenchmarkReferenceSegment(0.0, 5.0, "نحن نسجل هذا المقطع في مكان مزدحم لاختبار قدرة النموذج على عزل الضجيج", "SPEAKER_00"),
        ],
        reference_speakers=["SPEAKER_00"],
        has_real_audio_file=False,
        notes="Noisy cafe ambience; classified as OPTIONAL_COVERAGE stress test since video maker processes clean voiceover.",
    ),

    # 6. Music Under Speech — Video Background Music Bed (REQUIRED)
    BenchmarkSample(
        sample_id="corpus_music_under_speech_001",
        title="Voiceover with Cyber Synth BGM Ducking",
        language_category="ar_msa",
        audio_characteristics=["male", "music_under_speech", "production_bed"],
        reference_transcript="في هذا المشروع صممنا الهوية البصرية كاملة باستخدام تقنيات الموشن جرافيك",
        reference_language="ar",
        duration_seconds=5.5,
        requirement_level=CorpusRequirementLevel.REQUIRED_FOR_CURRENT_PRODUCT_GATE.value,
        reference_segments=[
            BenchmarkReferenceSegment(0.0, 5.5, "في هذا المشروع صممنا الهوية البصرية كاملة باستخدام تقنيات الموشن جرافيك", "SPEAKER_00"),
        ],
        reference_speakers=["SPEAKER_00"],
        has_real_audio_file=False,
        notes="Voiceover ducked over background music; mandatory production scenario for video rendering.",
    ),

    # 7. Female Voice — Clean Narration (REQUIRED)
    BenchmarkSample(
        sample_id="corpus_female_voice_001",
        title="Female Voiceover Educational Narration",
        language_category="ar_msa",
        audio_characteristics=["female", "studio", "clean"],
        reference_transcript="مرحبا بكم في الدرس الأول من دورة إنتاج الفيديو المتقدمة عبر المنصة السحابية",
        reference_language="ar",
        duration_seconds=5.2,
        requirement_level=CorpusRequirementLevel.REQUIRED_FOR_CURRENT_PRODUCT_GATE.value,
        reference_segments=[
            BenchmarkReferenceSegment(0.0, 5.2, "مرحبا بكم في الدرس الأول من دورة إنتاج الفيديو المتقدمة عبر المنصة السحابية", "SPEAKER_00"),
        ],
        reference_speakers=["SPEAKER_00"],
        has_real_audio_file=False,
        notes="Clean female narration; mandatory gender balance in video voiceover.",
    ),

    # 8. Multi-Speaker (Diarization) — Two-Speaker Dialogue (REQUIRED IF DIARIZATION IS CERTIFIED)
    BenchmarkSample(
        sample_id="corpus_multi_speaker_001",
        title="Two-Speaker Technical Interview (Diarization Test)",
        language_category="ar_msa",
        audio_characteristics=["male", "female", "multi_speaker", "turn_taking"],
        reference_transcript="كيف ترى مستقبل الذكاء الاصطناعي في المونتاج أراه ثورة حقيقية تختصر ساعات العمل",
        reference_language="ar",
        duration_seconds=6.0,
        requirement_level=CorpusRequirementLevel.REQUIRED_FOR_CURRENT_PRODUCT_GATE.value,
        reference_segments=[
            BenchmarkReferenceSegment(0.0, 2.8, "كيف ترى مستقبل الذكاء الاصطناعي في المونتاج", "SPEAKER_00"),
            BenchmarkReferenceSegment(3.0, 6.0, "أراه ثورة حقيقية تختصر ساعات العمل", "SPEAKER_01"),
        ],
        reference_speakers=["SPEAKER_00", "SPEAKER_01"],
        has_real_audio_file=False,
        notes="Two-speaker interview dialogue; mandatory ONLY IF DIARIZATION capability is certified for production now.",
    ),
]


def get_corpus_manifest(requirement_level: Optional[str] = None) -> List[BenchmarkSample]:
    """Returns the full benchmark corpus manifest, optionally filtered by requirement level."""
    if requirement_level is not None:
        return [s for s in PROJECT_SPEECH_BENCHMARK_CORPUS if s.requirement_level == requirement_level]
    return list(PROJECT_SPEECH_BENCHMARK_CORPUS)


def get_required_gate_corpus() -> List[BenchmarkSample]:
    """Returns only samples mandatory for the current production quality gate."""
    return get_corpus_manifest(CorpusRequirementLevel.REQUIRED_FOR_CURRENT_PRODUCT_GATE.value)


def get_optional_corpus() -> List[BenchmarkSample]:
    """Returns samples designated as optional or extended coverage."""
    return get_corpus_manifest(CorpusRequirementLevel.OPTIONAL_COVERAGE.value)


def get_corpus_categories_summary(requirement_level: Optional[str] = None) -> Dict[str, int]:
    """Returns coverage counts across all evaluation dimensions."""
    samples = get_corpus_manifest(requirement_level)
    summary: Dict[str, int] = {}
    for sample in samples:
        summary[sample.language_category] = summary.get(sample.language_category, 0) + 1
        for char in sample.audio_characteristics:
            summary[char] = summary.get(char, 0) + 1
    return summary
