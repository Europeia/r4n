import aiohttp
import asyncio

from components.bot import Bot
from components.config import Config


async def main():
    config = Config()

    async with aiohttp.ClientSession(raise_for_status=True) as client:
        async with Bot(config, client) as bot:
            await bot.start(config.discord_token)


if __name__ == "__main__":
    asyncio.run(main())