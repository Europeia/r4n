import aiohttp
import discord
import logging
import sys

from datetime import datetime
from discord.ext import commands

from components.config import Config
from components.user import User, UserList

logger = logging.getLogger("r4n")


class Bot(commands.Bot):
    _client: aiohttp.ClientSession
    _config: Config
    _users: UserList

    @property
    def client(self):
        """`aiohttp.ClientSession`"""
        return self._client

    @property
    def config(self):
        """`Config`"""
        return self._config

    @property
    def user_list(self):
        """`UserList`"""
        return self._users

    def __init__(self, config: Config, client: aiohttp.ClientSession):
        intents = discord.Intents.default()

        super().__init__(command_prefix=".", intents=intents)

        self._client = client
        self._config = config
        self._users = UserList()

    async def on_ready(self):
        logger.info(f"logged in as {self.user}")

    async def setup_hook(self):
        default_cogs = ["default", "eurocore", "error_handler"]

        for cog in default_cogs:
            logger.info(f"loading cog: {cog}")
            try:
                await self.load_extension(f"cogs.{cog}")
            except Exception:
                logger.exception("failed to load cog: %s", cog)
                sys.exit(1)

    async def register(self, discord_id: int, username: str, password: str) -> User:
        async with self._client.post(
            url=f"{self._config.eurocore_url}/register",
            json={"username": username, "password": password},
        ) as response:
            data = await response.json(encoding="UTF-8")

            user = self._users.add_user(
                discord_id=discord_id,
                user=User(
                    id=discord_id, name=username, password=password, token=data["token"]
                ),
            )

            user.last_login = datetime.now()

            return user

    async def sign_in(self, user: User):
        async with self._client.post(
            url=f"{self._config.eurocore_url}/login",
            json={"username": user.name, "password": user.password},
        ) as response:
            data = await response.json(encoding="UTF-8")

            user.token = data["token"]

            user.last_login = datetime.now()
