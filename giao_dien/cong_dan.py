# -*- coding: utf-8 -*-
"""Cổng người dân — hỏi đáp thủ tục bằng giọng nói.

Nguyên tắc giao diện (voice-first):

  * MỘT nút. Bà con bấm micro, nói, bấm dừng — hệ thống tự chạy hết chuỗi,
    không có nút "xử lý" thứ hai.
  * Không hiện con số kỹ thuật. Bà con không cần biết "độ tin cậy 10%";
    họ chỉ cần biết máy nghe rõ hay chưa. Mọi chỉ số dời vào mục dành cho
    cán bộ ở cuối trang.
  * Chữ nào cũng có loa. Người không đọc được vẫn phải dùng được trọn vẹn,
    nên mọi nội dung trả lời đều kèm trình phát tiếng.
  * Gõ chữ là đường phụ, đặt cuối trang, cỡ nhỏ.
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

if not kb.load_kb():
    st.error(
        "**Kho dữ liệu trống.** Hãy chạy một lần:  `python tools/extract_tthc.py`\n\n"
        "Lệnh này bóc 28 file PDF hướng dẫn đang bị nhúng bên trong 3 file Excel "
        "ở `file_dichvucong/` ra thành `data/tthc/` + `data/manifest.json`."
    )
    st.stop()


# ==========================================================================
# HÀM CÓ CACHE (giảm độ trễ: lần 2 trở đi gần như tức thì)
# ==========================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def _dinh_tuyen(cau_noi: str) -> dict:
    r = dinh_tuyen(cau_noi)
    r["_key"] = r["thu_tuc"].key if r["thu_tuc"] else ""   # ThuTuc không hash được
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
    """Đọc một đoạn chữ bằng giọng Việt. Trả về đường dẫn file, "" nếu hỏng."""
    try:
        p = tts_tieng_viet(text)
        return str(p) if p else ""
    except Exception:
        return ""


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _audio_b64(duong_dan: str) -> tuple[str, str]:
    """Đọc file âm thanh thành base64 để nhúng thẳng vào nút loa."""
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
    """Nút loa tròn, màu xanh dương, bấm một cái là nghe.

    Dùng component HTML riêng thay cho st.audio vì cần: nút tròn to cho người
    lớn tuổi dễ bấm, và khả năng TỰ PHÁT ngay khi có kết quả.
    Trả về False nếu không dựng được (không có file).
    """
    if not duong_dan:
        return False
    b64, mime = _audio_b64(str(duong_dan))
    if not b64:
        return False

    tu_phat_js = ("a.play().then(function(){}).catch(function(){"
                  "tt.textContent='Bấm vào loa để nghe';});") if tu_phat else ""
    _html(f"""
<div style="display:flex;align-items:center;gap:16px;
            font-family:'Times New Roman',Times,serif;padding:4px 0;">
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
    """Đọc một đoạn chữ bằng giọng Việt rồi hiện nút loa."""
    if not (text or "").strip():
        return
    p = _tts_vi(text)
    if p:
        nut_loa(p, nhan=nhan, tu_phat=tu_phat)


# ==========================================================================
# PIPELINE — mỗi bước cập nhật ngay khi xong, không chờ cả chuỗi
# ==========================================================================
def _thong_diep_loi(e: Exception) -> str:
    """Đổi lỗi kỹ thuật thành câu người thường đọc được."""
    if isinstance(e, LoiQuota):
        return ("Máy đang bận, bà con chờ vài phút rồi hỏi lại nhé. "
                "Hoặc chọn thủ tục ở mục **Cách khác** cuối trang — "
                "những việc đã có sẵn câu trả lời thì dùng được ngay.")
    s = str(e)
    if "GEMINI_API_KEY" in s:
        return "Máy chưa được cài đặt xong. Bà con báo cán bộ giúp nhé."
    if "model" in s.lower() and ("404" in s or "not_found" in s.lower()):
        return "Máy đang bảo trì. Bà con báo cán bộ giúp nhé."
    return "Máy đang bận. Bà con thử lại sau ít phút nhé."


