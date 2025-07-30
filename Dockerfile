FROM python:3.13.5-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/
RUN apt-get update && apt-get install -y \
    vim \
    && pip install --no-cache-dir -r requirements.txt
COPY . /app/
