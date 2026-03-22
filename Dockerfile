FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

CMD ["python", "-u", "main.py"]