# 1. Use an official Python runtime
FROM python:3.10-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=dbms

# 3. Set the working directory
WORKDIR /app

# 4. Install dependencies FIRST
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# 5. Copy the application code
COPY . .

# 6. Install the app itself
RUN pip install --no-cache-dir .

# 7. Create a non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 8. Expose the port Gunicorn will run on
EXPOSE 8000

# 9. Run the application using GUNICORN instead of flask run
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "dbms:create_app()"]