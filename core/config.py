# -*- coding: utf-8 -*-
"""Cấu hình tập trung. Mọi hằng số / đường dẫn / công tắc bật-tắt nằm ở đây."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TTHC_DIR = DATA / "tthc"
MANIFEST = DATA / "manifest.json"
CACHE_SIMPLIFIED = DATA / "cache" / "simplified"
CACHE_AUDIO = DATA / "cache" / "audio"
AUDIO_BANK = DATA / "audio_bank"
RAW_EXCEL = DATA / "raw_excel"

for _p in (CACHE_SIMPLIFIED, CACHE_AUDIO, AUDIO_BANK, RAW_EXCEL, TTHC_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ Models
UU_TIEN_QUALITY = [
    "gemini-3.8-flash", "gemini-3.1-pro", "gemini-pro-latest", "gemini-2.5-pro",
    "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
    "gemini-flash-latest", "gemini-2.5-flash",
]
UU_TIEN_FAST = [
    "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite", "gemini-3.7-flash", "gemini-flash-latest",
    "gemini-2.5-flash-lite", "gemini-2.5-flash",
]
UU_TIEN_STT = [
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest", "gemini-2.5-flash",
]

LOAI_TRU_MODEL = (
    "image", "-tts", "embedding", "computer-use", "robotics", "lyria",
    "nano-banana", "deep-research", "transcribe", "customtools",
    "antigravity", "gemma", "veo", "imagen",
)

MODEL_FAST = os.getenv("LGB_MODEL_FAST", "")
MODEL_QUALITY = os.getenv("LGB_MODEL_QUALITY", "")
MODEL_STT = os.getenv("LGB_MODEL_STT", "")

CACHE_MODELS = DATA / "cache" / "models.json"

# ------------------------------------------------------------ Tiếng Mông
TTS_HMONG_PROVIDER = os.getenv("LGB_TTS_HMONG", "auto")
TRANSLATE_PROVIDER = os.getenv("LGB_TRANSLATE", "gemini")
HMONG_ORTHOGRAPHY = os.getenv("LGB_HMONG_ORTHO", "vn")

# ---------------------------------------------------------------- Nhóm TTHC
DANH_MUC_THU_TUC = {
    "KHAI_SINH": "ĐĂNG KÝ KHAI SINH",
    "KET_HON": "ĐĂNG KÝ KẾT HÔN",
    "DOC_THAN": "XÁC NHẬN TÌNH TRẠNG HÔN NHÂN",
    "KHAI_TU": "ĐĂNG KÝ KHAI TỬ",
    "CHUNG_THUC": "SAO Y / CHỨNG THỰC",
    "DAT_DAI": "THỦ TỤC ĐẤT ĐAI",
    "TRO_CAP": "TRỢ CẤP XÃ HỘI",
    "KHAC": "VẤN ĐỀ KHÁC",
}

NGUONG_TU_TIN = float(os.getenv("LGB_NGUONG_TU_TIN", "0.55"))
