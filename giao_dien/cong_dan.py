# -*- coding: utf-8 -*-
"""Cổng thông tin bản làng — Trợ lý giọng nói tiếng Mông & Tiếng Việt (Bản chuẩn bản sắc vùng cao)."""
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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #1e293b;
        background-color: #f8fafc;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 6rem;
        max-width: 860px;
    }

    /* Banner mang đậm bản sắc vùng cao, ấm áp tình làng nghĩa xóm */
    .village-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%);
        color: white;
        padding: 28px 20px;
        border-radius: 24px;
        text-align: center;
        margin-bottom: 24px;
        box-shadow: 0 12px 30px -5px rgba(30, 58, 138, 0.25);
        border: 2px solid #3b82f6;
    }
    .village-badge {
        display: inline-block;
        background: #f59e0b;
        color: #ffffff;
        font-weight: 800;
        font-size: 11px;
        padding: 5px 16px;
        border-radius: 20px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
    }
    .village-title {
        font-size: 26px;
        font-weight: 800;
        margin-bottom: 6px;
        letter-spacing: -0.3px;
    }
    .village-desc {
        font-size: 14px;
        color: #cbd5e1;
        font-weight: 500;
    }

    /* Khối trung tâm micro đặt giữa màn hình, trực quan và ấn tượng */
    .central-voice-box {
        background: #ffffff;
        border: 3px solid #f59e0b;
        border-radius: 32px;
        padding: 36px 28px;
        box-shadow: 0 20px 50px rgba(245, 158, 11, 0.2);
        margin-bottom: 28px;
        text-align: center;
        position: relative;
    }

    .result-box {
        background: #ffffff;
        border: 2px solid #cbd5e1;
        border-radius: 24px;
        padding: 32px;
        box-shadow: 0 10px 30px -8px rgba(0,0,0,0.06);
        margin-top: 20px;
    }
    .meta-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #f1f5f9;
        padding: 8px 16px;
        border-radius: 14px;
        font-size: 13px;
        font-weight: 700;
        color: #1e3a8a;
        margin-right: 8px;
        margin-bottom: 8px;
        border: 1px solid #94a3b8;
    }

    .stButton > button {
        border-radius: 14px;
        font-weight: 700;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s ease;
        border: none;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }
</style>
""", unsafe_allow_html=True)

if not kb.load_kb():
    st.error("**Kho dữ liệu trống.** Hãy khởi tạo dữ liệu hướng dẫn dịch vụ công.")
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
                  "tt.textContent='Chạm để nghe lại âm thanh';});") if tu_phat else ""
    _html(f"""
<div style="display:flex;align-items:center;gap:14px;background:#ffffff;border:2px solid #2563eb;border-radius:18px;padding:14px 20px;margin:12px 0;box-shadow:0 4px 15px rgba(37,99,235,0.12);">
  <button id="b" aria-label="Nghe" style="
      width:48px;height:48px;min-width:48px;border-radius:50%;border:none;
      background:linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);cursor:pointer;display:flex;align-items:center;
      justify-content:center;box-shadow:0 4px 12px rgba(37,99,235,0.35);
      transition:all 0.2s;"></button>
  <div style="flex-grow:1;">
    <div style="font-size:15px;font-weight:700;color:#1e3a8a;">{nhan}</div>
    <div id="tt" style="font-size:12px;color:#475569;margin-top:2px;font-weight:500;">Chạm vào nút xanh để nghe hướng dẫn</div>
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
  b.onmousedown=function(){{ b.style.transform='scale(0.94)'; }};
  b.onmouseup=function(){{ b.style.transform='scale(1)'; }};
  a.onplay =function(){{ ve(true);  tt.textContent='Đang phát âm thanh cho bà con...'; }};
  a.onpause=function(){{ ve(false); tt.textContent='Đã tạm dừng'; }};
  a.onended=function(){{ ve(false); tt.textContent='Nghe lại từ đầu'; }};
  {tu_phat_js}
}})();
</script>
""", height=86)
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

    with st.status("Cán bộ số đang tìm kiếm theo lời dặn của bà con...", expanded=False) as box:
        try:
            tuyen = _dinh_tuyen(cau_noi)
        except Exception:
            kq["loi"] = "Hệ thống bận một chút, bà con bấm nói lại giúp mình nhé."
            box.update(label="Lỗi kết nối", state="error", expanded=False)
            return kq

        kq["tuyen"] = tuyen
        tt = kb.theo_key(tuyen["_key"]) if tuyen["_key"] else None
        kq["thu_tuc"] = tt

        if tuyen["can_can_bo"] or tt is None:
            box.update(label="Cần cán bộ xã hỗ trợ trực tiếp", state="complete", expanded=False)
            return kq

        try:
            kq["don_gian"] = _don_gian_hoa(tt.key, CAU_HOI_MAC_DINH)
        except Exception:
            kq["loi"] = "Không thể tải chi tiết thủ tục."
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
        box.update(label="Đã tìm thấy thông tin cho bà con", state="complete", expanded=False)
    return kq


def xu_ly_cau_noi(van_ban: str) -> None:
    ss.cau_noi = van_ban
    kq = chay_pipeline(van_ban)
    kq["la_tieng_mong"] = bool(ss.get("la_tieng_mong", True))
    ss.ket_qua = kq


# Tiêu đề trang trang trọng, đậm đà bản sắc
st.markdown("""
<div class="village-header">
    <div class="village-badge">🏛️ Cổng Thông Tin Bản Làng Vùng Cao</div>
    <div class="village-title">Luật Gần Bà Con — Nói Là Hiểu, Hỏi Là Biết</div>
    <div class="village-desc">Việc làng, việc nước, giấy tờ thủ tục — Bà con cứ thủ thỉ để hệ thống giúp tận tình!</div>
