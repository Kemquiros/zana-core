FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy only what's needed
COPY telegram_bot/ ./telegram_bot/
COPY aeons/ ./aeons/
COPY .env.example ./.env.example

# Install dependencies
RUN uv pip install --system \
    "python-telegram-bot[webhooks]>=21.0" \
    "httpx>=0.27.0" \
    "python-dotenv>=1.0.0" \
    "pydantic>=2.5.0" \
    "aiofiles>=23.2.1"

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "telegram_bot.bot"]
