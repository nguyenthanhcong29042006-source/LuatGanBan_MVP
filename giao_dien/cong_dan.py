# -*- coding: utf-8 -*-
"""Cổng người dân — hỏi đáp thủ tục bằng giọng nói (Chuẩn thiết kế cao cấp, sáng sủa, không rối mắt)."""
from __future__ import annotations

import base64
import hashlib
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from streamlit.components.v1 import html as _html

from core import auth, kb
from core.config import (DANH_MUC_THU_TUC, HMONG_ORTHOGRAPHY, NGUONG_TU_TIN,
                         TTS_HMONG_PROVIDER)
from core.llm import LoiQuota
from core.router import dinh_tuyen
from core.simplify import CAU_HOI_MAC_DINH, don_gian_hoa, thanh_van_ban_doc
from core.stt import nghe
from core.translate import dich_sang_mong, dich_sang_viet
from core.tts import NHAN_TANG, phat_tieng_mong, tts_tieng_viet

ss = st.session_state
ss.setdefault("danh_sach_yeu_cau", [])
ss.setdefault("ket_qua", None)
ss.setdefault("cau_noi", "")
ss.setdefault("audio_da_xu_ly", "")

# Cấu hình trang tối giản, tinh tế, nền sáng sạch sẽ, bố cục không gian mở
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #0f172a;
        background-color: #f8fafc;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 1000px;
    }

    /* Thanh điều hướng tối giản phía trên */
    .nav-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        margin-bottom: 32px;
        box-shadow: 0 4px 20px -4px rgba(0,0,0,0.03);
    }
    .nav-brand {
        font-weight: 800;
        font-size: 18px;
        color: #0f172a;
        letter-spacing: -0.5px;
    }
    .nav-badge {
        font-size: 13px;
        font-weight: 600;
        color: #4f46e5;
        background: #eef2ff;
        padding: 6px 14px;
        border-radius: 20px;
    }

    /* Khối Hero hai cột tinh tế, thoáng đãng, không rối mắt */
    .hero-container {
        display: grid;
        grid-template-columns: 1.2fr 1fr;
        gap: 24px;
        align-items: center;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 28px;
        padding: 40px;
        box-shadow: 0 10px 40px -10px rgba(0,0,0,0.04);
        margin-bottom: 32px;
    }
    .hero-title {
        font-size: 32px;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.25;
        letter-spacing: -0.8px;
        margin-bottom: 16px;
    }
    .hero-subtitle {
        font-size: 16px;
        color: #64748b;
        line-height: 1.6;
        font-weight: 400;
        margin-bottom: 24px;
    }

    /* Thẻ tương tác nổi bật bên phải */
    .interactive-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #cbd5e1;
        border-radius: 20px;
        padding: 28px;
        text-align: center;
    }

    /* Thẻ kết quả thông minh, mạch lạc */
    .result-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 24px;
        padding: 36px;
        box-shadow: 0 12px 35px -10px rgba(0,0,0,0.05);
        margin: 28px 0;
    }
    .chip-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #f1f5f9;
        padding: 8px 16px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 600;
        color: #334155;
        margin-right: 10px;
        margin-bottom: 10px;
        border: 1px solid #e2e8f0;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        padding: 0.7rem 1.5rem;
        transition: all 0.2s ease;
        border: none;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    }
</style>

<div class="nav-bar">
    <div class="nav-brand">🏛️ LUẬT GẦN BÀ CON</div>
    <div class="nav-badge">Trợ lý hành chính giọng nói thế hệ mới</div>
</div>
""", unsafe_allow_html=True)

if not kb.load_kb():
    st.error(
        "**Kho dữ liệu trống.** Hãy chạy lệnh: `python tools/extract_tthc.py` "
        "để khởi tạo dữ liệu hướng dẫn dịch vụ công."
    )
    st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def _dinh_tuyen(cau_noi: str) -> dict:
    r = dinh_tuyen(cau_noi)
    r["_key"] = r["thu_tuc"].key if r["thu_tuc"] else ""
    r.pop("thu_tuc", None)
    return r


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _don_gian_hoa(key: str, cau_hoi: str) -> dict:
    return don_gian_hoa(kb.theo_key(key), cau_hoi)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _dich_mong(text: str) -> dict:
    return dich_sang_mong(text)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _tts_vi(text: str) -> str:
    try:
        p = tts_tieng_viet(text)
        return str(p) if p else ""
    except Exception:
        return ""


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _audio_b64(duong_dan: str) -> tuple[str, str]:
    p = Path(duong_dan)
    if not p.exists():
        return "", ""
    mime = "audio/mpeg" if p.suffix.lower() == ".mp3" else "audio/wav"
    return base64.b64encode(p.read_bytes()).decode(), mime


_SVG_LOA = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="white">'
            '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05'
            'c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 '
            '5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>')
_SVG_DUNG = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="white">'
             '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>')


def nut_loa(duong_dan, *, nhan: str, tu_phat: bool = False) -> bool:
    if not duong_dan:
        return False
    b64, mime = _audio_b64(str(duong_dan))
    if not b64:
        return False

    tu_phat_js = ("a.play().then(function(){}).catch(function(){"
                  "tt.textContent='Bấm để nghe âm thanh';});") if tu_phat else ""
    _html(f"""
