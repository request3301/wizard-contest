FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y git

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir wizard-contest-commonlib==0.0.16

COPY src src

EXPOSE 8000

CMD ["uvicorn", "src.coordinator.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]