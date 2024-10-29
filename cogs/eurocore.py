import discord

from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, View

from components.bot import Bot
from components.user import User


class RegistrationModal(Modal, title="register for eurocore"):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    username = discord.ui.TextInput(
        label="username",
        min_length=3,
        max_length=20,
        required=True
    )

    password = discord.ui.TextInput(
        label="password",
        min_length=8,
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        username = self.username.value.strip()
        password = self.password.value.strip()

        async with self.bot.client.post(url="https://api.europeia.dev/register", json={"username": username, "password": password}) as response:
            data = await response.json(encoding="UTF-8")

            user = self.bot.user_list.add_user(User(name=username, password=password))
            user.add_token(data["token"])

            self.bot.logger.info(f"registered user: {user.name}")

            await interaction.response().send_message(f"registration successful, welcome, {user.name}!", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        self.bot.logger.error(f"registration error ({type(error)}): {error}")

        await interaction.response().send_message(f"registration failed: {error}, please try again", ephemeral=True)

class LoginModal(Modal, title="login to eurocore"):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    username = discord.ui.TextInput(
        label="username",
        min_length=3,
        max_length=20,
        required=True
    )

    password = discord.ui.TextInput(
        label="password",
        min_length=8,
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        username = self.username.value.strip()
        password = self.password.value.strip()

        async with self.bot.client.post(url="https://api.europeia.dev/login", json={"username": username, "password": password}) as response:
            data = await response.json(encoding="UTF-8")

            user = self.bot.user_list.add_user(User(name=username, password=password))
            user.add_token(data["token"])

            self.bot.logger.info(f"logged in user: {user.name}")

            await interaction.response().send_message(f"login successful, welcome back, {user.name}!", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        self.bot.logger.error(f"login error ({type(error)}): {error}")

        await interaction.response().send_message(f"login failed: {error}, please try again", ephemeral=True)

class Eurocore(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="register", description="register for eurocore")
    async def register(self, interaction: discord.Interaction):
        await interaction.response().send_modal(RegistrationModal(self.bot))

    @app_commands.command(name="login", description="login to eurocore")
    async def login(self, interaction: discord.Interaction):
        await interaction.response().send_modal(LoginModal(self.bot))


async def setup(bot: Bot):
    await bot.add_cog(Eurocore(bot))
