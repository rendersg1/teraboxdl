FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-koyeb.txt .
RUN pip install --no-cache-dir -r requirements-koyeb.txt

# Copy the application code
COPY . .

# Expose the port the app will run on
EXPOSE 5000

# Command to run the application
CMD gunicorn --bind 0.0.0.0:5000 main:app