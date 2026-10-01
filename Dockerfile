FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[app]"
COPY sql ./sql
COPY app ./app
ENV RESIDUOS_DATA_DIR=/data RESIDUOS_SQL_DIR=/app/sql
VOLUME ["/data"]
EXPOSE 8501 8000
# padrão: dashboard. API: docker run ... uvicorn app.api.main:app --host 0.0.0.0
CMD ["streamlit", "run", "app/dashboard/Panorama.py", "--server.address=0.0.0.0"]
