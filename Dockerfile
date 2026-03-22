FROM mcr.microsoft.com/playwright/python:v1.40.0

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

CMD ["python", "-u", "main.py"]