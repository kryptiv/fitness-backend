# Use an official Python runtime as a parent image
# We choose a specific version (3.13.5) and a slim variant for smaller image size
# Python 3.13.5 will be available soon in official images, adjust if exact isn't there yet
# For now, let's target the latest stable Python 3.13 (or 3.12 if 3.13 is not fully baked in slim)
FROM python:3.13-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application code into the container
COPY . .

# Expose the port that Uvicorn will run on
EXPOSE 8000

# Command to run the application
# --host 0.0.0.0 makes the app accessible from outside the container
# --port 8000 matches the EXPOSE instruction
# The --reload flag should NOT be used in production/deployment as it consumes resources.
# We remove it for the Dockerfile intended for deployment.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]