<div style="display:flex;align-items:center;gap:16px;background:#ffffff;border:1px solid #cbd5e1;border-radius:16px;padding:14px 20px;margin:12px 0;box-shadow:0 2px 10px rgba(0,0,0,0.02);">
  <button id="b" aria-label="Nghe" style="
      width:46px;height:46px;min-width:46px;border-radius:50%;border:none;
      background:#4f46e5;cursor:pointer;display:flex;align-items:center;
      justify-content:center;box-shadow:0 4px 12px rgba(79,70,229,0.3);
      transition:all 0.2s;"></button>
  <div style="flex-grow:1;">
    <div style="font-size:15px;font-weight:700;color:#0f172a;">{nhan}</div>
    <div id="tt" style="font-size:13px;color:#64748b;margin-top:2px;">Sẵn sàng phát âm thanh</div>
  </div>
  <audio id="a" src="data:{mime};base64,{b64}" preload="auto"></audio>
</div>
<script>
(function(){{
  var a=document.getElementById('a'), b=document.getElementById('b'),
      tt=document.getElementById('tt');
  var LOA=`{_SVG_LOA}`, DUNG=`{_SVG_DUNG}`;
  function ve(dangPhat){{ b.innerHTML = dangPhat ? DUNG : LOA; }}
  ve(false);
  b.onclick=function(){{ if(a.paused){{a.play();}} else {{a.pause();}} }};
  b.onmousedown=function(){{ b.style.transform='scale(0.95)'; }};
  b.onmouseup=function(){{ b.style.transform='scale(1)'; }};
  a.onplay =function(){{ ve(true);  tt.textContent='Đang phát âm thanh...'; }};
  a.onpause=function(){{ ve(false); tt.textContent='Đã tạm dừng'; }};
  a.onended=function(){{ ve(false); tt.textContent='Nghe lại từ đầu'; }};
  {tu_phat_js}
}})();
</script>
""", height=82)
    return True


def loa(text: str, *, nhan: str = "Nghe", tu_phat: bool = False) -> None:
    if not (text or "").strip():
        return
    p = _tts_vi(text)
    if p:
        nut_loa(p, nhan=nhan, tu_phat=tu_phat)


def chay_pipeline(cau_noi: str, *, phat_giong_mong: bool = True) -> dict:
    t0 = time.perf_counter()
    kq: dict = {"cau_noi": cau_noi, "thoi_gian": {}}

    with st.status("Hệ thống đang phân tích yêu cầu...", expanded=False) as box:
        try:
            tuyen = _dinh_tuyen(cau_noi)
        except Exception as e:
            kq["loi"] = "Hệ thống đang bận, vui lòng thử lại sau."
            box.update(label="Lỗi kết nối", state="error", expanded=False)
            return kq

        kq["tuyen"] = tuyen
        tt = kb.theo_key(tuyen["_key"]) if tuyen["_key"] else None
        kq["thu_tuc"] = tt

        if tuyen["can_can_bo"] or tt is None:
            box.update(label="Cần hỗ trợ từ chuyên viên", state="complete", expanded=False)
            return kq

        try:
            kq["don_gian"] = _don_gian_hoa(tt.key, CAU_HOI_MAC_DINH)
        except Exception as e:
            kq["loi"] = "Không thể tải nội dung chi tiết."
            box.update(label="Lỗi xử lý", state="error", expanded=False)
            return kq

        kq["kich_ban"] = thanh_van_ban_doc(kq["don_gian"])
        kq["audio_viet"] = _tts_vi(kq["kich_ban"])

        if phat_giong_mong:
            try:
                kq["mong"] = _dich_mong(kq["kich_ban"])
                audio, tang = phat_tieng_mong(kq["mong"]["rpa"], key=tt.key)
                kq["audio_mong"] = str(audio) if audio else ""
                kq["tang_tts"] = tang
            except Exception:
                kq["canh_bao"] = "Sử dụng âm thanh dự phòng."

        kq["thoi_gian"]["tong"] = time.perf_counter() - t0
        box.update(label="Tra cứu thành công", state="complete", expanded=False)
    return kq


def xu_ly_cau_noi(van_ban: str) -> None:
    ss.cau_noi = van_ban
    kq = chay_pipeline(van_ban)
    kq["la_tieng_mong"] = bool(ss.get("la_tieng_mong", True))
    ss.ket_qua = kq


# Bố cục Hero chia 2 cột rõ ràng, không rối mắt, làm nổi bật thông điệp và khu vực micro
col_hero_1, col_hero_2 = st.columns([1.3, 1], gap="large")

with col_hero_1:
    st.markdown("""
    <div style="padding-top: 10px;">
        <div style="font-size: 13px; font-weight: 700; color: #4f46e5; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px;">
            ✨ Giải pháp chuyển đổi số cộng đồng
        </div>
        <div style="font-size: 32px; font-weight: 800; color: #0f172a; line-height: 1.25; letter-spacing: -0.6px; margin-bottom: 14px;">
            Âm Vang Tiếng Núi — Thấu Hiểu Việc Nhà
        </div>
        <div style="font-size: 16px; color: #64748b; line-height: 1.6; font-weight: 400; margin-bottom: 24px;">
            Xóa nhòa mọi khoảng cách ngôn ngữ và địa lý, giúp bà con dễ dàng tra cứu thủ tục hành chính bằng chính giọng nói thân thuộc của mình.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    LUA_CHON = ["🌐 Tiếng Mông (Hmoob)", "🇻🇳 Tiếng Việt"]
    ngon_ngu = st.segmented_control(
        "Chọn ngôn ngữ", LUA_CHON,
        default=LUA_CHON[0], label_visibility="collapsed"
    ) or LUA_CHON[0]
    la_tieng_mong = ngon_ngu.endswith("Hmoob)")
    ss.la_tieng_mong = la_tieng_mong

