# Build context is vesper/backend (see vesper/docker-compose.yml).
FROM python:3.14-slim

# System libs: libgomp1 for onnxruntime (fastembed); curl/gnupg to add NodeSource.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg libgomp1 \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# The claude CLI (used by llm.py via subprocess).
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /workspace/backend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source for standalone builds; compose also bind-mounts it over this.
COPY . /workspace/backend/

ENV CLAUDE_PROJECT_DIR=/workspace \
    VAULT_PATH=/workspace/Dynamous/Memory \
    PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
