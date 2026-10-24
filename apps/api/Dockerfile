FROM python:3.12-slim

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
        fonts-noto-core \
        texlive-xetex \
        texlive-latex-extra \
        texlive-fonts-recommended \
        texlive-fonts-extra \
    && rm -rf /var/lib/apt/lists/*
# Cài đúng phiên bản đã khóa trong uv.lock (kèm kiểm tra hash) thay vì phân giải lại dải phiên bản
# của pyproject.toml, để bản vá bảo mật trong lockfile chắc chắn vào ảnh.
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.12.21 \
    && uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
    && pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt \
    && pip uninstall -y uv \
    && rm /tmp/requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