with col_hero_2:
    st.markdown("""
    <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 20px; padding: 24px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
        <div style="font-size: 15px; font-weight: 700; color: #0f172a; margin-bottom: 12px;">
            🎙️ Bấm để nói yêu cầu của bà con
        </div>
    """, unsafe_allow_html=True)
    
    audio_in = st.audio_input("Micro", label_visibility="collapsed")
    
    st.markdown("</div>", unsafe_allow_html=True)

if audio_in is not None:
    raw = audio_in.getvalue()
    van_tay = hashlib.sha256(raw).hexdigest()[:16]
    if van_tay != ss.audio_da_xu_ly and len(raw) > 2000:
        ss.audio_da_xu_ly = van_tay
        with st.spinner("Đang lắng nghe và nhận diện giọng nói..."):
            van_ban, _ = nghe(audio_in, tieng_mong=la_tieng_mong)
        if not van_ban:
            st.error("Chưa nghe rõ giọng nói, vui lòng bấm và nói lại rõ hơn.")
            loa("Chưa nghe rõ giọng nói, vui lòng bấm và nói lại rõ hơn.", tu_phat=True)
        else:
            if la_tieng_mong:
                dong_vi = [l for l in van_ban.splitlines() if l.startswith("VI:")]
                van_ban = (dong_vi[0][3:].strip() if dong_vi else dich_sang_viet(van_ban))
            st.success(f"Nội dung nhận diện: *{van_ban}*")
            xu_ly_cau_noi(van_ban)


def nut_goi_can_bo(kq: dict) -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🙋 KẾT NỐI TRỰC TIẾP VỚI CÁN BỘ XÃ HỖ TRỢ", use_container_width=True):
        tt = kq.get("thu_tuc")
        ss.danh_sach_yeu_cau.append({
            "thoi_gian": datetime.now().strftime("%H:%M - %d/%m"),
            "van_de": tt.ten if tt else kq["tuyen"]["ten_nhom"],
            "chi_tiet": kq["cau_noi"],
            "trang_thai": "Chờ xử lý",
        })
        st.success("Đã gửi yêu cầu thành công. Cán bộ sẽ liên hệ hỗ trợ bà con ngay.")


