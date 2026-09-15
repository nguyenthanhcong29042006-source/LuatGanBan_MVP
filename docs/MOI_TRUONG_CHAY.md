# LUẬT GẦN BẢN — Môi trường chạy

Tài liệu một trang, dành cho bộ phận quản trị máy chủ. Số liệu đo trên mã nguồn
thực tế tại thời điểm bàn giao.

## Tóm tắt

Ứng dụng web Python, một tiến trình, **không cần cơ sở dữ liệu, không cần GPU**.
Toàn bộ dữ liệu nghiệp vụ là tệp phẳng nằm sẵn trong mã nguồn.

| Hạng mục | Yêu cầu |
|---|---|
| Ngôn ngữ | Python **3.11** (chạy được 3.10 – 3.12) |
| Khung ứng dụng | Streamlit ≥ 1.40 |
| CPU | 1 vCPU |
| RAM | 1 GB (thực dùng khoảng 300 – 500 MB) |
| Đĩa | 2 GB (mã nguồn + dữ liệu hiện 9 MB, phần còn lại cho thư viện và bộ nhớ đệm) |
| Cổng | **8501** (HTTP) |
| Cơ sở dữ liệu | Không |
| GPU | Không |
| Số tiến trình | 1 |

## Thư viện

Xem `requirements.txt`. Tất cả đều là gói Python thuần hoặc có sẵn bản dựng
nhị phân, **không cần trình biên dịch C** trên máy chủ:

```
streamlit>=1.40        google-genai>=1.0.0    pdfplumber>=0.11
openpyxl>=3.1          pandas>=2.0            gTTS>=2.5
SpeechRecognition>=3.10
```

Không cần `ffmpeg`, không cần thư viện âm thanh hệ thống: việc ghi âm do trình
duyệt của người dùng đảm nhiệm, việc tạo giọng đọc gọi ra dịch vụ bên ngoài.

## Biến môi trường

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `GEMINI_API_KEY` | **Có** | Khoá API Google Gemini |
| `LGB_MODEL_QUALITY` | Không | Ép dùng một model cụ thể; để trống thì hệ thống tự dò model khả dụng |
| `LGB_TTS_HMONG` | Không | Chế độ giọng Mông: `auto` (mặc định), `audio_bank`, `vi_phonetic`, `off` |
| `LGB_NGUONG_TU_TIN` | Không | Ngưỡng tin cậy phân loại, mặc định `0.55` |

Ngoài biến môi trường, ứng dụng cũng đọc được khoá từ `.streamlit/secrets.toml`.
**Tệp này không nằm trong mã nguồn** và phải do quản trị viên tạo riêng.

## Kết nối ra ngoài

Máy chủ cần mở kết nối HTTPS đi ra tới:

| Đích | Dùng để |
|---|---|
| `generativelanguage.googleapis.com` | Nhận dạng giọng nói, phân loại, diễn giải, dịch |
| `translate.google.com` | Tạo giọng đọc tiếng Việt (thư viện gTTS) |

Nếu máy chủ nằm sau tường lửa chặn chiều ra thì phải cấp phép hai tên miền này,
nếu không ứng dụng chỉ phục vụ được nội dung đã có sẵn trong bộ nhớ đệm.

## Thư mục cần quyền ghi

Chỉ duy nhất `data/cache/`. Nên gắn volume riêng cho thư mục này để câu trả lời
đã được cán bộ duyệt không mất khi khởi động lại.

## Chạy thử nhanh

```bash
# Cách 1 — Docker (khuyến nghị)
docker compose up -d          # cần tệp .env chứa GEMINI_API_KEY

# Cách 2 — chạy trực tiếp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="..."
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

Kiểm tra sống: `GET http://<máy-chủ>:8501/_stcore/health` trả về `ok`.

## Khuyến nghị vận hành

Đặt sau một reverse proxy (Nginx, Caddy) để có HTTPS. **Bắt buộc phải có HTTPS**:
trình duyệt chỉ cho phép trang web dùng micrô khi kết nối được mã hoá, mà micrô
là chức năng chính của ứng dụng này.

Streamlit dùng WebSocket, nên cấu hình proxy phải cho phép nâng cấp kết nối:

```nginx
location / {
    proxy_pass http://127.0.0.1:8501;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;
}
```

## Ghi chú về chi phí

Chi phí máy chủ cho ứng dụng này rất thấp vì tải nhẹ và không có cơ sở dữ liệu.
Khoản chi đáng kể nằm ở **lượt gọi API Gemini**, và khoản đó không thay đổi theo
việc đặt ứng dụng ở đâu. Sau khi toàn bộ thủ tục đã được tạo sẵn và duyệt, phần
lớn lượt truy vấn được phục vụ từ bộ nhớ đệm và không phát sinh chi phí mô hình.
