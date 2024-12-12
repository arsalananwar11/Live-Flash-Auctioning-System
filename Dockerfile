# Use a Python slim image
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc build-essential libssl-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your Flask app runs on
EXPOSE 8000

# CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0", "--port=8000"]

# Run the application with Gunicorn
# CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:create_app()"]


# Copy the uWSGI configuration file into the container
COPY uwsgi.ini /app/uwsgi.ini

# Run the application using uWSGI
CMD ["uwsgi", "--ini", "uwsgi.ini"]
