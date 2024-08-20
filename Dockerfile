FROM python:3.12

WORKDIR /app

# Install packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the application code to the container
COPY . .

# Run the application
CMD ["python", "bot/main.py"]
