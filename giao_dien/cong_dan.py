# -*- coding: utf-8 -*-
"""Cổng thông tin trợ lý giọng nói đa ngôn ngữ — Giao diện ấm cúng, sang trọng và đậm chất bản làng."""
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
        color: #1f2937;
        background: linear-gradient(180deg, #fcfbf7 0%, #f4f0e8 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max-width: 860px;
    }

    /* Tiêu đề cao cấp, ấm áp mang hơi thở núi rừng */
    .village-header {
        background: linear-gradient(135deg, #1b4d3e 0%, #113227 60%, #0d251d 100%);
        color: white;
        border-radius: 28px;
        padding: 30px 36px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 24px;
        box-shadow: 0 18px 40px -12px rgba(27, 77, 62, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.18);
        position: relative;
        overflow: hidden;
    }
    .village-header::after {
        content: '';
        position: absolute;
        right: -40px;
        bottom: -40px;
        width: 180px;
        height: 180px;
        background: radial-gradient(circle, rgba(217, 119, 6, 0.3) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }

    /* Trạm tương tác giọng nói tinh tế, mộc mạc, gần gũi */
    .village-voice-box {
        background: #ffffff;
        border: 1px solid #e2dbcc;
        border-radius: 32px;
        padding: 34px;
        box-shadow: 0 14px 35px -10px rgba(44, 34, 30, 0.07);
        margin-bottom: 24px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .village-voice-box::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 6px;
        background: linear-gradient(90deg, #d97706, #16a34a, #0284c7, #9333ea);
    }

    /* Thẻ kết quả sắc nét, sang trọng như lời căn dặn chân tình */
    .village-result-card {
        background: #ffffff;
        border: 1px solid #e2dbcc;
        border-radius: 32px;
        padding: 36px;
        box-shadow: 0 16px 40px -12px rgba(44, 34, 30, 0.08);
        margin-top: 24px;
        position: relative;
    }

    .village-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #fef3c7;
        padding: 8px 16px;
        border-radius: 14px;
        font-size: 13px;
        font-weight: 700;
        color: #92400e;
        margin-right: 8px;
        margin-bottom: 8px;
        border: 1px solid #fde68a;
    }

    .stButton > button {
        border-radius: 16px;
        font-weight: 700;
        padding: 0.75rem 1.6rem;
        transition: all 0.25s ease;
        border: none;
        background: #b45309;
        color: white;
        box-shadow: 0 6px 16px rgba(180, 83, 9, 0.25);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 22px rgba(180, 83, 9, 0.35);
        background: #92400e;
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
                  "tt.textContent='Chạm để nghe lại ạ';});") if tu_phat else ""
    _html(f"""
<div style="display:flex;align-items:center;gap:16px;background:#fef3c7;border:1px solid #fde68a;border-radius:16px;padding:14px 20px;margin:14px 0;box-shadow: 0 4px 12px rgba(180, 83, 9, 0.05);">
  <button id="b" aria-label="Nghe" style="
      width:44px;height:44px;min-width:44px;border-radius:50%;border:none;
      background:#b45309;cursor:pointer;display:flex;align-items:center;
      justify-content:center;box-shadow:0 4px 12px rgba(180,83,9,0.3);
      transition:all 0.2s;"></button>
  <div style="flex-grow:1;">
    <div style="font-size:14px;font-weight:700;color:#92400e;">{nhan}</div>
    <div id="tt" style="font-size:12px;color:#b45309;margin-top:2px;font-weight:600;">Chạm vào đây để nghe trợ lý đọc nhé</div>
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
  a.onplay =function(){{ ve(true);  tt.textContent='Đang đọc cho bà con nghe...'; }};
  a.onpause=function(){{ ve(false); tt.textContent='Đã tạm dừng đọc'; }};
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

    with st.status("Trợ lý đang tìm xem việc này thế nào nhé...", expanded=False) as box:
        try:
            tuyen = _dinh_tuyen(cau_noi)
        except Exception:
            kq["loi"] = "Mạng hơi chập chờn rồi bà con ơi, thử lại giúp trợ lý nhé."
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
            kq["loi"] = "Chưa lấy được chi tiết thủ tục rồi ạ."
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
        box.update(label="Đã tìm thấy thông tin thủ tục rồi ạ", state="complete", expanded=False)
    return kq


def xu_ly_cau_noi(van_ban: str) -> None:
    ss.cau_noi = van_ban
    kq = chay_pipeline(van_ban)
    kq["la_tieng_mong"] = bool(ss.get("la_tieng_mong", True))
    ss.ket_qua = kq


# Tiêu đề cao cấp, thay đổi câu chữ thêm phần ấm áp, gần gũi
st.markdown("""
<div class="village-header">
    <div>
        <div style="font-size: 22px; font-weight: 800; letter-spacing: -0.3px; color: #ffffff;">TRỢ LÝ BẢN LÀNG — DỊCH VỤ CÔNG</div>
        <div style="font-size: 13px; font-weight: 500; color: #d1fae5; margin-top: 4px;">Việc xã việc bản, có trợ lý lo — Cứ thong thả, đâu vào đấy hết nha!</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Trạm tương tác giọng nói với lời văn thân thương, tự nhiên như người nhà
st.markdown("""
<div class="village-voice-box">
    <div style="font-size: 20px; font-weight: 800; color: #b45309; margin-bottom: 6px; letter-spacing: -0.2px;">
        ☕ Trợ lý đang ở đây nè, bà con cứ thong thả nói nha!
    </div>
    <div style="font-size: 13px; color: #57534e; font-weight: 500; margin-bottom: 20px;">
        Chọn tiếng nói quen thuộc của mình bên dưới, rồi bấm vào Micro để thủ thỉ việc cần làm nhé!
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
        with st.spinner("Trợ lý đang lắng nghe bà con nói..."):
            van_ban, _ = nghe(audio_in, tieng_mong=la_tieng_mong)
        if not van_ban:
            st.error("Trợ lý chưa nghe rõ lắm đâu. Bà con bấm lại và nói to, rõ hơn một chút giúp trợ lý nhé!")
            loa("Trợ lý chưa nghe rõ lắm đâu. Bà con bấm lại và nói to, rõ hơn một chút giúp trợ lý nhé!", tu_phat=True)
        else:
            if la_tieng_mong:
                dong_vi = [l for l in van_ban.splitlines() if l.startswith("VI:")]
                van_ban = (dong_vi[0][3:].strip() if dong_vi else dich_sang_viet(van_ban))
            st.success(f"Trợ lý đã nghe rõ rồi ạ: *{van_ban}*")
            xu_ly_cau_noi(van_ban)


def nut_goi_can_bo(kq: dict) -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🤝 NHỜ CÁN BỘ XÃ XUỐNG HƯỚNG DẪN TRỰC TIẾP", use_container_width=True):
        tt = kq.get("thu_tuc")
        ss.danh_sach_yeu_cau.append({
            "thoi_gian": datetime.now().strftime("%H:%M - %d/%m"),
            "van_de": tt.ten if tt else kq["tuyen"]["ten_nhom"],
            "chi_tiet": kq["cau_noi"],
            "trang_thai": "Chờ xử lý",
        })
        st.success("Đã gửi lời nhắn rồi bà con nhé! Cán bộ xã sẽ sớm liên hệ để giúp đỡ bà con tận tình ạ.")


def hien_ket_qua(kq: dict) -> None:
    if kq.get("loi"):
        st.error(kq["loi"])
        nut_goi_can_bo(kq)
        return

    tuyen, tt = kq["tuyen"], kq.get("thu_tuc")

    if tuyen["can_can_bo"] or tt is None:
        cau_hoi = tuyen.get("cau_hoi_lam_ro") or "Bà con cho trợ lý hỏi kỹ hơn một chút để tìm đúng việc cần làm nhé."
        st.warning(f"💡 {cau_hoi}")
        loa(cau_hoi, tu_phat=True)
        nut_goi_can_bo(kq)
        return

    dg = kq["don_gian"]
    
    st.markdown(f"""
    <div class="village-result-card">
        <div style="font-size: 21px; font-weight: 800; color: #92400e; margin-bottom: 12px; letter-spacing: -0.2px;">
            📋 {tt.ten}
        </div>
        <div style="font-size: 14px; color: #44403c; line-height: 1.6; margin-bottom: 20px; font-weight: 600;">
            {dg.get('tom_tat_1_cau','')}
        </div>
        <div>
            <span class="village-pill">📍 <b>Nơi làm:</b> {dg.get('di_dau', {}).get('noi_don_gian','—')}</span>
            <span class="village-pill">⏱️ <b>Thời gian:</b> {dg.get('bao_lau','—')}</span>
            <span class="village-pill">💰 <b>Lệ phí:</b> {dg.get('bao_nhieu_tien','—')}</span>
        </div>
    """, unsafe_allow_html=True)

    bb = [m for m in dg.get("mang_gi", []) if m.get("bat_buoc")]
    if bb:
        st.markdown("<div style='margin-top: 18px; font-size: 15px; font-weight: 800; color: #92400e;'>🎒 Những giấy tờ bà con cần chuẩn bị mang theo:</div>", unsafe_allow_html=True)
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
