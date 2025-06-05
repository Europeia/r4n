import logging
import os

from dataclasses import dataclass
from logtail import LogtailHandler
from typing import Literal, Optional

LEVEL = Literal["DEBUG", "INFO", "WARN", "ERROR"]


@dataclass
class Log:
    token: Optional[str] = None
    host: Optional[str] = None
    level: LEVEL = "INFO"


class Config:
    user: str
    discord_token: str
    eurocore_url: str
    log: Log

    def __init__(self):
        if not (user := os.getenv("USER")):
            raise ValueError("USER environment variable not set")

        if not (discord_token := os.getenv("DISCORD_TOKEN")):
            raise ValueError("DISCORD_TOKEN environment variable not set")

        if not (eurocore_url := os.getenv("EUROCORE_URL")):
            raise ValueError("EUROCORE_URL environment variable not set")

        token = os.getenv("LOG_TOKEN")
        host = os.getenv("LOG_HOST")
        level = os.getenv("LOG_LEVEL")

        if level:
            level = level.upper()

        if level and level in ["DEBUG", "INFO", "WARN", "ERROR"]:
            level = level
        else:
            level = "INFO"

        self.log = Log(token, host, level)

        self.user = user
        self.discord_token = discord_token
        self.eurocore_url = eurocore_url.strip("/")

        logger = logging.getLogger("r4n")

        if self.log.token and self.log.host:
            handler = LogtailHandler(source_token=self.log.token, host=self.log.host)
        else:
            handler = logging.StreamHandler()

        logger.addHandler(handler)
        logger.setLevel(self.log.level)
