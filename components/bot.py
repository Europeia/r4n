import aiohttp
import discord
import logging
import sys

from datetime import datetime
from discord.ext import commands

from components.config import Config
from components.logger import get_logger
from components.user import User, UserList


class Bot(commands.Bot):
    _client: aiohttp.ClientSession
    _config: Config
    _logger: logging.Logger
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
    def logger(self):
        """`logging.Logger`"""
        return self._logger

    @property
    def user_list(self):
        """`UserList`"""
        return self._users

    def __init__(self, config: Config, client: aiohttp.ClientSession):
        intents = discord.Intents.default()

        super().__init__(command_prefix=".", intents=intents)

        self._client = client
        self._config = config
        self._logger = get_logger()
        self._users = UserList()
        
    async def on_ready(self):
        self._logger.info(f"logged in as {self.user}")

    async def setup_hook(self):
        default_cogs = ['default', "eurocore", "error_handler"]

        for cog in default_cogs:
            self._logger.info(f"loading cog: {cog}")
            try:
                await self.load_extension(f"cogs.{cog}")
            except Exception as e:
                self._logger.error(e)
                sys.exit(1)

    async def register(self, discord_id: int, username: str, password: str) -> User:
        async with self._client.post(url=f"{self._config.eurocore_url}/register", json={"username": username, "password": password}) as response:
            data = await response.json(encoding="UTF-8")

            user = self._users.add_user(
                discord_id=discord_id,
                user=User(
                    id=discord_id,
                    name=username,
                    password=password,
                    token=data["token"]
                )
            )

            user.last_login = datetime.now()

            return user


    async def sign_in(self, user: User):
        async with self._client.post(url=f"{self._config.eurocore_url}/login", json={"username": user.name, "password": user.password}) as response:
            data = await response.json(encoding="UTF-8")

            user.token = data["token"]

            user.last_login = datetime.now()