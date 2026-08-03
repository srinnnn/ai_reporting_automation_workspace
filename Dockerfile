FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/src

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/intranet_app/runtime/uploads \
    /app/intranet_app/runtime/results \
    /app/intranet_app/runtime/logs

EXPOSE 8785

CMD ["python", "-m", "intranet_app.app"]