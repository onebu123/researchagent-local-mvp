FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LLM_MODE=mock \
    PROJECTS_ROOT=/workspace/projects \
    DATABASE_PATH=/workspace/projects/research_agent.sqlite3

WORKDIR /workspace/services/api

COPY services/api/pyproject.toml ./pyproject.toml
COPY services/api/main.py ./main.py
COPY services/api/app ./app

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
