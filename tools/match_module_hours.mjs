import fs from "node:fs/promises";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const ROOT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SOURCE_PATH = "C:/Users/JM042403/Downloads/内容任务耗时统计.xlsx";
const TARGET_PATH = "C:/Users/JM042403/Downloads/按模块区分.xlsx";
const OUTPUT_DIR = path.join(ROOT_DIR, "outputs", "module_summary");
const OUTPUT_PATH = path.join(OUTPUT_DIR, "按模块区分_已汇总.xlsx");

const CHANNELS = ["小程序&企微", "企微", "小程序", "CRM", "天猫", "飞猪", "京东", "经销"];
const SOURCE_SHEET = "运营";
const TARGET_SHEET = "Sheet2";

function requireNonEmptyString(value, label) {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new TypeError(`${label} must be a non-empty string`);
  }
  return value.trim();
}

function normalizeText(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value.trim().replace(/\s+/g, "");
  }
  return String(value).trim().replace(/\s+/g, "");
}

function parseNumericCell(value, context) {
  if (context === null || typeof context !== "object") {
    throw new TypeError("context must be an object");
  }
  if (value === null || value === undefined || value === "") {
    return 0;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new TypeError(`non-finite number at ${context.address}`);
    }
    return value;
  }
  if (typeof value === "string") {
    const cleaned = value.trim();
    if (cleaned.length === 0) {
      return 0;
    }
    const parsed = Number(cleaned);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  throw new TypeError(`non-numeric耗时 at ${context.address}: ${String(value)}`);
}

function fillForwardChannels(headerRow) {
  if (!Array.isArray(headerRow) || headerRow.length === 0) {
    throw new TypeError("headerRow must be a non-empty array");
  }
  const filled = [];
  let current = "";
  for (const value of headerRow) {
    const normalized = normalizeText(value);
    if (CHANNELS.includes(normalized)) {
      current = normalized;
    }
    filled.push(current);
  }
  assert.equal(filled.length, headerRow.length, "filled channel width mismatch");
  return filled;
}

function buildSourceSummary(sourceValues) {
  if (!Array.isArray(sourceValues) || sourceValues.length < 7) {
    throw new TypeError("sourceValues must contain source rows");
  }

  const platformRow = sourceValues[2];
  const fieldRow = sourceValues[4];
  const contentCol = fieldRow.findIndex((value) => normalizeText(value) === "工作内容");
  if (contentCol < 0) {
    throw new Error("source 工作内容 column not found");
  }

  const channelsByCol = fillForwardChannels(platformRow);
  const summaryByContent = new Map();
  const sourceContentKeys = new Set();
  const skippedRows = [];

  for (let rowIndex = 6; rowIndex < sourceValues.length; rowIndex += 1) {
    const row = sourceValues[rowIndex];
    const rawContent = row[contentCol];
    const contentKey = normalizeText(rawContent);
    if (contentKey.length === 0) {
      skippedRows.push({
        row: rowIndex + 1,
        reason: "工作内容为空",
        content: "",
      });
      continue;
    }

    const rowSummary = Object.fromEntries(CHANNELS.map((channel) => [channel, 0]));
    for (let colIndex = 0; colIndex < row.length; colIndex += 1) {
      const channel = channelsByCol[colIndex];
      if (!CHANNELS.includes(channel)) {
        continue;
      }
      const address = `${String.fromCharCode(65 + (colIndex % 26))}${rowIndex + 1}`;
      const value = parseNumericCell(row[colIndex], { address });
      rowSummary[channel] += value;
    }

    sourceContentKeys.add(contentKey);
    const existing = summaryByContent.get(contentKey);
    if (existing === undefined) {
      summaryByContent.set(contentKey, rowSummary);
    } else {
      for (const channel of CHANNELS) {
        existing[channel] += rowSummary[channel];
      }
    }
  }

  assert.ok(summaryByContent.size > 0, "source summary must not be empty");
  return { summaryByContent, sourceContentKeys, skippedRows };
}

