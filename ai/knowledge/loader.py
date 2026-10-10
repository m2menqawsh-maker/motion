"""
ai/knowledge/loader.py
======================
Knowledge loading, source integrity verification, and catalog initialization (S28-02).

Guarantees:
- Knowledge = Information & Experience (Knowledge ≠ Runtime Authority).
- Strict SHA-256 content hash verification against canonical descriptors.
- Rejection of missing files, hash mismatches, or retired documents when strict.
- Canonical seed descriptors mapped to existing references/ directory.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import KnowledgeCategory, KnowledgeDescriptor, KnowledgeStatus
from ai.knowledge.registry import KnowledgeRegistry


class KnowledgeLoaderError(Exception):
    """Base exception for Knowledge Loader errors."""
    pass


class KnowledgeSourceNotFoundError(KnowledgeLoaderError):
    """Raised when source file cannot be found on disk."""
    pass


class KnowledgeHashMismatchError(KnowledgeLoaderError):
    """Raised when source file SHA-256 hash does not match descriptor content_hash."""
    pass


class KnowledgeRetiredError(KnowledgeLoaderError):
    """Raised when attempting to load a retired knowledge artifact in strict mode."""
    pass


@dataclass(frozen=True)
class LoadedKnowledgeDocument:
    """A fully verified, loaded knowledge document with descriptor and content."""
    descriptor: KnowledgeDescriptor
    content: str
    absolute_path: Path


class KnowledgeLoader:
    """
    Loads and validates source knowledge documents from the filesystem.
    """

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = workspace_root or Path.cwd()

    def resolve_path(self, relative_or_absolute: str | Path) -> Path:
        """Resolves path relative to workspace_root if not absolute."""
        p = Path(relative_or_absolute)
        if p.is_absolute():
            return p
        return (self.workspace_root / p).resolve()

    def compute_hash(self, content: bytes | str) -> str:
        """Computes SHA-256 hexadecimal digest of content."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def load_document(
        self,
        descriptor: KnowledgeDescriptor,
        base_dir: Optional[Path] = None,
        verify_hash: bool = True,
        strict_status: bool = False,
    ) -> LoadedKnowledgeDocument:
        """
        Loads a document from disk according to its descriptor, verifying existence and hash.
        """
        if strict_status and descriptor.status == KnowledgeStatus.RETIRED:
            raise KnowledgeRetiredError(
                f"Knowledge item '{descriptor.knowledge_id}' is RETIRED and cannot be loaded."
            )

        root = base_dir or self.workspace_root
        src_path = Path(descriptor.source_uri)
        abs_path = src_path if src_path.is_absolute() else (root / src_path).resolve()

        if not abs_path.exists() or not abs_path.is_file():
            raise KnowledgeSourceNotFoundError(
                f"Knowledge source file not found: {abs_path} (for knowledge_id='{descriptor.knowledge_id}')"
            )

        raw_bytes = abs_path.read_bytes()
        actual_hash = self.compute_hash(raw_bytes)

        if verify_hash and descriptor.content_hash:
            if actual_hash != descriptor.content_hash:
                alt_hash = self.compute_hash(raw_bytes.replace(b"\r\n", b"\n"))
                alt_crlf_hash = self.compute_hash(raw_bytes.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
                if descriptor.content_hash not in (alt_hash, alt_crlf_hash):
                    raise KnowledgeHashMismatchError(
                        f"Content hash mismatch for '{descriptor.knowledge_id}': "
                        f"expected '{descriptor.content_hash}', got '{actual_hash}'"
                    )

        content_text = raw_bytes.decode("utf-8")
        return LoadedKnowledgeDocument(
            descriptor=descriptor,
            content=content_text,
            absolute_path=abs_path,
        )

    @classmethod
    def get_canonical_descriptors(cls) -> List[KnowledgeDescriptor]:
        """
        Returns the authoritative initial list of KnowledgeDescriptors for the workspace.
        Derived from legacy creative inventory (S28-01) and references/.
        """
        return [
            KnowledgeDescriptor(
                knowledge_id="know_playbook_ffmpeg",
                title="FFmpeg Transcoding & Normalization Playbook",
                category="PLAYBOOK",
                source_uri="references/1_playbooks/ffmpeg_recipes.md",
                content_hash="c50172ff0a6d16d172b6852d1121bfaf806581995c44cf566c4d593a0bd74e3f",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["ffmpeg", "transcoding", "codec", "normalization", "audio"],
                video_types=[],
                platforms=[],
                audio_modes=[],
                language="any",
                summary="FFmpeg CLI recipes for audio/video normalization, all-intra transcoding, and concatenation.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_playbook_hook_sprint",
                title="Hook Playbook: 30s Article Sprint Reels",
                category="PLAYBOOK",
                source_uri="references/1_playbooks/hook_playbook_article_sprint.md",
                content_hash="3dd24f518d3eb1fee4f7766d0b124018eebd69d560b382b6c5cd935fa6348f41",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["hook", "sprint", "article", "fast_paced", "short_form"],
                video_types=["sprint", "reel", "short"],
                platforms=["tiktok", "instagram", "youtube_shorts"],
                audio_modes=[AudioMode.VO_ONLY, AudioMode.VO_MUSIC],
                language="en",
                summary="Production playbook for high-velocity 30s article sprint reels with aggressive hooks.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_playbook_living_canvas",
                title="Living Canvas Continuous Explainer Playbook",
                category="PLAYBOOK",
                source_uri="references/1_playbooks/living_canvas.md",
                content_hash="93c483e304ba7c1886c552d1aea90399c6c647bc7cf9f9f10526c12346eb81d4",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["canvas", "seamless", "continuous", "explainer", "saas", "motion"],
                video_types=["explainer", "saas_demo"],
                platforms=["youtube", "web", "linkedin"],
                audio_modes=[AudioMode.VO_MUSIC, AudioMode.VO_ONLY],
                language="any",
                summary="Continuous living canvas explainer methodology with seamless camera motion and zero hard cuts.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_playbook_motion_collage",
                title="Motion Collage Cutout Animation Playbook",
                category="PLAYBOOK",
                source_uri="references/1_playbooks/motion_collage.md",
                content_hash="cfdcc35e39d42f49d96bfea50124abaea2b21773a7ac48582dd6b577e4b8e38b",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["montage", "collage", "cutout", "motion", "creative", "paper_tear"],
                video_types=["montage", "collage", "creative_ad"],
                platforms=["instagram", "tiktok", "youtube"],
                audio_modes=[AudioMode.MUSIC_ONLY, AudioMode.VO_MUSIC],
                language="any",
                summary="Layered cutout collage animation principles, textures, and kinetic pacing.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_playbook_review",
                title="Competitor Review Conquest Compilation Playbook",
                category="PLAYBOOK",
                source_uri="references/1_playbooks/review_video.md",
                content_hash="fd6babe73c3ffdb0c34cc933071e742aa33ea2c5ef18a60f09dd55961092076f",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["review", "comparison", "conquest", "social_proof", "testimonials"],
                video_types=["review", "comparison"],
                platforms=["youtube", "linkedin", "tiktok"],
                audio_modes=[AudioMode.VO_MUSIC, AudioMode.VO_ONLY],
                language="any",
                summary="Conquest compilation video playbook highlighting product differentiation and social proof.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_playbook_tabletop",
                title="Tabletop Layered Concept Explainer Playbook",
                category="PLAYBOOK",
                source_uri="references/1_playbooks/tabletop_explainer.md",
                content_hash="26349fc7befac7fd06e7bb6538496d1b3bdeb9091b80a1fcdc71b2fc1432c19f",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["tabletop", "layered", "concept", "explainer", "top_down"],
                video_types=["explainer", "concept_demo"],
                platforms=["youtube", "linkedin"],
                audio_modes=[AudioMode.VO_MUSIC, AudioMode.VO_ONLY],
                language="any",
                summary="Tiered concept layered tabletop explainer reels with top-down staging.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_playbook_video_copy",
                title="Video Copywriting & Voiceover Pacing Rules",
                category="PLAYBOOK",
                source_uri="references/1_playbooks/video_copy.md",
                content_hash="49d5d459537d5cee2614d2d1fb0443eeea9e809a5024068e113ea5aa05dde609",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["copywriting", "script", "pacing", "wpm", "voiceover"],
                video_types=["explainer", "ad", "social_short"],
                platforms=["youtube", "tiktok", "instagram"],
                audio_modes=[AudioMode.VO_ONLY, AudioMode.VO_MUSIC],
                language="any",
                summary="Voiceover pacing guidelines, word budgets (150 wpm), and narrative copywriting rules.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_sop_hyperrealistic",
                title="Hyperrealistic Image & Prompting SOP",
                category="SOP",
                source_uri="references/2_sops/hyperrealistic_image.md",
                content_hash="57871d745e6a6b805bdb555e9beae1e3c3c3d4c34e8c9eecee65c1af05221f61",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["image", "prompting", "photorealistic", "midjourney", "lighting", "optics"],
                video_types=["ad", "explainer"],
                platforms=[],
                audio_modes=[],
                language="any",
                summary="Standard operating procedure for realistic lighting, lens choices, and generative image prompts.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_sop_seedance_avatar",
                title="Seedance Avatar Video Synthesis SOP",
                category="SOP",
                source_uri="references/2_sops/seedance_avatar.md",
                content_hash="e2a4fedf5ded777e91f8b47aa2d68fdaa3e76b1289520db72e80503a5adee59d",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["avatar", "seedance", "talking_head", "green_screen", "lip_sync"],
                video_types=["explainer", "avatar_reel"],
                platforms=["tiktok", "instagram", "youtube"],
                audio_modes=[AudioMode.VO_ONLY, AudioMode.VO_MUSIC],
                language="any",
                summary="SOP for avatar video generation, lip sync calibration, and green-screen chroma keying.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_sop_spoken_vo",
                title="Spoken-VO Humanizer SOP (Speech & Cadence)",
                category="SOP",
                source_uri="references/2_sops/spoken_vo_humanizer.md",
                content_hash="1b2dfc24a8de75716c0256045ecdd8ad8dce455bb2ae4f0a6120f963cefb513b",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["voiceover", "speech", "spoken_vo", "tts", "humanizer", "cadence"],
                video_types=["explainer", "ad", "review"],
                platforms=["tiktok", "instagram", "youtube"],
                audio_modes=[AudioMode.VO_ONLY, AudioMode.VO_MUSIC],
                language="any",
                summary="12 rules of natural conversational voiceover; eliminates robotic AI cadence.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_sop_template_proposal",
                title="Template Proposal & Contribution SOP",
                category="SOP",
                source_uri="references/2_sops/template_proposal.md",
                content_hash="4e38948bf07afed8563d8682fc2e8e37687ad2b4129be3c866f4e512e6aaeaa8",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["template", "proposal", "contribution", "governance"],
                video_types=[],
                platforms=[],
                audio_modes=[],
                language="any",
                summary="SOP for proposing novel templates into candidate quarantine and formal promotion.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_eng_remotion",
                title="Remotion Engineering Principles & Spring Physics",
                category="ENGINEERING_GUIDE",
                source_uri="references/3_engineering/remotion_guide.md",
                content_hash="80abf267f3b606cbbe1dcf82387eff78e3e7cc42bf9c3f3091a301b17b4d77eb",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["remotion", "react", "spring", "engineering", "lifecycle", "declarative"],
                video_types=[],
                platforms=[],
                audio_modes=[],
                language="any",
                summary="Remotion code architecture, sequence lifecycle, interpolate math, and spring physics.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_taste_disney",
                title="12 Disney Animation Principles for Declarative Motion",
                category="TASTE_REFERENCE",
                source_uri="references/4_taste_engine/disney-principles.md",
                content_hash="78c7527d849f5282ebeef484c7cd95aa0483ad9f0e564ccefc266921a428c5b7",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["disney", "animation", "motion", "physics", "timing", "squash_and_stretch"],
                video_types=[],
                platforms=[],
                audio_modes=[],
                language="any",
                summary="Application of the 12 classical Disney animation principles to React Remotion code.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_taste_motion_personality",
                title="Motion Personality Profiles & Timing Framework",
                category="TASTE_REFERENCE",
                source_uri="references/4_taste_engine/motion-personality.md",
                content_hash="f71357c55ea6ca21ac0ea542d646643433c5e9365bc1bc93d2a1fe361de9e259",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["personality", "motion", "spring", "timing", "easing", "cinematic", "energetic"],
                video_types=[],
                platforms=[],
                audio_modes=[],
                language="any",
                summary="Timing, damping, and stiffness specifications for Cinematic, Energetic, Playful, and Technical personalities.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_taste_sfx_matrix",
                title="SFX Gesture Binding Matrix & Audio Ducking",
                category="TASTE_REFERENCE",
                source_uri="references/4_taste_engine/sfx_binding_matrix.md",
                content_hash="fb58bcc2ae38f1ddae86f2149abcb43ed215e5899205efb04f51700c276a42d0",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["sfx", "audio", "ducking", "gestures", "sound_design"],
                video_types=[],
                platforms=[],
                audio_modes=[AudioMode.MUSIC_ONLY, AudioMode.VO_MUSIC],
                language="any",
                summary="Binding matrix pairing visual gestures (whoosh, pop, slide) with sound effects and audio ducking.",
            ),
            KnowledgeDescriptor(
                knowledge_id="know_taste_signature_style",
                title="Director Signature Style & Visual Grammar",
                category="TASTE_REFERENCE",
                source_uri="references/4_taste_engine/user-signature-style.md",
                content_hash="b0928c626f6762ff5d5bafff76bfcd8a2a99a6dc0ac419b7a5368537c3cf22f9",
                version="1.0.0",
                status=KnowledgeStatus.ACTIVE,
                tags=["signature", "style", "director", "taste", "rules", "double_variance"],
                video_types=[],
                platforms=[],
                audio_modes=[],
                language="any",
                summary="Core director rules: Scene=Sentence, Shot=Beat, double variance, and emphasis grammar.",
            ),
        ]

    def load_canonical_catalog(
        self,
        registry: Optional[KnowledgeRegistry] = None,
        verify_hash: bool = True,
    ) -> List[LoadedKnowledgeDocument]:
        """
        Loads all canonical descriptors from references/ and optionally registers them in registry.
        """
        descriptors = self.get_canonical_descriptors()
        docs: List[LoadedKnowledgeDocument] = []
        for d in descriptors:
            doc = self.load_document(d, verify_hash=verify_hash)
            docs.append(doc)
            if registry is not None:
                registry.register(d)
        return docs
