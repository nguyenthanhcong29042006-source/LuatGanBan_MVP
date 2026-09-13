# -*- coding: utf-8 -*-
"""Cổng người dân — Giao diện đỉnh cao, kết hợp sự sang trọng hiện đại và bản sắc vùng cao ấm áp."""
from __future__ import annotations

import hashlib
import time
from datetime import datetime

import streamlit as st

from core import kb
from core.llm import LoiQuota
from core.router import dinh_tuyen
from core.simplify import CAU_HOI_MAC_DINH, don_gian_hoa, thanh_van_ban_doc
from core.stt import nghe
from core.translate import dich_sang_mong, dich_sang_viet
from core.tts import phat_tieng_mong, tts_tieng_viet

DANH_MUC_THU_TUC = {
    "khai_sinh": "Đăng ký khai sinh",
    "ket_hon": "Đăng ký kết hôn",
    "khai_tu": "Đăng ký khai tử",
    "ho_khau": "Đăng ký cư trú / Hộ khẩu",
    "dat_dai": "Thủ tục đất đai",
    "tro_cap": "Chính sách trợ cấp xã hội"
}

ss = st.session_state
ss.setdefault("danh_sach_yeu_cau", [])
ss.setdefault("ket_qua", None)
ss.setdefault("cau_noi", "")
ss.setdefault("audio_da_xu_ly", "")

if not kb.load_kb():
    st.error("**Kho dữ liệu trống.** Hãy chạy: `python tools/extract_tthc.py`")
    st.stop()

# Giao diện nâng cấp toàn diện: Sang trọng, đẳng cấp nhưng cực kỳ gần gũi với đồng bào
st.markdown("""
<style>
  .stApp {
      background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  }

  /* Banner đỉnh cao mang đậm hơi thở bản làng và số hóa */
  .vung-cao-banner {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #091e3a 100%);
      color: #ffffff;
      padding: 32px 24px;
      border-radius: 24px;
      text-align: center;
      box-shadow: 0 15px 35px rgba(15, 23, 42, 0.25);
      margin-bottom: 25px;
      border: 1px solid rgba(250, 204, 21, 0.4);
      position: relative;
      overflow: hidden;
  }
  .vung-cao-banner::after {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; height: 4px;
      background: linear-gradient(90deg, #facc15, #38bdf8, #facc15);
  }
  .vung-cao-title {
      font-size: 28px;
      font-weight: 800;
      color: #facc15;
      margin-bottom: 10px;
      letter-spacing: 0.8px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.3);
  }
  .vung-cao-slogan {
      font-size: 16px;
      color: #e2e8f0;
      font-weight: 500;
      font-style: italic;
      letter-spacing: 0.5px;
  }

  /* Tùy chỉnh nút chọn ngôn ngữ dạng thẻ cao cấp */
  .stRadio > div {
      display: flex;
      justify-content: center;
      gap: 16px;
      margin-bottom: 20px;
  }
  .stRadio label {
      background: #ffffff;
      border: 2px solid #cbd5e1;
      border-radius: 16px;
      padding: 10px 24px;
      font-weight: 700;
      color: #1e293b;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.04);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .stRadio label:hover {
      border-color: #facc15;
      background: #fffbeb;
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(250, 204, 21, 0.2);
  }

  /* Khung Micro sinh động, bắt mắt */
  .mic-container {
      background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
      border: 3px dashed #38bdf8;
      border-radius: 28px;
      padding: 30px;
      text-align: center;
      box-shadow: 0 12px 30px rgba(56, 189, 248, 0.12);
      margin-bottom: 25px;
      transition: all 0.3s ease;
  }
  .mic-container:hover {
      border-color: #0f172a;
      box-shadow: 0 16px 40px rgba(15, 23, 42, 0.15);
  }

  /* Thẻ kết quả hiển thị cao cấp */
  .card-ket-qua {
      background: #ffffff;
      border-left: 6px solid #facc15;
      border-top: 1px solid #e2e8f0;
      border-right: 1px solid #e2e8f0;
      border-bottom: 1px solid #e2e8f0;
      padding: 26px;
      border-radius: 20px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06);
      margin-top: 20px;
      margin-bottom: 20px;
  }
  .text-highlight {
      font-size: 20px;
      line-height: 1.6;
      color: #0f172a;
      font-weight: 700;
  }
</style>
""", unsafe_allow_html=True)


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


def _thong_diep_loi(e: Exception) -> str:
    if isinstance(e, LoiQuota):
        return ("Hệ thống đang bận do vượt quá lượt miễn phí tạm thời. "
                "Bà con vui lòng thử lại sau ít phút hoặc chọn nhanh thủ tục ở mục bên dưới.")
    return "Máy chưa nghe rõ, bà con bấm nói lại nhé."


