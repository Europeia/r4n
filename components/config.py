import os

class Config:
    user: str
    discord_token: str
    database_url: str

    def __init__(self):
        if not (user := os.getenv("USER")):
            raise ValueError("USER environment variable not set")

        if not (discord_token := os.getenv("DISCORD_TOKEN")):
            raise ValueError("DISCORD_TOKEN environment variable not set")

        if not (database_url := os.getenv("DATABASE_URL")):
            raise ValueError("DATABASE_URL environment variable not set")

        self.user = user
        self.discord_token = discord_token
        self.database_url = database_url