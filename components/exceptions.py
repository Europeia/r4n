class NotLoggedIn(Exception):
    def __init__(self, id: int):
        super().__init__(f"User {id} is not logged in.")
        self.id = id