def chay_pipeline(cau_noi: str, *, phat_giong_mong: bool = True) -> dict:
    t0 = time.perf_counter()
    kq: dict = {"cau_noi": cau_noi, "thoi_gian": {}}

    with st.status("🎧 Đang lắng nghe và tìm kiếm hướng dẫn…", expanded=True) as box:
        box.write("🧭 Đang tra cứu thủ tục cho bà con…")
        t = time.perf_counter()
        try:
            tuyen = _dinh_tuyen(cau_noi)
        except Exception as e:
            kq["loi"] = _thong_diep_loi(e)
            box.update(label="Chưa xử lý được", state="error", expanded=False)
            return kq
        kq["thoi_gian"]["dinh_tuyen"] = time.perf_counter() - t
        kq["tuyen"] = tuyen
        tt = kb.theo_key(tuyen["_key"]) if tuyen["_key"] else None
        kq["thu_tuc"] = tt

        if tuyen["can_can_bo"] or tt is None:
            box.update(label="Cần cán bộ hỗ trợ trực tiếp", state="complete", expanded=False)
            return kq
        box.write(f"   ↳ **{tt.ten}**")

        box.write("📖 Đang rút gọn nội dung hướng dẫn…")
        t = time.perf_counter()
        try:
            kq["don_gian"] = _don_gian_hoa(tt.key, CAU_HOI_MAC_DINH)
        except Exception as e:
            kq["loi"] = _thong_diep_loi(e)
            box.update(label="Chưa xử lý được", state="error", expanded=False)
            return kq
        kq["thoi_gian"]["don_gian_hoa"] = time.perf_counter() - t
        kq["kich_ban"] = thanh_van_ban_doc(kq["don_gian"])

        if phat_giong_mong:
            box.write("🔄 Đang chuyển sang tiếng Mông…")
            t = time.perf_counter()
            try:
                kq["mong"] = _dich_mong(kq["kich_ban"])
                kq["thoi_gian"]["dich"] = time.perf_counter() - t

                box.write("🔊 Đang tạo giọng đọc…")
                t = time.perf_counter()
                audio, tang = phat_tieng_mong(kq["mong"]["rpa"], key=tt.key)
                kq["thoi_gian"]["tts"] = time.perf_counter() - t
                kq["audio_mong"] = str(audio) if audio else ""
                kq["tang_tts"] = tang
            except Exception as e:
                kq["canh_bao"] = "Phần âm thanh tiếng Mông đang bận, đã hiển thị đầy đủ văn bản."
        
        kq["thoi_gian"]["tong"] = time.perf_counter() - t0
        box.update(label="✨ Đã hoàn thành hướng dẫn!", state="complete", expanded=False)
    return kq


def xu_ly_cau_noi(van_ban: str) -> None:
    ss.cau_noi = van_ban
    ss.ket_qua = chay_pipeline(van_ban)


# Banner chính với slogan mới cực kỳ cảm xúc và đẳng cấp
st.markdown("""
<div class="vung-cao-banner">
  <div class="vung-cao-title">🎙️ LUẬT VỀ BẢN LÀNG — ẤM LÒNG ĐỒNG BÀO</div>
  <div class="vung-cao-slogan">"Chuyển đổi số tận tâm, đưa chính sách pháp luật đến từng mái nhà"</div>
</div>
""", unsafe_allow_html=True)

st.info("🎤 **Mẹo nhỏ cho bà con:** Hãy bấm vào biểu tượng Micro bên dưới và nói rõ yêu cầu bằng Tiếng Mông hoặc Tiếng Việt. Nếu trình duyệt hỏi quyền micro, hãy bấm **Cho phép (Allow)** nhé.", icon="💡")

ngon_ngu = st.radio(
    "Chọn ngôn ngữ", 
    ["🔊 Tiếng Mông (Hmong)", "🔊 Tiếng Việt"],
    index=0, 
    horizontal=True, 
    label_visibility="collapsed"
)

st.markdown("<div class='mic-container'>", unsafe_allow_html=True)
st.markdown("<h3 style='color: #0f172a; margin-bottom: 12px; font-weight: 700;'>Bấm vào micro bên dưới để bắt đầu nói</h3>", unsafe_allow_html=True)
audio_in = st.audio_input("Nói yêu cầu tại đây", label_visibility="collapsed")
st.markdown("</div>", unsafe_allow_html=True)

if audio_in is not None:
    raw = audio_in.getvalue()
    van_tay = hashlib.sha256(raw).hexdigest()[:16]
    is_mong = ("Tiếng Mông" in ngon_ngu)
    if van_tay != ss.audio_da_xu_ly and len(raw) > 2000:
        ss.audio_da_xu_ly = van_tay
        with st.spinner("🎧 Máy đang lắng nghe và phân tích yêu cầu…"):
            van_ban, _nguon = nghe(audio_in, tieng_mong=is_mong)
        if not van_ban:
            st.error("Máy chưa nghe rõ, bà con bấm nói lại nhé.")
        else:
            if is_mong:
                dong_vi = [l for l in van_ban.splitlines() if l.startswith("VI:")]
                van_ban = (dong_vi[0][3:].strip() if dong_vi
                           else dich_sang_viet(van_ban))
            xu_ly_cau_noi(van_ban)
    elif 0 < len(raw) <= 2000:
        st.warning("Bản ghi quá ngắn. Bà con bấm micro và nói rõ hơn một chút nhé.")


