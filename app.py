# -*- coding: utf-8 -*-
"""LUẬT GẦN BẢN — điểm vào duy nhất của ứng dụng.
"Chuyển đổi số: không để ai bị bỏ lại phía sau"

File này chỉ làm 3 việc: dựng header, xử lý đăng nhập, và quyết định
người đang dùng được vào những trang nào (st.navigation).

Chạy:  python -m streamlit run app.py
"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
from streamlit.components.v1 import html as _html

from core import auth

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Luật Gần Bản", page_icon="⚖️",
                   layout="centered", initial_sidebar_state="collapsed")

# ==========================================================================
# GIAO DIỆN CHUNG
#
# Nguyên tắc: màn hình của bà con chỉ nên có MỘT thứ nổi bật — nút micro.
# Mọi thứ Streamlit tự thêm vào (thanh Deploy, menu ⋮, huy hiệu GitHub, đồng
# hồ chạy ở góc) đều bị ẩn, vì bà con không hiểu chúng là gì và rất dễ bấm
# nhầm. Nút mở thanh bên vẫn giữ lại nhưng làm mờ đi, bởi cán bộ cần nó để
# đăng nhập.
# ==========================================================================
st.markdown("""
<style>
  /* ---------- phông chữ ---------- */
  .stApp, p, h1,h2,h3,h4,h5,h6, label, button, input, .stMarkdown, .stText, .stTextArea
      { font-family: 'Times New Roman', Times, serif !important; }
  [data-testid="stExpanderToggleIcon"], [data-testid="stIconMaterial"],
  [data-testid="stFileUploadDropzone"] span, .st-icon, .material-icons,
  .material-symbols-rounded
      { font-family: 'Material Symbols Rounded','Material Icons',sans-serif !important; }

  /* ---------- ẩn thanh công cụ mặc định của Streamlit ---------- */
  [data-testid="stToolbar"],
  [data-testid="stDecoration"],
  [data-testid="stStatusWidget"],
  [data-testid="manage-app-button"],
  .stAppDeployButton,
  #MainMenu,
  footer,
  [class*="viewerBadge"],
  [class*="profileContainer"]        { display: none !important; }
  /* Lưu ý: trên Streamlit Cloud, huy hiệu "Made with Streamlit" và ảnh đại diện
     chủ app nằm ở TRANG BAO NGOÀI, không nằm trong iframe chạy app này, nên CSS
     ở đây KHÔNG với tới được. Muốn màn hình sạch hoàn toàn thì mở app bằng địa
     chỉ trần:  https://<ten-app>.streamlit.app/~/+/  */

  /* header trong suốt, không chiếm chiều cao */
  header[data-testid="stHeader"] {
      background: transparent !important;
      height: 0 !important;
      min-height: 0 !important;
  }
  /* Nút mở thanh bên (>>) mặc định bị ẩn — xem phần xử lý ?canbo=1 bên dưới. */

  /* kéo nội dung lên sát đỉnh vì header đã bị thu về 0 */
  .block-container { padding-top: 2.2rem !important; padding-bottom: 3rem !important; }

  /* Component HTML: bỏ viền. Riêng cái cao 0 (đoạn JS dọn trang bao) thì
     không được chiếm chỗ. KHÔNG ẩn tất cả — nút loa cũng là component. */
  iframe[title="streamlit.components.v1.html"] { border: 0 !important; }
  iframe[title="streamlit.components.v1.html"][height="0"] {
      height: 0 !important; display: block !important;
  }

  /* ---------- header dự án: gom về MỘT dòng ---------- */
  .lgb-header {
      display: flex; align-items: center; gap: 10px;
      padding-bottom: 8px; margin-bottom: 14px;
      border-bottom: 1px solid #e3e6ea;
  }
  .lgb-header img { width: 34px; height: 34px; object-fit: contain; flex-shrink: 0; }
  .lgb-ten {
      color: #003366; font-size: 17px; font-weight: bold;
      letter-spacing: .3px; white-space: nowrap;
  }
  .lgb-slogan {
      color: #666; font-size: 11.5px; font-style: italic;
      border-left: 1px solid #ccc; padding-left: 10px; margin-left: 8px;
  }
  @media (max-width: 640px) {
      .lgb-slogan { display: none; }          /* điện thoại: bỏ slogan cho gọn */
      .lgb-ten    { font-size: 16px; }
  }

  /* ---------- khu ghi âm: nút micro tròn, to ---------- */
  /* Khung ngoài. Phải nới chiều cao: mặc định Streamlit chỉ dành 68px cho cả
     widget, nút 96px sẽ bị cắt cụt. */
  [data-testid="stAudioInput"] {
      display: flex !important; justify-content: center !important;
      height: auto !important; min-height: 240px !important;
      overflow: visible !important;
      max-width: 560px; margin: 0 auto !important;
  }
  /* Khung trong — CHÍNH chỗ này cắt mất nút (height:68px + overflow:hidden).
     Phải mở overflow và bỏ chiều cao cố định, nếu không nút chỉ hiện một vệt. */
  [data-testid="stAudioInput"] > div {
      flex-direction: column !important;
      align-items: center !important;
      justify-content: flex-start !important;
      gap: 14px !important;
      width: 100% !important;
      height: auto !important; min-height: 230px !important;
      overflow: visible !important;
      border: none !important;
      background: transparent !important;
      box-shadow: none !important;
      padding-top: 10px !important;
  }
  [data-testid="stAudioInput"] > div > div { justify-content: center !important; }
  /* thanh công cụ nhỏ hiện khi rê chuột vào widget — bà con không cần */
  [data-testid="stAudioInput"] [data-testid="stElementToolbar"] { display: none !important; }
  [data-testid="stAudioInputActionButton"] {
      width: 96px !important; height: 96px !important;
      min-width: 96px !important; min-height: 96px !important;
      border-radius: 50% !important;
      background: #1B7F4B !important;
      border: 4px solid #d6efe0 !important;
      box-shadow: 0 6px 18px rgba(27,127,75,.30) !important;
      animation: lgb-tho 2.4s ease-in-out infinite;
      position: relative !important;     /* để gắn vòng sóng bên dưới */
  }
  /* Vòng sóng lan nhẹ khi CHƯA bấm — dấu hiệu "máy đang sẵn sàng nghe" */
  [data-testid="stAudioInputActionButton"]::before,
  [data-testid="stAudioInputActionButton"]::after {
      content: ""; position: absolute; left: 50%; top: 50%;
      width: 96px; height: 96px; margin: -48px 0 0 -48px;
      border-radius: 50%; border: 3px solid rgba(27,127,75,.40);
      pointer-events: none;
      animation: lgb-song 2.6s ease-out infinite;
  }
  [data-testid="stAudioInputActionButton"]::after { animation-delay: 1.3s; }
  @keyframes lgb-song {
      0%   { transform: scale(1);    opacity: .65; }
      100% { transform: scale(1.85); opacity: 0; }
  }
  [data-testid="stAudioInputActionButton"]:hover { background: #15653C !important; }
  [data-testid="stAudioInputActionButton"] svg,
  [data-testid="stAudioInputActionButton"] path {
      width: 44px !important; height: 44px !important;
      fill: #ffffff !important; color: #ffffff !important;
  }
  /* đang thu âm: Streamlit đổi nhãn nút sang "Stop" -> chuyển đỏ + nhịp sóng */
  [data-testid="stAudioInputActionButton"][aria-label*="top" i],
  [data-testid="stAudioInputActionButton"][title*="top" i] {
      background: #C62828 !important;
      border-color: #f7d5d5 !important;
      animation: lgb-thu 1.1s ease-out infinite;
  }
  /* đang thu thì tắt vòng sóng chờ — lúc này đã có sóng âm thật chuyển động */
  [data-testid="stAudioInputActionButton"][aria-label*="top" i]::before,
  [data-testid="stAudioInputActionButton"][aria-label*="top" i]::after {
      display: none !important;
  }
  @keyframes lgb-tho {
      0%,100% { transform: scale(1); }
      50%     { transform: scale(1.05); }
  }
  @keyframes lgb-thu {
      0%   { box-shadow: 0 0 0 0 rgba(198,40,40,.55); }
      70%  { box-shadow: 0 0 0 28px rgba(198,40,40,0); }
      100% { box-shadow: 0 0 0 0 rgba(198,40,40,0); }
  }
  [data-testid="stAudioInputWaveSurfer"] { width: 100% !important; min-height: 54px !important; }
  [data-testid="stAudioInputWaveformTimeCode"] { font-size: 15px !important; }

  /* ---------- nút chọn ngôn ngữ: to, rõ ---------- */
  [data-testid="stSegmentedControl"] { display: flex; justify-content: center; }
  [data-testid="stSegmentedControl"] button {
      font-size: 17px !important; padding: 9px 26px !important; font-weight: 600 !important;
  }

  /* ---------- chữ trong thẻ trả lời ---------- */
  .the-tra-loi { font-size: 20px; line-height: 1.65; }
  .the-tra-loi b { color: #003366; }
  div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 10px; }

  /* mục "cách khác" ở cuối trang: thu nhỏ, không hút mắt */
  .lgb-phu [data-testid="stExpander"] summary p { font-size: 13px !important; color: #777 !important; }
</style>
""", unsafe_allow_html=True)


# ==========================================================================
# DỌN TRANG BAO NGOÀI CỦA STREAMLIT CLOUD
#
# Khi mở bằng địa chỉ  https://<ten-app>.streamlit.app  thì app này KHÔNG phải
# là trang gốc: Streamlit Cloud phục vụ một trang bao, rồi nhúng app vào trong
# một iframe. Huy hiệu "Made with Streamlit", ảnh đại diện chủ app và nút
# "Manage app" nằm ở TRANG BAO, nên CSS viết trong app không với tới được.
#
# Iframe đó cùng tên miền với trang bao và có cờ allow-same-origin, nên một
# đoạn JS chạy trong app vẫn chạm được vào window.top. Đây là cách duy nhất
# dọn sạch màn hình mà vẫn giữ nguyên địa chỉ gốc đã công bố.
#
# Chạy cục bộ (streamlit run app.py) thì không có trang bao, window.top chính
# là app — đoạn mã chỉ thêm một thẻ style vô hại rồi thôi.
# ==========================================================================
_html("""
<script>
(function () {
  function don() {
    try {
      var d = window.top.document;
      if (d.getElementById('lgb-don-trang-bao')) return true;   // đã dọn rồi
      var st = d.createElement('style');
      st.id = 'lgb-don-trang-bao';
      st.textContent =
        '[class*="viewerBadge"],[class*="profileContainer"],' +
        '[data-testid="manage-app-button"],[class*="manageAppButton"]' +
        '{display:none !important;}';
      d.head.appendChild(st);
      return true;
    } catch (e) {
      return false;      // khác nguồn thì thôi, không làm gì cả
    }
  }
  if (!don()) {          // trang bao có thể dựng xong sau app -> thử lại vài lần
    var n = 0;
    var t = setInterval(function () { if (don() || ++n > 20) clearInterval(t); }, 500);
  }
})();
</script>
""", height=0)


@st.cache_data(show_spinner=False)
def _logo_b64() -> str:
    p = ROOT / "logo_hoc_vien.png"
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def header() -> None:
    """Header một dòng — nhường toàn bộ màn hình cho nút micro."""
    b64 = _logo_b64()
    img = (f'<img src="data:image/png;base64,{b64}" alt="">' if b64 else "")
    st.markdown(
        f'<div class="lgb-header">{img}'
        f'<span class="lgb-ten">LUẬT GẦN BẢN</span>'
        f'<span class="lgb-slogan">Chuyển đổi số: '
        f'không để ai bị bỏ lại phía sau</span></div>',
        unsafe_allow_html=True,
    )


header()

# ======================================================= ĐĂNG NHẬP (thanh bên)
auth.khoi_tao_mac_dinh()          # lần chạy đầu tiên: tạo 4 tài khoản mặc định

# Màn hình của bà con phải sạch tuyệt đối: không nút >>, không thanh công cụ.
# Cán bộ vào bằng địa chỉ riêng có thêm ?canbo=1 thì mới thấy nút mở thanh bên.
# Đã đăng nhập rồi thì giữ nguyên nút, để không bị khoá ngoài giữa chừng.
if not ("canbo" in st.query_params or auth.nguoi_dang_nhap()):
    st.markdown(
        '<style>[data-testid="stSidebarCollapsedControl"]{display:none !important;}</style>',
        unsafe_allow_html=True,
    )

with st.sidebar:
    u = auth.nguoi_dang_nhap()
    if u:
        st.markdown(f"**{u.get('mo_ta') or u['ten_dang_nhap']}**")
        st.caption(f"`{u['ten_dang_nhap']}` · "
                   f"{'Quản trị viên' if u['vai_tro'] == 'admin' else 'Cán bộ'}")
        if u.get("phai_doi_mk"):
            st.warning("Bạn cần đổi mật khẩu.", icon="🔑")
        if st.button("Đăng xuất", use_container_width=True):
            del st.session_state["nguoi_dung"]
            st.rerun()
    else:
        st.markdown("### Đăng nhập cán bộ")
        st.caption("Bà con không cần đăng nhập — cứ dùng trang Hỏi đáp.")
        with st.form("dang_nhap", clear_on_submit=False):
            ten = st.text_input("Tên đăng nhập")
            mk = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("Đăng nhập", type="primary",
                                     use_container_width=True):
                nd = auth.kiem_tra_dang_nhap(ten, mk)
                if nd:
                    st.session_state["nguoi_dung"] = nd
                    st.rerun()
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu.")

# ============================================================ ĐIỀU HƯỚNG
if not hasattr(st, "navigation") or not hasattr(st, "Page"):
    st.error(
        "Phiên bản Streamlit đang cài quá cũ (cần từ **1.36** trở lên).\n\n"
        "Mở terminal ở thư mục dự án và chạy:\n\n"
        "```\npip install -U streamlit\n```"
    )
    st.stop()

trang = [st.Page("giao_dien/cong_dan.py", title="Hỏi đáp thủ tục",
                 icon=":material/record_voice_over:", default=True)]

u = auth.nguoi_dang_nhap()
if u and (auth.la_admin() or auth.quyen_cua(u)):
    trang.append(st.Page("giao_dien/quan_tri.py", title="Quản trị kho",
                         icon=":material/settings:"))
if auth.la_admin():
    trang.append(st.Page("giao_dien/tai_khoan.py", title="Tài khoản & phân quyền",
                         icon=":material/manage_accounts:"))

st.navigation(trang, position="sidebar").run()
