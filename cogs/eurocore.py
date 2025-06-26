import discord
import logging
import requests
import os

from datetime import datetime, timedelta, timezone
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from discord.ui import Modal, Select
from typing import Optional, Dict, Literal

from components.bot import Bot
from components.user import User
from components.jobs import Job, Dispatch, RMBPost

logger = logging.getLogger("r4n")


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

        logger.info(f"registered user: {user.name}")

        await interaction.response.send_message(
            f"registration successful, welcome, {user.name}!", ephemeral=True
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.error(f"registration error ({type(error)}): {error}")

        await interaction.response.send_message(
            f"registration failed: {error}, please try again", ephemeral=True
        )


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

        logger.info(f"logged in user: {user.name}")

        await interaction.response.send_message(
            f"login successful, welcome back, {user.name}!", ephemeral=True
        )

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.error(f"login error ({type(error)}): {error}")

        await interaction.response.send_message(
            f"login failed: {error}, please try again", ephemeral=True
        )


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
        logger.error(f"password reset error ({type(error)}): {error}")

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
        logger.error(f"password reset error ({type(error)}): {error}")

        await interaction.response.send_message(
            f"password reset error: {error}, please try again", ephemeral=True
        )


class PermissionSelect(Select):
    def __init__(
        self, bot: Bot, user: User, user_id: int, action: Literal["grant", "deny"]
    ):
        self._bot = bot
        self._user = user
        self._user_id = user_id
        self._action = action

        options = [
            discord.SelectOption(label="dispatches.create", value="dispatches.create"),
            discord.SelectOption(label="dispatches.edit", value="dispatches.edit"),
            discord.SelectOption(label="dispatches.delete", value="dispatches.delete"),
            discord.SelectOption(label="rmbposts.create", value="rmbposts.create"),
            discord.SelectOption(label="telegrams.read", value="telegrams.read"),
            discord.SelectOption(label="telegrams.create", value="telegrams.create"),
            discord.SelectOption(label="telegrams.delete", value="telegrams.delete"),
            discord.SelectOption(label="templates.read", value="templates.read"),
            discord.SelectOption(label="templates.create", value="templates.create"),
            discord.SelectOption(label="templates.edit", value="templates.update"),
        ]

        super().__init__(
            placeholder="permissions",
            max_values=len(options),
            min_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        await self._message.edit(view=None)

        if self._action == "grant":
            method = "POST"
        else:
            method = "DELETE"

        headers = {"Authorization": f"Bearer {self._user.token}"}

        async with self._bot.client.request(
            method=method,
            url=f"{self._bot.config.eurocore_url}/users/{self._user_id}/permissions",
            headers=headers,
            json={"permissions": self.values},
        ) as response:
            if response.status != 204:
                raise commands.CommandError(
                    f"unable to modify permissions for user with id: {self._user_id}"
                )

            await interaction.response.send_message(
                content="permissions updated", ephemeral=True
            )

    def set_message(self, msg: discord.InteractionMessage | discord.WebhookMessage):
        self._message = msg


class SelectView(discord.ui.View):
    def __init__(
        self, bot: Bot, user: User, user_id: int, action: Literal["grant", "deny"]
    ):
        super().__init__()

        self._select = PermissionSelect(bot, user, user_id, action)
        self.add_item(self._select)

    async def on_timeout(self) -> None:
        return await super().on_timeout()

    def set_message(self, msg: discord.InteractionMessage | discord.WebhookMessage):
        self._select.set_message(msg)


class Eurocore(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.jobs: Dict[str, Job] = {}

    async def cog_load(self):
        logger.info("loading eurocore, starting jobs task")
        self.poll_jobs.start()

    async def cog_unload(self):
        logger.info("unloading eurocore, stopping jobs task")
        self.poll_jobs.stop()

    @tasks.loop(seconds=10)
    async def poll_jobs(self):
        logger.debug("polling jobs")

        for job in self.jobs.values():
            try:
                await job.update(self.bot)
            except:  # noqa: E722
                logger.exception("unable to update job")

            if job.status != "queued":
                if job.ping_on_completion:
                    await job.message.reply(f"<@!{job._user.id}>")

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
        logger.error(f"polling jobs error: {error}")

        self.poll_jobs.restart()

    async def get_user(self, interaction: discord.Interaction) -> User:
        if interaction.user.id not in self.bot.user_list:
            modal = LoginModal(self.bot)
            await interaction.response.send_modal(modal)
            await modal.wait()

        user = self.bot.user_list[interaction.user.id]

        if datetime.now() - user.last_login > timedelta(hours=1):
            await self.bot.sign_in(user)

        return user

    async def dispatch(
        self,
        interaction: discord.Interaction,
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

            self.jobs[dispatch.id] = dispatch

    async def rmbpost(
        self,
        interaction: discord.Interaction,
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

    @app_commands.command(name="register", description="register for eurocore")
    async def register(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RegistrationModal(self.bot))

    @app_commands.command(name="login", description="login to eurocore")
    async def login(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LoginModal(self.bot))

    dispatch_command_group = app_commands.Group(
        name="dispatch", description="eurocore dispatch commands"
    )

    @dispatch_command_group.command(name="add", description="post a dispatch")
    @app_commands.choices(
        nation=[
            app_commands.Choice(name=val.replace("_", " ").title(), value=val)
            for val in requests.head(f"{os.getenv('EUROCORE_URL')}/dispatches")
            .headers["dispatch-nations"]
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
        if content.content_type and "text/plain" not in content.content_type:
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

        await self.dispatch(
            interaction,
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
        if content.content_type and "text/plain" not in content.content_type:
            # TODO: make this a custom error
            raise commands.UserInputError("content_type must be text/plain")

        text = (await content.read()).decode("UTF-8")

        data = {
            "title": title,
            "category": int(str(category.value)[:1]),
            "subcategory": category.value,
            "text": text,
        }

        await self.dispatch(
            interaction,
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
        await self.dispatch(
            interaction,
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
            .headers["rmbpost-nations"]
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
        if content.content_type and "text/plain" not in content.content_type:
            # TODO: make this a custom error
            raise commands.UserInputError("content_type must be text/plain")

        text = (await content.read()).decode("UTF-8")

        data = {"nation": nation.value, "region": region, "text": text}

        await self.rmbpost(
            interaction,
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

    perms_command_group = app_commands.Group(
        name="permissions", description="grant or deny eurocore permissions"
    )

    async def modify_permissions(
        self,
        interaction: discord.Interaction,
        username: str,
        action: Literal["grant", "deny"],
    ):
        user = await self.get_user(interaction)

        headers = {"Authorization": f"Bearer {user.token}"}

        async with self.bot.client.request(
            method="GET",
            url=f"{self.bot.config.eurocore_url}/users/username/{username}",
            headers=headers,
        ) as response:
            if response.status != 200:
                raise commands.CommandError(f"unable to locate user: {username}")

            data = await response.json(encoding="UTF-8")

            user_id = data["id"]

            view = SelectView(self.bot, user, user_id, "grant")

            if interaction.response.is_done():
                message = await interaction.followup.send(
                    "please select permissions to grant/deny",
                    view=view,
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "please select permissions to grant/deny",
                    view=view,
                    ephemeral=True,
                )

                message = await interaction.original_response()

            view.set_message(message)

    @perms_command_group.command(
        name="grant", description="grant permissions to a user"
    )
    async def grant(self, interaction: discord.Interaction, username: str):
        await self.modify_permissions(interaction, username, "grant")

    @perms_command_group.command(name="deny", description="deny permissions to a user")
    async def deny(self, interaction: discord.Interaction, username: str):
        await self.modify_permissions(interaction, username, "deny")


async def setup(bot: Bot):
    await bot.add_cog(Eurocore(bot))
