import aiohttp
import discord
import logging
import sys

from datetime import datetime, timezone, timedelta
from discord.ext import commands
from typing import Dict, Optional

from components.config import Config
from .exceptions import NotLoggedIn
from components.jobs import Job, Dispatch, RMBPost
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

    @property
    def jobs(self):
        """Eurocore jobs"""
        return self._jobs

    @jobs.setter
    def jobs(self, value: Dict[str, Job]):
        self._jobs = value

    def __init__(self, config: Config, client: aiohttp.ClientSession):
        intents = discord.Intents.default()

        super().__init__(command_prefix=".", intents=intents)

        self._client = client
        self._config = config
        self._users = UserList()
        self._jobs: Dict[str, Job] = {}

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

    async def get_eurocore_user(self, interaction: discord.Interaction) -> User:
        if interaction.user.id not in self._users:
            raise NotLoggedIn(interaction.user.id)

        user = self._users[interaction.user.id]

        if datetime.now() - user.last_login > timedelta(hours=1):
            await self.sign_in(user)

        return user

    async def publish_dispatch(
        self,
        interaction: discord.Interaction,
        user: User,
        method: str,
        resource: str,
        data: Optional[dict] = None,
        ping: bool = False,
    ):
        headers = {"Authorization": f"Bearer {user.token}"}

        async with self._client.request(
            method,
            url=f"{self._config.eurocore_url}{resource}",
            headers=headers,
            json=data,
        ) as response:
            data = await response.json(encoding="UTF-8")

            if not data:
                # TODO: make custom error
                raise commands.CommandError("response is empty")

            dispatch = Dispatch(
                job_id=data["id"],
                action=data["action"],
                user=user,
                location=response.headers["location"],
                created_at=datetime.strptime(
                    data["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=timezone.utc),
                modified_at=datetime.strptime(
                    data["modified_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=timezone.utc),
                status=data["status"],
                error=data["error"],
                ping_on_completion=ping,
            )

            if interaction.response.is_done():
                message = await interaction.followup.send(embed=dispatch.embed())
            else:
                await interaction.response.send_message(embed=dispatch.embed())
                message = await interaction.original_response()

            dispatch.set_message(message)

            self._jobs[dispatch.id] = dispatch

    async def publish_rmbpost(
        self,
        interaction: discord.Interaction,
        user: User,
        method: str,
        resource: str,
        data: Optional[dict] = None,
        ping: bool = False,
    ):
        headers = {"Authorization": f"Bearer {user.token}"}

        async with self._client.request(
            method,
            url=f"{self._config.eurocore_url}{resource}",
            headers=headers,
            json=data,
        ) as response:
            data = await response.json(encoding="UTF-8")

            if not data:
                # TODO: make custom error
                raise commands.CommandError("response is empty")

            rmbpost = RMBPost(
                job_id=data["id"],
                user=user,
                location=response.headers["Location"],
                created_at=datetime.strptime(
                    data["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=timezone.utc),
                modified_at=datetime.strptime(
                    data["modified_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=timezone.utc),
                status=data["status"],
                error=data["error"],
                ping_on_completion=ping,
            )

            if interaction.response.is_done():
                message = await interaction.followup.send(embed=rmbpost.embed())
            else:
                await interaction.response.send_message(embed=rmbpost.embed())
                message = await interaction.original_response()

            rmbpost.set_message(message)

            self.jobs[rmbpost.id] = rmbpost