def chay_pipeline(cau_noi: str, *, phat_giong_mong: bool = True) -> dict:
    t0 = time.perf_counter()
    kq: dict = {"cau_noi": cau_noi, "thoi_gian": {}}

    with st.status("Đang tìm hướng dẫn cho bà con…", expanded=False) as box:
        box.write("Đang xem bà con cần làm việc gì…")
        t = time.perf_counter()
        try:
            tuyen = _dinh_tuyen(cau_noi)
        except Exception as e:
            kq["loi"] = _thong_diep_loi(e)
            box.update(label="Chưa xong", state="error", expanded=False)
            return kq
        kq["thoi_gian"]["dinh_tuyen"] = time.perf_counter() - t
        kq["tuyen"] = tuyen
        tt = kb.theo_key(tuyen["_key"]) if tuyen["_key"] else None
        kq["thu_tuc"] = tt

        if tuyen["can_can_bo"] or tt is None:
            box.update(label="Cần cán bộ hỗ trợ", state="complete", expanded=False)
            return kq
        box.write(f"Đúng việc: {tt.ten}")

        box.write("Đang đọc hướng dẫn của Nhà nước…")
        t = time.perf_counter()
        try:
            kq["don_gian"] = _don_gian_hoa(tt.key, CAU_HOI_MAC_DINH)
        except Exception as e:
            kq["loi"] = _thong_diep_loi(e)
            box.update(label="Chưa xong", state="error", expanded=False)
            return kq
        kq["thoi_gian"]["don_gian_hoa"] = time.perf_counter() - t
        kq["kich_ban"] = thanh_van_ban_doc(kq["don_gian"])

        # Giọng đọc tiếng Việt: tạo sẵn để bà con chỉ việc bấm ▶, không phải
        # bấm thêm một nút "tạo giọng" nữa.
        box.write("Đang chuẩn bị giọng đọc…")
        kq["audio_viet"] = _tts_vi(kq["kich_ban"])

        # Bước dịch + giọng Mông KHÔNG sống còn: hỏng thì vẫn còn tiếng Việt.
        if phat_giong_mong:
            box.write("Đang dịch sang tiếng Mông…")
            t = time.perf_counter()
            try:
                kq["mong"] = _dich_mong(kq["kich_ban"])
                kq["thoi_gian"]["dich"] = time.perf_counter() - t

                t = time.perf_counter()
                audio, tang = phat_tieng_mong(kq["mong"]["rpa"], key=tt.key)
                kq["thoi_gian"]["tts"] = time.perf_counter() - t
                kq["audio_mong"] = str(audio) if audio else ""
                kq["tang_tts"] = tang
            except Exception as e:
                kq["canh_bao"] = "Phần tiếng Mông chưa sẵn sàng, bà con nghe tạm tiếng Việt nhé."
                kq["_loi_mong"] = str(e)

        kq["thoi_gian"]["tong"] = time.perf_counter() - t0
        box.update(label="Đã có hướng dẫn cho bà con", state="complete", expanded=False)
    return kq


def xu_ly_cau_noi(van_ban: str) -> None:
    ss.cau_noi = van_ban
    kq = chay_pipeline(van_ban)
    # Nhớ bà con đang dùng tiếng gì, để lát nữa TỰ PHÁT đúng thứ tiếng đó.
    kq["la_tieng_mong"] = bool(ss.get("la_tieng_mong", True))
    ss.ket_qua = kq


# ==========================================================================
# 1. CHỌN TIẾNG — mặc định tiếng Mông
# ==========================================================================
LUA_CHON = ["🔊 Tiếng Mông", "🔊 Tiếng Việt"]

if hasattr(st, "segmented_control"):
    ngon_ngu = st.segmented_control(
        "Bà con nói bằng tiếng gì?", LUA_CHON,
        default=LUA_CHON[0], label_visibility="collapsed",
    ) or LUA_CHON[0]
else:                                    # Streamlit cũ: quay về radio
    ngon_ngu = st.radio("Bà con nói bằng tiếng gì?", LUA_CHON,
                        index=0, horizontal=True, label_visibility="collapsed")

la_tieng_mong = ngon_ngu.endswith("Mông")
ss.la_tieng_mong = la_tieng_mong

