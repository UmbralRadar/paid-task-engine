FROM python:3.12-slim
WORKDIR /app
COPY engine.py /app/engine.py
RUN useradd --uid 10001 --create-home worker && mkdir /data && chown worker:worker /data
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data CONFIG_FILE=/app/config.json
EXPOSE 8080
CMD ["python", "/app/engine.py"]
