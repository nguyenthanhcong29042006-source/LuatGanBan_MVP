# -*- coding: utf-8 -*-
"""Cổng thông tin trợ lý giọng nói đa ngôn ngữ — Giao diện chuẩn mực, luôn đảm bảo hiện đủ âm thanh."""
from __future__ import annotations

import base64
import hashlib
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from streamlit.components.v1 import html as _html

from core import auth, kb
from core.config import DANH_MUC_THU_TUC
from core.router import dinh_tuyen
from core.simplify import CAU_HOI_MAC_DINH, don_gian_hoa, thanh_van_ban_doc
from core.stt import nghe
from core.translate import dich_sang_mong, dich_sang_viet
from core.tts import phat_tieng_mong, tts_tieng_viet

ss = st.session_state
ss.setdefault("danh_sach_yeu_cau", [])
ss.setdefault("ket_qua", None)
ss.setdefault("cau_noi", "")
ss.setdefault("audio_da_xu_ly", "")
ss.setdefault("la_tieng_mong", True)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        color: #1f2937;
        background: linear-gradient(180deg, #fcfbf7 0%, #f4f0e8 100%);
    }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; max-width: 860px; }
    .village-header {
        background: linear-gradient(135deg, #1b4d3e 0%, #113227 60%, #0d251d 100%);
        color: white; border-radius: 28px; padding: 30px 36px; display: flex;
        align-items: center; justify-content: space-between; margin-bottom: 24px;
        box-shadow: 0 18px 40px -12px rgba(27, 77, 62, 0.4);
    }
    .village-voice-box {
        background: #ffffff; border: 1px solid #e2dbcc; border-radius: 32px;
        padding: 34px; box-shadow: 0 14px 35px -10px rgba(44, 34, 30, 0.07);
        margin-bottom: 24px; text-align: center;
    }
    .village-result-card {
        background: #ffffff; border: 1px solid #e2dbcc; border-radius: 32px;
        padding: 36px; box-shadow: 0 16px 40px -12px rgba(44, 34, 30, 0.08); margin-top: 24px;
    }
    .village-pill {
        display: inline-flex; align-items: center; gap: 6px; background: #fef3c7;
        padding: 8px 16px; border-radius: 14px; font-size: 13px; font-weight: 700;
        color: #92400e; margin-right: 8px; margin-bottom: 8px; border: 1px solid #fde68a;
    }
    .stButton > button {
        border-radius: 16px; font-weight: 700; padding: 0.75rem 1.6rem;
        border: none; background: #b45309; color: white;
    }
    .stButton > button:hover { background: #92400e; }
</style>
""", unsafe_allow_html=True)

if not kb.load_kb():
    st.error("**Kho dữ liệu trống.** Vui lòng khởi tạo cơ sở tri thức dịch vụ công.")
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


_SVG_LOA = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="white">'
            '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05'
            'c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 '
            '5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>')
_SVG_DUNG = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="white">'
             '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>')


def nut_loa(duong_dan, *, nhan: str, tu_phat: bool = False) -> bool:
    if not duong_dan:
        return False
    b64, mime = _audio_b64(str(duong_dan))
    if not b64:
        return False

    tu_phat_js = ("a.play().then(function(){}).catch(function(){"
                  "tt.textContent='Chạm để phát lại âm thanh';});") if tu_phat else ""
    _html(f"""
<div style="display:flex;align-items:center;gap:16px;background:#fef3c7;border:1px solid #fde68a;border-radius:16px;padding:14px 20px;margin:14px 0;">
  <button id="b" style="width:44px;height:44px;border-radius:50%;border:none;background:#b45309;cursor:pointer;display:flex;align-items:center;justify-content:center;"></button>
  <div style="flex-grow:1;">
    <div style="font-size:14px;font-weight:700;color:#92400e;">{nhan}</div>
    <div id="tt" style="font-size:12px;color:#b45309;margin-top:2px;font-weight:600;">Chọn để nghe hệ thống đọc hướng dẫn</div>
  </div>
  <audio id="a" src="data:{mime};base64,{b64}" preload="auto"></audio>
</div>
<script>
(function(){{
  var a=document.getElementById('a'), b=document.getElementById('b'), tt=document.getElementById('tt');
  var LOA=`{_SVG_LOA}`, DUNG=`{_SVG_DUNG}`;
  function ve(dangPhat){{ b.innerHTML = dangPhat ? DUNG : LOA; }}
  ve(false);
  b.onclick=function(){{ if(a.paused){{a.play();}} else {{a.pause();}} }};
  a.onplay =function(){{ ve(true); tt.textContent='Đang phát âm thanh hướng dẫn...'; }};
  a.onpause=function(){{ ve(false); tt.textContent='Đã tạm dừng'; }};
  a.onended=function(){{ ve(false); tt.textContent='Phát lại từ đầu'; }};
  {tu_phat_js}
}})();
</script>
""", height=86)
    return True


def chay_pipeline_truc_tiep(tt: kb.ThuTuc, cau_noi: str = "", *, phat_giong_mong: bool = True) -> dict:
    """Nạp tức thì dữ liệu và ép buộc sinh âm thanh đầy đủ."""
    t0 = time.perf_counter()
    dg = _don_gian_hoa(tt.key, CAU_HOI_MAC_DINH)
    kb_doc = thanh_van_ban_doc(dg)
    
    # Ép tạo sẵn audio tiếng Việt
    audio_v = _tts_vi(kb_doc)
    
    audio_m = ""
    tang_dung = "vi_phonetic"
    if phat_giong_mong:
        try:
            m = _dich_mong(kb_doc)
            rpa_text = m.get("rpa", kb_doc) if isinstance(m, dict) else kb_doc
            audio_path, tang = phat_tieng_mong(rpa_text, key=tt.key)
            if audio_path:
                audio_m = str(audio_path)
                tang_dung = tang
        except Exception:
            pass
            
    # Dự phòng nếu audio_m rỗng thì dùng tạm tiếng Việt
    if not audio_m:
        audio_m = audio_v

    kq: dict = {
        "cau_noi": cau_noi or tt.ten,
        "thoi_gian": {},
        "tuyen": {"_key": tt.key, "can_can_bo": False, "ten_nhom": tt.ten},
        "thu_tuc": tt,
        "don_gian": dg,
        "kich_ban": kb_doc,
        "audio_viet": audio_v,
        "audio_mong": audio_m,
        "tang_tts": tang_dung,
    }

    kq["thoi_gian"]["tong"] = time.perf_counter() - t0
    return kq


def chay_pipeline(cau_noi: str, *, phat_giong_mong: bool = True) -> dict:
    t0 = time.perf_counter()
    kq: dict = {"cau_noi": cau_noi, "thoi_gian": {}}

    try:
        tuyen = _dinh_tuyen(cau_noi)
    except Exception:
        kq["loi"] = "Đường truyền kết nối gặp sự cố. Vui lòng thử lại sau."
        return kq

    kq["tuyen"] = tuyen
    tt = kb.theo_key(tuyen["_key"]) if tuyen["_key"] else None
    kq["thu_tuc"] = tt

    if tuyen.get("can_can_bo") or tt is None:
        return kq

    try:
        dg = _don_gian_hoa(tt.key, CAU_HOI_MAC_DINH)
        kq["don_gian"] = dg
    except Exception:
        kq["loi"] = "Không thể tải thông tin chi tiết thủ tục."
        return kq

    kb_doc = thanh_van_ban_doc(dg)
    kq["kich_ban"] = kb_doc
    
    audio_v = _tts_vi(kb_doc)
    kq["audio_viet"] = audio_v
    
    audio_m = ""
    if phat_giong_mong:
        try:
            m = _dich_mong(kb_doc)
            rpa_text = m.get("rpa", kb_doc) if isinstance(m, dict) else kb_doc
            audio_path, _ = phat_tieng_mong(rpa_text, key=tt.key)
            if audio_path:
                audio_m = str(audio_path)
        except Exception:
            pass
            
    if not audio_m:
        audio_m = audio_v
        
    kq["audio_mong"] = audio_m
    kq["thoi_gian"]["tong"] = time.perf_counter() - t0
    return kq


def xu_ly_cau_noi(van_ban: str) -> None:
    ss.cau_noi = van_ban
    tt_match = None
    for item in kb.danh_sach():
        if item.ten.strip().lower() == van_ban.strip().lower():
            tt_match = item
            break

    if tt_match:
        kq = chay_pipeline_truc_tiep(tt_match, cau_noi=van_ban)
    else:
        kq = chay_pipeline(van_ban)

    kq["la_tieng_mong"] = bool(ss.get("la_tieng_mong", True))
    ss.ket_qua = kq


# Giao diện chính
st.markdown("""
<div class="village-header">
    <div>
        <div style="font-size: 22px; font-weight: 800; color: #ffffff;">CỔNG THÔNG TIN DỊCH VỤ CÔNG TRỰC TUYẾN</div>
        <div style="font-size: 13px; font-weight: 500; color: #d1fae5; margin-top: 4px;">Hệ thống hỗ trợ tra cứu thủ tục hành chính nhanh chóng, chính xác và thuận tiện</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="village-voice-box">
    <div style="font-size: 20px; font-weight: 800; color: #b45309; margin-bottom: 6px;">
        Hệ thống Tra cứu Thủ tục Hành chính Bằng Giọng nói
    </div>
    <div style="font-size: 13px; color: #57534e; font-weight: 500; margin-bottom: 20px;">
        Vui lòng chọn ngôn ngữ tra cứu và sử dụng micro để trình bày nội dung cần hỗ trợ.
    </div>
""", unsafe_allow_html=True)

LUA_CHON = ["🌐 Tiếng Mông (Hmoob)", "🇻🇳 Tiếng Việt"]
ngon_ngu = st.segmented_control("Chọn ngôn ngữ", LUA_CHON, default=LUA_CHON[0], label_visibility="collapsed") or LUA_CHON[0]
la_tieng_mong = "Tiếng Mông" in ngon_ngu
ss.la_tieng_mong = la_tieng_mong

audio_in = st.audio_input("Micro chính", label_visibility="collapsed")
st.markdown("</div>", unsafe_allow_html=True)

if audio_in is not None:
    raw = audio_in.getvalue()
    van_tay = hashlib.sha256(raw).hexdigest()[:16]
    if van_tay != ss.audio_da_xu_ly and len(raw) > 2000:
        ss.audio_da_xu_ly = van_tay
        with st.spinner("Hệ thống đang xử lý âm thanh..."):
            van_ban, _ = nghe(audio_in, tieng_mong=la_tieng_mong)
        if not van_ban:
            st.error("Hệ thống chưa nhận diện rõ âm thanh. Vui lòng ghi âm lại và nói rõ hơn.")
            loa("Hệ thống chưa nhận diện rõ âm thanh. Vui lòng ghi âm lại và nói rõ hơn.", tu_phat=True)
        else:
            if la_tieng_mong:
                dong_vi = [l for l in van_ban.splitlines() if l.startswith("VI:")]
                van_ban = (dong_vi[0][3:].strip() if dong_vi else dich_sang_viet(van_ban))
            st.success(f"Hệ thống đã ghi nhận nội dung: *{van_ban}*")
            xu_ly_cau_noi(van_ban)


def nut_goi_can_bo(kq: dict) -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🤝 GỬI YÊU CẦU HỖ TRỢ ĐẾN CÁN BỘ CHUYÊN MÔN", use_container_width=True):
        tt = kq.get("thu_tuc")
        tuyen = kq.get("tuyen") or {}
        van_de = tt.ten if tt else tuyen.get("ten_nhom", "Yêu cầu tra cứu thủ tục")

        ss.danh_sach_yeu_cau.append({
            "thoi_gian": datetime.now().strftime("%H:%M - %d/%m"),
            "van_de": van_de,
            "chi_tiet": kq.get("cau_noi", ""),
            "trang_thai": "Chờ xử lý",
        })
        st.success("Yêu cầu hỗ trợ đã được gửi thành công. Cán bộ chuyên môn sẽ liên hệ trong thời gian sớm nhất.")


def hien_ket_qua(kq: dict) -> None:
    if kq.get("loi"):
        st.error(kq["loi"])
        nut_goi_can_bo(kq)
        return

    tuyen, tt = kq.get("tuyen", {}), kq.get("thu_tuc")

    if tuyen.get("can_can_bo") or tt is None:
        cau_hoi = tuyen.get("cau_hoi_lam_ro") or "Vui lòng cung cấp thêm thông tin chi tiết để hệ thống xác định chính xác thủ tục cần tra cứu."
        st.warning(f"💡 {cau_hoi}")
        loa(cau_hoi, tu_phat=True)
        nut_goi_can_bo(kq)
        return

    dg = kq["don_gian"]

    st.markdown(f"""
    <div class="village-result-card">
        <div style="font-size: 21px; font-weight: 800; color: #92400e; margin-bottom: 12px;">📋 {tt.ten}</div>
        <div style="font-size: 14px; color: #44403c; line-height: 1.6; margin-bottom: 20px; font-weight: 600;">{dg.get('tom_tat_1_cau','')}</div>
        <div>
            <span class="village-pill">📍 <b>Nơi thực hiện:</b> {dg.get('di_dau', {}).get('noi_don_gian','—')}</span>
            <span class="village-pill">⏱️ <b>Thời gian giải quyết:</b> {dg.get('bao_lau','—')}</span>
            <span class="village-pill">💰 <b>Lệ phí:</b> {dg.get('bao_nhieu_tien','—')}</span>
        </div>
    """, unsafe_allow_html=True)

    bb = [m for m in dg.get("mang_gi", []) if m.get("bat_buoc")]
    if bb:
        st.markdown("<div style='margin-top: 18px; font-size: 15px; font-weight: 800; color: #92400e;'>🎒 Hồ sơ, giấy tờ cần chuẩn bị:</div>", unsafe_allow_html=True)
        for m in bb:
            sl = f" ({m['so_luong']})" if m.get("so_luong") else ""
            st.markdown(f"- {m['ten_don_gian']}{sl}")

    st.markdown("</div>", unsafe_allow_html=True)

    # Hiển thị nút nghe Tiếng Mông và Tiếng Việt đảm bảo luôn có đường dẫn audio
    uu_tien_mong = bool(kq.get("la_tieng_mong", True)) and bool(kq.get("audio_mong"))
    if kq.get("audio_mong"):
        nut_loa(kq["audio_mong"], nhan="🔊 Nghe hướng dẫn bằng Tiếng Mông (Hmoob)", tu_phat=uu_tien_mong)

    if kq.get("audio_viet"):
        nut_loa(kq["audio_viet"], nhan="🔊 Nghe hướng dẫn bằng Tiếng Việt", tu_phat=not uu_tien_mong)

    nut_goi_can_bo(kq)


if ss.ket_qua:
    hien_ket_qua(ss.ket_qua)

st.markdown("<br>", unsafe_allow_html=True)
with st.expander("⌨️ Tra cứu thủ công: Nhập văn bản hoặc chọn từ danh mục"):
    t_go, t_chon = st.tabs(["Nhập văn bản trực tiếp", "Chọn từ danh mục thủ tục"])
    with t_go:
        txt = st.text_input("Nhập nội dung cần tìm:", label_visibility="collapsed", placeholder="Ví dụ: Đăng ký kết hôn cần giấy tờ gì...")
        if st.button("Tra cứu ngay", type="primary") and txt.strip():
            xu_ly_cau_noi(txt.strip())
            st.rerun()
    with t_chon:
        nhom_chon = st.selectbox("Chọn lĩnh vực:", list(DANH_MUC_THU_TUC.keys()), format_func=lambda k: DANH_MUC_THU_TUC[k])
        ds = kb.theo_nhom(nhom_chon)
        if ds:
            tt_chon = st.selectbox("Chọn thủ tục:", ds, format_func=lambda t: t.ten)
            if st.button("Xem chi tiết thủ tục", type="primary"):
                ss.cau_noi = tt_chon.ten
                kq = chay_pipeline_truc_tiep(tt_chon)
                kq["la_tieng_mong"] = bool(ss.get("la_tieng_mong", True))
                ss.ket_qua = kq
                st.rerun()

if auth.nguoi_dang_nhap():
    with st.sidebar:
        st.divider()
        st.markdown("### Cán bộ quản lý")
        tk = kb.thong_ke()
        st.metric("Tổng thủ tục", tk["so_thu_tuc"])
        if ss.danh_sach_yeu_cau:
            st.markdown("### Danh sách yêu cầu hỗ trợ")
            for p in ss.danh_sach_yeu_cau[-3:]:
                st.caption(f"{p['thoi_gian']} — {p['van_de']}")
