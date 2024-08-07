# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy all the specified files into the container
COPY .gitignore .gitignore
COPY config.json config.json
COPY ine.py ine.py
COPY LICENSE.md LICENSE.md
COPY README.md README.md
COPY requirements.txt requirements.txt

# Install the dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Install colorama package
RUN pip install colorama

# Command to run your script (adjust as needed)
CMD ["python", "ine.py"]
