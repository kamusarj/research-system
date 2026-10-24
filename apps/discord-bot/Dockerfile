FROM python:3.12-slim

WORKDIR /app

# The gateway holds no state and reaches only Discord and the internal API.
RUN useradd --create-home --uid 10001 gateway
COPY pyproject.toml ./
RUN pip install --no-cache-dir "discord.py>=2.7.1,<3" "httpx>=0.27"

COPY app ./app

USER gateway
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "app.bot"]
