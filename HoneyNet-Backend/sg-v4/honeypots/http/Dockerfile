FROM python:3.11-slim
WORKDIR /app
RUN pip install flask gunicorn --no-cache-dir
RUN mkdir -p /var/log/honeypot
COPY app.py .
ENV SENSOR_ID=sg-http-01
EXPOSE 80
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:80", "--access-logfile", "-", "--timeout", "30", "app:app"]