# ==========================================================================
# 2. MỘT NÚT DUY NHẤT
# ==========================================================================
st.markdown(
    '<div style="text-align:center;font-size:26px;font-weight:bold;'
    'color:#003366;margin:10px 0 2px 0;">Bấm vào đây để nói</div>',
    unsafe_allow_html=True,
)

audio_in = st.audio_input("Bấm micro để nói", label_visibility="collapsed")

# Tự xử lý ngay khi có bản ghi MỚI. Dấu vân tay nội dung để không chạy lại
# mỗi lần Streamlit vẽ lại trang.
if audio_in is not None:
    raw = audio_in.getvalue()
    van_tay = hashlib.sha256(raw).hexdigest()[:16]
    if van_tay != ss.audio_da_xu_ly and len(raw) > 2000:
        ss.audio_da_xu_ly = van_tay
        with st.spinner("Đang nghe bà con nói…"):
            van_ban, _nguon = nghe(audio_in, tieng_mong=la_tieng_mong)
        if not van_ban:
            st.error("Máy chưa nghe rõ, bà con bấm nói lại nhé.")
            loa("Máy chưa nghe rõ, bà con bấm nói lại nhé.",
                nhan="Nghe lại lời nhắc", tu_phat=True)
        else:
            if la_tieng_mong:
                dong_vi = [l for l in van_ban.splitlines() if l.startswith("VI:")]
                van_ban = (dong_vi[0][3:].strip() if dong_vi
                           else dich_sang_viet(van_ban))
            st.success(f"Bà con nói: *{van_ban}*")
            xu_ly_cau_noi(van_ban)
    elif 0 < len(raw) <= 2000:
        st.warning("Bà con bấm micro rồi nói lâu hơn một chút nhé.")


# ==========================================================================
# 3. KẾT QUẢ
# ==========================================================================
def nut_goi_can_bo(kq: dict) -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🙋 CẦN CÁN BỘ HỖ TRỢ TRỰC TIẾP", use_container_width=True):
        tt = kq.get("thu_tuc")
        ss.danh_sach_yeu_cau.append({
            "thoi_gian": datetime.now().strftime("%d/%m %H:%M:%S"),
            "van_de": tt.ten if tt else kq["tuyen"]["ten_nhom"],
            "ma": tt.ma_thu_tuc if tt else "",
            "chi_tiet": kq["cau_noi"],
            "tin_cay": kq["tuyen"].get("tin_cay_thu_tuc", 0),
            "trang_thai": "Mới",
        })
        st.success("✅ Đã gửi. Cán bộ sẽ liên hệ với bà con.")


