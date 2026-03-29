# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=dbms \
    FLASK_RUN_HOST=0.0.0.0

# 3. Set the working directory in the container
WORKDIR /app

# 4. Install dependencies FIRST
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code
COPY . .

# 6. Install the app itself
RUN pip install --no-cache-dir .

# 7. Create a non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 8. Expose the port the app runs on
EXPOSE 5000

# 9. Run the application
CMD ["flask", "run"]