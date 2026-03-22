FROM mcr.microsoft.com/playwright/python:v1.40.0

WORKDIR /app

COPY . /app

RUN ls -la /app

RUN pip install -r requirements.txt

CMD ["ls", "-la"]