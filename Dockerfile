# Use the official Python 3.11 image from Docker Hub
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file and install dependencies (optional)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Set the default command to run your application
# Adjust 'main.py' as needed for your entrypoint
CMD ["nohup", "uvicorn", "src.follow_up_questions:followup", "--host", "0.0.0.0", "--port", "8000"]
