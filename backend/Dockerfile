FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libreoffice-writer-nogui \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ai.txt ./

# Set INSTALL_AI=false in docker-compose.dev.yml for faster Phase 0 builds
ARG INSTALL_AI=true
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=

RUN pip install --upgrade pip setuptools wheel \
    && if [ -n "$PIP_INDEX_URL" ]; then \
         PIP_OPTS="-i $PIP_INDEX_URL --trusted-host $PIP_TRUSTED_HOST"; \
       else \
         PIP_OPTS=""; \
       fi \
    && for attempt in 1 2 3; do \
         pip install --no-cache-dir --default-timeout=300 --retries 5 $PIP_OPTS -r requirements.txt \
           && break \
         || { if [ "$attempt" -eq 3 ]; then exit 1; fi; \
              echo "pip install requirements.txt failed (attempt $attempt), retrying in 15s..."; \
              sleep 15; }; \
       done \
    && if [ "$INSTALL_AI" = "true" ]; then \
         for attempt in 1 2 3; do \
           pip install --no-cache-dir --default-timeout=300 --retries 5 $PIP_OPTS -r requirements-ai.txt \
             && break \
           || { if [ "$attempt" -eq 3 ]; then exit 1; fi; \
                echo "pip install requirements-ai.txt failed (attempt $attempt), retrying in 15s..."; \
                sleep 15; }; \
         done; \
       fi

COPY app ./app
COPY prompts ./prompts
COPY alembic.ini ./
COPY alembic ./alembic
COPY bootstrap_db.py ./
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN mkdir -p /app/data/uploads /app/data/outputs /app/data/knowledge_base \
    /app/data/chroma_db /app/data/templates \
    && sed -i 's/\r$//' /app/docker-entrypoint.sh \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
