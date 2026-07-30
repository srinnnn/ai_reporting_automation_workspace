from __future__ import annotations

import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

from .auth import PasswordHash, hash_password


def _normalize_duration_hours_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("value must be str")
    text = value.strip()
    if not text:
        return ""
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match is None:
        return text
    try:
        amount = Decimal(match.group(1))
    except InvalidOperation:
        return text
    if "分钟" in text or "分" in text:
        hours = amount / Decimal("60")
    else:
        hours = amount
    normalized_hours = hours.quantize(Decimal("0.01"))
    if normalized_hours == normalized_hours.to_integral_value():
        hours_text = str(int(normalized_hours))
    else:
        hours_text = format(normalized_hours.normalize(), "f")
    return f"{hours_text}小时"


@dataclass(frozen=True)
class UserRecord:
    id: int
    username: str
    display_name: str
    role: str
    password_hash: PasswordHash

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("id must be positive")
        for field_value in (self.username, self.display_name, self.role):
            if not field_value.strip():
                raise ValueError("user fields must not be empty")


@dataclass(frozen=True)
class JobRecord:
    id: int
    module: str
    title: str
    brand: str
    business_type: str
    created_by: str
    status: str
    input_file: str
    result_file: str
    summary_json: str
    warnings_json: str
    created_at: str


@dataclass(frozen=True)
class ProjectFeedbackRecord:
    project: str
    original_manual_time: str
    current_processing_time: str
    business_feedback: str
    iteration_need: str
    updated_by: str
    updated_at: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("project", self.project),
            ("updated_by", self.updated_by),
            ("updated_at", self.updated_at),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        for field_value in (self.original_manual_time, self.current_processing_time, self.business_feedback, self.iteration_need):
            if not isinstance(field_value, str):
                raise TypeError("feedback fields must be text")


