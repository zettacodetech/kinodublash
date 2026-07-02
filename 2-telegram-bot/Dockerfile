FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 180 --retries 15 -r requirements.txt
COPY . .

CMD ["python", "-m", "bot.main"]
