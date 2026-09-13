# -*- coding: utf-8 -*-
"""Phiên âm tiếng Mông: RPA  ->  chính tả kiểu Việt Nam.

*** ĐÂY LÀ "THỦ THUẬT PHIÊN ÂM" GIẢI QUYẾT BẾ TẮC TTS ***

Bối cảnh:
  - Google Translate / Azure trả tiếng Mông theo RPA (Romanized Popular
    Alphabet, do các nhà truyền giáo lập ở Lào 1951-53): thanh điệu ghi bằng
    CHỮ CÁI cuối âm tiết (nyob, kuv, mus...).
  - Không có dịch vụ TTS thương mại nào (Google/Azure/AWS/ElevenLabs) đọc
    được tiếng Mông.
  - NHƯNG: tiếng Mông là ngôn ngữ có thanh điệu, và người Mông ở Việt Nam
    dùng chữ Mông Latin hoá theo lối Việt. Bộ âm vị tiếng Việt phủ được phần
    lớn âm tiết Mông.
  => Chuyển RPA sang cách viết mà máy đọc tiếng Việt phát âm đúng nhất,
     rồi dùng TTS tiếng Việt (rẻ, sẵn có, chất lượng cao) để phát.

Kết quả nghe được KHÔNG phải giọng Mông chuẩn. Nó là giọng "người Việt đọc
tiếng Mông" — dễ hiểu hơn nhiều so với để máy đọc RPA theo lối tiếng Anh
("nyob zoo" -> "nai-ốp zu"), và đủ dùng cho bản demo.

CẢNH BÁO: bảng dưới đây là BẢN NHÁP do kỹ sư lập từ bảng IPA của RPA.
Bắt buộc phải cho 1 người Mông bản địa nghe và hiệu đính trước khi dùng
với bà con. Mọi ô đều sửa được mà không cần sửa code (xem BANG_PHU_AM).
"""
from __future__ import annotations

import re
import unicodedata

# ----------------------------------------------------------------- THANH ĐIỆU
# RPA có 7-8 thanh, tiếng Việt có 6 -> ánh xạ CÓ MẤT MÁT (lossy).
# Ưu tiên giữ được sự PHÂN BIỆT giữa các thanh hơn là khớp tuyệt đối cao độ.
SAC, HUYEN, HOI, NGA, NANG = "́", "̀", "̉", "̃", "̣"
BANG_THANH = {
    "b": SAC,    # cao      /pɔ́/  -> sắc
    "":  "",     # giữa     /pɔ/   -> ngang
    "s": HUYEN,  # thấp     /pɔ̀/  -> huyền
    "j": NGA,    # cao xuống /pɔ̂/ -> ngã   (xấp xỉ: tiếng Việt không có thanh này)
    "v": HOI,    # giữa lên /pɔ̌/  -> hỏi
    "m": NANG,   # thanh tắc nghẽn /pɔ̰/ -> nặng (khớp tốt)
    "g": HUYEN,  # thấp xuống, hơi thở /pɔ̤/ -> huyền (trùng với 's', chưa phân biệt được)
    "d": NANG,   # thấp lên, tắc nghẽn (hiếm) -> nặng
}
CHU_THANH = set("bsjvmgd")

# ----------------------------------------------------------------- PHỤ ÂM ĐẦU
# Xếp theo độ dài giảm dần khi khớp (xem _tach_am_tiet).
# Cột phải = cách viết để máy đọc TIẾNG VIỆT phát ra âm gần nhất.
BANG_PHU_AM: dict[str, str] = {
    # tắc + tiền mũi hoá
    "npl": "bl", "ndl": "đl", "ntx": "d",  "nts": "tr",
    "np": "b",   "nt": "đ",   "nr": "tr",  "nc": "nh", "nk": "g", "nq": "g",
    # bật hơi
    "plh": "pl", "dlh": "tl", "tsh": "tr", "txh": "ch", "qh": "kh",
    "ph": "p",   # RPA ph = /pʰ/  KHÔNG phải /f/ — tiếng Việt "ph" = /f/ nên phải đổi thành "p"
    "th": "th", "dh": "đ", "rh": "tr", "ch": "ch", "kh": "kh",
    # tắc đơn
    "ny": "nh", "ml": "ml", "pl": "pl", "dl": "tl",
    "ts": "tr", "tx": "ch", "hl": "hl", "xy": "s",
    "ng": "ng", "hm": "hm", "hn": "hn",
    "p": "p", "t": "t", "d": "đ", "r": "tr", "c": "ch",
    "k": "c", "q": "c", "n": "n", "m": "m", "l": "l",
    # xát
    "f": "ph", "v": "v", "x": "x", "s": "s", "z": "r", "y": "gi", "h": "h",
    "w": "qu",
}
_PHU_AM_SAP_XEP = sorted(BANG_PHU_AM, key=len, reverse=True)

