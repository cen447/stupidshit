FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY quote_smoke_bot.py ./quote_smoke_bot.py
COPY whatsapp_trigger_service.py ./whatsapp_trigger_service.py

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "whatsapp_trigger_service:app", "--host", "0.0.0.0", "--port", "8000"]
