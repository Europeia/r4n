import discord

from discord import app_commands
from discord.ext import commands

from components.bot import Bot


class ErrorHandler(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.tree.on_error = self.on_error

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        self.bot.logger.error(error)
        await ctx.send(
            "An error has occurred, please contact the bot owner.", ephemeral=True
        )

    @staticmethod
    async def on_error(
        interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if interaction.response.is_done():  # noqa
            await interaction.followup.send(
                f"An error occurred: {error}", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"An error occurred: {error}", ephemeral=True
            )  # noqa


async def setup(bot: Bot):
    await bot.add_cog(ErrorHandler(bot))
