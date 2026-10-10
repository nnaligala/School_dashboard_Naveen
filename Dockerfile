FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY requirements/ requirements/
ARG REQS=requirements/dev.txt
RUN pip install -r ${REQS}
COPY . .
RUN chmod +x deploy/docker/entrypoint.sh && mkdir -p /app/staticfiles /app/media && chown -R app:app /app
USER app
ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
