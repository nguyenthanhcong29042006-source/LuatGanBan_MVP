# -*- coding: utf-8 -*-
"""NHIỆM VỤ 1b — Nhận diện giọng nói đa phương thức bằng Gemini Flash."""
from __future__ import annotations

import io
import os
import streamlit as st
import google.generativeai as genai
from core.config import UU_TIEN_STT

SYSTEM_STT_VIET = """\
Bạn là trợ lý chuyển từ giọng nói sang văn bản (STT).
Nhiệm vụ: Chuyển toàn bộ lời nói trong file âm thanh thành văn bản tiếng Việt.
Yêu cầu:
1. Ghi lại chính xác từng từ người nói.
2. Không thêm bớt lời dẫn, không giải thích.
3. Nếu âm thanh quá mờ hoặc không có tiếng người nói, chỉ trả về chuỗi rỗng.
"""

SYSTEM_STT_MONG = """\
Bạn là phiên dịch viên giọng nói tiếng Mông sang tiếng Việt.
Nhiệm vụ: Nghe lời nói tiếng Mông trong file audio và trả về bản dịch tiếng Việt.
Yêu cầu:
1. Dịch ý chính xác sang tiếng Việt tự nhiên.
2. Trả về format đúng 2 dòng:
   MON: <văn bản phiên âm Mông RPA nếu có>
   VI: <bản dịch tiếng Việt chuẩn>
3. Không thêm lời giải thích nào khác.
"""


def nghe(audio_file: io.BytesIO | bytes, *, tieng_mong: bool = False) -> tuple[str, dict]:
    """Chuyển audio thành văn bản sử dụng trực tiếp mô hình Gemini Flash."""
    if isinstance(audio_file, io.BytesIO):
        audio_bytes = audio_file.getvalue()
    else:
        audio_bytes = audio_file

    system_prompt = SYSTEM_STT_MONG if tieng_mong else SYSTEM_STT_VIET
    
    # Lấy API key từ Secrets hoặc biến môi trường
    api_key = os.getenv("GEMINI_API_KEY") or getattr(st, "secrets", {}).get("GEMINI_API_KEY", "")
    if not api_key:
        return "", {"error": "Thiếu GEMINI_API_KEY"}

    genai.configure(api_key=api_key)
    
    van_ban = ""
    for model_name in UU_TIEN_STT:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt
            )
            response = model.generate_content([
                {"mime_type": "audio/wav", "data": audio_bytes},
                "Hãy nghe và chuyển đổi âm thanh này thành văn bản:"
            ])
            if response and response.text:
                van_ban = response.text.strip()
                break
        except Exception:
            continue

    return van_ban, {"do_dai_bytes": len(audio_bytes)}