</div>
""", unsafe_allow_html=True)

# KHỐI TRUNG TÂM TUYỆT ĐỐI: MICRO ĐẶT Ở GIỮA, RÕ RÀNG VÀ GẦN GŨI
st.markdown("""
<div class="central-voice-box">
    <div style="font-size: 20px; font-weight: 800; color: #1e3a8a; margin-bottom: 6px;">
        🎙️ BÀ CON MUỐN LÀM GIẤY TỜ GÌ, CỨ BẤM MICRO RỒI NÓI NHÉ!
    </div>
    <div style="font-size: 13px; color: #64748b; margin-bottom: 22px; font-weight: 500;">
        Hệ thống luôn lắng nghe bằng cả tiếng Mông và tiếng Việt để phục vụ bà con
    </div>
""", unsafe_allow_html=True)

# Sắp xếp bố cục cân đối bên trong khối trung tâm
col_lang, col_mic = st.columns([1, 1.3], gap="large")

with col_lang:
    st.markdown("<div style='font-size:13px; font-weight:700; color:#1e3a8a; margin-bottom:8px; text-align:left;'>🌐 Chọn tiếng để nói chuyện:</div>", unsafe_allow_html=True)
    LUA_CHON = ["🌐 Tiếng Mông (Hmoob) [Mặc định]", "🇻🇳 Tiếng Việt"]
    ngon_ngu = st.segmented_control(
        "Chọn ngôn ngữ", LUA_CHON,
        default=LUA_CHON[0], label_visibility="collapsed"
    ) or LUA_CHON[0]
    la_tieng_mong = "Tiếng Mông" in ngon_ngu
    ss.la_tieng_mong = la_tieng_mong

with col_mic:
    st.markdown("<div style='font-size:13px; font-weight:700; color:#1e3a8a; margin-bottom:8px; text-align:left;'>🎤 Chạm vào đây để ghi âm giọng nói:</div>", unsafe_allow_html=True)
    audio_in = st.audio_input("Micro chính", label_visibility="collapsed")

st.markdown("</div>", unsafe_allow_html=True)

if audio_in is not None:
    raw = audio_in.getvalue()
    van_tay = hashlib.sha256(raw).hexdigest()[:16]
    if van_tay != ss.audio_da_xu_ly and len(raw) > 2000:
        ss.audio_da_xu_ly = van_tay
        with st.spinner("Đang lắng nghe tiếng lòng của bà con..."):
            van_ban, _ = nghe(audio_in, tieng_mong=la_tieng_mong)
        if not van_ban:
            st.error("Ơ, chưa nghe rõ tiếng của bà con rồi. Bà con bấm nút nói lại to và rõ hơn một chút nhé!")
            loa("Ơ, chưa nghe rõ tiếng của bà con rồi. Bà con bấm nút nói lại to và rõ hơn một chút nhé!", tu_phat=True)
        else:
            if la_tieng_mong:
                dong_vi = [l for l in van_ban.splitlines() if l.startswith("VI:")]
                van_ban = (dong_vi[0][3:].strip() if dong_vi else dich_sang_viet(van_ban))
            st.success(f"Hệ thống đã nghe rõ câu của bà con: *{van_ban}*")
            xu_ly_cau_noi(van_ban)


def nut_goi_can_bo(kq: dict) -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🤝 KẾT NỐI NGAY VỚI CÁN BỘ XÃ ĐỂ ĐƯỢC GIÚP ĐỠ", use_container_width=True):
        tt = kq.get("thu_tuc")
        ss.danh_sach_yeu_cau.append({
            "thoi_gian": datetime.now().strftime("%H:%M - %d/%m"),
            "van_de": tt.ten if tt else kq["tuyen"]["ten_nhom"],
            "chi_tiet": kq["cau_noi"],
            "trang_thai": "Chờ xử lý",
        })
        st.success("Đã gửi gắm thành công! Cán bộ xã sẽ liên hệ trực tiếp hỗ trợ bà con ngay nhà nhé.")


def hien_ket_qua(kq: dict) -> None:
    if kq.get("loi"):
        st.error(kq["loi"])
        nut_goi_can_bo(kq)
        return

    tuyen, tt = kq["tuyen"], kq.get("thu_tuc")

    if tuyen["can_can_bo"] or tt is None:
        cau_hoi = tuyen.get("cau_hoi_lam_ro") or "Bà con nói cụ thể hơn giúp mình xem cần làm thủ tục gì ở xã nhé."
        st.warning(f"💡 {cau_hoi}")
        loa(cau_hoi, tu_phat=True)
        nut_goi_can_bo(kq)
        return

    dg = kq["don_gian"]
    
    st.markdown(f"""
    <div class="result-box">
        <div style="font-size: 22px; font-weight: 800; color: #1e3a8a; margin-bottom: 12px; letter-spacing: -0.3px;">
            📋 {tt.ten}
        </div>
        <div style="font-size: 16px; color: #334155; line-height: 1.7; margin-bottom: 20px; font-weight: 600;">
            {dg.get('tom_tat_1_cau','')}
        </div>
        <div>
            <span class="meta-tag">📍 <b>Đến làm tại:</b> {dg.get('di_dau', {}).get('noi_don_gian','—')}</span>
            <span class="meta-tag">⏱️ <b>Thời gian:</b> {dg.get('bao_lau','—')}</span>
            <span class="meta-tag">💰 <b>Lệ phí:</b> {dg.get('bao_nhieu_tien','—')}</span>
        </div>
    """, unsafe_allow_html=True)

    bb = [m for m in dg.get("mang_gi", []) if m.get("bat_buoc")]
    if bb:
        st.markdown("**🎒 Những giấy tờ quan trọng bà con tuyệt đối phải mang theo:**")
        for m in bb:
            sl = f" ({m['so_luong']})" if m.get("so_luong") else ""
            st.markdown(f"- {m['ten_don_gian']}{sl}")

    st.markdown("</div>", unsafe_allow_html=True)

    uu_tien_mong = bool(kq.get("la_tieng_mong", True)) and bool(kq.get("audio_mong"))
    if kq.get("audio_mong"):
        nut_loa(kq["audio_mong"], nhan="🔊 Nghe hướng dẫn chi tiết bằng tiếng Mông (Hmoob)", tu_phat=uu_tien_mong)

    if kq.get("audio_viet"):
        nut_loa(kq["audio_viet"], nhan="🔊 Nghe hướng dẫn chi tiết bằng tiếng Việt", tu_phat=not uu_tien_mong)

    if auth.nguoi_dang_nhap():
        with st.expander("⚙️ Thông số hệ thống chuyên sâu (Cán bộ xã xem)"):
            st.metric("Độ tin cậy xử lý", f"{dg.get('do_tin_cay', 0):.0%}")
            st.caption(f"Mã thủ tục: {tt.ma_thu_tuc}")

    nut_goi_can_bo(kq)


if ss.ket_qua:
    hien_ket_qua(ss.ket_qua)

st.markdown("<br>", unsafe_allow_html=True)
with st.expander("⌨️ Bàn phím phụ: Gõ chữ hoặc chọn từ danh mục (Dành cho con cháu trợ giúp ông bà)"):
    t_go, t_chon = st.tabs(["Gõ câu hỏi trực tiếp", "Chọn từ danh mục thủ tục"])
    with t_go:
        txt = st.text_input("Nhập nội dung cần tìm:", label_visibility="collapsed", placeholder="Ví dụ: Đăng ký kết hôn cần giấy tờ gì...")
        if st.button("Tra cứu ngay bằng văn bản", type="primary") and txt.strip():
            xu_ly_cau_noi(txt.strip())
            st.rerun()
    with t_chon:
        nhom_chon = st.selectbox("Chọn lĩnh vực hành chính:", list(DANH_MUC_THU_TUC.keys()), format_func=lambda k: DANH_MUC_THU_TUC[k])
        ds = kb.theo_nhom(nhom_chon)
        if ds:
            tt_chon = st.selectbox("Chọn thủ tục cụ thể:", ds, format_func=lambda t: t.ten)
            if st.button("Xem hướng dẫn chi tiết từ danh mục", type="primary"):
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