def hien_ket_qua(kq: dict) -> None:
    if kq.get("loi"):
        st.error(kq["loi"])
        nut_goi_can_bo(kq)
        return

    tuyen, tt = kq["tuyen"], kq.get("thu_tuc")

    if tuyen["can_can_bo"] or tt is None:
        cau_hoi = tuyen.get("cau_hoi_lam_ro") or "Vui lòng mô tả chi tiết hơn thủ tục bà con muốn thực hiện."
        st.warning(f"💡 {cau_hoi}")
        loa(cau_hoi, tu_phat=True)
        nut_goi_can_bo(kq)
        return

    dg = kq["don_gian"]
    
    st.markdown(f"""
    <div class="result-card">
        <div style="font-size: 22px; font-weight: 800; color: #0f172a; margin-bottom: 14px; letter-spacing: -0.4px;">
            📋 {tt.ten}
        </div>
        <div style="font-size: 16px; color: #334155; line-height: 1.7; margin-bottom: 20px; font-weight: 500;">
            {dg.get('tom_tat_1_cau','')}
        </div>
        <div>
            <span class="chip-tag">📍 <b>Nơi làm:</b> {dg.get('di_dau', {}).get('noi_don_gian','—')}</span>
            <span class="chip-tag">⏱️ <b>Thời gian:</b> {dg.get('bao_lau','—')}</span>
            <span class="chip-tag">💰 <b>Lệ phí:</b> {dg.get('bao_nhieu_tien','—')}</span>
        </div>
    """, unsafe_allow_html=True)

    bb = [m for m in dg.get("mang_gi", []) if m.get("bat_buoc")]
    if bb:
        st.markdown("**🎒 Giấy tờ bắt buộc mang theo:**")
        for m in bb:
            sl = f" ({m['so_luong']})" if m.get("so_luong") else ""
            st.markdown(f"- {m['ten_don_gian']}{sl}")

    st.markdown("</div>", unsafe_allow_html=True)

    uu_tien_mong = bool(kq.get("la_tieng_mong", True)) and bool(kq.get("audio_mong"))
    if kq.get("audio_mong"):
        nut_loa(kq["audio_mong"], nhan="Nghe hướng dẫn bằng tiếng Mông (Hmoob)", tu_phat=uu_tien_mong)

    if kq.get("audio_viet"):
        nut_loa(kq["audio_viet"], nhan="Nghe hướng dẫn bằng tiếng Việt", tu_phat=not uu_tien_mong)

    if auth.nguoi_dang_nhap():
        with st.expander("⚙️ Thông số hệ thống chuyên sâu (Cán bộ xem)"):
            st.metric("Độ tin cậy xử lý", f"{dg.get('do_tin_cay', 0):.0%}")
            st.caption(f"Mã thủ tục: {tt.ma_thu_tuc}")

    nut_goi_can_bo(kq)


if ss.ket_qua:
    st.write("---")
    hien_ket_qua(ss.ket_qua)

# Phần thay thế trực quan được gọn gàng hóa trong expander tinh tế
with st.expander("⌨️ Tùy chọn thay thế: Nhập chữ hoặc chọn danh mục nhanh"):
    t_go, t_chon = st.tabs(["Gõ câu hỏi trực tiếp", "Chọn từ danh sách thủ tục"])
    with t_go:
        txt = st.text_input("Nhập nội dung cần tìm:", label_visibility="collapsed", placeholder="Ví dụ: Đăng ký kết hôn cần giấy tờ gì...")
        if st.button("Tra cứu ngay", type="primary") and txt.strip():
            xu_ly_cau_noi(txt.strip())
            st.rerun()
    with t_chon:
        nhom_chon = st.selectbox("Chọn lĩnh vực hành chính:", list(DANH_MUC_THU_TUC.keys()), format_func=lambda k: DANH_MUC_THU_TUC[k])
        ds = kb.theo_nhom(nhom_chon)
        if ds:
            tt_chon = st.selectbox("Chọn thủ tục cụ thể:", ds, format_func=lambda t: t.ten)
            if st.button("Xem hướng dẫn chi tiết", type="primary"):
                xu_ly_cau_noi(tt_chon.ten)
                st.rerun()

if auth.nguoi_dang_nhap():
    with st.sidebar:
        st.divider()
        st.markdown("### Quản trị viên")
        tk = kb.thong_ke()
        st.metric("Tổng số thủ tục", tk["so_thu_tuc"])
        if ss.danh_sach_yeu_cau:
            st.markdown("### Yêu cầu hỗ trợ mới")
            for p in ss.danh_sach_yeu_cau[-3:]:
                st.caption(f"{p['thoi_gian']} — {p['van_de']}")
