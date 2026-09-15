# -*- coding: utf-8 -*-
"""Đơn giản hóa thủ tục hành chính — Chế độ siêu tốc Tức thì (Instant Response)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from core.config import CACHE_SIMPLIFIED
from core.kb import ThuTuc

CAU_HOI_MAC_DINH = "Hướng dẫn thủ tục này cho bà con dân bản"

def boc_tach_nhanh_python(tt: ThuTuc) -> dict:
    """Rút thông tin siêu tốc (0.01s) trực tiếp từ dữ liệu thủ tục."""
    raw_text = tt.text() or ""
    
    noi_thuc_hien = f"Bộ phận một cửa UBND {tt.cap_thuc_hien if tt.cap_thuc_hien else 'cấp xã'}"
    if "Trung tâm phục vụ hành chính công" in raw_text:
        noi_thuc_hien = "Trung tâm phục vụ hành chính công"

    bao_lau = "Từ 1 đến 5 ngày làm việc"
    m_time = re.search(r"(thời gian|thời hạn|giải quyết)[^\n:]*[:\s]+([^\n.]+)", raw_text, re.IGNORECASE)
    if m_time:
        bao_lau = m_time.group(2).strip()[:40]

    bao_nhieu_tien = "Miễn phí (hoặc theo quy định)"
    m_fee = re.search(r"(lệ phí|phí)[^\n:]*[:\s]+([^\n.]+)", raw_text, re.IGNORECASE)
    if m_fee:
        bao_nhieu_tien = m_fee.group(2).strip()[:40]

    giay_to = []
    for line in raw_text.splitlines():
        line_str = line.strip()
        if any(k in line_str.lower() for k in ["tờ khai", "đơn", "giấy khai sinh", "căn cước", "hộ chiếu", "xác nhận"]):
            if 5 < len(line_str) < 90:
                giay_to.append({
                    "ten_don_gian": line_str.strip("- *•1234567890."),
                    "so_luong": "1 bản chính",
                    "bat_buoc": True
                })
    
    if not giay_to:
        giay_to = [
            {"ten_don_gian": "Giấy tờ tùy thân (Căn cước công dân / Hộ chiếu)", "so_luong": "1 bản chính", "bat_buoc": True},
            {"ten_don_gian": "Tờ khai theo mẫu quy định", "so_luong": "1 bản chính", "bat_buoc": True}
        ]

    return {
        "tom_tat_1_cau": f"Bà con xin thực hiện {tt.ten.lower()}.",
        "di_dau": {"noi_don_gian": noi_thuc_hien},
        "mang_gi": giay_to[:5],
        "bao_lau": bao_lau,
        "bao_nhieu_tien": bao_nhieu_tien,
        "kich_ban_doc": f"Bà con đến {noi_thuc_hien} để làm {tt.ten}. Thời gian giải quyết {bao_lau}, lệ phí {bao_nhieu_tien}."
    }

def don_gian_hoa(tt: ThuTuc, cau_hoi: str = CAU_HOI_MAC_DINH, *, dung_cache: bool = True) -> dict:
    """Trả về kết quả tức thì không chờ đợi."""
    cf = CACHE_SIMPLIFIED / f"{tt.key}.json"
    if dung_cache and cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass

    data = boc_tach_nhanh_python(tt)
    data["_key"] = tt.key
    try:
        cf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return data

def thanh_van_ban_doc(dg: dict) -> str:
    return dg.get("kich_ban_doc", "Bà con đến UBND xã để được hướng dẫn trực tiếp.")
