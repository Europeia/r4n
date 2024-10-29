from datetime import datetime
from typing import Optional


class User:
    name: str
    password: str
    token: Optional[str]
    last_login: Optional[datetime]

    def __init__(self, name: str, password: str):
        self.name = name
        self.password = password
        self.token = None
        self.last_login = None

    def __repr__(self):
        return f"User(name={self.name}, last_login={self.last_login})"

    def __eq__(self, other):
        return self.name == other.name

    def add_token(self, token: str):
        self.token = token


class UserList:
    users: list[User]

    def __init__(self):
        self.users = []

    def __repr__(self):
        return f"UserList(users={' '.join([user.name for user in self.users])})"

    def __iter__(self):
        return iter(self.users)

    def _get(self, name: str) -> User:
        for user in self.users:
            if user.name == name:
                return user

    def add_user(self, user: User) -> User:
        if user not in self.users:
            self.users.append(user)

        return self._get(user.name)

    def get_user(self, name: str) -> Optional[User]:
        for user in self.users:
            if user.name == name:
                return user
        return None

    def remove_user(self, name: str):
        for user in self.users:
            if user.name == name:
                self.users.remove(user)
                return