# -*- coding: utf-8 -*-
"""NHIỆM VỤ 1b — Phát giọng nói tiếng Mông (Chuỗi dự phòng 4 tầng)."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from core.config import AUDIO_BANK, CACHE_AUDIO, TTS_HMONG_PROVIDER
from core.hmong.rpa_vi import co_ve_la_rpa, rpa_sang_vi

BANK_INDEX = AUDIO_BANK / "index.json"


def _hash(text: str, tag: str) -> str:
    return hashlib.sha256(f"{tag}::{text}".encode("utf-8")).hexdigest()[:24]


def _chuan_hoa(text: str) -> str:
    return " ".join((text or "").lower().split())


def _load_bank() -> dict:
    if BANK_INDEX.exists():
        return json.loads(BANK_INDEX.read_text(encoding="utf-8"))
    return {}


def tts_audio_bank(text: str, *, key: str | None = None) -> Path | None:
    bank = _load_bank()
    if key:
        f = bank.get("theo_thu_tuc", {}).get(key)
        if f and (AUDIO_BANK / f).exists():
            return AUDIO_BANK / f
    f = bank.get("theo_cau", {}).get(_chuan_hoa(text))
    if f and (AUDIO_BANK / f).exists():
        return AUDIO_BANK / f
    return None


LOCAL_TTS_SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "tts_hmong_local.py"


def tts_local_neural(text_rpa: str) -> Path | None:
    if not LOCAL_TTS_SCRIPT.exists():
        return None
    out = CACHE_AUDIO / f"neural_{_hash(text_rpa, 'neural')}.wav"
    if out.exists():
        return out
    try:
        r = subprocess.run(
            ["python", str(LOCAL_TTS_SCRIPT), "--text", text_rpa, "--out", str(out)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0 and out.exists() and out.stat().st_size > 1024:
            return out
    except Exception:
        pass
    return None


def tts_tieng_viet(text: str, *, tag: str = "vi") -> Path | None:
    out = CACHE_AUDIO / f"{tag}_{_hash(text, tag)}.mp3"
    if out.exists():
        return out
    try:
        from gtts import gTTS
        gTTS(text=text, lang="vi", slow=False).save(str(out))
        return out
    except Exception:
        pass
    try:
        import asyncio
        import edge_tts

        async def _run():
            await edge_tts.Communicate(text, "vi-VN-HoaiMyNeural").save(str(out))

        asyncio.run(_run())
        return out if out.exists() else None
    except Exception:
        return None


def tts_vi_phonetic(text_rpa: str) -> Path | None:
    text_vn = rpa_sang_vi(text_rpa) if co_ve_la_rpa(text_rpa) else text_rpa
    return tts_tieng_viet(text_vn, tag="hmong_phonetic")


def phat_tieng_mong(
    text_rpa: str,
    *,
    key: str | None = None,
    provider: str | None = None,
) -> tuple[Path | None, str]:
    provider = provider or TTS_HMONG_PROVIDER
    if provider == "off" or not (text_rpa or "").strip():
        return None, "off"

    thu_tu = {
        "auto": ["audio_bank", "local_neural", "vi_phonetic"],
        "audio_bank": ["audio_bank"],
        "local_neural": ["local_neural"],
        "cosyvoice": ["local_neural"],
        "vi_phonetic": ["vi_phonetic"],
    }.get(provider, ["vi_phonetic"])

    for tang in thu_tu:
        if tang == "audio_bank":
            p = tts_audio_bank(text_rpa, key=key)
        elif tang == "local_neural":
            p = tts_local_neural(text_rpa)
        else:
            p = tts_vi_phonetic(text_rpa)
        if p is not None:
            return p, tang
    return None, "that_bai"


NHAN_TANG = {
    "audio_bank": "🎙️ Giọng người Mông thu sẵn",
    "local_neural": "🤖 Giọng máy (model tiếng Mông)",
    "vi_phonetic": "🔤 Giọng máy đọc phiên âm (tạm thời, chưa chuẩn)",
    "off": "🔇 Đã tắt giọng Mông",
    "that_bai": "⚠️ Chưa tạo được giọng nói",
}