def hien_ket_qua(kq: dict) -> None:
    if kq.get("loi"):
        st.error(kq["loi"])
        loa(kq["loi"], nhan="Nghe lời nhắc", tu_phat=True)
        kq.setdefault("tuyen", {"ten_nhom": "VẤN ĐỀ KHÁC", "tin_cay_thu_tuc": 0})
        nut_goi_can_bo(kq)
        return
    if kq.get("canh_bao"):
        st.info(kq["canh_bao"])

    tuyen, tt = kq["tuyen"], kq.get("thu_tuc")

    # --- máy chưa chắc chắn: hỏi lại bằng lời, KHÔNG hiện phần trăm ---
    if tuyen["can_can_bo"] or tt is None:
        cau_hoi = (tuyen.get("cau_hoi_lam_ro")
                   or "Bà con muốn hỏi về việc gì ạ? Bà con nói rõ hơn giúp máy nhé.")
        st.markdown(
            f'<div style="font-size:22px;line-height:1.6;padding:14px 16px;'
            f'background:#FFF8E1;border-left:5px solid #F0A500;border-radius:8px;">'
            f'❓ {cau_hoi}</div>',
            unsafe_allow_html=True,
        )
        loa(cau_hoi, nhan="Nghe câu hỏi", tu_phat=True)
        st.caption("Bà con bấm micro ở trên để nói lại, hoặc bấm nút dưới để gặp cán bộ.")
        nut_goi_can_bo(kq)
        return

    dg = kq["don_gian"]
    st.success(f"🏷️ **{tt.ten}**")
    if dg.get("_da_duyet"):
        st.caption(f"✅ Nội dung đã được **{dg.get('_nguoi_duyet','cán bộ')}** duyệt.")

    with st.container(border=True):
        st.markdown('<div class="the-tra-loi">', unsafe_allow_html=True)
        st.markdown(f"**{dg.get('tom_tat_1_cau','')}**")
        di = dg.get("di_dau", {})
        st.markdown(f"📍 **Đi đâu:** {di.get('noi_don_gian','—')}")
        bb = [m for m in dg.get("mang_gi", []) if m.get("bat_buoc")]
        kbb = [m for m in dg.get("mang_gi", []) if not m.get("bat_buoc")]
        if bb:
            st.markdown("🎒 **Mang theo:**")
            for m in bb:
                sl = f" — {m['so_luong']}" if m.get("so_luong") else ""
                st.markdown(f"  • {m['ten_don_gian']}{sl}")
        c1, c2 = st.columns(2)
        c1.markdown(f"⏱️ **Chờ:** {dg.get('bao_lau','—')}")
        c2.markdown(f"💰 **Tiền:** {dg.get('bao_nhieu_tien','—')}")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- NGHE CÂU TRẢ LỜI ---
    # Bà con chọn tiếng nào thì thứ tiếng đó TỰ PHÁT ngay, không phải bấm.
    # Thứ tiếng còn lại vẫn có nút loa để nghe đối chiếu.
    uu_tien_mong = bool(kq.get("la_tieng_mong", True)) and bool(kq.get("audio_mong"))

    if kq.get("audio_mong"):
        nut_loa(kq["audio_mong"], nhan="Nghe bằng tiếng Mông", tu_phat=uu_tien_mong)
        if kq.get("tang_tts") == "vi_phonetic":
            st.caption("Đây là giọng máy đọc phiên âm, chưa phải giọng Mông chuẩn.")

    if kq.get("audio_viet"):
        nut_loa(kq["audio_viet"], nhan="Nghe bằng tiếng Việt",
                tu_phat=not uu_tien_mong)
    else:
        loa(kq.get("kich_ban", ""), nhan="Nghe bằng tiếng Việt",
            tu_phat=not uu_tien_mong)

    if kq.get("mong"):
        with st.expander("📖 Xem chữ tiếng Mông"):
            nhan_ortho = ("chữ Mông kiểu Việt Nam" if HMONG_ORTHOGRAPHY == "vn"
                          else "chữ Mông RPA")
            st.caption(nhan_ortho)
            st.markdown(f"### {kq['mong']['hien_thi']}")
            st.text(f"RPA        : {kq['mong']['rpa']}")
            st.text(f"Phiên âm VN: {kq['mong']['vn']}")

    # Các chỉ số kỹ thuật (phần trăm, thời gian xử lý, tên tầng giọng nói) CHỈ
    # hiện khi có cán bộ đăng nhập. Màn hình của bà con tuyệt đối không có con số.
    la_can_bo = bool(auth.nguoi_dang_nhap())

    with st.expander("⚖️ Căn cứ pháp lý & đối chiếu tài liệu gốc"):
        st.caption(f"Mã thủ tục {tt.ma_thu_tuc} · cấp {tt.cap_thuc_hien}")
        if la_can_bo:
            cot1, cot2 = st.columns(2)
            cot1.metric("Độ tin cậy bản tóm tắt", f"{dg.get('do_tin_cay', 0):.0%}")
            cot2.metric("Độ tin cậy phân loại", f"{tuyen.get('tin_cay_thu_tuc', 0):.0%}")
            st.caption(f"Giọng Mông đã dùng: {NHAN_TANG.get(kq.get('tang_tts',''), '—')}")
            if kq.get("_loi_mong"):
                st.caption(f"Lỗi tiếng Mông: {kq['_loi_mong'][:200]}")
        if dg.get("chua_ro"):
            st.warning("Tài liệu **không nêu rõ**: " + "; ".join(dg["chua_ro"]))
        for l in dg.get("luu_y", []):
            st.markdown(f"- {l}")
        if dg.get("cac_buoc"):
            st.markdown("**Các bước:**")
            for i, b in enumerate(dg["cac_buoc"], 1):
                st.markdown(f"{i}. {b}")
        if dg.get("trich_dan"):
            st.markdown("**Trích nguyên văn tài liệu gốc:**")
            for q in dg["trich_dan"]:
                st.markdown(f"> {q}")
        if kbb:
            st.markdown("**Giấy tờ không bắt buộc:** "
                        + ", ".join(m["ten_don_gian"] for m in kbb))
        if tt.pdf_path.exists():
            st.download_button("⬇️ Tải file hướng dẫn gốc (PDF)",
                               tt.pdf_path.read_bytes(),
                               file_name=f"{tt.ma_thu_tuc}.pdf", mime="application/pdf")
        if la_can_bo:
            tg = kq.get("thoi_gian", {})
            st.caption("Thời gian xử lý: "
                       + "  ·  ".join(f"{k} {v:.1f}s" for k, v in tg.items()))

    nut_goi_can_bo(kq)


