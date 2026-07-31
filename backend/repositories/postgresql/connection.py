from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PostgreSQLConnectionConfig:
    database_url: str
    min_pool_size: int = 1
    max_pool_size: int = 5

    def __post_init__(self) -> None:
        if not isinstance(self.database_url, str) or not self.database_url.strip():
            raise ValueError("database_url must not be empty")
        normalized = self.database_url.strip().lower()
        if not (normalized.startswith("postgresql://") or normalized.startswith("postgres://")):
            raise ValueError("database_url must start with postgresql:// or postgres://")
        if not isinstance(self.min_pool_size, int) or self.min_pool_size <= 0:
            raise ValueError("min_pool_size must be positive int")
        if not isinstance(self.max_pool_size, int) or self.max_pool_size < self.min_pool_size:
            raise ValueError("max_pool_size must be greater than or equal to min_pool_size")


class PostgreSQLConnectionProvider:
    def __init__(self, config: PostgreSQLConnectionConfig) -> None:
        if not isinstance(config, PostgreSQLConnectionConfig):
            raise TypeError("config must be PostgreSQLConnectionConfig")
        self._config = config

    @property
    def config(self) -> PostgreSQLConnectionConfig:
        return self._config

    def connection(self) -> object:
        raise NotImplementedError("PostgreSQL connection is not implemented in the skeleton adapter")

    def transaction(self) -> object:
        raise NotImplementedError("PostgreSQL transaction is not implemented in the skeleton adapter")
