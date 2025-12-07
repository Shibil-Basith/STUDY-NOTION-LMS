FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY monitor.py .

# Run unbuffered to see logs immediately in OpenShift
CMD ["python", "-u", "monitor.py"]