function buildTargetMatrix(targetValues, sourceSummary) {
  if (!Array.isArray(targetValues) || targetValues.length < 2) {
    throw new TypeError("targetValues must contain target rows");
  }
  if (sourceSummary === null || typeof sourceSummary !== "object") {
    throw new TypeError("sourceSummary must be an object");
  }

  const header = targetValues[0].map((value) => normalizeText(value));
  const contentCol = header.indexOf("工作内容");
  if (contentCol < 0) {
    throw new Error("target 工作内容 column not found");
  }

  const channelColIndexes = CHANNELS.map((channel) => {
    const colIndex = header.indexOf(channel);
    if (colIndex < 0) {
      throw new Error(`target channel column not found: ${channel}`);
    }
    return colIndex;
  });

  const matrix = [];
  const matchedKeys = new Set();
  const unmatchedTargetRows = [];
  for (let rowIndex = 1; rowIndex < targetValues.length; rowIndex += 1) {
    const row = targetValues[rowIndex];
    const contentKey = normalizeText(row[contentCol]);
    if (contentKey.length === 0) {
      unmatchedTargetRows.push({ row: rowIndex + 1, reason: "目标工作内容为空", content: "" });
      matrix.push(CHANNELS.map(() => null));
      continue;
    }
    const summary = sourceSummary.summaryByContent.get(contentKey);
    if (summary === undefined) {
      unmatchedTargetRows.push({ row: rowIndex + 1, reason: "来源未找到同名工作内容", content: row[contentCol] });
      matrix.push(CHANNELS.map(() => null));
      continue;
    }
    matchedKeys.add(contentKey);
    matrix.push(CHANNELS.map((channel) => {
      const rounded = Math.round((summary[channel] + Number.EPSILON) * 100) / 100;
      return rounded === 0 ? null : rounded;
    }));
  }

  const unmatchedSourceRows = [];
  for (const contentKey of sourceSummary.sourceContentKeys) {
    if (!matchedKeys.has(contentKey)) {
      unmatchedSourceRows.push({ reason: "目标未找到同名工作内容", content: contentKey });
    }
  }

  assert.equal(matrix.length, targetValues.length - 1, "target matrix row count mismatch");
  assert.ok(channelColIndexes.length === CHANNELS.length, "channel column count mismatch");
  return { matrix, channelColIndexes, unmatchedTargetRows, unmatchedSourceRows };
}

async function main() {
  console.info("Loading source and target workbooks");
  const sourceWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(SOURCE_PATH));
  const targetWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(TARGET_PATH));

  const sourceSheet = sourceWorkbook.worksheets.getItem(requireNonEmptyString(SOURCE_SHEET, "SOURCE_SHEET"));
  const targetSheet = targetWorkbook.worksheets.getItem(requireNonEmptyString(TARGET_SHEET, "TARGET_SHEET"));

  const sourceValues = sourceSheet.getRange("A1:BP50").values;
  const targetValues = targetSheet.getRange("A1:O45").values;
  const sourceSummary = buildSourceSummary(sourceValues);
  const result = buildTargetMatrix(targetValues, sourceSummary);

  console.info(`Matched rows: ${result.matrix.length - result.unmatchedTargetRows.length}`);
  console.info(`Unmatched target rows: ${result.unmatchedTargetRows.length}`);
  console.info(`Unmatched source rows: ${result.unmatchedSourceRows.length}`);

  console.info("Writing channel summary to target sheet");
  targetSheet.getRange("H2:O45").values = result.matrix;
  targetSheet.getRange("H2:O45").format.numberFormat = "#,##0.##";

  const auditRows = [
    ...sourceSummary.skippedRows.map((item) => ["来源", item.row, item.reason, item.content, "未纳入汇总"]),
    ...result.unmatchedTargetRows.map((item) => ["目标", item.row, item.reason, item.content, "对应渠道列保留为空"]),
    ...result.unmatchedSourceRows.map((item) => ["来源", "", item.reason, item.content, "未写入目标表"]),
  ];
  if (auditRows.length > 0) {
    console.info("Writing audit sheet");
    const auditSheet = targetWorkbook.worksheets.add("待核验");
    auditSheet.getRange("A1:E1").values = [["类型", "行号", "原因", "工作内容", "备注"]];
    auditSheet.getRangeByIndexes(1, 0, auditRows.length, 5).values = auditRows;
    auditSheet.getRange("A1:E1").format = {
      fill: "#244062",
      font: { bold: true, color: "#FFFFFF" },
    };
    const auditEndRow = Math.max(auditRows.length + 1, 1);
    auditSheet.getRange(`A1:E${auditEndRow}`).format.autofitColumns();
  }

  console.info("Scanning formula errors");
  const errors = await targetWorkbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "final formula error scan",
  });
  console.log(errors.ndjson);

  console.info("Exporting workbook");
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(targetWorkbook);
  await output.save(OUTPUT_PATH);
  console.info(`Saved ${OUTPUT_PATH}`);
}

try {
  await main();
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  process.exitCode = 1;
}
