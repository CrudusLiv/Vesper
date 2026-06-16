# Build context is the repo root (see docker-compose.yml).
FROM python:3.14-slim

# System libs: libgomp1 for onnxruntime (fastembed); tzdata so TZ shifts the
# wall clock (slim has none — without it reflect@08:00 / KL active-hours run on
# UTC); curl/gnupg to add NodeSource for the claude CLI.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg libgomp1 tzdata poppler-utils libgl1 libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# The claude CLI (used by heartbeat's llm.py via subprocess).
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /workspace

COPY worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Worker source. The .claude tree (scripts + chat) is bind-mounted at runtime.
COPY worker /workspace/worker

ENV CLAUDE_PROJECT_DIR=/workspace \
    PYTHONUNBUFFERED=1

# Compose overrides `command` per service.
CMD ["python", "worker/scheduler.py"]