# ----------------------------------------------------------------- NGUYÊN ÂM
BANG_NGUYEN_AM: dict[str, str] = {
    "aa": "ang",  # /ã/  mũi hoá -> tiếng Việt ghi bằng vần mũi
    "ee": "ênh",  # /ẽ/
    "oo": "ong",  # /ɔ̃/
    "ai": "ai", "aw": "âu", "au": "au", "ia": "ia", "ua": "ua",
    "a": "a", "e": "e", "i": "i", "o": "o", "u": "u",
    "w": "ư",     # /ɨ/ -> "ư" khớp rất tốt
}
_NGUYEN_AM_SAP_XEP = sorted(BANG_NGUYEN_AM, key=len, reverse=True)
_VOWEL_CHARS = set("aeiouwàáảãạ")


def _dat_thanh(van: str, dau: str) -> str:
    """Đặt dấu thanh lên nguyên âm chính của vần tiếng Việt."""
    if not dau:
        return van
    for i, ch in enumerate(van):
        if ch in "aăâeêioôơuưy":
            return unicodedata.normalize("NFC", van[:i + 1] + dau + van[i + 1:])
    return van


def _tach_am_tiet(am_tiet: str) -> tuple[str, str, str]:
    """'nyob' -> ('ny', 'o', 'b') ; 'zoo' -> ('z', 'oo', '') ; 'kuv' -> ('k','u','v')"""
    s = am_tiet.lower()
    thanh = ""
    if len(s) > 1 and s[-1] in CHU_THANH and s[-2] in "aeiouw":
        thanh, s = s[-1], s[:-1]
    phu_am = ""
    for p in _PHU_AM_SAP_XEP:
        if s.startswith(p) and len(s) > len(p):   # phải còn nguyên âm phía sau
            phu_am, s = p, s[len(p):]
            break
    return phu_am, s, thanh


def am_tiet_rpa_sang_vi(am_tiet: str) -> str:
    phu_am, van, thanh = _tach_am_tiet(am_tiet)
    vi_phu_am = BANG_PHU_AM.get(phu_am, phu_am)
    vi_van = None
    for v in _NGUYEN_AM_SAP_XEP:
        if van == v:
            vi_van = BANG_NGUYEN_AM[v]
            break
    if vi_van is None:                     # vần lạ: ghép dần từng phần
        out, rest = [], van
        while rest:
            for v in _NGUYEN_AM_SAP_XEP:
                if rest.startswith(v):
                    out.append(BANG_NGUYEN_AM[v])
                    rest = rest[len(v):]
                    break
            else:
                out.append(rest[0])
                rest = rest[1:]
        vi_van = "".join(out)
    # "c" + e/i/ê  -> "k" cho đúng chính tả tiếng Việt
    if vi_phu_am == "c" and vi_van[:1] in "eiê":
        vi_phu_am = "k"
    return vi_phu_am + _dat_thanh(vi_van, BANG_THANH.get(thanh, ""))


_TOKEN = re.compile(r"[A-Za-z]+|[^A-Za-z]+")


def rpa_sang_vi(text: str) -> str:
    """Phiên âm cả đoạn. Giữ nguyên dấu câu, chữ số, tên riêng có chữ hoa giữa câu."""
    out = []
    for tok in _TOKEN.findall(text or ""):
        if tok.isalpha():
            if tok.isupper() and len(tok) <= 4:   # viết tắt (ID, UBND) -> giữ nguyên
                out.append(tok)
                continue
            chuyen = am_tiet_rpa_sang_vi(tok)
            out.append(chuyen.capitalize() if tok[0].isupper() else chuyen)
        else:
            out.append(tok)
    return "".join(out)


def co_ve_la_rpa(text: str) -> bool:
    """Đoán xem chuỗi có phải RPA (để không phiên âm 2 lần văn bản đã là chữ Việt)."""
    if re.search(r"[ăâêôơưđàáảãạèéẻẽẹìíỉĩị]", (text or "").lower()):
        return False
    tokens = re.findall(r"[a-z]+", (text or "").lower())
    if not tokens:
        return False
    ket_thanh = sum(1 for t in tokens if len(t) > 1 and t[-1] in CHU_THANH)
    return ket_thanh / len(tokens) >= 0.35


if __name__ == "__main__":
    for cau in [
        "Nyob zoo, kuv xav ua ntawv pov thawj av",
        "Koj mus rau lub chaw ua ntaub ntawv hauv nroog",
        "Nqa koj daim npav ID thiab ntawv yug",
    ]:
        print(f"{cau}\n  -> {rpa_sang_vi(cau)}\n")
