#!/usr/bin/env python3
"""ElevenLabs helper for NON-ENGLISH avatar VO.

When a project's language is not English, the avatar-insta-split pipeline can no longer
rely on the HeyGen text voice (which is the English default). This helper:
  1. picks a voice that matches the project language from ElevenLabs' shared voice library
     (dynamically — no hardcoded per-language voice id), and
  2. synthesizes the script with eleven_v3 (latest, 74 languages; falls back to
     eleven_multilingual_v2 if v3 is unavailable on the account).

English projects never call this — their path stays byte-identical (HeyGen TTS).

CLI:
    python3 elevenlabs_voice.py --language Dutch --gender female            # just pick a voice
    python3 elevenlabs_voice.py --language Dutch --text "Hallo" --out a.mp3 # pick + synthesize
"""
import argparse, json, os, urllib.request, urllib.error
from pathlib import Path

EL_BASE = "https://api.elevenlabs.io"
PRIMARY_MODEL = "eleven_v3"                 # latest, 74 langs (verified live 2026-06)
FALLBACK_MODEL = "eleven_multilingual_v2"   # 29 langs incl. nl/fr/de/es — wide account access

# free-text Projects.Language -> ISO 639-1. Unknown -> fail loud (never silently English).
LANG_MAP = {
    "english": "en", "dutch": "nl", "nederlands": "nl", "flemish": "nl", "vlaams": "nl",
    "french": "fr", "français": "fr", "francais": "fr", "spanish": "es", "español": "es",
    "espanol": "es", "german": "de", "deutsch": "de", "italian": "it", "italiano": "it",
    "portuguese": "pt", "português": "pt", "polish": "pl", "swedish": "sv", "danish": "da",
    "norwegian": "no", "finnish": "fi", "turkish": "tr", "czech": "cs", "greek": "el",
    "romanian": "ro", "hungarian": "hu", "russian": "ru", "ukrainian": "uk", "arabic": "ar",
    "hindi": "hi", "japanese": "ja", "korean": "ko", "chinese": "zh", "mandarin": "zh",
    "indonesian": "id", "vietnamese": "vi", "tagalog": "tl", "filipino": "tl",
}


def is_english(language: str) -> bool:
    """True for any English value/locale so it stays on the unchanged HeyGen text path:
    '', 'en', 'en-US'/'en_GB'/..., 'English', 'English (Australia)', etc."""
    s = (language or "").strip().lower()
    return s in ("", "en") or s.startswith("english") or s.startswith("en-") or s.startswith("en_")


def to_iso(language: str) -> str:
    s = (language or "").strip().lower()
    if not s:
        return "en"
    if len(s) == 2 and s.isalpha():
        return s
    if s not in LANG_MAP:
        raise SystemExit(f"unknown project language {language!r}; add it to LANG_MAP in elevenlabs_voice.py")
    return LANG_MAP[s]


def _key() -> str:
    raise PermissionError("DIRECT SECRET ACCESS BLOCKED: Raw ELEVENLABS_API_KEY access outside canonical S27 capability adapters is prohibited.")


def _get(url: str):
    raise RuntimeError("DIRECT PROVIDER EXECUTION BLOCKED: Direct ElevenLabs network calls via legacy elevenlabs_voice.py are prohibited.")


def pick_voice(language: str, gender: str = None, prefer: str = None) -> dict:
    """Pick a shared-library voice matching `language` (ISO or free-text).
    gender ('female'|'male') and prefer (substring of a voice name) bias the choice."""
    raise RuntimeError(
        "DIRECT PROVIDER EXECUTION BLOCKED: Direct voice picking via legacy elevenlabs_voice.py is prohibited. "
        "Use canonical S27 speech capability adapters and ModelRouter."
    )


def tts(text: str, voice_id: str, out_path: str, model_id: str = PRIMARY_MODEL,
        stability: float = 0.4, similarity: float = 0.75) -> dict:
    """Synthesize `text` to mp3. Tries model_id, then FALLBACK_MODEL. Returns {out, model}."""
    raise RuntimeError(
        "DIRECT PROVIDER EXECUTION BLOCKED: Direct TTS execution via legacy elevenlabs_voice.py is prohibited. "
        "Use canonical S27 speech capability adapters and ModelRouter."
    )


if __name__ == "__main__":
    raise RuntimeError(
        "DIRECT PROVIDER BYPASS BLOCKED: Direct CLI execution of elevenlabs_voice.py is prohibited. "
        "Route all speech requests via S27 speech capabilities and ModelRouter."
    )
