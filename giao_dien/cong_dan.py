# -*- coding: utf-8 -*-
"""Cổng người dân — hỏi đáp thủ tục bằng giọng nói (Bản nâng cấp toàn diện).

Nguyên tắc thiết kế (Voice-First & Accessibility):
  * MỘT nút bấm duy nhất, trực quan, không rườm rà.
  * Tự động hóa toàn bộ chuỗi xử lý, phát âm thanh ngay khi có kết quả.
  * Tách biệt hoàn toàn thông tin kỹ thuật cho cán bộ và giao diện đơn giản cho bà con.
"""
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

# CSS Tùy chỉnh nâng cao cho giao diện thân thiện với đồng bào
st.markdown("""
<style>
    .slogan-banner {
        background: linear-gradient(135deg, #0B4F9E 0%, #1976D2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(11,79,158,0.2);
    }
    .slogan-title {
        font-size: 26px;
        font-weight: 800;
        margin-bottom: 6px;
        font-family: 'Times New Roman', Times, serif;
    }
    .slogan-sub {
        font-size: 16px;
        opacity: 0.9;
    }
    .the-tra-loi {
        background: #F8FAFC;
        border: 2px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Banner Slogan Cấp Cao
st.markdown("""
<div class="slogan-banner">
    <div class="slogan-title">🗣️ Nói tiếng của mình — Thấu việc nước nhà</div>
    <div class="slogan-sub">Cổng thông tin thủ tục hành chính thông minh dành cho đồng bào</div>
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


_SVG_LOA = ('<svg width="38" height="38" viewBox="0 0 24 24" fill="white">'
            '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05'
            'c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 '
            '5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>')
_SVG_DUNG = ('<svg width="34" height="34" viewBox="0 0 24 24" fill="white">'
             '<path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>')


def nut_loa(duong_dan, *, nhan: str, tu_phat: bool = False) -> bool:
    if not duong_dan:
        return False
    b64, mime = _audio_b64(str(duong_dan))
    if not b64:
        return False

    tu_phat_js = ("a.play().then(function(){}).catch(function(){"
                  "tt.textContent='Bấm vào loa để nghe';});") if tu_phat else ""
    _html(f"""
<div style="display:flex;align-items:center;gap:16px;padding:6px 0;">
  <button id="b" aria-label="Nghe" style="
      width:76px;height:76px;min-width:76px;border-radius:50%;border:4px solid #cfe0f7;
      background:#0B4F9E;cursor:pointer;display:flex;align-items:center;
      justify-content:center;box-shadow:0 4px 14px rgba(11,79,158,.35);
      transition:transform .15s;"></button>
  <div>
    <div style="font-size:19px;font-weight:bold;color:#0B4F9E;">{nhan}</div>
    <div id="tt" style="font-size:14px;color:#666;margin-top:2px;">Bấm để nghe</div>
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
  b.onmousedown=function(){{ b.style.transform='scale(.94)'; }};
  b.onmouseup=function(){{ b.style.transform='scale(1)'; }};
  a.onplay =function(){{ ve(true);  tt.textContent='Đang đọc…'; }};
  a.onpause=function(){{ ve(false); tt.textContent='Bấm để nghe lại'; }};
  a.onended=function(){{ ve(false); tt.textContent='Bấm để nghe lại'; }};
  {tu_phat_js}
}})();
</script>
""", height=100)
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

    with st.status("Đang tìm hướng dẫn cho bà con…", expanded=False) as box:
        box.write("Đang phân tích yêu cầu của bà con…")
        try:
            tuyen = _dinh_tuyen(cau_noi)
        except Exception as e:
            kq["loi"] = "Hệ thống đang bận, bà con vui lòng thử lại sau ít phút."
            box.update(label="Chưa hoàn tất", state="error", expanded=False)
            return kq
        
        kq["tuyen"] = tuyen
        tt = kb.theo_key(tuyen["_key"]) if tuyen["_key"] else None
        kq["thu_tuc"] = tt

        if tuyen["can_can_bo"] or tt is None:
            box.update(label="Cần cán bộ hỗ trợ trực tiếp", state="complete", expanded=False)
            return kq

        box.write("Đang tổng hợp thông tin nhà nước...")
        try:
            kq["don_gian"] = _don_gian_hoa(tt.key, CAU_HOI_MAC_DINH)
        except Exception as e:
            kq["loi"] = "Không thể tải dữ liệu thủ tục lúc này."
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
                kq["canh_bao"] = "Đang dùng âm thanh tiếng Việt do tiếng Mông đang cập nhật."

        kq["thoi_gian"]["tong"] = time.perf_counter() - t0
        box.update(label="Đã có hướng dẫn chính xác", state="complete", expanded=False)
    return kq


def xu_ly_cau_noi(van_ban: str) -> None:
    ss.cau_noi = van_ban
    kq = chay_pipeline(van_ban)
    kq["la_tieng_mong"] = bool(ss.get("la_tieng_mong", True))
    ss.ket_qua = kq


# Lựa chọn ngôn ngữ giao tiếp
LUA_CHON = ["🔊 Tiếng Mông", "🔊 Tiếng Việt"]
ngon_ngu = st.segmented_control(
    "Bà con nói bằng tiếng gì?", LUA_CHON,
    default=LUA_CHON[0], label_visibility="collapsed"
) or LUA_CHON[0]

la_tieng_mong = ngon_ngu.endswith("Mông")
ss.la_tieng_mong = la_tieng_mong

st.markdown(
    '<div style="text-align:center;font-size:24px;font-weight:700;'
    'color:#0f172a;margin:16px 0 8px 0;">Bấm vào micro và nói yêu cầu của bạn</div>',
    unsafe_allow_html=True,
)

audio_in = st.audio_input("Bấm micro để nói", label_visibility="collapsed")

if audio_in is not None:
    raw = audio_in.getvalue()
    van_tay = hashlib.sha256(raw).hexdigest()[:16]
    if van_tay != ss.audio_da_xu_ly and len(raw) > 2000:
        ss.audio_da_xu_ly = van_tay
        with st.spinner("Hệ thống đang lắng nghe..."):
            van_ban, _ = nghe(audio_in, tieng_mong=la_tieng_mong)
        if not van_ban:
            st.error("Chưa nghe rõ giọng nói, bà con vui lòng bấm nói lại.")
            loa("Chưa nghe rõ giọng nói, bà con vui lòng bấm nói lại.", tu_phat=True)
        else:
            if la_tieng_mong:
                dong_vi = [l for l in van_ban.splitlines() if l.startswith("VI:")]
                van_ban = (dong_vi[0][3:].strip() if dong_vi else dich_sang_viet(van_ban))
            st.success(f"Nội dung nhận diện: *{van_ban}*")
            xu_ly_cau_noi(van_ban)


def nut_goi_can_bo(kq: dict) -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🙋 KẾT NỐI NGAY VỚI CÁN BỘ XÃ", use_container_width=True):
        tt = kq.get("thu_tuc")
        ss.danh_sach_yeu_cau.append({
            "thoi_gian": datetime.now().strftime("%H:%M:%S - %d/%m"),
            "van_de": tt.ten if tt else kq["tuyen"]["ten_nhom"],
            "chi_tiet": kq["cau_noi"],
            "trang_thai": "Đang chờ",
        })
        st.success("✅ Đã gửi yêu cầu thành công. Cán bộ sẽ hỗ trợ bà con ngay.")


def hien_ket_qua(kq: dict) -> None:
    if kq.get("loi"):
        st.error(kq["loi"])
        nut_goi_can_bo(kq)
        return

    tuyen, tt = kq["tuyen"], kq.get("thu_tuc")

    if tuyen["can_can_bo"] or tt is None:
        cau_hoi = tuyen.get("cau_hoi_lam_ro") or "Bà con cần hỗ trợ cụ thể thủ tục nào?"
        st.warning(f"❓ {cau_hoi}")
        loa(cau_hoi, tu_phat=True)
        nut_goi_can_bo(kq)
        return

    dg = kq["don_gian"]
    st.success(f"🏷️ **{tt.ten}**")

    with st.container():
        st.markdown('<div class="the-tra-loi">', unsafe_allow_html=True)
        st.markdown(f"**{dg.get('tom_tat_1_cau','')}**")
        di = dg.get("di_dau", {})
        st.markdown(f"📍 **Nơi thực hiện:** {di.get('noi_don_gian','—')}")
        
        bb = [m for m in dg.get("mang_gi", []) if m.get("bat_buoc")]
        if bb:
            st.markdown("🎒 **Giấy tờ cần mang:**")
            for m in bb:
                sl = f" ({m['so_luong']})" if m.get("so_luong") else ""
                st.markdown(f"  • {m['ten_don_gian']}{sl}")
                
        c1, c2 = st.columns(2)
        c1.markdown(f"⏱️ **Thời gian:** {dg.get('bao_lau','—')}")
        c2.markdown(f"💰 **Lệ phí:** {dg.get('bao_nhieu_tien','—')}")
        st.markdown("</div>", unsafe_allow_html=True)

    uu_tien_mong = bool(kq.get("la_tieng_mong", True)) and bool(kq.get("audio_mong"))
    if kq.get("audio_mong"):
        nut_loa(kq["audio_mong"], nhan="Nghe hướng dẫn bằng tiếng Mông", tu_phat=uu_tien_mong)

    if kq.get("audio_viet"):
        nut_loa(kq["audio_viet"], nhan="Nghe hướng dẫn bằng tiếng Việt", tu_phat=not uu_tien_mong)

    # Vùng chỉ dành cho cán bộ xem chỉ số kỹ thuật
    if auth.nguoi_dang_nhap():
        with st.expander("⚙️ Dành cho cán bộ: Kiểm tra kỹ thuật"):
            st.metric("Độ tin cậy xử lý", f"{dg.get('do_tin_cay', 0):.0%}")
            st.caption(f"Mã thủ tục: {tt.ma_thu_tuc}")

    nut_goi_can_bo(kq)


if ss.ket_qua:
    st.write("---")
    hien_ket_qual = hien_ket_qua(ss.ket_qua)

# Phần phụ trợ gõ chữ cho trường hợp đặc biệt
with st.expander("⌨️ Phương án phụ: Gõ chữ hoặc chọn danh mục thủ tục"):
    t_go, t_chon = st.tabs(["Gõ câu hỏi", "Chọn từ danh mục"])
    with t_go:
        txt = st.text_input("Nhập nội dung cần hỏi:")
        if st.button("Tra cứu ngay") and txt.strip():
            xu_ly_cau_noi(txt.strip())
            st.rerun()
    with t_chon:
        nhom_chon = st.selectbox("Chọn lĩnh vực:", list(DANH_MUC_THU_TUC.keys()), format_func=lambda k: DANH_MUC_THU_TUC[k])
        ds = kb.theo_nhom(nhom_chon)
        if ds:
            tt_chon = st.selectbox("Chọn thủ tục cụ thể:", ds, format_func=lambda t: t.ten)
            if st.button("Xem ngay hướng dẫn"):
                xu_ly_cau_noi(tt_chon.ten)
                st.rerun()

# Thanh bên độc quyền cho cán bộ quản trị
if auth.nguoi_dang_nhap():
    with st.sidebar:
        st.divider()
        st.markdown("### Quản trị hệ thống")
        tk = kb.thong_ke()
        st.metric("Tổng số thủ tục", tk["so_thu_tuc"])
        if ss.danh_sach_yeu_cau:
            st.markdown("### Yêu cầu hỗ trợ mới")
            for p in ss.danh_sach_yeu_cau[-3:]:
                st.caption(f"{p['thoi_gian']} — {p['van_de']}")
