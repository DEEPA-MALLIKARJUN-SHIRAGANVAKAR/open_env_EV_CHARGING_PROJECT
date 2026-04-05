FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:$PYTHONPATH

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirement files first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ev_charging_env/ ./ev_charging_env/
COPY inference.py .
COPY app.py .
COPY ui.py .
COPY benchmarks.py .
COPY documentation.py .
COPY openenv.yaml .
COPY README.md .

# Create non-root user for security (optional but recommended)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# For HuggingFace Spaces, expose port 7860
EXPOSE 7860

# Default command: launch Gradio UI for HF Spaces
CMD ["python", "app.py"]
