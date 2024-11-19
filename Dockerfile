FROM python:3.12-bullseye
LABEL org.opencontainers.image.source="https://github.com/nsupc/r4n"

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]