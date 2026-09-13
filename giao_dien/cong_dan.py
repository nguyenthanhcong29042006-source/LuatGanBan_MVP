# -*- coding: utf-8 -*-
"""Cổng thông tin trợ lý giọng nói đa ngôn ngữ — Giao diện ấm áp, rực rỡ và nổi bật mang sắc màu bản làng."""
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

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #111827;
        background: #fffbf5;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 840px;
    }

    /* Tiêu đề rực rỡ, ấm áp mang sắc màu thổ cẩm và văn hóa vùng cao */
    .vibrant-header {
        background: linear-gradient(135deg, #e11d48 0%, #be123c 50%, #9f1239 100%);
        color: white;
        border-radius: 20px;
        padding: 22px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -6px rgba(225, 29, 72, 0.3);
        border: 2px solid rgba(255, 255, 255, 0.2);
    }

    /* Trạm tương tác giọng nói nổi bật, sinh động */
    .vibrant-voice-box {
        background: #ffffff;
        border: 2px solid #fecdd3;
        border-radius: 24px;
        padding: 24px 28px;
        box-shadow: 0 10px 25px -6px rgba(225, 29, 72, 0.08);
        margin-bottom: 20px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .vibrant-voice-box::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 5px;
        background: linear-gradient(90deg, #e11d48, #f59e0b, #10b981, #3b82f6);
    }

    /* Thẻ kết quả nổi bật, thu hút */
    .vibrant-result-card {
        background: #ffffff;
        border: 2px solid #fbcfe8;
        border-radius: 24px;
        padding: 28px;
        box-shadow: 0 10px 25px -6px rgba(225, 29, 72, 0.08);
        margin-top: 20px;
    }

    .vibrant-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #fff1f2;
        padding: 8px 14px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 700;
        color: #be123c;
        margin-right: 8px;
        margin-bottom: 8px;
        border: 1px solid #fecdd3;
    }

    .stButton > button {
        border-radius: 14px;
        font-weight: 700;
        padding: 0.6rem 1.4rem;
        transition: all 0.2s ease;
        border: none;
        background: #e11d48;
        color: white;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(225, 29, 72, 0.35);
        background: #be123c;
    }
</style>
""", unsafe_allow_html=True)

if not kb.load_kb():
    st.error("**Kho dữ liệu trống.** Hãy khởi tạo cơ sở tri thức dịch vụ công.")
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
                  "tt.textContent='Chạm để nghe lại';});") if tu_phat else ""
    _html(f"""
<div style="display:flex;align-items:center;gap:14px;background:#fff1f2;border:1px solid #fecdd3;border-radius:14px;padding:12px 18px;margin:12px 0;">
  <button id="b" aria-label="Nghe" style="
      width:42px;height:42px;min-width:42px;border-radius:50%;border:none;
      background:#e11d48;cursor:pointer;display:flex;align-items:center;
      justify-content:center;box-shadow:0 4px 12px rgba(225,29,72,0.3);
      transition:all 0.2s;"></button>
  <div style="flex-grow:1;">
    <div style="font-size:14px;font-weight:700;color:#be123c;">{nhan}</div>
    <div id="tt" style="font-size:11px;color:#9f1239;margin-top:2px;font-weight:600;">Chạm để nghe tiếng nói hướng dẫn</div>
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
  a.onplay =function(){{ ve(true);  tt.textContent='Đang phát âm thanh...'; }};
  a.onpause=function(){{ ve(false); tt.textContent='Đã tạm dừng phát'; }};
  a.onended=function(){{ ve(false); tt.textContent='Phát lại từ đầu'; }};
  {tu_phat_js}
}})();
</script>
""", height=78)
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

    with st.status("Đang xem xét yêu cầu của bà con...", expanded=False) as box:
        try:
            tuyen = _dinh_tuyen(cau_noi)
        except Exception:
            kq["loi"] = "Hệ thống đang bận, bà con vui lòng thử lại sau giây lát nhé."
            box.update(label="Lỗi kết nối", state="error", expanded=False)
            return kq

        kq["tuyen"] = tuyen
        tt = kb.theo_key(tuyen["_key"]) if tuyen["_key"] else None
        kq["thu_tuc"] = tt

        if tuyen["can_can_bo"] or tt is None:
            box.update(label="Cần cán bộ bản hỗ trợ trực tiếp", state="complete", expanded=False)
            return kq

        try:
            kq["don_gian"] = _don_gian_hoa(tt.key, CAU_HOI_MAC_DINH)
        except Exception:
            kq["loi"] = "Không thể tải chi tiết thủ tục."
            box.update(label="Lỗi dữ liệu", state="error", expanded=False)
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
        box.update(label="Đã tìm thấy thông tin thủ tục", state="complete", expanded=False)
    return kq


def xu_ly_cau_noi(van_ban: str) -> None:
    ss.cau_noi = van_ban
    kq = chay_pipeline(van_ban)
    kq["la_tieng_mong"] = bool(ss.get("la_tieng_mong", True))
    ss.ket_qua = kq


# Tiêu đề rực rỡ, ấm cúng, nổi bật
st.markdown("""
<div class="vibrant-header">
    <div>
        <div style="font-size: 19px; font-weight: 800; letter-spacing: -0.3px; color: #ffffff;">TRỢ LÝ BẢN LÀNG — DỊCH VỤ CÔNG</div>
        <div style="font-size: 13px; font-weight: 500; color: #ffe4e6; margin-top: 2px;">Đồng hành cùng bà con giải quyết thủ tục nhanh chóng, dễ hiểu</div>
    </div>
    <div style="background: rgba(255, 255, 255, 0.2); backdrop-filter: blur(10px); padding: 6px 12px; border-radius: 10px; font-size: 11px; font-weight: 700; border: 1px solid rgba(255,255,255,0.3); color: #ffffff; white-space: nowrap;">
        🌸 Thân thiện & Nổi bật
    </div>
