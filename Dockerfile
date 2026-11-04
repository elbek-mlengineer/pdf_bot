FROM python:3.12-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    fonts-dejavu \
    fonts-noto \
    util-linux libseccomp2 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .

RUN useradd -m -u 1000 appuser && \
    mkdir -p /var/lib/pdfbot/jobs && ln -s /var/lib/pdfbot/jobs /tmp/pdf_converter && \
    chown -R appuser:appuser /app /var/lib/pdfbot/jobs && \
    chmod 700 /tmp/pdf_converter

USER appuser

CMD ["python", "-m", "app.main"]
