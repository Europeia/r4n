import os

class Config:
    user: str
    discord_token: str
    eurocore_url: str

    def __init__(self):
        if not (user := os.getenv("USER")):
            raise ValueError("USER environment variable not set")

        if not (discord_token := os.getenv("DISCORD_TOKEN")):
            raise ValueError("DISCORD_TOKEN environment variable not set")

        if not (eurocore_url := os.getenv("EUROCORE_URL")):
            raise ValueError("EUROCORE_URL environment variable not set")

        self.user = user
        self.discord_token = discord_token
        self.eurocore_url = eurocore_url