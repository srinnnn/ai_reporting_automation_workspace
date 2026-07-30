from __future__ import annotations

import csv
import hashlib
import logging
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SUPPORTED_SUFFIXES = (".csv", ".xls", ".xlsx")
MEITUAN_FILE_TYPE_TOKENS = {
    "product_order": ("商品数据", "product_order"),
    "store_finance": ("门店财务明细", "store_finance"),
    "store_traffic": ("门店流量明细", "store_traffic"),
    "service_review": ("评价分析明细", "service_review"),
}
MEITUAN_REPORT_KEYWORDS = tuple(token for tokens in MEITUAN_FILE_TYPE_TOKENS.values() for token in tokens)


@dataclass(frozen=True)
class SyncConfig:
    source_root: Path
    target_root: Path
    index_path: Path
    file_name_keywords: tuple[str, ...] = ()
    excluded_dir_names: tuple[str, ...] = ()
    structure_meituan_reports: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.source_root, Path):
            raise TypeError("source_root must be Path")
        if not isinstance(self.target_root, Path):
            raise TypeError("target_root must be Path")
        if not isinstance(self.index_path, Path):
            raise TypeError("index_path must be Path")
        if not isinstance(self.file_name_keywords, tuple):
            raise TypeError("file_name_keywords must be tuple")
        if not isinstance(self.excluded_dir_names, tuple):
            raise TypeError("excluded_dir_names must be tuple")
        if not isinstance(self.structure_meituan_reports, bool):
            raise TypeError("structure_meituan_reports must be bool")


@dataclass(frozen=True)
class SyncedFile:
    source_path: Path
    target_path: Path
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not self.sha256:
            raise ValueError("sha256 must not be empty")
        if self.size_bytes <= 0:
            raise ValueError("size_bytes must be positive")


def default_config(project_root: Path) -> SyncConfig:
    if not isinstance(project_root, Path):
        raise TypeError("project_root must be Path")
    source_root = Path.home() / "Downloads" / "meituan_auto_download"
    target_root = project_root / "intranet_app" / "runtime" / "intake" / "meituan_auto_download"
    index_path = target_root / "download_index.csv"
    config = SyncConfig(source_root=source_root, target_root=target_root, index_path=index_path)
    assert isinstance(config, SyncConfig)
    return config


def sha256_file(path: Path) -> str:
    if not isinstance(path, Path):
        raise TypeError("path must be Path")
    if not path.is_file():
        raise ValueError(f"path is not a file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    result = digest.hexdigest()
    assert result
    return result


def list_download_files(source_root: Path) -> list[Path]:
    if not isinstance(source_root, Path):
        raise TypeError("source_root must be Path")
    if not source_root.exists():
        logging.info("source root does not exist: %s", source_root)
        return []
    files = sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    logging.info("found %s candidate download files", len(files))
    assert isinstance(files, list)
    return files


def existing_hashes(index_path: Path) -> set[str]:
    if not isinstance(index_path, Path):
        raise TypeError("index_path must be Path")
    if not index_path.exists():
        return set()
    hashes: set[str] = set()
    with index_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            value = (row.get("sha256") or "").strip()
            if value:
                hashes.add(value)
    assert isinstance(hashes, set)
    return hashes


def copy_new_files(config: SyncConfig) -> list[SyncedFile]:
    if not isinstance(config, SyncConfig):
        raise TypeError("config must be SyncConfig")
    config.target_root.mkdir(parents=True, exist_ok=True)
    known_hashes = existing_hashes(config.index_path)
    synced: list[SyncedFile] = []
    for source_path in list_download_files(config.source_root):
        if not _should_sync_file(config, source_path):
            continue
        file_hash = sha256_file(source_path)
        if file_hash in known_hashes:
            logging.info("skip duplicated file: %s", source_path)
            continue
        relative_path = _target_relative_path(config, source_path)
        target_path = config.target_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        record = SyncedFile(
            source_path=source_path,
            target_path=target_path,
            sha256=file_hash,
            size_bytes=target_path.stat().st_size,
        )
        synced.append(record)
        known_hashes.add(file_hash)
        logging.info("synced file: %s -> %s", source_path, target_path)
    append_index(config.index_path, synced)
    assert isinstance(synced, list)
    return synced


def _should_sync_file(config: SyncConfig, source_path: Path) -> bool:
    if not isinstance(config, SyncConfig):
        raise TypeError("config must be SyncConfig")
    if not isinstance(source_path, Path):
        raise TypeError("source_path must be Path")
    if any(part in config.excluded_dir_names for part in source_path.parts):
        return False
    if not config.file_name_keywords:
        return True
    normalized_name = source_path.name.lower()
    return any(keyword.lower() in normalized_name for keyword in config.file_name_keywords)


def _target_relative_path(config: SyncConfig, source_path: Path) -> Path:
    if not isinstance(config, SyncConfig):
        raise TypeError("config must be SyncConfig")
    if not isinstance(source_path, Path):
        raise TypeError("source_path must be Path")
    if not config.structure_meituan_reports:
        return source_path.relative_to(config.source_root)
    file_type = _meituan_file_type_from_name(source_path.name)
    if not file_type:
        raise ValueError(f"unrecognized Meituan report file: {source_path.name}")
    date_range = _date_range_from_name(source_path.name)
    result = Path("anta_kids") / "instant_retail" / date_range / file_type / source_path.name
    assert str(result)
    return result


def _meituan_file_type_from_name(file_name: str) -> str:
    if not isinstance(file_name, str) or not file_name.strip():
        raise ValueError("file_name must not be empty")
    lowered = file_name.lower()
    for file_type, tokens in MEITUAN_FILE_TYPE_TOKENS.items():
        if any(token.lower() in lowered for token in tokens):
            return file_type
    return ""


def _date_range_from_name(file_name: str) -> str:
    if not isinstance(file_name, str) or not file_name.strip():
        raise ValueError("file_name must not be empty")
    dates = re.findall(r"20\d{6}", file_name)
    if not dates:
        return "undated"
    unique_dates = list(dict.fromkeys(dates))
    result = unique_dates[0] if len(unique_dates) == 1 else f"{unique_dates[0]}_{unique_dates[-1]}"
    assert result
    return result


def append_index(index_path: Path, records: list[SyncedFile]) -> None:
    if not isinstance(index_path, Path):
        raise TypeError("index_path must be Path")
    if not isinstance(records, list):
        raise TypeError("records must be list")
    if not records:
        logging.info("no new files to append into index")
        return
    index_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not index_path.exists()
    with index_path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["synced_at", "source_path", "target_path", "sha256", "size_bytes"],
        )
        if write_header:
            writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "synced_at": datetime.now().isoformat(timespec="seconds"),
                    "source_path": str(record.source_path),
                    "target_path": str(record.target_path),
                    "sha256": record.sha256,
                    "size_bytes": str(record.size_bytes),
                }
            )
    logging.info("appended %s records into index: %s", len(records), index_path)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = default_config(Path.cwd())
    synced = copy_new_files(config)
    print(f"synced_files={len(synced)}")
    print(f"source_root={config.source_root}")
    print(f"target_root={config.target_root}")
    print(f"index_path={config.index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
