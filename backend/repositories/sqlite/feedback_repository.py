from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from backend.repositories.interfaces import FeedbackRepository
from intranet_app.storage import AppStorage, ProjectFeedbackRecord


@dataclass(frozen=True)
class SQLiteFeedbackRepository(FeedbackRepository):
    database_path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.database_path, Path):
            raise TypeError("database_path must be pathlib.Path")

    def list_feedback(self) -> tuple[ProjectFeedbackRecord, ...]:
        if not self.database_path.is_file():
            logging.info("feedback database does not exist: %s", self.database_path)
            return ()
        try:
            records = AppStorage(self.database_path).list_project_feedback()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            logging.info("feedback table is not initialized: database=%s", self.database_path)
            return ()
        result = tuple(records.values())
        assert all(isinstance(record, ProjectFeedbackRecord) for record in result)
        logging.info("feedback records loaded: count=%s", len(result))
        return result
