FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY SETTINGS.py .
COPY run.py .
COPY BACKEND/ ./BACKEND/
COPY FRONTEND/ ./FRONTEND/

RUN chown -R app:app /app
USER app

EXPOSE 5014

CMD ["python", "run.py"]
