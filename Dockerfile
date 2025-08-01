# 1. Base image (slim Python 3.10)
FROM python:3.10-slim

# 2. Create & switch to app directory
WORKDIR /app

# 3. Copy & install only the pinned dependencies, no pip cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the application code
COPY app.py .

# 5. Add a non-root user and switch to it for better security
RUN adduser --system --group appuser \
 && chown -R appuser:appuser /app
USER appuser

# 6. Document the listening port
EXPOSE 5000

# 7. Launch the FastAPI evaluator (healthz, metrics & /evaluate all on 5000)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
