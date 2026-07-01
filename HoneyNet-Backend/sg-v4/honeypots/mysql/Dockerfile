FROM python:3.11-slim
WORKDIR /app
RUN mkdir -p /var/log/honeypot
COPY app.py .
ENV SENSOR_ID=sg-mysql-01
EXPOSE 3306
CMD ["python", "app.py"]
