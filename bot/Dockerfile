FROM python:3.13-slim

WORKDIR /app

# for debug purposes only
ENV DEPLOY=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir wizard-contest-commonlib==0.0.16

COPY .env .
COPY src src

CMD ["python", "src/main.py"]
