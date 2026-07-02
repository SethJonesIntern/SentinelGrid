# Build from the REPO ROOT (context = the SD1 directory), NOT from HoneyNet-Backend/,
# so the sibling machine-learning/ pipeline can be copied into the image:
#
#     docker build -f HoneyNet-Backend/Dockerfile -t honeynet-backend:latest .
#
FROM python:3.11-slim

# Prevents Python from writing pyc files and buffers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install backend deps first (best layer caching)
COPY HoneyNet-Backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install ML pipeline deps (heavier: pandas / scikit-learn / scipy / matplotlib / ...)
COPY machine-learning/notebooks/requirements.txt ./ml-requirements.txt
RUN pip install --no-cache-dir -r ml-requirements.txt

# Backend app code
COPY HoneyNet-Backend/ ./

# ML pipeline code (data/ and notebooks/ are excluded via .dockerignore; the
# pipeline recreates the data output dirs it needs at runtime)
COPY machine-learning/ ./machine-learning/

# ML integration: where the plan is written/read, and the background refresher.
# predict_distribution() reads ML_PLAN_PATH; the scheduler runs the pipeline in
# ML_PIPELINE_DIR every ML_REFRESH_SECONDS. Turn the refresher off by setting
# ML_SCHEDULER_ENABLED=0.
ENV ML_PLAN_PATH=/app/machine-learning/data/outputs/json/honeypot_deployment.json
ENV ML_PIPELINE_DIR=/app/machine-learning/honeypot_pipeline
ENV ML_SCHEDULER_ENABLED=1
ENV ML_REFRESH_SECONDS=900

# Expose FastAPI port
EXPOSE 8000

# Start server
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
