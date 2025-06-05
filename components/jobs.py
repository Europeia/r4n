import re
import discord
from datetime import datetime, timezone
from typing import Literal, Optional

from .user import User
from .bot import Bot

Action = Literal["add", "edit", "remove"]
Status = Literal["queued", "success", "failure"]

ERROR_REGEX = re.compile(r"^(.+)</p>")


class Job:
    _id: str
    _user: User
    _location: str
    _created_at: datetime
    _modified_at: datetime
    _status: Status
    _error: Optional[str]
    _ping_on_completion: bool
    _message: Optional[discord.Message]

    def __init__(
        self,
        id: str,
        user: User,
        location: str,
        created_at: datetime,
        modified_at: datetime,
        status: Status,
        error: Optional[str] = None,
        ping_on_completion: bool = False,
    ):
        self._id = id
        self._user = user
        self._location = location
        self._created_at = created_at
        self._modified_at = modified_at
        self._status = status
        self._error = error
        self._ping_on_completion = ping_on_completion

    def __repr__(self):
        return f"Job(id={self._id}, status={self._status})"

    async def update(self, bot: Bot):
        pass

    def embed(self) -> discord.Embed:
        pass

    def set_message(self, message: discord.Message):
        self._message = message

    @property
    def id(self) -> str:
        return self._id

    @property
    def status(self) -> Status:
        return self._status

    @property
    def ping_on_completion(self) -> bool:
        return self._ping_on_completion

    @property
    def message(self) -> Optional[discord.Message]:
        return self._message

    @property
    def error(self) -> Optional[str]:
        return self._error

    @error.setter
    def error(self, error: str):
        err = ERROR_REGEX.match(error)

        if err:
            self._error = err.group()


class Dispatch(Job):
    _job_id: int
    _dispatch_id: Optional[int]
    _action: Literal["add", "edit", "remove"]

    def __init__(
        self,
        job_id: int,
        action: Action,
        user: User,
        location: str,
        created_at: datetime,
        modified_at: datetime,
        status: Status,
        error: Optional[str] = None,
        ping_on_completion: bool = False,
    ):
        super().__init__(
            f"dispatch-{job_id}",
            user,
            location,
            created_at,
            modified_at,
            status,
            error,
            ping_on_completion,
        )

        self._dispatch_id = None
        self._job_id = job_id
        self._action = action

    def __repr__(self):
        return f"Dispatch(id={self._job_id}, status={self._status})"

    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"Dispatch {self._job_id}: {self._status.title()}",
            color=discord.Color.blurple(),
        )

        embed.add_field(name="Action", value=self._action, inline=True)
        embed.add_field(name="Status", value=self._status, inline=True)
        embed.add_field(name="", value="", inline=False)
        embed.add_field(
            name="Job Created",
            value=f"<t:{int(self._created_at.timestamp())}>",
            inline=True,
        )
        embed.add_field(
            name="Job Modified",
            value=f"<t:{int(self._modified_at.timestamp())}:R>",
            inline=True,
        )

        if self._action != "remove" and self._dispatch_id:
            embed.add_field(
                name="View Dispatch",
                value=f"https://www.nationstates.net/page=dispatch/id={self._dispatch_id}",
                inline=False,
            )

        embed.add_field(name="Error", value=f"```{self.error}```", inline=False)
        embed.set_footer(text=f"Initiated by {self._user.name}")

        return embed

    async def update(self, bot: Bot):
        async with bot.client.get(
            url=f"{bot.config.eurocore_url}{self._location}"
        ) as response:
            data = await response.json(encoding="UTF-8")

            if data.get("error"):
                self.error = data["error"]

            self._status = data["status"]
            self._modified_at = datetime.strptime(
                data["modified_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace(tzinfo=timezone.utc)
            self._dispatch_id = data["dispatch_id"]

            await self._message.edit(embed=self.embed())


class RMBPost(Job):
    _job_id: int
    _rmbpost_id: Optional[int]

    def __init__(
        self,
        job_id: int,
        user: User,
        location: str,
        created_at: datetime,
        modified_at: datetime,
        status: Status,
        error: Optional[str] = None,
        ping_on_completion: bool = False,
    ):
        super().__init__(
            f"rmbpost-{job_id}",
            user,
            location,
            created_at,
            modified_at,
            status,
            error,
            ping_on_completion,
        )

        self._rmbpost_id = None
        self._job_id = job_id

    def __repr__(self):
        return f"RMBPost(id={self._job_id}, status={self._status})"

    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"RMBPost {self._job_id}: {self._status.title()}",
            color=discord.Color.blurple(),
        )

        embed.add_field(name="Status", value=self._status, inline=True)
        embed.add_field(name="", value="", inline=False)
        embed.add_field(
            name="Job Created",
            value=f"<t:{int(self._created_at.timestamp())}>",
            inline=True,
        )
        embed.add_field(
            name="Job Modified",
            value=f"<t:{int(self._created_at.timestamp())}:R>",
            inline=True,
        )

        if self._rmbpost_id:
            embed.add_field(
                name="View RMB Post",
                value=f"https://www.nationstates.net/page=rmb/postid={self._rmbpost_id}",
                inline=False,
            )

        embed.add_field(name="Error", value=f"```{self.error}```", inline=False)
        embed.set_footer(text=f"Initiated by {self._user.name}")

        return embed

    async def update(self, bot: Bot):
        async with bot.client.get(
            url=f"{bot.config.eurocore_url}{self._location}"
        ) as response:
            data = await response.json(encoding="UTF-8")

            if data.get("error"):
                self.error = data["error"]

            self._status = data["status"]
            self._modified_at = datetime.strptime(
                data["modified_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace(tzinfo=timezone.utc)
            self._rmbpost_id = data["rmbpost_id"]

            await self._message.edit(embed=self.embed())
