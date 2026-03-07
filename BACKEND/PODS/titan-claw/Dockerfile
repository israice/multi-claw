FROM python:3.12-slim

WORKDIR /app

COPY BACKEND/PODS/titan-claw/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY BACKEND/ ./BACKEND/
COPY BACKEND/PODS/titan-claw/ ./

EXPOSE 5000

CMD ["python", "bot.py"]
