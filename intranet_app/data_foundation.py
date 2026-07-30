from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from .domain import ValidationError


SUPPORTED_PLATFORMS = ("meituan", "jd", "tmall", "mini_program", "official_site")
SUPPORTED_CHANNELS = ("instant_retail", "ecommerce", "private_domain", "official_direct")
SUPPORTED_FILE_TYPES = ("product_order", "store_finance", "store_traffic", "service_review")
AUTO_PASS_SCORE = 90
MANUAL_REVIEW_SCORE = 70


def _normalize_cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\t", "").strip()


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(field_name, str) or not field_name.strip():
        raise ValueError("field_name must be non-empty text")
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must not be empty")
    return value.strip()


@dataclass(frozen=True)
class UploadMetadata:
    business_unit: str
    brand_id: str
    brand_name: str
    platform: str
    channel: str
    project_code: str
    declared_file_type: str
    data_start_date: str
    data_end_date: str
    uploaded_by: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("business_unit", self.business_unit),
            ("brand_id", self.brand_id),
            ("brand_name", self.brand_name),
            ("platform", self.platform),
            ("channel", self.channel),
            ("project_code", self.project_code),
            ("declared_file_type", self.declared_file_type),
            ("data_start_date", self.data_start_date),
            ("data_end_date", self.data_end_date),
            ("uploaded_by", self.uploaded_by),
        ):
            _require_text(field_value, field_name)
        if self.platform not in SUPPORTED_PLATFORMS:
            raise ValidationError(f"platform must be one of: {', '.join(SUPPORTED_PLATFORMS)}")
        if self.channel not in SUPPORTED_CHANNELS:
            raise ValidationError(f"channel must be one of: {', '.join(SUPPORTED_CHANNELS)}")
        if self.declared_file_type not in SUPPORTED_FILE_TYPES:
            raise ValidationError(f"declared_file_type must be one of: {', '.join(SUPPORTED_FILE_TYPES)}")
        if self.data_start_date > self.data_end_date:
            raise ValidationError("data_start_date must not be later than data_end_date")


@dataclass(frozen=True)
class FieldMappingRule:
    platform: str
    file_type: str
    raw_field: str
    standard_field: str
    required: bool
    data_type: str
    empty_strategy: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("platform", self.platform),
            ("file_type", self.file_type),
            ("raw_field", self.raw_field),
            ("standard_field", self.standard_field),
            ("data_type", self.data_type),
            ("empty_strategy", self.empty_strategy),
        ):
            _require_text(field_value, field_name)
        if self.platform not in SUPPORTED_PLATFORMS:
            raise ValidationError("unsupported platform in field mapping")
        if self.file_type not in SUPPORTED_FILE_TYPES:
            raise ValidationError("unsupported file_type in field mapping")


@dataclass(frozen=True)
class FileRecognitionResult:
    file_type: str
    confidence: int
    matched_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.file_type, "file_type")
        if self.confidence < 0 or self.confidence > 100:
            raise ValueError("confidence must be between 0 and 100")
        if not isinstance(self.matched_fields, tuple):
            raise TypeError("matched_fields must be tuple")
        if not isinstance(self.missing_fields, tuple):
            raise TypeError("missing_fields must be tuple")


@dataclass(frozen=True)
class BrandMatchScore:
    store_score: int
    product_score: int
    platform_score: int
    date_score: int
    total_score: int
    decision: str
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, score in (
            ("store_score", self.store_score),
            ("product_score", self.product_score),
            ("platform_score", self.platform_score),
            ("date_score", self.date_score),
            ("total_score", self.total_score),
        ):
            if score < 0:
                raise ValueError(f"{field_name} must not be negative")
        if self.total_score != self.store_score + self.product_score + self.platform_score + self.date_score:
            raise ValueError("total_score must equal component scores")
        if self.decision not in ("auto_pass", "manual_review", "reject"):
            raise ValidationError("invalid brand match decision")


@dataclass(frozen=True)
class FoundationValidationResult:
    passed: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool):
            raise TypeError("passed must be bool")
        if not isinstance(self.errors, tuple):
            raise TypeError("errors must be tuple")
        if not isinstance(self.warnings, tuple):
            raise TypeError("warnings must be tuple")
        if self.passed and self.errors:
            raise ValueError("passed validation cannot contain errors")