def nut_goi_can_bo(kq: dict) -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🙋 CẦN CÁN BỘ / TÌNH NGUYỆN VIÊN HỖ TRỢ TRỰC TIẾP",
                 use_container_width=True, type="primary"):
        tt = kq.get("thu_tuc")
        ss.danh_sach_yeu_cau.append({
            "thoi_gian": datetime.now().strftime("%d/%m %H:%M:%S"),
            "van_de": tt.ten if tt else kq["tuyen"]["ten_nhom"],
            "ma": tt.ma_thu_tuc if tt else "",
            "chi_tiet": kq["cau_noi"],
            "trang_thai": "Mới",
        })
        st.success("✅ Đã gửi yêu cầu thành công. Cán bộ xã sẽ sớm liên hệ hỗ trợ bà con.")


def hien_ket_qua(kq: dict) -> None:
    if kq.get("loi"):
        st.error(f"⚠️ {kq['loi']}")
        nut_goi_can_bo(kq)
        return
    if kq.get("canh_bao"):
        st.warning(f"⚠️ {kq['canh_bao']}")

    tuyen, tt = kq["tuyen"], kq.get("thu_tuc")

    if tuyen["can_can_bo"] or tt is None:
        st.warning("🏷️ Nội dung này cần có sự hướng dẫn trực tiếp từ cán bộ.")
        nut_goi_can_bo(kq)
        return

    dg = kq["don_gian"]
    st.success(f"📌 **{tt.ten}**  ·  Mã thủ tục: `{tt.ma_thu_tuc}`")

    st.markdown('<div class="card-ket-qua">', unsafe_allow_html=True)
    st.markdown(f"<div class='text-highlight'><b>{dg.get('tom_tat_1_cau','')}</b></div>", unsafe_allow_html=True)
    di = dg.get("di_dau", {})
    st.markdown(f"<br>📍 **Đi đến:** {di.get('noi_don_gian','—')}", unsafe_allow_html=True)
    bb = [m for m in dg.get("mang_gi", []) if m.get("bat_buoc")]
    if bb:
        st.markdown("<br>🎒 **Giấy tờ cần mang theo:**", unsafe_allow_html=True)
        for m in bb:
            sl = f" — {m['so_luong']}" if m.get("so_luong") else ""
            st.markdown(f"  • {m['ten_don_gian']}{sl}")
    c1, c2 = st.columns(2)
    c1.markdown(f"<br>⏱️ **Thời gian chờ:** {dg.get('bao_lau','—')}", unsafe_allow_html=True)
    c2.markdown(f"<br>💰 **Lệ phí:** {dg.get('bao_nhieu_tien','—')}", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔊 Nghe hướng dẫn bằng Tiếng Việt", use_container_width=True):
        p = tts_tieng_viet(kq["kich_ban"])
        if p:
            st.audio(str(p))
        else:
            st.warning("Đang chuẩn bị âm thanh, vui lòng thử lại.")

    if kq.get("mong"):
        with st.container(border=True):
            st.markdown("### 📖 Hướng dẫn bằng Tiếng Mông")
            st.markdown(f"**{kq['mong']['hien_thi']}**")
            if kq.get("audio_mong"):
                st.audio(kq["audio_mong"])
            with st.expander("Xem phiên âm phụ"):
                st.text(f"RPA: {kq['mong']['rpa']}")

    nut_goi_can_bo(kq)


if ss.ket_qua:
    st.write("---")
    hien_ket_qua(ss.ket_qua)

st.markdown("<br><hr>", unsafe_allow_html=True)
with st.expander("⌨️ Cách khác: Nhập chữ hoặc chọn thủ tục từ danh sách"):
    t_go, t_chon = st.tabs(["Gõ câu hỏi", "Chọn từ danh sách"])

    with t_go:
        with st.form("form_go", clear_on_submit=False):
            txt = st.text_area(
                "Bà con cần hỏi việc gì?",
                placeholder="Ví dụ: Làm giấy khai sinh cho con ở đâu?",
                height=80)
            if st.form_submit_button("Gửi câu hỏi", type="primary",
                                     use_container_width=True) and txt.strip():
                xu_ly_cau_noi(txt.strip())

    with t_chon:
        nhom_chon = st.selectbox("Chọn nhóm việc:", list(DANH_MUC_THU_TUC.keys()),
                                 format_func=lambda k: DANH_MUC_THU_TUC[k])
        ds = kb.theo_nhom(nhom_chon)
        if ds:
            tt_chon = st.selectbox("Chọn thủ tục cụ thể:", ds, format_func=lambda t: t.ten)
            if st.button("Xem hướng dẫn ngay", type="primary", use_container_width=True):
                xu_ly_cau_noi(tt_chon.ten)

with st.sidebar:
    st.divider()
    st.markdown("### Trạng thái hệ thống")
    tk = kb.thong_ke()
    st.metric("Thủ tục trong kho", tk["so_thu_tuc"])
    if ss.danh_sach_yeu_cau:
        st.markdown("### Phiếu chờ cán bộ")
        for p in reversed(ss.danh_sach_yeu_cau[-5:]):
            st.caption(f"{p['thoi_gian']} — {p['van_de']}")
