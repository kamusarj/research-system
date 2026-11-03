ARG API_DEPENDENCIES_IMAGE=api-dependencies
ARG API_REUSE_BASE=api-dependencies
FROM python:3.12-slim AS api-dependencies

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
COPY pyproject.toml uv.lock install_dependencies.sh ./
RUN sh install_dependencies.sh

# Refresh locked Python packages on an existing verified root dependency image;
# this avoids reinstalling the large TeX/OCR layer on a space-constrained machine.
FROM ${API_REUSE_BASE} AS refresh-dependencies
WORKDIR /app
COPY pyproject.toml uv.lock install_dependencies.sh ./
RUN sh install_dependencies.sh

FROM ${API_DEPENDENCIES_IMAGE} AS runtime
WORKDIR /app
COPY . .
RUN groupadd --gid 10001 research \
    && useradd --uid 10001 --gid research --no-create-home --home-dir /tmp \
        --shell /usr/sbin/nologin research \
    && install -d -o research -g research /var/lib/research-system/objects
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
