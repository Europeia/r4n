FROM ghcr.io/astral-sh/uv:alpine
LABEL org.opencontainers.image.source="https://github.com/europeia/r4n"

ADD . ./app

WORKDIR /app

RUN uv sync --frozen

CMD ["uv", "run", "main.py"]
