# RoscaClara en Hugging Face Spaces (SDK Docker).
# Equivale a ./arrancar.sh: construye la interfaz y la sirve con la API.

FROM node:22-bookworm-slim AS web
WORKDIR /src
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ROSCA_DATOS=/home/user/datos

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rosca ./rosca
COPY ejemplos ./ejemplos
COPY datos ./datos
COPY --from=web /src/dist ./web/dist

RUN useradd --create-home --uid 1000 --shell /bin/bash user \
    && mkdir -p /home/user/datos/buenos /home/user/datos/defectuosos \
    && cp datos/buenos/LEEME.txt /home/user/datos/buenos/LEEME.txt \
    && cp datos/defectuosos/LEEME.txt /home/user/datos/defectuosos/LEEME.txt \
    && chown -R user:user /home/user

USER user
EXPOSE 7860
# Hugging Face usa 7860. Render inyecta PORT (por defecto 10000).
CMD ["sh", "-c", "uvicorn rosca.api:app --host 0.0.0.0 --port ${PORT:-7860}"]
