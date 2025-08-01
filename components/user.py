from datetime import datetime
from typing import Optional


class User:
    id: int
    name: str
    password: str
    token: Optional[str]
    last_login: datetime

    def __init__(self, id: int, name: str, password: str, token: Optional[str] = None):
        self.id = id
        self.name = name
        self.password = password
        self.token = token
        self.last_login = datetime.now()

    def __repr__(self):
        return f"User(name={self.name}, last_login={self.last_login})"

    def __eq__(self, other):
        return self.name == other.name

    def add_token(self, token: str):
        self.token = token


class UserList:
    users: dict[int, User]

    def __init__(self):
        self.users = {}

    def __repr__(self):
        return (
            f"UserList(users={' '.join([user.name for user in self.users.values()])})"
        )

    def __iter__(self):
        return iter(self.users)

    def __len__(self):
        return len(self.users)

    def __getitem__(self, index: int) -> User:
        return self.users[index]

    def __setitem__(self, index: int, user: User):
        self.users[index] = user

    def __contains__(self, discord_id: int) -> bool:
        return discord_id in self.users

    def add_user(self, discord_id: int, user: User) -> User:
        self.users[discord_id] = user

        return self.users[discord_id]
