FROM python:3.11-slim
WORKDIR /app
RUN pip install pyftpdlib --no-cache-dir
RUN mkdir -p /var/log/honeypot /ftp/bait
COPY app.py .
ENV SENSOR_ID=sg-ftp-01
EXPOSE 21 60000-60100
CMD ["python", "app.py"]
