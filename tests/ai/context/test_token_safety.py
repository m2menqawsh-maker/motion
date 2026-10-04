"""
tests/ai/context/test_token_safety.py
=====================================
Token Estimator Safety, Multilingual Bounding Invariants, and Token Ceiling Gate (S27.8).
"""

from __future__ import annotations

import math
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.memory import MemoryType
from ai.context import (
    ConservativeTokenEstimator,
    ContextBuilder,
    ContextBudgetPolicy,
    ContextPackage,
    ContextRequest,
    EstimatorKind,
)
from ai.memory.models import TrustedTenantContext
from ai.memory.types import MemoryScope
from tests.ai.context.conftest import (
    MockLifecycleDTO,
    MockProjectService,
    make_test_memory_service,
)


def reference_tokenizer_oracle(text: str) -> int:
    """
    Reference test oracle simulating BPE / WordPiece tokenizer behavior across
    Latin, Arabic, Emoji, Code, JSON, and punctuation.
    """
    if not text:
        return 0

    tokens = 0
    i = 0
    n = len(text)

    while i < n:
        c = text[i]
        cat = unicodedata.category(c)
        cp = ord(c)

        # 1. Whitespace
        if c in " \t":
            run = 0
            while i < n and text[i] in " \t":
                run += 1
                i += 1
            if run > 2:
                tokens += (run // 4) + 1
            continue
        elif c in "\r\n":
            while i < n and text[i] in "\r\n":
                tokens += 1
                i += 1
            continue

        # 2. Emoji & Miscellaneous Symbols (e.g. >= 0x1F000 or So category)
        if cp >= 0x1F000 or cat == "So":
            tokens += 2
            i += 1
            continue

        # 3. Punctuation & Symbols
        if cat.startswith("P") or cat.startswith("S"):
            tokens += 1
            i += 1
            continue

        # 4. Numbers (digits 1-3 per token)
        if cat.startswith("N"):
            digit_count = 0
            while i < n and unicodedata.category(text[i]).startswith("N"):
                digit_count += 1
                i += 1
            tokens += math.ceil(digit_count / 3.0)
            continue

        # 5. Letters
        if cat.startswith("L"):
            word_chars = []
            is_arabic = False
            while i < n and unicodedata.category(text[i]).startswith("L"):
                ch = text[i]
                if 0x0600 <= ord(ch) <= 0x08FF:
                    is_arabic = True
                word_chars.append(ch)
                i += 1

            wlen = len(word_chars)
            if is_arabic:
                tokens += max(1, math.ceil(wlen / 2.0))
            else:
                tokens += max(1, math.ceil(wlen / 4.0))
            continue

        tokens += 1
        i += 1

    return max(1, tokens)


MULTILINGUAL_TOKEN_DATASET = {
    "english_prose": (
        "This is an enterprise clean video production pipeline. "
        "Every phase adheres to taste gates and quality control before rendering."
    ),
    "arabic_msa": (
        "هذا النظام البرمجي المتكامل لإنتاج الفيديو يلتزم بالمعايير الفنية والسينمائية الصارمة "
        "مع تدقيق تلقائي للجودة والتناسق الصوتي والمرئي."
    ),
    "arabic_palestinian": (
        "شو رأيك نعمل فيديو سريع مرتب وفيه فكرة رهيبة تجيب مشاهدات وتفاعل عالي بكل بساطة؟"
    ),
    "arabic_english_mixed": (
        "فيديو Hook مدته 3 ثواني مع B-roll سينمائي و voiceover واضح بدقة 1080p بمعدل 30 fps."
    ),
    "emoji_heavy": (
        "🎬🔥🚀🎉✨🎥💡⭐⚡🎯🏆📱🎨🔊"
    ),
    "json": (
        '{"project_id": "prj_sample_100", "lifecycle_state": "PLAN_READY", "fps": 30, '
        '"resolution": {"width": 1080, "height": 1920}, "scenes": [1, 2, 3]}'
    ),
    "code": (
        "def calculate_render(duration: float, fps: int = 30) -> int:\n"
        "    if duration <= 0:\n"
        '        raise ValueError("Invalid duration")\n'
        "    return int(duration * fps)"
    ),
    "urls": (
        "https://api.cleanvideo.workspace.internal/v2/workspaces/ws_alpha/projects/prj_100/render?format=mp4&quality=high"
    ),
    "numbers": (
        "1080 1920 30 60 44100 48000 128000 256000 999999999 1234567890 3.14159"
    ),
    "punctuation_heavy": (
        "[[[CRITICAL WARNING!]]] <<<status: error?>>> (code: 500, type: 'INTERNAL_ERROR'; retry=False, retry_after=None); !!!"
    ),
    "very_short_english": "Hi",
    "very_short_arabic": "نعم",
    "very_short_emoji": "🔥",
    "long_mixed_prose": (
        "Cinematic video editing requires strict typography symmetry. النصوص لا تتداخل أبداً. "
        "Audio normalization is locked to -16 LUFS. الصوت البشري متزن تماماً. "
    ) * 30,
}


class TestTokenEstimatorSafety:

    def test_estimator_classification_is_explicit(self):
        estimator = ConservativeTokenEstimator()
        kind = estimator.get_estimator_kind()
        assert kind in (EstimatorKind.CONSERVATIVE_HEURISTIC, EstimatorKind.APPROXIMATE)
        assert kind == EstimatorKind.CONSERVATIVE_HEURISTIC

    def test_underestimation_gate_across_multilingual_dataset(self):
        """
        Mandatory Invariant Gate:
        For every class in MULTILINGUAL_TOKEN_DATASET:
            estimated_tokens >= reference_actual_tokens
        Underestimation is strictly forbidden (0 violations).
        """
        estimator = ConservativeTokenEstimator()
        violations = []

        for category, text in MULTILINGUAL_TOKEN_DATASET.items():
            actual = reference_tokenizer_oracle(text)
            estimated = estimator.estimate_tokens(text)
            if estimated < actual:
                violations.append((category, actual, estimated))

        assert not violations, (
            f"Token underestimation detected in categories:\n"
            + "\n".join(f"  • {cat}: actual={act} > estimated={est}" for cat, act, est in violations)
        )

    def test_actual_token_ceiling_integration(self):
        """
        Token Ceiling Integration Test:
        - Model context limit: 8,000 tokens
        - Output reserve: 2,000 tokens
        - Allowed actual input: <= 6,000 tokens
        - Payload: large Arabic, English, JSON, code, emoji text.
        
        Guarantees:
        After ContextBuilder assembly, the actual token count of the assembled
        text (as measured by reference oracle) MUST be <= 6,000 tokens!
        """
        # Configure policy with total_budget=8000, output_reserve=2000, safety factor=1.10
        policy = ContextBudgetPolicy(
            total_budget=8000,
            output_reserve=2000,
            token_safety_factor=Decimal("1.10"),
            token_safety_reserve=100,
            model_context_limit=8000,
        )
        ctx = TrustedTenantContext(workspace_id="ws_safe", user_id="u_safe")
        mem_svc = make_test_memory_service()

        # Add heavy multilingual content (Arabic, English, JSON, code, emoji)
        for i in range(50):
            sample_content = (
                f"مشروع رقم {i}: "
                f"نص باللغة العربية مع تفاصيل سينمائية ومؤثرات 🎬🔥. "
                f"Code snippet: def render_{i}(): return '{i}' * 10\n"
                f"JSON payload: {{\"iteration\": {i}, \"status\": \"ACTIVE\", \"tokens\": 100}}\n"
                f"English documentation: Seamless transitions and punchy typography across all scenes."
            )
            mem_svc.store_memory(
                context=ctx,
                content=sample_content,
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.WORKSPACE,
                confidence=0.85,
                metadata={"domain": "tone"},
            )

        proj_svc = MockProjectService({
            "prj_safe": MockLifecycleDTO(project_id="prj_safe", lifecycle_state="PLAN_READY")
        })

        builder = ContextBuilder(
            project_service=proj_svc,
            memory_service=mem_svc,
            budget_policy=policy,
        )

        req = ContextRequest(
            request_id="req_token_ceiling_gate",
            trusted_context=ctx,
            capability=CapabilityType.TEXT_GENERATION,
            project_id="prj_safe",
            query_text="Build full high-density multilingual video production script",
            created_at=datetime.now(timezone.utc),
        )

        package: ContextPackage = builder.build(req)

        # 1. Assembled estimated tokens must be <= usable input ceiling
        usable_ceiling = policy.calculate_usable_input_ceiling()
        assert package.diagnostics.total_estimated_tokens <= usable_ceiling
        assert package.diagnostics.budget_ceiling == usable_ceiling

        # 2. Measure ACTUAL tokens of the entire assembled prompt text using reference oracle
        full_assembled_text = package.to_prompt_text()
        actual_tokens = reference_tokenizer_oracle(full_assembled_text)

        # 3. Model limit verification: actual input tokens MUST be <= 6,000 (8000 - 2000)
        max_allowed_actual_input = 8000 - 2000
        assert actual_tokens <= max_allowed_actual_input, (
            f"Actual token ceiling breached! actual_tokens={actual_tokens} > "
            f"max_allowed={max_allowed_actual_input}"
        )

        # 4. Invariant: estimated tokens >= actual tokens
        assert package.diagnostics.total_estimated_tokens >= actual_tokens

    def test_model_context_limit_and_safety_margin_bounds(self):
        """Verifies model_context_limit caps total budget and safety factor reserves headroom."""
        policy = ContextBudgetPolicy(
            total_budget=16000,
            output_reserve=4000,
            token_safety_factor=Decimal("1.20"),
            token_safety_reserve=200,
            model_context_limit=10000,  # model caps 16000 down to 10000
        )
        assert policy.get_effective_total_budget() == 10000

        # effective total = 10000
        # reserve = 4000
        # safety reserve = 200
        # available = 10000 - 4000 - 200 = 5800
        # usable ceiling = floor(5800 / 1.20) = 4833
        ceiling = policy.calculate_usable_input_ceiling()
        assert ceiling == 4833
        assert ceiling < (10000 - 4000)
