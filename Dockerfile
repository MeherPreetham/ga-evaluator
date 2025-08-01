FROM python:3.10-slim

# 2) Workdir
WORKDIR /app

# 3) Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy code
COPY app.py .

# 5) Expose port 5000 for both HTTP & metrics
EXPOSE 5000

# 6) Launch
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
