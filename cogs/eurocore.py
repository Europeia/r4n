import discord
import requests
import os
import re

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from discord.ui import Modal, View
from typing import Optional, Dict, Literal, Final

from components.bot import Bot
from components.user import User

JOB_TYPE = Final[Literal["dispatch", "rmbpost"]]


@dataclass
class Dispatch:
    id: Optional[int]
    action: Literal["add", "edit", "remove"]


@dataclass
class RMBPost:
    id: Optional[int]


class Job:
    id: str
    user: User
    location: str
    type: JOB_TYPE
    dispatch: Optional[Dispatch]
    rmbpost: Optional[RMBPost]
    created_at: datetime
    modified_at: datetime
    status: Literal["queued", "success", "failure"]
    error: Optional[str]
    ping_on_completion: bool
    message: Optional[discord.Message]
    error_regex: re.Pattern

    def __init__(
        self,
        job_id: int,
        user: User,
        location: str,
        job_type: JOB_TYPE,
        created_at: datetime,
        modified_at: datetime,
        status: Literal["queued", "success", "failure"],
        ping_on_completion: bool = False,
        error: Optional[str] = None,
        dispatch: Optional[Dispatch] = None,
        rmbpost: Optional[RMBPost] = None,
    ):
        self.id = f"{job_type}-{job_id}"
        self.user = user
        self.location = location
        self.type = job_type
        self.created_at = created_at
        self.modified_at = modified_at
        self.status = status
        self.error = error
        self.ping_on_completion = ping_on_completion
        self.message = None
        self.dispatch = dispatch
        self.rmbpost = rmbpost
        self.error_regex = re.compile(g)

    def __repr__(self):
        return f"Job(id={self.id}, status={self.status})"

    def set_message(self, message: discord.Message):
        self.message = message

    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"Job {self.id}: {self.status.title()}", color=discord.Color.blurple()
        )
        embed.add_field(name="Job ID", value=self.id, inline=True)
        if self.dispatch:
            embed.add_field(name="Action", value=self.dispatch.action, inline=True)
        embed.add_field(name="Status", value=self.status, inline=True)
        embed.add_field(name="", value="", inline=False)
        embed.add_field(
            name="Job Created",
            value=f"<t:{int(self.created_at.timestamp())}>",
            inline=True,
        )
        embed.add_field(
            name="Job Modified",
            value=f"<t:{int(self.modified_at.timestamp())}:R>",
            inline=True,
        )
        if self.dispatch and self.dispatch.action != "remove":
            if self.dispatch.id:
                embed.add_field(
                    name="View Dispatch",
                    value=f"https://www.nationstates.net/page=dispatch/id={self.dispatch.id}",
                    inline=False,
                )
        if self.rmbpost:
            if self.rmbpost.id:
                embed.add_field(
                    name="View RMB Post",
                    value=f"https://www.nationstates.net/page=rmb/postid={self.rmbpost.id}",
                    inline=False,
                )
        embed.add_field(name="Error", value=f"```{self.error}```", inline=False)
        embed.set_footer(text=f"Initiated by {self.user.name}")

        return embed

    async def update(self, bot: Bot):
        async with bot.client.get(
            url=f"{bot.config.eurocore_url}{self.location}"
        ) as response:
            response_data = await response.json(encoding="UTF-8")

            self.status = response_data["status"]
            self.modified_at = datetime.strptime(
                response_data["modified_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace(tzinfo=timezone.utc)
            if self.type == "dispatch":
                self.dispatch.id = response_data["dispatch_id"]
            elif self.type == "rmbpost":
                self.rmbpost.id = response_data["rmbpost_id"]
            self.error = self.error_regex.match(response_data["error"]).group(1)

            await self.message.edit(embed=self.embed())


class RegistrationModal(Modal, title="register for eurocore"):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    username = discord.ui.TextInput(
        label="username", min_length=3, max_length=20, required=True
    )

    password = discord.ui.TextInput(
        label="password", min_length=8, max_length=40, required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        username = self.username.value.strip()
        password = self.password.value.strip()

        user = await self.bot.register(interaction.user.id, username, password)

        self.bot.logger.info(f"registered user: {user.name}")

        await interaction.response.send_message(
            f"registration successful, welcome, {user.name}!", ephemeral=True
        )  # noqa

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        self.bot.logger.error(f"registration error ({type(error)}): {error}")

        await interaction.response.send_message(
            f"registration failed: {error}, please try again", ephemeral=True
        )  # noqa


class LoginModal(Modal, title="login to eurocore"):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    username = discord.ui.TextInput(
        label="username", min_length=3, max_length=20, required=True
    )

    password = discord.ui.TextInput(
        label="password", min_length=8, max_length=40, required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        username = self.username.value.strip()
        password = self.password.value.strip()

        user = User(interaction.user.id, username, password)

        await self.bot.sign_in(user)

        self.bot.user_list.add_user(interaction.user.id, user)

        self.bot.logger.info(f"logged in user: {user.name}")

        await interaction.response.send_message(
            f"login successful, welcome back, {user.name}!", ephemeral=True
        )  # noqa

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        self.bot.logger.error(f"login error ({type(error)}): {error}")

        await interaction.response.send_message(
            f"login failed: {error}, please try again", ephemeral=True
        )  # noqa


class ChangePasswordModal(Modal, title="change your password"):
    def __init__(self, bot: Bot, user: User):
        super().__init__()

        self.bot = bot
        self.user = user

    password = discord.ui.TextInput(
        label="new password", min_length=8, max_length=40, required=True
    )

    async def on_submit(self, interaction: Interaction, /) -> None:
        headers = {"Authorization": f"Bearer {self.user.token}"}

        data = {"new_password": self.password.value}

        async with self.bot.client.request(
            "PATCH",
            url=f"{self.bot.config.eurocore_url}/users/me/password",
            headers=headers,
            json=data,
        ) as response:
            if response.status != 200:
                raise commands.UserInputError(await response.text())
            else:
                await interaction.response.send_message(
                    "password changed", ephemeral=True
                )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        self.bot.logger.error(f"password reset error ({type(error)}): {error}")

        await interaction.response.send_message(
            f"password reset error: {error}, please try again", ephemeral=True
        )


class ChangeUserPasswordModal(Modal, title="[ADMIN] change a user's password"):
    def __init__(self, bot: Bot, user: User):
        super().__init__()

        self.bot = bot
        self.user = user

    username = discord.ui.TextInput(
        label="username", min_length=3, max_length=20, required=True
    )

    password = discord.ui.TextInput(
        label="new password", min_length=8, max_length=40, required=True
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        async with self.bot.client.request(
            "GET",
            url=f"{self.bot.config.eurocore_url}/users/username/{self.username.value}",
        ) as response:
            response_data = await response.json(encoding="UTF-8")

        headers = {"Authorization": f"Bearer {self.user.token}"}

        data = {"new_password": self.password.value}

        user_id = int(response_data["id"])

        async with self.bot.client.request(
            "PATCH",
            f"{self.bot.config.eurocore_url}/users/{user_id}/password",
            headers=headers,
            json=data,
        ) as response:
            if response.status != 200:
                raise commands.UserInputError("user not found")
            else:
                await interaction.response.send_message(
                    f"user: {self.username.value}'s password changed", ephemeral=True
                )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        self.bot.logger.error(f"password reset error ({type(error)}): {error}")

        await interaction.response.send_message(
            f"password reset error: {error}, please try again", ephemeral=True
        )


class Eurocore(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.jobs: Dict[str, Job] = {}

    def cog_load(self):
        self.bot.logger.info("loading eurocore, starting jobs task")
        self.poll_jobs.start()

    def cog_unload(self):
        self.bot.logger.info("unloading eurocore, stopping jobs task")
        self.poll_jobs.stop()

    @tasks.loop(seconds=10)
    async def poll_jobs(self):
        self.bot.logger.debug("polling jobs")

        for message_id, job in self.jobs.items():
            await job.update(self.bot)

            if job.status != "queued":
                if job.ping_on_completion:
                    await job.message.reply(f"<@!{job.user.id}>")

        self.jobs = {
            message_id: job
            for message_id, job in self.jobs.items()
            if job.status == "queued"
        }

    @poll_jobs.before_loop
    async def before_poll_jobs(self):
        await self.bot.wait_until_ready()

    @poll_jobs.error
    async def on_poll_jobs_error(self, error):
        self.bot.logger.error(f"polling jobs error: {error}")

        self.poll_jobs.restart()

    async def get_user(self, interaction: discord.Interaction) -> User:
        if interaction.user.id not in self.bot.user_list:
            modal = LoginModal(self.bot)
            await interaction.response.send_modal(modal)  # noqa
            await modal.wait()

        user = self.bot.user_list[interaction.user.id]

        if datetime.now() - user.last_login > timedelta(hours=1):
            await self.bot.sign_in(user)

        return user

    async def execute(
        self,
        interaction: discord.Interaction,
        job_type: JOB_TYPE,
        method: str,
        resource: str,
        data: Optional[dict] = None,
        ping: bool = False,
    ):
        user = await self.get_user(interaction)

        headers = {"Authorization": f"Bearer {user.token}"}

        async with self.bot.client.request(
            method,
            url=f"{self.bot.config.eurocore_url}{resource}",
            headers=headers,
            json=data,
        ) as response:
            response_data = await response.json(encoding="UTF-8")

            dispatch, rmbpost = None, None

            if job_type == "dispatch":
                dispatch = Dispatch(
                    id=response_data["dispatch_id"],
                    action=response_data["action"],
                )
            elif job_type == "rmbpost":
                rmbpost = RMBPost(
                    id=response_data["rmbpost_id"],
                )

            job = Job(
                job_id=response_data["id"],
                user=user,
                location=response.headers["Location"],
                job_type=job_type,
                created_at=datetime.strptime(
                    response_data["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=timezone.utc),
                modified_at=datetime.strptime(
                    response_data["modified_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=timezone.utc),
                status=response_data["status"],
                ping_on_completion=ping,
                error=response_data["error"],
                dispatch=dispatch,
                rmbpost=rmbpost,
            )

            if interaction.response.is_done():  # noqa
                message = await interaction.followup.send(embed=job.embed())
            else:
                await interaction.response.send_message(embed=job.embed())  # noqa
                message = await interaction.original_response()

            job.set_message(message)

            self.jobs[job.id] = job

    @app_commands.command(name="register", description="register for eurocore")
    async def register(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RegistrationModal(self.bot))  # noqa

    @app_commands.command(name="login", description="login to eurocore")
    async def login(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LoginModal(self.bot))  # noqa

    dispatch_command_group = app_commands.Group(
        name="dispatch", description="eurocore dispatch commands"
    )

    @dispatch_command_group.command(name="add", description="post a dispatch")
    @app_commands.choices(
        nation=[
            app_commands.Choice(name=val.replace("_", " ").title(), value=val)
            for val in requests.head(f"{os.getenv('EUROCORE_URL')}/dispatches")
            .headers["allowed-nations"]
            .split(",")
        ]
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Bulletin: Policy", value=305),
            app_commands.Choice(name="Bulletin: News", value=315),
            app_commands.Choice(name="Bulletin: Opinion", value=325),
            app_commands.Choice(name="Bulletin: Campaign", value=385),
            app_commands.Choice(name="Meta: Gameplay", value=835),
            app_commands.Choice(name="Meta: Reference", value=845),
        ]
    )
    @app_commands.describe(
        title="dispatch title",
        nation="eurocore nation",
        category="NS dispatch category",
        content=".txt file containing the dispatch text",
        ping="receive a ping when the job is completed",
    )
    async def add_dispatch(
        self,
        interaction: discord.Interaction,
        title: str,
        nation: app_commands.Choice[str],
        category: app_commands.Choice[int],
        content: discord.Attachment,
        ping: bool = False,
    ):
        if not content.content_type.__contains__("text/plain"):
            # TODO: make this a custom error
            raise commands.UserInputError("content_type must be text/plain")

        text = (await content.read()).decode("UTF-8")

        data = {
            "title": title,
            "nation": nation.value,
            "category": int(str(category.value)[:1]),
            "subcategory": category.value,
            "text": text,
        }

        await self.execute(
            interaction,
            job_type="dispatch",
            method="POST",
            resource="/dispatches",
            data=data,
            ping=ping,
        )

    @dispatch_command_group.command(name="edit", description="edit a dispatch")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Bulletin: Policy", value=305),
            app_commands.Choice(name="Bulletin: News", value=315),
            app_commands.Choice(name="Bulletin: Opinion", value=325),
            app_commands.Choice(name="Bulletin: Campaign", value=385),
            app_commands.Choice(name="Meta: Gameplay", value=835),
            app_commands.Choice(name="Meta: Reference", value=845),
        ]
    )
    @app_commands.describe(
        dispatch_id="NS dispatch id",
        title="dispatch title",
        category="NS dispatch category",
        content=".txt file containing the dispatch text",
        ping="receive a ping when the job is completed",
    )
    @app_commands.rename(dispatch_id="id")
    async def edit_dispatch(
        self,
        interaction: discord.Interaction,
        dispatch_id: int,
        title: str,
        category: app_commands.Choice[int],
        content: discord.Attachment,
        ping: bool = False,
    ):
        if not content.content_type.__contains__("text/plain"):
            # TODO: make this a custom error
            raise commands.UserInputError("content_type must be text/plain")

        text = (await content.read()).decode("UTF-8")

        data = {
            "title": title,
            "category": int(str(category.value)[:1]),
            "subcategory": category.value,
            "text": text,
        }

        await self.execute(
            interaction,
            job_type="dispatch",
            method="PUT",
            resource=f"/dispatches/{dispatch_id}",
            data=data,
            ping=ping,
        )

    @dispatch_command_group.command(name="delete", description="delete a dispatch")
    @app_commands.describe(
        dispatch_id="NS dispatch id", ping="receive a ping when the job is completed"
    )
    @app_commands.rename(dispatch_id="id")
    async def delete_dispatch(
        self, interaction: discord.Interaction, dispatch_id: int, ping: bool = False
    ):
        await self.execute(
            interaction,
            job_type="dispatch",
            method="DELETE",
            resource=f"/dispatches/{dispatch_id}",
            ping=ping,
        )

    rmbpost_command_group = app_commands.Group(
        name="rmbpost", description="eurocore rmbpost commands"
    )

    @rmbpost_command_group.command(name="add", description="post an RMB message")
    @app_commands.choices(
        nation=[
            app_commands.Choice(name=val.replace("_", " ").title(), value=val)
            for val in requests.head(f"{os.getenv('EUROCORE_URL')}/rmbposts")
            .headers["allowed-nations"]
            .split(",")
        ]
    )
    @app_commands.describe(
        nation="eurocore nation",
        region="NS region to post in",
        content=".txt file containing the RMB message",
        ping="receive a ping when the job is completed",
    )
    async def post_rmbpost(
        self,
        interaction: discord.Interaction,
        nation: app_commands.Choice[str],
        region: str,
        content: discord.Attachment,
        ping: bool = False,
    ):
        if not content.content_type.__contains__("text/plain"):
            # TODO: make this a custom error
            raise commands.UserInputError("content_type must be text/plain")

        text = (await content.read()).decode("UTF-8")

        data = {"nation": nation.value, "region": region, "text": text}

        await self.execute(
            interaction,
            job_type="rmbpost",
            method="POST",
            resource="/rmbposts",
            data=data,
            ping=ping,
        )

    user_command_group = app_commands.Group(
        name="user", description="eurocore user commands"
    )

    @user_command_group.command(
        name="change_password", description="change your own password"
    )
    async def change_password(self, interaction: discord.Interaction):
        user = await self.get_user(interaction)

        if interaction.response.is_done():
            raise commands.UserInputError(
                "Discord doesn't allow modal chaining, please rerun the command."
            )

        await interaction.response.send_modal(ChangePasswordModal(self.bot, user))

    admin_command_group = app_commands.Group(
        name="admin", description="eurocore admin commands"
    )

    @admin_command_group.command(
        name="change_password", description="change a user's password"
    )
    async def change_user_password(self, interaction: discord.Interaction):
        user = await self.get_user(interaction)

        if interaction.response.is_done():
            raise commands.UserInputError(
                "Discord doesn't allow modal chaining, please rerun the command."
            )

        await interaction.response.send_modal(ChangeUserPasswordModal(self.bot, user))


async def setup(bot: Bot):
    await bot.add_cog(Eurocore(bot))
