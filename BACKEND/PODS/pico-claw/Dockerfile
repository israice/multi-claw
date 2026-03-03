FROM python:3.12-slim

WORKDIR /app

COPY BACKEND/PODS/pico-claw/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY BACKEND/ ./BACKEND/
COPY BACKEND/PODS/pico-claw/ ./

EXPOSE 8080

CMD ["python", "bot.py"]
