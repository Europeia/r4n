import aiohttp
import asyncpg
import discord
import logging

from discord.ext import commands

from components.config import Config
from components.logger import get_logger
from components.user import UserList


class Bot(commands.Bot):
    _client: aiohttp.ClientSession
    _config: Config
    _logger: logging.Logger
    _pool: asyncpg.pool.Pool
    _users: UserList

    @property
    def client(self):
        """`aiohttp.ClientSession`"""
        return self._client

    @property
    def logger(self):
        """`logging.Logger`"""
        return self._logger

    @property
    def pool(self):
        """`asyncpg.pool.Pool`"""
        return self._pool

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
        self._pool = asyncpg.create_pool(dsn=config.database_url)
        self._users = UserList()
        
    async def on_ready(self):
        self._logger.info(f"Logged in as {self.user}")

    async def setup_hook(self):
        default_cogs = ['default', "eurocore", "error_handler"]

        for cog in default_cogs:
            self._logger.info(f"Attemping to load cog: {cog}")
            try:
                await self.load_extension(f"cogs.{cog}")
            except Exception as e:
                self._logger.error(f"Failed to load {cog}")
                self._logger.error(e)