if ss.ket_qua:
    st.write("---")
    hien_ket_qua(ss.ket_qua)


# ==========================================================================
# 4. ĐƯỜNG PHỤ — gõ chữ / chọn danh sách. Đặt cuối trang, cỡ nhỏ.
# ==========================================================================
st.markdown('<div class="lgb-phu">', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

with st.expander("⌨️ Không nói được? Gõ chữ hoặc chọn từ danh sách"):
    t_go, t_chon = st.tabs(["Gõ câu hỏi", "Chọn thủ tục"])

    with t_go:
        with st.form("form_go", clear_on_submit=False):
            txt = st.text_area(
                "Bà con cần hỏi việc gì?",
                placeholder="Ví dụ: Vợ tôi mới sinh con, tôi muốn làm giấy khai sinh",
                height=90)
            if st.form_submit_button("Gửi câu hỏi", type="primary",
                                     use_container_width=True) and txt.strip():
                xu_ly_cau_noi(txt.strip())
                st.rerun()

    with t_chon:
        st.caption("Chọn trực tiếp — trả lời ngay, dùng khi phòng ồn hoặc mạng yếu.")
        nhom_chon = st.selectbox("Việc gì?", list(DANH_MUC_THU_TUC.keys()),
                                 format_func=lambda k: DANH_MUC_THU_TUC[k])
        ds = kb.theo_nhom(nhom_chon)
        if not ds:
            st.warning("Chưa có dữ liệu cho nhóm này. Nhóm đã có dữ liệu: "
                       + ", ".join(sorted({n for t in kb.load_kb() for n in t.nhom})))
        else:
            tt_chon = st.selectbox("Thủ tục cụ thể", ds, format_func=lambda t: t.ten)
            if st.button("Xem hướng dẫn", type="primary", use_container_width=True):
                xu_ly_cau_noi(tt_chon.ten)
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# ==========================================================================
# 5. THANH BÊN — chỉ dành cho cán bộ
# ==========================================================================
# Bảng trạng thái kỹ thuật chỉ dựng khi có cán bộ đăng nhập. Không chỉ ẩn bằng
# CSS mà KHÔNG SINH RA phần tử, để trên màn hình của bà con không tồn tại bất kỳ
# con số nào — kể cả khi có ai đó mở được thanh bên.
if auth.nguoi_dang_nhap():
    with st.sidebar:
        st.divider()
        st.markdown("### Trạng thái hệ thống")
        tk = kb.thong_ke()
        st.metric("Thủ tục trong kho", tk["so_thu_tuc"])
        st.caption(f"Nhóm có dữ liệu: {tk['so_nhom']}  ·  "
                   f"{tk['tong_ky_tu']:,} ký tự văn bản gốc")
        st.caption(f"Giọng Mông: `{TTS_HMONG_PROVIDER}`  ·  "
                   f"Ngưỡng tin cậy: {NGUONG_TU_TIN:.0%}")
        if tk["thieu_pdf"]:
            st.error(f"Thiếu PDF: {', '.join(tk['thieu_pdf'][:5])}")
        if ss.danh_sach_yeu_cau:
            st.markdown("### Phiếu chờ cán bộ")
            for p in reversed(ss.danh_sach_yeu_cau[-5:]):
                st.caption(f"{p['thoi_gian']} — {p['van_de']}")
