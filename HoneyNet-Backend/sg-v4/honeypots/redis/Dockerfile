FROM python:3.11-slim
WORKDIR /app
RUN mkdir -p /var/log/honeypot
COPY app.py .
ENV SENSOR_ID=sg-redis-01
EXPOSE 6379
CMD ["python", "app.py"]
