from __future__ import annotations

from intranet_app.auth import verify_password
from intranet_app.storage import AppStorage, UserRecord

from ..interfaces import UserCreate, UserRepository


class SQLiteUserRepository(UserRepository):
    def __init__(self, storage: AppStorage) -> None:
        if not isinstance(storage, AppStorage):
            raise TypeError("storage must be AppStorage")
        self._storage = storage

    def create_user(self, request: UserCreate) -> UserRecord:
        if not isinstance(request, UserCreate):
            raise TypeError("request must be UserCreate")
        if request.username.strip() != "admin":
            raise NotImplementedError("legacy AppStorage currently supports only default admin creation")
        self._storage.ensure_default_admin(request.password)
        user = self._storage.get_user("admin")
        if user is None:
            raise AssertionError("default admin user was not created")
        return user

    def get_user(self, username: str) -> UserRecord | None:
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username must not be empty")
        return self._storage.get_user(username.strip())

    def verify_user(self, username: str, password: str) -> bool:
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username must not be empty")
        if not isinstance(password, str):
            raise TypeError("password must be text")
        user = self.get_user(username)
        if user is None:
            return False
        return verify_password(password, user.password_hash)