</div>
""", unsafe_allow_html=True)

# Trạm tương tác giọng nói nổi bật
st.markdown("""
<div class="vibrant-voice-box">
    <div style="font-size: 18px; font-weight: 800; color: #be123c; margin-bottom: 4px; letter-spacing: -0.2px;">
        🎙️ Trò Chuyện Cùng Trợ Lý Bản Làng
    </div>
    <div style="font-size: 13px; color: #4b5563; font-weight: 500; margin-bottom: 16px;">
        Bà con hãy chọn tiếng nói quen thuộc, sau đó bấm vào nút Micro để nói việc cần làm nhé
    </div>
""", unsafe_allow_html=True)

LUA_CHON = ["🌐 Tiếng Mông (Hmoob)", "🇻🇳 Tiếng Việt"]
ngon_ngu = st.segmented_control(
    "Chọn ngôn ngữ", LUA_CHON,
    default=LUA_CHON[0], label_visibility="collapsed"
) or LUA_CHON[0]
la_tieng_mong = "Tiếng Mông" in ngon_ngu
ss.la_tieng_mong = la_tieng_mong

audio_in = st.audio_input("Micro chính", label_visibility="collapsed")

st.markdown("</div>", unsafe_allow_html=True)

if audio_in is not None:
    raw = audio_in.getvalue()
    van_tay = hashlib.sha256(raw).hexdigest()[:16]
    if van_tay != ss.audio_da_xu_ly and len(raw) > 2000:
        ss.audio_da_xu_ly = van_tay
        with st.spinner("Đang nghe bà con nói..."):
            van_ban, _ = nghe(audio_in, tieng_mong=la_tieng_mong)
        if not van_ban:
            st.error("Trợ lý chưa nghe rõ lắm. Bà con bấm lại và nói to rõ hơn một chút nhé!")
            loa("Trợ lý chưa nghe rõ lắm. Bà con bấm lại và nói to rõ hơn một chút nhé!", tu_phat=True)
        else:
            if la_tieng_mong:
                dong_vi = [l for l in van_ban.splitlines() if l.startswith("VI:")]
                van_ban = (dong_vi[0][3:].strip() if dong_vi else dich_sang_viet(van_ban))
            st.success(f"Trợ lý đã nghe được: *{van_ban}*")
            xu_ly_cau_noi(van_ban)


def nut_goi_can_bo(kq: dict) -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🤝 GỌI CÁN BỘ ĐẾN HƯỚNG DẪN TRỰC TIẾP", use_container_width=True):
        tt = kq.get("thu_tuc")
        ss.danh_sach_yeu_cau.append({
            "thoi_gian": datetime.now().strftime("%H:%M - %d/%m"),
            "van_de": tt.ten if tt else kq["tuyen"]["ten_nhom"],
            "chi_tiet": kq["cau_noi"],
            "trang_thai": "Chờ xử lý",
        })
        st.success("Đã gửi lời nhắn thành công! Cán bộ xã sẽ sớm liên hệ giúp đỡ bà con.")


def hien_ket_qua(kq: dict) -> None:
    if kq.get("loi"):
        st.error(kq["loi"])
        nut_goi_can_bo(kq)
        return

    tuyen, tt = kq["tuyen"], kq.get("thu_tuc")

    if tuyen["can_can_bo"] or tt is None:
        cau_hoi = tuyen.get("cau_hoi_lam_ro") or "Bà con cho trợ lý hỏi thêm chi tiết để tìm đúng việc cần làm nhé."
        st.warning(f"💡 {cau_hoi}")
        loa(cau_hoi, tu_phat=True)
        nut_goi_can_bo(kq)
        return

    dg = kq["don_gian"]
    
    st.markdown(f"""
    <div class="vibrant-result-card">
        <div style="font-size: 20px; font-weight: 800; color: #be123c; margin-bottom: 10px; letter-spacing: -0.2px;">
            📋 {tt.ten}
        </div>
        <div style="font-size: 14px; color: #374151; line-height: 1.6; margin-bottom: 18px; font-weight: 600;">
            {dg.get('tom_tat_1_cau','')}
        </div>
        <div>
            <span class="vibrant-pill">📍 <b>Nơi làm:</b> {dg.get('di_dau', {}).get('noi_don_gian','—')}</span>
            <span class="vibrant-pill">⏱️ <b>Thời gian:</b> {dg.get('bao_lau','—')}</span>
            <span class="vibrant-pill">💰 <b>Lệ phí:</b> {dg.get('bao_nhieu_tien','—')}</span>
        </div>
    """, unsafe_allow_html=True)

    bb = [m for m in dg.get("mang_gi", []) if m.get("bat_buoc")]
    if bb:
        st.markdown("<div style='margin-top: 16px; font-size: 15px; font-weight: 800; color: #be123c;'>🎒 Giấy tờ bà con cần chuẩn bị mang theo:</div>", unsafe_allow_html=True)
        for m in bb:
            sl = f" ({m['so_luong']})" if m.get("so_luong") else ""
            st.markdown(f"- {m['ten_don_gian']}{sl}")

    st.markdown("</div>", unsafe_allow_html=True)

    uu_tien_mong = bool(kq.get("la_tieng_mong", True)) and bool(kq.get("audio_mong"))
    if kq.get("audio_mong"):
        nut_loa(kq["audio_mong"], nhan="🔊 Nghe hướng dẫn bằng Tiếng Mông (Hmoob)", tu_phat=uu_tien_mong)

    if kq.get("audio_viet"):
        nut_loa(kq["audio_viet"], nhan="🔊 Nghe hướng dẫn bằng Tiếng Việt", tu_phat=not uu_tien_mong)

    nut_goi_can_bo(kq)


if ss.ket_qua:
    hien_ket_qua(ss.ket_qua)

st.markdown("<br>", unsafe_allow_html=True)
with st.expander("⌨️ Bàn phím phụ: Tự gõ chữ hoặc chọn nhanh thủ tục"):
    t_go, t_chon = st.tabs(["Gõ chữ trực tiếp", "Chọn từ danh mục"])
    with t_go:
        txt = st.text_input("Nhập việc cần tìm:", label_visibility="collapsed", placeholder="Ví dụ: Đăng ký kết hôn cần giấy tờ gì...")
        if st.button("Tìm ngay", type="primary") and txt.strip():
            xu_ly_cau_noi(txt.strip())
            st.rerun()
    with t_chon:
        nhom_chon = st.selectbox("Chọn lĩnh vực:", list(DANH_MUC_THU_TUC.keys()), format_func=lambda k: DANH_MUC_THU_TUC[k])
        ds = kb.theo_nhom(nhom_chon)
        if ds:
            tt_chon = st.selectbox("Chọn thủ tục:", ds, format_func=lambda t: t.ten)
            if st.button("Xem thủ tục này", type="primary"):
                xu_ly_cau_noi(tt_chon.ten)
                st.rerun()

if auth.nguoi_dang_nhap():
    with st.sidebar:
        st.divider()
        st.markdown("### Cán bộ quản lý")
        tk = kb.thong_ke()
        st.metric("Tổng thủ tục", tk["so_thu_tuc"])
        if ss.danh_sach_yeu_cau:
            st.markdown("### Yêu cầu mới của bà con")
            for p in ss.danh_sach_yeu_cau[-3:]:
                st.caption(f"{p['thoi_gian']} — {p['van_de']}")
