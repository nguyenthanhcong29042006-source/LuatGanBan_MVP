# LUẬT GẦN BẢN — ảnh Docker cho máy chủ
#
# Dựng:   docker build -t luatganban .
# Chạy:   docker run -d -p 8501:8501 \
#             -e GEMINI_API_KEY="khoa_cua_ban" \
#             -v luatganban_cache:/app/data/cache \
#             --name luatganban --restart unless-stopped luatganban
#
# Không cần GPU. Không cần cơ sở dữ liệu. Toàn bộ dữ liệu là tệp phẳng nằm
# sẵn trong ảnh; chỉ thư mục data/cache cần ghi được nên gắn volume riêng.

FROM python:3.11-slim

# Múi giờ Việt Nam để dấu thời gian kiểm duyệt hiển thị đúng
ENV TZ=Asia/Ho_Chi_Minh \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata curl \
 && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài thư viện trước, tách khỏi mã nguồn để tận dụng cache khi build lại
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Chạy bằng người dùng thường, nhưng data/cache phải ghi được
RUN useradd -m -u 1000 lgb \
 && mkdir -p /app/data/cache/simplified /app/data/cache/audio /app/data/audio_bank \
 && chown -R lgb:lgb /app/data
USER lgb

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