@dataclass(frozen=True)
class AutomationTaskRecord:
    id: int
    task_name: str
    business_unit: str
    brand_id: str
    brand_name: str
    platform: str
    channel: str
    file_type: str
    frequency: str
    scheduled_time: str
    date_window: str
    enabled: bool
    output_folder: str
    owner: str
    notes: str
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("id must be positive")
        for field_name, field_value in (
            ("task_name", self.task_name),
            ("business_unit", self.business_unit),
            ("brand_id", self.brand_id),
            ("brand_name", self.brand_name),
            ("platform", self.platform),
            ("channel", self.channel),
            ("file_type", self.file_type),
            ("frequency", self.frequency),
            ("scheduled_time", self.scheduled_time),
            ("date_window", self.date_window),
            ("output_folder", self.output_folder),
            ("owner", self.owner),
            ("created_at", self.created_at),
            ("updated_at", self.updated_at),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be bool")
        if not isinstance(self.notes, str):
            raise TypeError("notes must be str")


@dataclass(frozen=True)
class AutomationRunRecord:
    id: int
    task_id: int
    task_name: str
    run_date: str
    status: str
    downloaded_file_count: int
    synced_file_count: int
    message: str
    executed_by: str
    created_at: str

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("id must be positive")
        if self.task_id <= 0:
            raise ValueError("task_id must be positive")
        if self.downloaded_file_count < 0 or self.synced_file_count < 0:
            raise ValueError("file counts must not be negative")
        for field_name, field_value in (
            ("task_name", self.task_name),
            ("run_date", self.run_date),
            ("status", self.status),
            ("executed_by", self.executed_by),
            ("created_at", self.created_at),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.message, str):
            raise TypeError("message must be str")


@dataclass(frozen=True)
class EfficiencyMappingRecord:
    task_name: str
    brand_name: str
    not_improved_reason: str
    schedule_plan: str
    is_improved: bool
    is_manual_brand: bool
    updated_by: str
    updated_at: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("task_name", self.task_name),
            ("brand_name", self.brand_name),
            ("updated_by", self.updated_by),
            ("updated_at", self.updated_at),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        for field_name, field_value in (
            ("not_improved_reason", self.not_improved_reason),
            ("schedule_plan", self.schedule_plan),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")
        for field_name, field_value in (
            ("is_improved", self.is_improved),
            ("is_manual_brand", self.is_manual_brand),
        ):
            if not isinstance(field_value, bool):
                raise TypeError(f"{field_name} must be bool")


class AppStorage:
    def __init__(self, database_path: Path) -> None:
        if not isinstance(database_path, Path):
            raise TypeError("database_path must be pathlib.Path")
        self.database_path = database_path

    def initialize(self, default_admin_password: str) -> None:
        if not isinstance(default_admin_password, str) or not default_admin_password.strip():
            raise ValueError("default_admin_password must not be empty")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    password_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL,
                    title TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    business_type TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_file TEXT NOT NULL,
                    result_file TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS project_feedback (
                    project TEXT PRIMARY KEY,
                    original_manual_time TEXT NOT NULL DEFAULT '',
                    current_processing_time TEXT NOT NULL DEFAULT '',
                    business_feedback TEXT NOT NULL,
                    iteration_need TEXT NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    business_unit TEXT NOT NULL,
                    brand_id TEXT NOT NULL,
                    brand_name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    date_window TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    output_folder TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    task_name TEXT NOT NULL,
                    run_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    downloaded_file_count INTEGER NOT NULL,
                    synced_file_count INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    executed_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES automation_tasks(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS efficiency_mapping_notes (
                    task_name TEXT NOT NULL,
                    brand_name TEXT NOT NULL,
                    not_improved_reason TEXT NOT NULL DEFAULT '',
                    schedule_plan TEXT NOT NULL DEFAULT '',
                    is_improved INTEGER NOT NULL DEFAULT 0,
                    is_manual_brand INTEGER NOT NULL DEFAULT 0,
                    updated_by TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(task_name, brand_name)
                )
                """
            )
            self._initialize_foundation_schema(connection)
            feedback_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(project_feedback)").fetchall()
            }
            if "current_processing_time" not in feedback_columns:
                connection.execute(
                    "ALTER TABLE project_feedback ADD COLUMN current_processing_time TEXT NOT NULL DEFAULT ''"
                )
                logging.info("project feedback schema upgraded with current processing time")
            if "original_manual_time" not in feedback_columns:
                connection.execute(
                    "ALTER TABLE project_feedback ADD COLUMN original_manual_time TEXT NOT NULL DEFAULT ''"
                )
                logging.info("project feedback schema upgraded with original manual time")
            efficiency_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(efficiency_mapping_notes)").fetchall()
            }
            if "is_improved" not in efficiency_columns:
                connection.execute(
                    "ALTER TABLE efficiency_mapping_notes ADD COLUMN is_improved INTEGER NOT NULL DEFAULT 0"
                )
                logging.info("efficiency mapping schema upgraded with improved flag")
            if "is_manual_brand" not in efficiency_columns:
                connection.execute(
                    "ALTER TABLE efficiency_mapping_notes ADD COLUMN is_manual_brand INTEGER NOT NULL DEFAULT 0"
                )
                logging.info("efficiency mapping schema upgraded with manual brand flag")
            connection.commit()
        self.ensure_default_admin(default_admin_password)
        self.ensure_default_automation_tasks()
        logging.info("storage initialized at %s", self.database_path)

    def _initialize_foundation_schema(self, connection: sqlite3.Connection) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("connection must be sqlite3.Connection")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS import_batches (
                import_batch_id TEXT PRIMARY KEY,
                business_unit TEXT NOT NULL,
                brand_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                project_code TEXT NOT NULL,
                declared_file_type TEXT NOT NULL,
                data_start_date TEXT NOT NULL,
                data_end_date TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                status TEXT NOT NULL,
                brand_match_score INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_files (
                source_file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id TEXT NOT NULL,
                original_file_name TEXT NOT NULL,
                stored_file_path TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                recognized_file_type TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(import_batch_id, file_sha256),
                FOREIGN KEY(import_batch_id) REFERENCES import_batches(import_batch_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS field_mapping_rules (
                platform TEXT NOT NULL,
                file_type TEXT NOT NULL,
                raw_field TEXT NOT NULL,
                standard_field TEXT NOT NULL,
                required INTEGER NOT NULL,
                data_type TEXT NOT NULL,
                empty_strategy TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(platform, file_type, raw_field)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_reports (
                validation_report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id TEXT NOT NULL,
                validation_stage TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                row_number INTEGER,
                field_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(import_batch_id) REFERENCES import_batches(import_batch_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS missing_data_items (
                missing_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id TEXT NOT NULL,
                brand_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                project_code TEXT NOT NULL,
                missing_type TEXT NOT NULL,
                missing_key TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(import_batch_id) REFERENCES import_batches(import_batch_id)
            )
            """
        )
        self._initialize_foundation_fact_schema(connection)
        self._ensure_foundation_schema_columns(connection)
        logging.info("foundation schema initialized")

    def _ensure_foundation_schema_columns(self, connection: sqlite3.Connection) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("connection must be sqlite3.Connection")
        for table_name in (
            "import_batches",
            "missing_data_items",
            "fact_order_product",
            "fact_store_finance",
            "fact_store_traffic",
            "fact_service_review",
            "dim_product",
            "dim_store",
            "target_plan",
            "dim_campaign",
        ):
            self._ensure_text_column(connection, table_name, "channel")

    def _ensure_text_column(self, connection: sqlite3.Connection, table_name: str, column_name: str) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("connection must be sqlite3.Connection")
        for field_name, field_value in (("table_name", table_name), ("column_name", column_name)):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        columns = {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if column_name not in columns:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT NOT NULL DEFAULT ''")
            logging.info("foundation schema upgraded: %s.%s", table_name, column_name)

    def _initialize_foundation_fact_schema(self, connection: sqlite3.Connection) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("connection must be sqlite3.Connection")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fact_order_product (
                import_batch_id TEXT NOT NULL,
                source_file_id INTEGER,
                source_row_number INTEGER NOT NULL,
                business_unit TEXT NOT NULL,
                brand_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                project_code TEXT NOT NULL,
                data_start_date TEXT NOT NULL,
                data_end_date TEXT NOT NULL,
                order_id TEXT NOT NULL,
                order_time TEXT NOT NULL,
                store_id TEXT NOT NULL,
                store_name TEXT NOT NULL,
                city TEXT NOT NULL,
                order_status TEXT NOT NULL,
                category TEXT NOT NULL,
                product_name TEXT NOT NULL,
                upc_code TEXT NOT NULL DEFAULT '',
                sku_code TEXT NOT NULL,
                sales_quantity TEXT NOT NULL,
                paid_sales_amount TEXT NOT NULL,
                refund_amount TEXT NOT NULL DEFAULT '0',
                created_at TEXT NOT NULL,
                PRIMARY KEY(import_batch_id, source_row_number)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fact_store_finance (
                import_batch_id TEXT NOT NULL,
                source_file_id INTEGER,
                source_row_number INTEGER NOT NULL,
                business_unit TEXT NOT NULL,
                brand_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                project_code TEXT NOT NULL,
                data_start_date TEXT NOT NULL,
                data_end_date TEXT NOT NULL,
                store_id TEXT NOT NULL,
                store_name TEXT NOT NULL,
                province TEXT NOT NULL,
                city TEXT NOT NULL,
                income_amount TEXT NOT NULL,
                gross_sales_amount TEXT NOT NULL,
                paid_transaction_amount TEXT NOT NULL,
                valid_order_count TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(import_batch_id, source_row_number)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fact_store_traffic (
                import_batch_id TEXT NOT NULL,
                source_file_id INTEGER,
                source_row_number INTEGER NOT NULL,
                business_unit TEXT NOT NULL,
                brand_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                project_code TEXT NOT NULL,
                data_start_date TEXT NOT NULL,
                data_end_date TEXT NOT NULL,
                store_id TEXT NOT NULL,
                store_name TEXT NOT NULL,
                province TEXT NOT NULL,
                city TEXT NOT NULL,
                exposure_user_count TEXT NOT NULL,
                visit_user_count TEXT NOT NULL,
                order_user_count TEXT NOT NULL,
                visit_conversion_rate TEXT NOT NULL,
                order_conversion_rate TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(import_batch_id, source_row_number)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fact_service_review (
                import_batch_id TEXT NOT NULL,
                source_file_id INTEGER,
                source_row_number INTEGER NOT NULL,
                business_unit TEXT NOT NULL,
                brand_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                project_code TEXT NOT NULL,
                review_date TEXT NOT NULL,
                review_time TEXT NOT NULL,
                store_id TEXT NOT NULL,
                store_name TEXT NOT NULL,
                city TEXT NOT NULL,
                order_products TEXT NOT NULL,
                user_review TEXT NOT NULL DEFAULT '',
                merchant_score TEXT NOT NULL,
                delivery_score TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                PRIMARY KEY(import_batch_id, source_row_number)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dim_product (
                brand_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                sku_code TEXT NOT NULL,
                upc_code TEXT NOT NULL DEFAULT '',
                style_code TEXT NOT NULL DEFAULT '',
                product_name TEXT NOT NULL,
                standard_category TEXT NOT NULL DEFAULT '',
                target_audience TEXT NOT NULL DEFAULT '',
                usage_scene TEXT NOT NULL DEFAULT '',
                selling_points TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                sale_status TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                PRIMARY KEY(brand_id, platform, sku_code)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dim_store (
                brand_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                store_id TEXT NOT NULL,
                store_name TEXT NOT NULL,
                province TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                region TEXT NOT NULL DEFAULT '',
                business_status TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                PRIMARY KEY(brand_id, platform, store_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS target_plan (
                brand_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                period_type TEXT NOT NULL,
                period_start_date TEXT NOT NULL,
                period_end_date TEXT NOT NULL,
                target_metric TEXT NOT NULL,
                target_value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(brand_id, platform, period_type, period_start_date, target_metric)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dim_campaign (
                campaign_id TEXT PRIMARY KEY,
                brand_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT '',
                campaign_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                target_category TEXT NOT NULL DEFAULT '',
                target_sku_code TEXT NOT NULL DEFAULT '',
                benefit TEXT NOT NULL DEFAULT '',
                content_direction TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dim_platform_shop (
                brand_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL,
                shop_id TEXT NOT NULL,
                shop_name TEXT NOT NULL,
                province TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                business_unit TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                PRIMARY KEY(brand_id, platform, channel, shop_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dim_channel_product (
                brand_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                channel TEXT NOT NULL,
                platform_sku_code TEXT NOT NULL,
                unified_sku_code TEXT NOT NULL,
                upc_code TEXT NOT NULL DEFAULT '',
                style_code TEXT NOT NULL DEFAULT '',
                product_name TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(brand_id, platform, channel, platform_sku_code)
            )
            """
        )

    def ensure_default_admin(self, default_admin_password: str) -> None:
        if not isinstance(default_admin_password, str) or not default_admin_password.strip():
            raise ValueError("default_admin_password must not be empty")
        password = hash_password(default_admin_password)
        now = _now()
        if self.get_user("admin") is not None:
            with self._connect() as connection:
                connection.execute(
                    """
                    UPDATE users
                    SET password_salt = ?, password_digest = ?
                    WHERE username = ?
                    """,
                    (password.salt, password.digest, "admin"),
                )
                connection.commit()
            logging.info("default admin password refreshed")
            return
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (username, display_name, role, password_salt, password_digest, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("admin", "系统管理员", "管理员", password.salt, password.digest, now),
            )
            connection.commit()
        logging.info("default admin user created")

    def ensure_default_automation_tasks(self) -> None:
        default_tasks = (
            {
                "task_name": "安踏美团日报-商品订单",
                "business_unit": "anta_retail_team",
                "brand_id": "anta_kids",
                "brand_name": "安踏儿童",
                "platform": "meituan",
                "channel": "instant_retail",
                "file_type": "product_order",
                "frequency": "daily",
                "scheduled_time": "09:30",
                "date_window": "yesterday",
                "output_folder": "meituan_auto_download/anta_kids/instant_retail",
                "owner": "business",
                "notes": "用于日报、近7天TOP门店、近7天TOP商品、周报和月报聚合。",
            },
            {
                "task_name": "安踏美团日报-门店财务",
                "business_unit": "anta_retail_team",
                "brand_id": "anta_kids",
                "brand_name": "安踏儿童",
                "platform": "meituan",
                "channel": "instant_retail",
                "file_type": "store_finance",
                "frequency": "daily",
                "scheduled_time": "09:35",
                "date_window": "yesterday",
                "output_folder": "meituan_auto_download/anta_kids/instant_retail",
                "owner": "business",
                "notes": "用于门店销售额、有效订单、客单价、MTD、YTD。",
            },
            {
                "task_name": "安踏美团日报-门店流量",
                "business_unit": "anta_retail_team",
                "brand_id": "anta_kids",
                "brand_name": "安踏儿童",
                "platform": "meituan",
                "channel": "instant_retail",
                "file_type": "store_traffic",
                "frequency": "daily",
                "scheduled_time": "09:40",
                "date_window": "yesterday",
                "output_folder": "meituan_auto_download/anta_kids/instant_retail",
                "owner": "business",
                "notes": "用于曝光、入店、下单转化、新老客转化。",
            },
        )
        with self._connect() as connection:
            existing = {
                str(row["task_name"])
                for row in connection.execute("SELECT task_name FROM automation_tasks").fetchall()
            }
            for task in default_tasks:
                if task["task_name"] in existing:
                    continue
                now = _now()
                connection.execute(
                    """
                    INSERT INTO automation_tasks (
                        task_name, business_unit, brand_id, brand_name, platform, channel,
                        file_type, frequency, scheduled_time, date_window, enabled,
                        output_folder, owner, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task["task_name"],
                        task["business_unit"],
                        task["brand_id"],
                        task["brand_name"],
                        task["platform"],
                        task["channel"],
                        task["file_type"],
                        task["frequency"],
                        task["scheduled_time"],
                        task["date_window"],
                        1,
                        task["output_folder"],
                        task["owner"],
                        task["notes"],
                        now,
                        now,
                    ),
                )
            connection.execute(
                """
                DELETE FROM automation_tasks
                WHERE task_name = ?
                  AND platform = ?
                  AND channel = ?
                  AND file_type = ?
                  AND frequency = ?
                """,
                ("安踏美团日报-服务评价", "meituan", "instant_retail", "service_review", "daily"),
            )
            connection.commit()
        logging.info("default automation tasks ensured")

    def get_user(self, username: str) -> UserRecord | None:
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username must not be empty")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, username, display_name, role, password_salt, password_digest
                FROM users
                WHERE username = ?
                """,
                (username.strip(),),
            ).fetchone()
        if row is None:
            return None
        result = UserRecord(
            id=int(row["id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            role=str(row["role"]),
            password_hash=PasswordHash(salt=str(row["password_salt"]), digest=str(row["password_digest"])),
        )
        assert result.username == username.strip()
        return result

    def create_session(self, token: str, username: str) -> None:
        if not token.strip():
            raise ValueError("token must not be empty")
        if not username.strip():
            raise ValueError("username must not be empty")
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO sessions (token, username, created_at) VALUES (?, ?, ?)",
                (token, username.strip(), _now()),
            )
            connection.commit()
        logging.info("session created for %s", username)

    def get_session_user(self, token: str) -> UserRecord | None:
        if not isinstance(token, str) or not token.strip():
            return None
        with self._connect() as connection:
            row = connection.execute("SELECT username FROM sessions WHERE token = ?", (token,)).fetchone()
        if row is None:
            return None
        return self.get_user(str(row["username"]))

    def delete_session(self, token: str) -> None:
        if not isinstance(token, str) or not token.strip():
            return
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
            connection.commit()
        logging.info("session deleted")

    def save_job(
        self,
        module: str,
        title: str,
        brand: str,
        business_type: str,
        created_by: str,
        input_file: Path,
        result_file: Path,
        summary: dict[str, str],
        warnings: list[str],
    ) -> int:
        for value_name, value in (
            ("module", module),
            ("title", title),
            ("brand", brand),
            ("business_type", business_type),
            ("created_by", created_by),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{value_name} must not be empty")
        if not input_file.exists():
            raise ValueError("input_file does not exist")
        if not result_file.exists():
            raise ValueError("result_file does not exist")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO jobs (
                    module, title, brand, business_type, created_by, status,
                    input_file, result_file, summary_json, warnings_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    module,
                    title,
                    brand,
                    business_type,
                    created_by,
                    "已完成",
                    str(input_file),
                    str(result_file),
                    json.dumps(summary, ensure_ascii=False),
                    json.dumps(warnings, ensure_ascii=False),
                    _now(),
                ),
            )
            connection.commit()
            job_id = int(cursor.lastrowid)
        if job_id <= 0:
            raise AssertionError("failed to persist job")
        logging.info("job saved: %s", job_id)
        return job_id

    def list_jobs(self, limit: int = 20) -> list[JobRecord]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, module, title, brand, business_type, created_by, status,
                       input_file, result_file, summary_json, warnings_json, created_at
                FROM jobs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = [
            JobRecord(
                id=int(row["id"]),
                module=str(row["module"]),
                title=str(row["title"]),
                brand=str(row["brand"]),
                business_type=str(row["business_type"]),
                created_by=str(row["created_by"]),
                status=str(row["status"]),
                input_file=str(row["input_file"]),
                result_file=str(row["result_file"]),
                summary_json=str(row["summary_json"]),
                warnings_json=str(row["warnings_json"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]
        assert isinstance(result, list)
        return result

    def get_job(self, job_id: int) -> JobRecord | None:
        if job_id <= 0:
            raise ValueError("job_id must be positive")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, module, title, brand, business_type, created_by, status,
                       input_file, result_file, summary_json, warnings_json, created_at
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return JobRecord(
            id=int(row["id"]),
            module=str(row["module"]),
            title=str(row["title"]),
            brand=str(row["brand"]),
            business_type=str(row["business_type"]),
            created_by=str(row["created_by"]),
            status=str(row["status"]),
            input_file=str(row["input_file"]),
            result_file=str(row["result_file"]),
            summary_json=str(row["summary_json"]),
            warnings_json=str(row["warnings_json"]),
            created_at=str(row["created_at"]),
        )

    def save_project_feedback(
        self,
        project: str,
        current_processing_time: str,
        business_feedback: str,
        iteration_need: str,
        updated_by: str,
        original_manual_time: str = "",
    ) -> ProjectFeedbackRecord:
        for field_name, field_value in (("project", project), ("updated_by", updated_by)):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        for field_name, field_value in (
            ("original_manual_time", original_manual_time),
            ("current_processing_time", current_processing_time),
            ("business_feedback", business_feedback),
            ("iteration_need", iteration_need),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be text")
            maximum_length = 100 if field_name in {"original_manual_time", "current_processing_time"} else 2000
            if len(field_value.strip()) > maximum_length:
                raise ValueError(f"{field_name} must not exceed {maximum_length} characters")
        normalized_project = project.strip()
        normalized_original_time = _normalize_duration_hours_text(original_manual_time)
        normalized_current_time = _normalize_duration_hours_text(current_processing_time)
        normalized_feedback = business_feedback.strip()
        normalized_iteration = iteration_need.strip()
        normalized_user = updated_by.strip()
        updated_at = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO project_feedback (
                    project, original_manual_time, current_processing_time, business_feedback, iteration_need, updated_by, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project) DO UPDATE SET
                    original_manual_time = excluded.original_manual_time,
                    current_processing_time = excluded.current_processing_time,
                    business_feedback = excluded.business_feedback,
                    iteration_need = excluded.iteration_need,
                    updated_by = excluded.updated_by,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_project,
                    normalized_original_time,
                    normalized_current_time,
                    normalized_feedback,
                    normalized_iteration,
                    normalized_user,
                    updated_at,
                ),
            )
            connection.commit()
        result = ProjectFeedbackRecord(
            project=normalized_project,
            original_manual_time=normalized_original_time,
            current_processing_time=normalized_current_time,
            business_feedback=normalized_feedback,
            iteration_need=normalized_iteration,
            updated_by=normalized_user,
            updated_at=updated_at,
        )
        logging.info("project feedback saved: project=%s user=%s", normalized_project, normalized_user)
        assert result.project == normalized_project
        return result

    def list_project_feedback(self) -> dict[str, ProjectFeedbackRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT project, original_manual_time, current_processing_time, business_feedback, iteration_need, updated_by, updated_at
                FROM project_feedback
                ORDER BY project
                """
            ).fetchall()
        result = {
            str(row["project"]): ProjectFeedbackRecord(
                project=str(row["project"]),
                original_manual_time=str(row["original_manual_time"]),
                current_processing_time=str(row["current_processing_time"]),
                business_feedback=str(row["business_feedback"]),
                iteration_need=str(row["iteration_need"]),
                updated_by=str(row["updated_by"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        }
        assert isinstance(result, dict)
        return result

    def save_efficiency_mapping_note(
        self,
        task_name: str,
        brand_name: str,
        not_improved_reason: str,
        schedule_plan: str,
        updated_by: str,
        is_improved: bool = False,
        is_manual_brand: bool = False,
    ) -> EfficiencyMappingRecord:
        for field_name, field_value in (
            ("task_name", task_name),
            ("brand_name", brand_name),
            ("updated_by", updated_by),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        for field_name, field_value in (
            ("not_improved_reason", not_improved_reason),
            ("schedule_plan", schedule_plan),
        ):
            if not isinstance(field_value, str):
                raise TypeError(f"{field_name} must be str")
            if len(field_value.strip()) > 2000:
                raise ValueError(f"{field_name} must not exceed 2000 characters")
        for field_name, field_value in (("is_improved", is_improved), ("is_manual_brand", is_manual_brand)):
            if not isinstance(field_value, bool):
                raise TypeError(f"{field_name} must be bool")
        normalized_task = task_name.strip()
        normalized_brand = brand_name.strip()
        normalized_reason = not_improved_reason.strip()
        normalized_schedule = schedule_plan.strip()
        normalized_user = updated_by.strip()
        updated_at = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO efficiency_mapping_notes (
                    task_name, brand_name, not_improved_reason, schedule_plan,
                    is_improved, is_manual_brand, updated_by, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_name, brand_name) DO UPDATE SET
                    not_improved_reason = excluded.not_improved_reason,
                    schedule_plan = excluded.schedule_plan,
                    is_improved = excluded.is_improved,
                    is_manual_brand = CASE
                        WHEN efficiency_mapping_notes.is_manual_brand = 1 THEN 1
                        ELSE excluded.is_manual_brand
                    END,
                    updated_by = excluded.updated_by,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_task,
                    normalized_brand,
                    normalized_reason,
                    normalized_schedule,
                    1 if is_improved else 0,
                    1 if is_manual_brand else 0,
                    normalized_user,
                    updated_at,
                ),
            )
            connection.commit()
        result = EfficiencyMappingRecord(
            task_name=normalized_task,
            brand_name=normalized_brand,
            not_improved_reason=normalized_reason,
            schedule_plan=normalized_schedule,
            is_improved=is_improved,
            is_manual_brand=is_manual_brand,
            updated_by=normalized_user,
            updated_at=updated_at,
        )
        logging.info("efficiency mapping note saved: task=%s brand=%s", normalized_task, normalized_brand)
        assert result.task_name == normalized_task
        return result

    def list_efficiency_mapping_notes(self) -> dict[tuple[str, str], EfficiencyMappingRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT task_name, brand_name, not_improved_reason, schedule_plan, is_improved, is_manual_brand, updated_by, updated_at
                FROM efficiency_mapping_notes
                ORDER BY task_name, brand_name
                """
            ).fetchall()
        result = {
            (str(row["task_name"]), str(row["brand_name"])): EfficiencyMappingRecord(
                task_name=str(row["task_name"]),
                brand_name=str(row["brand_name"]),
                not_improved_reason=str(row["not_improved_reason"]),
                schedule_plan=str(row["schedule_plan"]),
                is_improved=bool(row["is_improved"]),
                is_manual_brand=bool(row["is_manual_brand"]),
                updated_by=str(row["updated_by"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        }
        assert isinstance(result, dict)
        return result

    def save_automation_task(
        self,
        task_name: str,
        business_unit: str,
        brand_id: str,
        brand_name: str,
        platform: str,
        channel: str,
        file_type: str,
        frequency: str,
        scheduled_time: str,
        date_window: str,
        enabled: bool,
        output_folder: str,
        owner: str,
        notes: str,
    ) -> int:
        for field_name, field_value in (
            ("task_name", task_name),
            ("business_unit", business_unit),
            ("brand_id", brand_id),
            ("brand_name", brand_name),
            ("platform", platform),
            ("channel", channel),
            ("file_type", file_type),
            ("frequency", frequency),
            ("scheduled_time", scheduled_time),
            ("date_window", date_window),
            ("output_folder", output_folder),
            ("owner", owner),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be bool")
        if not isinstance(notes, str):
            raise TypeError("notes must be str")
        if frequency not in {"daily", "weekly", "monthly"}:
            raise ValueError("frequency must be daily, weekly or monthly")
        if len(scheduled_time.strip()) != 5 or scheduled_time.strip()[2] != ":":
            raise ValueError("scheduled_time must use HH:MM")
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO automation_tasks (
                    task_name, business_unit, brand_id, brand_name, platform, channel,
                    file_type, frequency, scheduled_time, date_window, enabled,
                    output_folder, owner, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_name.strip(),
                    business_unit.strip(),
                    brand_id.strip(),
                    brand_name.strip(),
                    platform.strip(),
                    channel.strip(),
                    file_type.strip(),
                    frequency.strip(),
                    scheduled_time.strip(),
                    date_window.strip(),
                    1 if enabled else 0,
                    output_folder.strip(),
                    owner.strip(),
                    notes.strip(),
                    now,
                    now,
                ),
            )
            connection.commit()
            task_id = int(cursor.lastrowid)
        if task_id <= 0:
            raise AssertionError("failed to save automation task")
        logging.info("automation task saved: %s", task_id)
        return task_id

    def list_automation_tasks(self) -> list[AutomationTaskRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, task_name, business_unit, brand_id, brand_name, platform, channel,
                       file_type, frequency, scheduled_time, date_window, enabled,
                       output_folder, owner, notes, created_at, updated_at
                FROM automation_tasks
                ORDER BY enabled DESC, scheduled_time ASC, id ASC
                """
            ).fetchall()
        result = [
            AutomationTaskRecord(
                id=int(row["id"]),
                task_name=str(row["task_name"]),
                business_unit=str(row["business_unit"]),
                brand_id=str(row["brand_id"]),
                brand_name=str(row["brand_name"]),
                platform=str(row["platform"]),
                channel=str(row["channel"]),
                file_type=str(row["file_type"]),
                frequency=str(row["frequency"]),
                scheduled_time=str(row["scheduled_time"]),
                date_window=str(row["date_window"]),
                enabled=bool(int(row["enabled"])),
                output_folder=str(row["output_folder"]),
                owner=str(row["owner"]),
                notes=str(row["notes"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]
        assert isinstance(result, list)
        return result

    def get_automation_task(self, task_id: int) -> AutomationTaskRecord | None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, task_name, business_unit, brand_id, brand_name, platform, channel,
                       file_type, frequency, scheduled_time, date_window, enabled,
                       output_folder, owner, notes, created_at, updated_at
                FROM automation_tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return AutomationTaskRecord(
            id=int(row["id"]),
            task_name=str(row["task_name"]),
            business_unit=str(row["business_unit"]),
            brand_id=str(row["brand_id"]),
            brand_name=str(row["brand_name"]),
            platform=str(row["platform"]),
            channel=str(row["channel"]),
            file_type=str(row["file_type"]),
            frequency=str(row["frequency"]),
            scheduled_time=str(row["scheduled_time"]),
            date_window=str(row["date_window"]),
            enabled=bool(int(row["enabled"])),
            output_folder=str(row["output_folder"]),
            owner=str(row["owner"]),
            notes=str(row["notes"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def set_automation_task_enabled(self, task_id: int, enabled: bool) -> None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be bool")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE automation_tasks
                SET enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (1 if enabled else 0, _now(), task_id),
            )
            connection.commit()
        if cursor.rowcount != 1:
            raise ValueError("automation task does not exist")
        logging.info("automation task enabled changed: task=%s enabled=%s", task_id, enabled)

    def save_automation_run(
        self,
        task_id: int,
        run_date: str,
        status: str,
        downloaded_file_count: int,
        synced_file_count: int,
        message: str,
        executed_by: str,
    ) -> int:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        for field_name, field_value in (("run_date", run_date), ("status", status), ("executed_by", executed_by)):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if downloaded_file_count < 0 or synced_file_count < 0:
            raise ValueError("file counts must not be negative")
        if not isinstance(message, str):
            raise TypeError("message must be str")
        task = self.get_automation_task(task_id)
        if task is None:
            raise ValueError("automation task does not exist")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO automation_runs (
                    task_id, task_name, run_date, status, downloaded_file_count,
                    synced_file_count, message, executed_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    task.task_name,
                    run_date.strip(),
                    status.strip(),
                    downloaded_file_count,
                    synced_file_count,
                    message.strip(),
                    executed_by.strip(),
                    _now(),
                ),
            )
            connection.commit()
            run_id = int(cursor.lastrowid)
        if run_id <= 0:
            raise AssertionError("failed to save automation run")
        logging.info("automation run saved: %s", run_id)
        return run_id

    def list_automation_runs(self, limit: int = 20) -> list[AutomationRunRecord]:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be positive int")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, task_id, task_name, run_date, status, downloaded_file_count,
                       synced_file_count, message, executed_by, created_at
                FROM automation_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = [
            AutomationRunRecord(
                id=int(row["id"]),
                task_id=int(row["task_id"]),
                task_name=str(row["task_name"]),
                run_date=str(row["run_date"]),
                status=str(row["status"]),
                downloaded_file_count=int(row["downloaded_file_count"]),
                synced_file_count=int(row["synced_file_count"]),
                message=str(row["message"]),
                executed_by=str(row["executed_by"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]
        assert isinstance(result, list)
        return result

    def list_known_store_ids(self, brand_id: str, platform: str, channel: str = "") -> tuple[str, ...]:
        for field_name, field_value in (("brand_id", brand_id), ("platform", platform)):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        with self._connect() as connection:
            if channel.strip():
                rows = connection.execute(
                    """
                    SELECT store_id
                    FROM dim_store
                    WHERE brand_id = ? AND platform = ? AND channel = ?
                    """,
                    (brand_id.strip(), platform.strip(), channel.strip()),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT store_id
                    FROM dim_store
                    WHERE brand_id = ? AND platform = ?
                    """,
                    (brand_id.strip(), platform.strip()),
                ).fetchall()
        result = tuple(str(row["store_id"]) for row in rows)
        assert isinstance(result, tuple)
        return result

    def list_known_product_codes(self, brand_id: str, platform: str, channel: str = "") -> tuple[str, ...]:
        for field_name, field_value in (("brand_id", brand_id), ("platform", platform)):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        with self._connect() as connection:
            if channel.strip():
                rows = connection.execute(
                    """
                    SELECT sku_code, upc_code
                    FROM dim_product
                    WHERE brand_id = ? AND platform = ? AND channel = ?
                    """,
                    (brand_id.strip(), platform.strip(), channel.strip()),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT sku_code, upc_code
                    FROM dim_product
                    WHERE brand_id = ? AND platform = ?
                    """,
                    (brand_id.strip(), platform.strip()),
                ).fetchall()
        values: list[str] = []
        for row in rows:
            sku_code = str(row["sku_code"]).strip()
            upc_code = str(row["upc_code"]).strip()
            if sku_code:
                values.append(sku_code)
            if upc_code:
                values.append(upc_code)
        result = tuple(dict.fromkeys(values))
        assert isinstance(result, tuple)
        return result

    def save_foundation_check(
        self,
        import_batch_id: str,
        metadata: object,
        original_file_name: str,
        stored_file_path: Path,
        file_sha256: str,
        recognized_file_type: str,
        row_count: int,
        status: str,
        brand_match_score: int,
        validation_errors: tuple[str, ...],
        validation_warnings: tuple[str, ...],
    ) -> None:
        from .data_foundation import UploadMetadata

        if not isinstance(metadata, UploadMetadata):
            raise TypeError("metadata must be UploadMetadata")
        for field_name, field_value in (
            ("import_batch_id", import_batch_id),
            ("original_file_name", original_file_name),
            ("file_sha256", file_sha256),
            ("recognized_file_type", recognized_file_type),
            ("status", status),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(stored_file_path, Path):
            raise TypeError("stored_file_path must be pathlib.Path")
        if row_count < 0:
            raise ValueError("row_count must not be negative")
        if brand_match_score < 0:
            raise ValueError("brand_match_score must not be negative")
        if not isinstance(validation_errors, tuple) or not isinstance(validation_warnings, tuple):
            raise TypeError("validation messages must be tuple")
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO import_batches (
                    import_batch_id, business_unit, brand_id, brand_name, platform, channel,
                    project_code, declared_file_type, data_start_date, data_end_date,
                    uploaded_by, status, brand_match_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_batch_id,
                    metadata.business_unit,
                    metadata.brand_id,
                    metadata.brand_name,
                    metadata.platform,
                    metadata.channel,
                    metadata.project_code,
                    metadata.declared_file_type,
                    metadata.data_start_date,
                    metadata.data_end_date,
                    metadata.uploaded_by,
                    status,
                    brand_match_score,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO source_files (
                    import_batch_id, original_file_name, stored_file_path, file_sha256,
                    recognized_file_type, row_count, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_batch_id,
                    original_file_name,
                    str(stored_file_path),
                    file_sha256,
                    recognized_file_type,
                    row_count,
                    status,
                    now,
                ),
            )
            connection.execute("DELETE FROM validation_reports WHERE import_batch_id = ?", (import_batch_id,))
            for severity, messages in (("error", validation_errors), ("warning", validation_warnings)):
                for message in messages:
                    connection.execute(
                        """
                        INSERT INTO validation_reports (
                            import_batch_id, validation_stage, severity, message, row_number, field_name, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (import_batch_id, "foundation_check", severity, str(message), None, "", now),
                    )
            connection.commit()
        logging.info("foundation check saved: batch=%s status=%s", import_batch_id, status)

    def save_foundation_fact_rows(self, import_batch_id: str, plan: object) -> None:
        from .data_foundation import IngestionPlan

        if not isinstance(plan, IngestionPlan):
            raise TypeError("plan must be IngestionPlan")
        if not isinstance(import_batch_id, str) or not import_batch_id.strip():
            raise ValueError("import_batch_id must not be empty")
        if not plan.validation.passed:
            raise ValueError("only passed foundation plans can be written into fact tables")
        if plan.brand_match.decision != "auto_pass":
            raise ValueError("only auto_pass foundation plans can be written into fact tables")
        if plan.target_table not in {"fact_order_product", "fact_store_finance", "fact_store_traffic", "fact_service_review"}:
            raise ValueError(f"unsupported target table: {plan.target_table}")
        now = _now()
        with self._connect() as connection:
            source_file_id = self._source_file_id(connection, import_batch_id)
            connection.execute(f"DELETE FROM {plan.target_table} WHERE import_batch_id = ?", (import_batch_id,))
            if plan.target_table == "fact_order_product":
                self._insert_fact_order_product(connection, import_batch_id, source_file_id, plan, now)
            elif plan.target_table == "fact_store_finance":
                self._insert_fact_store_finance(connection, import_batch_id, source_file_id, plan, now)
            elif plan.target_table == "fact_store_traffic":
                self._insert_fact_store_traffic(connection, import_batch_id, source_file_id, plan, now)
            elif plan.target_table == "fact_service_review":
                self._insert_fact_service_review(connection, import_batch_id, source_file_id, plan, now)
            connection.commit()
        logging.info("foundation fact rows saved: batch=%s table=%s rows=%s", import_batch_id, plan.target_table, len(plan.normalized_rows))

    def load_meituan_foundation_rows(self, brand_id: str, platform: str, channel: str, file_type: str) -> list[dict[str, str]]:
        for field_name, field_value in (
            ("brand_id", brand_id),
            ("platform", platform),
            ("channel", channel),
            ("file_type", file_type),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if platform != "meituan":
            raise ValueError("only meituan foundation rows are currently supported")
        loaders = {
            "product_order": self._load_meituan_product_rows,
            "store_finance": self._load_meituan_finance_rows,
            "store_traffic": self._load_meituan_traffic_rows,
            "service_review": self._load_meituan_review_rows,
        }
        if file_type not in loaders:
            raise ValueError(f"unsupported file_type: {file_type}")
        with self._connect() as connection:
            rows = loaders[file_type](connection, brand_id.strip(), platform.strip(), channel.strip())
        assert isinstance(rows, list)
        return rows

    def _source_file_id(self, connection: sqlite3.Connection, import_batch_id: str) -> int | None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("connection must be sqlite3.Connection")
        row = connection.execute(
            "SELECT source_file_id FROM source_files WHERE import_batch_id = ? ORDER BY source_file_id DESC LIMIT 1",
            (import_batch_id,),
        ).fetchone()
        return int(row["source_file_id"]) if row is not None else None

    def _insert_fact_order_product(self, connection: sqlite3.Connection, import_batch_id: str, source_file_id: int | None, plan: object, now: str) -> None:
        from .data_foundation import IngestionPlan

        if not isinstance(plan, IngestionPlan):
            raise TypeError("plan must be IngestionPlan")
        for row in plan.normalized_rows:
            connection.execute(
                """
                INSERT OR REPLACE INTO fact_order_product (
                    import_batch_id, source_file_id, source_row_number, business_unit, brand_id, brand_name,
                    platform, channel, project_code, data_start_date, data_end_date, order_id, order_time,
                    store_id, store_name, city, order_status, category, product_name, upc_code, sku_code,
                    sales_quantity, paid_sales_amount, refund_amount, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_batch_id,
                    source_file_id,
                    int(row["source_row_number"]),
                    plan.metadata.business_unit,
                    plan.metadata.brand_id,
                    plan.metadata.brand_name,
                    plan.metadata.platform,
                    plan.metadata.channel,
                    plan.metadata.project_code,
                    plan.metadata.data_start_date,
                    plan.metadata.data_end_date,
                    row["order_id"],
                    row["order_time"],
                    row["store_id"],
                    row["store_name"],
                    row["city"],
                    row["order_status"],
                    row["category"],
                    row["product_name"],
                    row.get("upc_code", ""),
                    row["sku_code"],
                    row["sales_quantity"],
                    row["paid_sales_amount"],
                    row.get("refund_amount", "0"),
                    now,
                ),
            )
            self._upsert_dim_store(connection, plan, row.get("store_id", ""), row.get("store_name", ""), "", row.get("city", ""), now)
            self._upsert_dim_product(connection, plan, row.get("sku_code", ""), row.get("upc_code", ""), row.get("product_name", ""), row.get("category", ""), now)

    def _insert_fact_store_finance(self, connection: sqlite3.Connection, import_batch_id: str, source_file_id: int | None, plan: object, now: str) -> None:
        from .data_foundation import IngestionPlan

        if not isinstance(plan, IngestionPlan):
            raise TypeError("plan must be IngestionPlan")
        for row in plan.normalized_rows:
            connection.execute(
                """
                INSERT OR REPLACE INTO fact_store_finance (
                    import_batch_id, source_file_id, source_row_number, business_unit, brand_id, brand_name,
                    platform, channel, project_code, data_start_date, data_end_date, store_id, store_name,
                    province, city, income_amount, gross_sales_amount, paid_transaction_amount,
                    valid_order_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_batch_id,
                    source_file_id,
                    int(row["source_row_number"]),
                    plan.metadata.business_unit,
                    plan.metadata.brand_id,
                    plan.metadata.brand_name,
                    plan.metadata.platform,
                    plan.metadata.channel,
                    plan.metadata.project_code,
                    row["data_start_date"],
                    row["data_end_date"],
                    row["store_id"],
                    row["store_name"],
                    row["province"],
                    row["city"],
                    row["income_amount"],
                    row["gross_sales_amount"],
                    row["paid_transaction_amount"],
                    row["valid_order_count"],
                    now,
                ),
            )
            self._upsert_dim_store(connection, plan, row.get("store_id", ""), row.get("store_name", ""), row.get("province", ""), row.get("city", ""), now)

    def _insert_fact_store_traffic(self, connection: sqlite3.Connection, import_batch_id: str, source_file_id: int | None, plan: object, now: str) -> None:
        from .data_foundation import IngestionPlan

        if not isinstance(plan, IngestionPlan):
            raise TypeError("plan must be IngestionPlan")
        for row in plan.normalized_rows:
            connection.execute(
                """
                INSERT OR REPLACE INTO fact_store_traffic (
                    import_batch_id, source_file_id, source_row_number, business_unit, brand_id, brand_name,
                    platform, channel, project_code, data_start_date, data_end_date, store_id, store_name,
                    province, city, exposure_user_count, visit_user_count, order_user_count,
                    visit_conversion_rate, order_conversion_rate, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_batch_id,
                    source_file_id,
                    int(row["source_row_number"]),
                    plan.metadata.business_unit,
                    plan.metadata.brand_id,
                    plan.metadata.brand_name,
                    plan.metadata.platform,
                    plan.metadata.channel,
                    plan.metadata.project_code,
                    row["data_start_date"],
                    row["data_end_date"],
                    row["store_id"],
                    row["store_name"],
                    row["province"],
                    row["city"],
                    row["exposure_user_count"],
                    row["visit_user_count"],
                    row["order_user_count"],
                    row["visit_conversion_rate"],
                    row["order_conversion_rate"],
                    now,
                ),
            )
            self._upsert_dim_store(connection, plan, row.get("store_id", ""), row.get("store_name", ""), row.get("province", ""), row.get("city", ""), now)

    def _insert_fact_service_review(self, connection: sqlite3.Connection, import_batch_id: str, source_file_id: int | None, plan: object, now: str) -> None:
        from .data_foundation import IngestionPlan

        if not isinstance(plan, IngestionPlan):
            raise TypeError("plan must be IngestionPlan")
        for row in plan.normalized_rows:
            connection.execute(
                """
                INSERT OR REPLACE INTO fact_service_review (
                    import_batch_id, source_file_id, source_row_number, business_unit, brand_id, brand_name,
                    platform, channel, project_code, review_date, review_time, store_id, store_name, city,
                    order_products, user_review, merchant_score, delivery_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_batch_id,
                    source_file_id,
                    int(row["source_row_number"]),
                    plan.metadata.business_unit,
                    plan.metadata.brand_id,
                    plan.metadata.brand_name,
                    plan.metadata.platform,
                    plan.metadata.channel,
                    plan.metadata.project_code,
                    row["review_date"],
                    row["review_time"],
                    row["store_id"],
                    row["store_name"],
                    row["city"],
                    row["order_products"],
                    row.get("user_review", ""),
                    row["merchant_score"],
                    row.get("delivery_score", ""),
                    now,
                ),
            )
            self._upsert_dim_store(connection, plan, row.get("store_id", ""), row.get("store_name", ""), "", row.get("city", ""), now)

    def _upsert_dim_store(self, connection: sqlite3.Connection, plan: object, store_id: str, store_name: str, province: str, city: str, now: str) -> None:
        from .data_foundation import IngestionPlan

        if not isinstance(plan, IngestionPlan):
            raise TypeError("plan must be IngestionPlan")
        if not store_id.strip():
            return
        connection.execute(
            """
            INSERT OR REPLACE INTO dim_store (
                brand_id, platform, channel, store_id, store_name, province, city, region, business_status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, '', '', ?)
            """,
            (plan.metadata.brand_id, plan.metadata.platform, plan.metadata.channel, store_id, store_name, province, city, now),
        )

    def _upsert_dim_product(self, connection: sqlite3.Connection, plan: object, sku_code: str, upc_code: str, product_name: str, category: str, now: str) -> None:
        from .data_foundation import IngestionPlan

        if not isinstance(plan, IngestionPlan):
            raise TypeError("plan must be IngestionPlan")
        if not sku_code.strip():
            return
        connection.execute(
            """
            INSERT OR REPLACE INTO dim_product (
                brand_id, platform, channel, sku_code, upc_code, style_code, product_name, standard_category,
                target_audience, usage_scene, selling_points, image_url, sale_status, updated_at
            ) VALUES (?, ?, ?, ?, ?, '', ?, ?, '', '', '', '', '', ?)
            """,
            (plan.metadata.brand_id, plan.metadata.platform, plan.metadata.channel, sku_code, upc_code, product_name, category, now),
        )

    def _load_meituan_product_rows(self, connection: sqlite3.Connection, brand_id: str, platform: str, channel: str) -> list[dict[str, str]]:
        rows = connection.execute(
            """
            SELECT *
            FROM fact_order_product
            WHERE brand_id = ? AND platform = ? AND channel = ?
            ORDER BY order_time, source_row_number
            """,
            (brand_id, platform, channel),
        ).fetchall()
        result = [
            {
                "日期": f"{row['data_start_date']}-{row['data_end_date']}",
                "订单编号": str(row["order_id"]),
                "下单时间": str(row["order_time"]),
                "店铺名称": str(row["store_name"]),
                "店铺ID": str(row["store_id"]),
                "店铺所在城市": str(row["city"]),
                "订单状态": str(row["order_status"]),
                "商品分类": str(row["category"]),
                "商品名称": str(row["product_name"]),
                "UPC码": str(row["upc_code"]),
                "商品SKU码": str(row["sku_code"]),
                "商品销售数量": str(row["sales_quantity"]),
                "商品实付销售额": str(row["paid_sales_amount"]),
                "部分退款商品金额": str(row["refund_amount"]),
            }
            for row in rows
        ]
        assert isinstance(result, list)
        return result

    def _load_meituan_finance_rows(self, connection: sqlite3.Connection, brand_id: str, platform: str, channel: str) -> list[dict[str, str]]:
        rows = connection.execute(
            """
            SELECT *
            FROM fact_store_finance
            WHERE brand_id = ? AND platform = ? AND channel = ?
            ORDER BY data_start_date, source_row_number
            """,
            (brand_id, platform, channel),
        ).fetchall()
        result = [
            {
                "开始时间": str(row["data_start_date"]),
                "结束时间": str(row["data_end_date"]),
                "商家ID": str(row["store_id"]),
                "商家名称": str(row["store_name"]),
                "省份": str(row["province"]),
                "城市": str(row["city"]),
                "收入": str(row["income_amount"]),
                "营业额": str(row["gross_sales_amount"]),
                "实付交易额": str(row["paid_transaction_amount"]),
                "有效订单数": str(row["valid_order_count"]),
                "实付单均价": self._finance_unit_price_text(row["paid_transaction_amount"], row["valid_order_count"]),
            }
            for row in rows
        ]
        assert isinstance(result, list)
        return result

    @staticmethod
    def _finance_unit_price_text(paid_transaction_amount: object, valid_order_count: object) -> str:
        from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

        paid_text = "" if paid_transaction_amount is None else str(paid_transaction_amount).strip().replace(",", "")
        order_text = "" if valid_order_count is None else str(valid_order_count).strip().replace(",", "")
        try:
            paid_amount = Decimal(paid_text or "0")
            order_count = Decimal(order_text or "0")
        except InvalidOperation as exc:
            raise ValueError("finance amount and order count must be numeric") from exc
        if order_count <= 0:
            return "0.00"
        result = str((paid_amount / order_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        assert result
        return result

    def _load_meituan_traffic_rows(self, connection: sqlite3.Connection, brand_id: str, platform: str, channel: str) -> list[dict[str, str]]:
        rows = connection.execute(
            """
            SELECT *
            FROM fact_store_traffic
            WHERE brand_id = ? AND platform = ? AND channel = ?
            ORDER BY data_start_date, source_row_number
            """,
            (brand_id, platform, channel),
        ).fetchall()
        result = [
            {
                "开始时间": str(row["data_start_date"]),
                "结束时间": str(row["data_end_date"]),
                "商家ID": str(row["store_id"]),
                "商家名称": str(row["store_name"]),
                "省份": str(row["province"]),
                "城市": str(row["city"]),
                "曝光人数": str(row["exposure_user_count"]),
                "入店人数": str(row["visit_user_count"]),
                "下单人数": str(row["order_user_count"]),
                "入店转化率": str(row["visit_conversion_rate"]),
                "下单转化率": str(row["order_conversion_rate"]),
            }
            for row in rows
        ]
        assert isinstance(result, list)
        return result

    def _load_meituan_review_rows(self, connection: sqlite3.Connection, brand_id: str, platform: str, channel: str) -> list[dict[str, str]]:
        rows = connection.execute(
            """
            SELECT *
            FROM fact_service_review
            WHERE brand_id = ? AND platform = ? AND channel = ?
            ORDER BY review_date, source_row_number
            """,
            (brand_id, platform, channel),
        ).fetchall()
        result = [
            {
                "评价提交日期": str(row["review_date"]),
                "评价提交时间": str(row["review_time"]),
                "店铺名称": str(row["store_name"]),
                "店铺ID": str(row["store_id"]),
                "店铺所在城市": str(row["city"]),
                "订单商品": str(row["order_products"]),
                "用户评价": str(row["user_review"]),
                "商家评分": str(row["merchant_score"]),
                "配送体验评分": str(row["delivery_score"]),
            }
            for row in rows
        ]
        assert isinstance(result, list)
        return result

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