@dataclass(frozen=True)
class IngestionPlan:
    metadata: UploadMetadata
    recognition: FileRecognitionResult
    validation: FoundationValidationResult
    brand_match: BrandMatchScore
    target_table: str
    normalized_rows: tuple[dict[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, UploadMetadata):
            raise TypeError("metadata must be UploadMetadata")
        if not isinstance(self.recognition, FileRecognitionResult):
            raise TypeError("recognition must be FileRecognitionResult")
        if not isinstance(self.validation, FoundationValidationResult):
            raise TypeError("validation must be FoundationValidationResult")
        if not isinstance(self.brand_match, BrandMatchScore):
            raise TypeError("brand_match must be BrandMatchScore")
        _require_text(self.target_table, "target_table")
        if not isinstance(self.normalized_rows, tuple):
            raise TypeError("normalized_rows must be tuple")


MEITUAN_FIELD_MAPPINGS: dict[str, tuple[FieldMappingRule, ...]] = {
    "product_order": (
        FieldMappingRule("meituan", "product_order", "日期", "date_range", True, "date_range", "raise"),
        FieldMappingRule("meituan", "product_order", "订单编号", "order_id", True, "text", "raise"),
        FieldMappingRule("meituan", "product_order", "下单时间", "order_time", True, "datetime", "raise"),
        FieldMappingRule("meituan", "product_order", "店铺名称", "store_name", True, "text", "raise"),
        FieldMappingRule("meituan", "product_order", "店铺ID", "store_id", True, "text", "raise"),
        FieldMappingRule("meituan", "product_order", "店铺所在城市", "city", True, "text", "raise"),
        FieldMappingRule("meituan", "product_order", "订单状态", "order_status", True, "text", "raise"),
        FieldMappingRule("meituan", "product_order", "商品分类", "category", True, "text", "raise"),
        FieldMappingRule("meituan", "product_order", "商品名称", "product_name", True, "text", "raise"),
        FieldMappingRule("meituan", "product_order", "UPC码", "upc_code", False, "text", "empty"),
        FieldMappingRule("meituan", "product_order", "商品SKU码", "sku_code", True, "text", "raise"),
        FieldMappingRule("meituan", "product_order", "商品销售数量", "sales_quantity", True, "decimal", "raise"),
        FieldMappingRule("meituan", "product_order", "商品实付销售额", "paid_sales_amount", True, "money", "raise"),
        FieldMappingRule("meituan", "product_order", "部分退款商品金额", "refund_amount", False, "money", "zero"),
    ),
    "store_finance": (
        FieldMappingRule("meituan", "store_finance", "开始时间", "data_start_date", True, "date", "raise"),
        FieldMappingRule("meituan", "store_finance", "结束时间", "data_end_date", True, "date", "raise"),
        FieldMappingRule("meituan", "store_finance", "商家ID", "store_id", True, "text", "raise"),
        FieldMappingRule("meituan", "store_finance", "商家名称", "store_name", True, "text", "raise"),
        FieldMappingRule("meituan", "store_finance", "省份", "province", True, "text", "raise"),
        FieldMappingRule("meituan", "store_finance", "城市", "city", True, "text", "raise"),
        FieldMappingRule("meituan", "store_finance", "收入", "income_amount", True, "money", "raise"),
        FieldMappingRule("meituan", "store_finance", "营业额", "gross_sales_amount", True, "money", "raise"),
        FieldMappingRule("meituan", "store_finance", "实付交易额", "paid_transaction_amount", True, "money", "raise"),
        FieldMappingRule("meituan", "store_finance", "有效订单数", "valid_order_count", True, "integer", "raise"),
    ),
    "store_traffic": (
        FieldMappingRule("meituan", "store_traffic", "开始时间", "data_start_date", True, "date", "raise"),
        FieldMappingRule("meituan", "store_traffic", "结束时间", "data_end_date", True, "date", "raise"),
        FieldMappingRule("meituan", "store_traffic", "商家ID", "store_id", True, "text", "raise"),
        FieldMappingRule("meituan", "store_traffic", "商家名称", "store_name", True, "text", "raise"),
        FieldMappingRule("meituan", "store_traffic", "省份", "province", True, "text", "raise"),
        FieldMappingRule("meituan", "store_traffic", "城市", "city", True, "text", "raise"),
        FieldMappingRule("meituan", "store_traffic", "曝光人数", "exposure_user_count", True, "integer", "raise"),
        FieldMappingRule("meituan", "store_traffic", "入店人数", "visit_user_count", True, "integer", "raise"),
        FieldMappingRule("meituan", "store_traffic", "下单人数", "order_user_count", True, "integer", "raise"),
        FieldMappingRule("meituan", "store_traffic", "入店转化率", "visit_conversion_rate", True, "decimal", "raise"),
        FieldMappingRule("meituan", "store_traffic", "下单转化率", "order_conversion_rate", True, "decimal", "raise"),
    ),
    "service_review": (
        FieldMappingRule("meituan", "service_review", "评价提交日期", "review_date", True, "date", "raise"),
        FieldMappingRule("meituan", "service_review", "评价提交时间", "review_time", True, "datetime", "raise"),
        FieldMappingRule("meituan", "service_review", "店铺名称", "store_name", True, "text", "raise"),
        FieldMappingRule("meituan", "service_review", "店铺ID", "store_id", True, "text", "raise"),
        FieldMappingRule("meituan", "service_review", "店铺所在城市", "city", True, "text", "raise"),
        FieldMappingRule("meituan", "service_review", "订单商品", "order_products", True, "text", "raise"),
        FieldMappingRule("meituan", "service_review", "用户评价", "user_review", False, "text", "empty"),
        FieldMappingRule("meituan", "service_review", "商家评分", "merchant_score", True, "decimal", "raise"),
        FieldMappingRule("meituan", "service_review", "配送体验评分", "delivery_score", False, "decimal", "empty"),
    ),
}

TARGET_TABLE_BY_FILE_TYPE = {
    "product_order": "fact_order_product",
    "store_finance": "fact_store_finance",
    "store_traffic": "fact_store_traffic",
    "service_review": "fact_service_review",
}


def build_ingestion_plan(
    metadata: UploadMetadata,
    rows: list[dict[str, str]],
    known_store_ids: Iterable[str],
    known_product_codes: Iterable[str],
) -> IngestionPlan:
    if not isinstance(metadata, UploadMetadata):
        raise TypeError("metadata must be UploadMetadata")
    if not isinstance(rows, list):
        raise TypeError("rows must be list")
    if not rows:
        raise ValidationError("rows must not be empty")
    headers = tuple(str(header).strip() for header in rows[0].keys() if str(header).strip())
    recognition = recognize_file_type(headers, metadata.platform)
    errors: list[str] = []
    warnings: list[str] = []
    if recognition.file_type != metadata.declared_file_type:
        errors.append(
            f"declared file type {metadata.declared_file_type} does not match recognized type {recognition.file_type}"
        )
    mapping_rules = get_field_mapping(metadata.platform, metadata.declared_file_type)
    required_result = validate_required_fields(headers, mapping_rules)
    errors.extend(required_result.errors)
    warnings.extend(required_result.warnings)
    normalized_rows = normalize_rows(rows, mapping_rules)
    value_result = validate_standard_values(normalized_rows, mapping_rules)
    errors.extend(value_result.errors)
    warnings.extend(value_result.warnings)
    brand_match = score_brand_ownership(metadata, normalized_rows, known_store_ids, known_product_codes)
    if brand_match.decision == "reject":
        errors.append("brand ownership score is below the import threshold")
    elif brand_match.decision == "manual_review":
        warnings.append("brand ownership requires manual review before import")
    validation = FoundationValidationResult(passed=not errors, errors=tuple(errors), warnings=tuple(warnings))
    target_table = TARGET_TABLE_BY_FILE_TYPE[metadata.declared_file_type]
    plan = IngestionPlan(
        metadata=metadata,
        recognition=recognition,
        validation=validation,
        brand_match=brand_match,
        target_table=target_table,
        normalized_rows=tuple(normalized_rows),
    )
    logging.info(
        "foundation ingestion planned: platform=%s file_type=%s rows=%s passed=%s",
        metadata.platform,
        metadata.declared_file_type,
        len(plan.normalized_rows),
        plan.validation.passed,
    )
    assert plan.target_table.startswith(("fact_", "dim_", "target_"))
    return plan


def recognize_file_type(headers: Iterable[str], platform: str) -> FileRecognitionResult:
    if not isinstance(platform, str) or platform not in SUPPORTED_PLATFORMS:
        raise ValidationError("unsupported platform")
    if platform != "meituan":
        raise ValidationError(f"field mapping is not configured for platform: {platform}")
    header_set = {_normalize_cell(header) for header in headers if _normalize_cell(header)}
    if not header_set:
        raise ValidationError("headers must not be empty")
    candidates: list[FileRecognitionResult] = []
    for file_type, rules in MEITUAN_FIELD_MAPPINGS.items():
        required_fields = tuple(rule.raw_field for rule in rules if rule.required)
        matched = tuple(field for field in required_fields if field in header_set)
        missing = tuple(field for field in required_fields if field not in header_set)
        confidence = int((len(matched) / len(required_fields)) * 100) if required_fields else 0
        candidates.append(FileRecognitionResult(file_type=file_type, confidence=confidence, matched_fields=matched, missing_fields=missing))
    result = max(candidates, key=lambda item: item.confidence)
    if result.confidence < 50:
        raise ValidationError("file type recognition confidence is too low")
    logging.info("file type recognized: %s confidence=%s", result.file_type, result.confidence)
    assert result.confidence >= 50
    return result


def get_field_mapping(platform: str, file_type: str) -> tuple[FieldMappingRule, ...]:
    if platform != "meituan":
        raise ValidationError(f"field mapping is not configured for platform: {platform}")
    if file_type not in MEITUAN_FIELD_MAPPINGS:
        raise ValidationError(f"unsupported file_type: {file_type}")
    result = MEITUAN_FIELD_MAPPINGS[file_type]
    assert result
    return result


def validate_required_fields(headers: Iterable[str], mapping_rules: tuple[FieldMappingRule, ...]) -> FoundationValidationResult:
    header_set = {_normalize_cell(header) for header in headers if _normalize_cell(header)}
    missing = tuple(rule.raw_field for rule in mapping_rules if rule.required and rule.raw_field not in header_set)
    result = FoundationValidationResult(passed=not missing, errors=tuple(f"missing required field: {field}" for field in missing), warnings=())
    if missing:
        logging.error("required fields missing: %s", missing)
    assert result.passed is (not missing)
    return result


def normalize_rows(rows: list[dict[str, str]], mapping_rules: tuple[FieldMappingRule, ...]) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise TypeError("rows must be list")
    if not rows:
        raise ValidationError("rows must not be empty")
    normalized: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise TypeError("each row must be dict")
        normalized_row: dict[str, str] = {"source_row_number": str(index)}
        for rule in mapping_rules:
            raw_value = row.get(rule.raw_field, "")
            cleaned = _normalize_cell(raw_value)
            if cleaned == "" and rule.empty_strategy == "zero":
                cleaned = "0"
            normalized_row[rule.standard_field] = cleaned
        normalized.append(normalized_row)
    if not normalized:
        raise AssertionError("normalized rows must not be empty")
    logging.info("rows normalized: %s", len(normalized))
    return normalized


def validate_standard_values(
    normalized_rows: list[dict[str, str]],
    mapping_rules: tuple[FieldMappingRule, ...],
) -> FoundationValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    data_types = {rule.standard_field: rule.data_type for rule in mapping_rules}
    required_fields = {rule.standard_field for rule in mapping_rules if rule.required}
    for row in normalized_rows:
        row_number = row.get("source_row_number", "?")
        for field in required_fields:
            if _normalize_cell(row.get(field, "")) == "":
                errors.append(f"row {row_number}: required value is empty: {field}")
        for field, data_type in data_types.items():
            value = _normalize_cell(row.get(field, ""))
            if value == "":
                continue
            if data_type in ("money", "decimal"):
                _validate_decimal(value, field, row_number, errors)
            elif data_type == "integer":
                _validate_integer(value, field, row_number, errors)
    result = FoundationValidationResult(passed=not errors, errors=tuple(errors), warnings=tuple(warnings))
    if errors:
        logging.error("standard value validation failed: %s", len(errors))
    assert isinstance(result, FoundationValidationResult)
    return result


def score_brand_ownership(
    metadata: UploadMetadata,
    normalized_rows: list[dict[str, str]],
    known_store_ids: Iterable[str],
    known_product_codes: Iterable[str],
) -> BrandMatchScore:
    if not isinstance(metadata, UploadMetadata):
        raise TypeError("metadata must be UploadMetadata")
    if not normalized_rows:
        raise ValidationError("normalized_rows must not be empty")
    store_ids = {_normalize_cell(value) for value in known_store_ids if _normalize_cell(value)}
    product_codes = {_normalize_cell(value) for value in known_product_codes if _normalize_cell(value)}
    store_values = [_normalize_cell(row.get("store_id", "")) for row in normalized_rows if _normalize_cell(row.get("store_id", ""))]
    product_values = [
        _normalize_cell(row.get("sku_code", "") or row.get("upc_code", ""))
        for row in normalized_rows
        if _normalize_cell(row.get("sku_code", "") or row.get("upc_code", ""))
    ]
    warnings: list[str] = []
    store_score = _score_ratio(store_values, store_ids, 40)
    if not store_ids:
        warnings.append("known store library is empty; store score uses brand-name fallback")
        store_score = _score_store_name_fallback(metadata.brand_name, normalized_rows)
    product_score = _score_ratio(product_values, product_codes, 40)
    if not product_values:
        warnings.append("no product code fields in this file; product score is treated as not applicable")
        product_score = 40
    elif not product_codes:
        warnings.append("known product library is empty; product score requires manual review")
        product_score = 20
    platform_score = 10 if metadata.platform in SUPPORTED_PLATFORMS and metadata.channel in SUPPORTED_CHANNELS else 0
    date_score = 10 if metadata.data_start_date <= metadata.data_end_date else 0
    total = store_score + product_score + platform_score + date_score
    if total >= AUTO_PASS_SCORE:
        decision = "auto_pass"
    elif total >= MANUAL_REVIEW_SCORE:
        decision = "manual_review"
    else:
        decision = "reject"
    result = BrandMatchScore(
        store_score=store_score,
        product_score=product_score,
        platform_score=platform_score,
        date_score=date_score,
        total_score=total,
        decision=decision,
        warnings=tuple(warnings),
    )
    logging.info("brand ownership scored: total=%s decision=%s", result.total_score, result.decision)
    assert result.total_score >= 0
    return result


def _score_ratio(values: list[str], known_values: set[str], maximum_score: int) -> int:
    if maximum_score <= 0:
        raise ValueError("maximum_score must be positive")
    if not values or not known_values:
        return 0
    matched_count = sum(1 for value in values if value in known_values)
    ratio = Decimal(matched_count) / Decimal(len(values))
    score = int((ratio * Decimal(maximum_score)).to_integral_value())
    return min(score, maximum_score)


def _score_store_name_fallback(brand_name: str, normalized_rows: list[dict[str, str]]) -> int:
    brand = _normalize_cell(brand_name)
    if not brand:
        return 0
    names = [_normalize_cell(row.get("store_name", "")) for row in normalized_rows if _normalize_cell(row.get("store_name", ""))]
    if not names:
        return 0
    matched = sum(1 for name in names if brand in name)
    ratio = Decimal(matched) / Decimal(len(names))
    return int((ratio * Decimal(40)).to_integral_value())


def _validate_decimal(value: str, field: str, row_number: str, errors: list[str]) -> None:
    try:
        Decimal(value.replace(",", ""))
    except InvalidOperation:
        errors.append(f"row {row_number}: {field} must be decimal")


def _validate_integer(value: str, field: str, row_number: str, errors: list[str]) -> None:
    try:
        Decimal(value.replace(",", "")).to_integral_exact()
    except InvalidOperation:
        errors.append(f"row {row_number}: {field} must be integer")
