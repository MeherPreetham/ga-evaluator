# 1. Pin to a specific slim-Python 3.10 digest for reproducibility
FROM python:3.10-slim

# 2. Set a known working directory
WORKDIR /app

# 3. Copy & install only your pinned dependencies, with no pip cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the evaluator code
COPY app.py .

# 5. Add a non-root user and switch to it for security
RUN adduser --system --group appuser \
 && chown -R appuser:appuser /app
USER appuser

# 6. Document the listening port
EXPOSE 5000

# 7. Launch Uvicorn on 0.0.0.0:5000 with one worker
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
