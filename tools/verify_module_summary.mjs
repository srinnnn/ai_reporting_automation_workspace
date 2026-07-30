import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT_PATH = path.join(ROOT_DIR, "outputs", "module_summary", "按模块区分_已汇总.xlsx");

async function main() {
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(OUTPUT_PATH));

const sample = await workbook.inspect({
  kind: "table",
  range: "Sheet2!A1:O12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 15,
  maxChars: 8000,
});
console.log(sample.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const values = workbook.worksheets.getItem("Sheet2").getRange("A1:O45").values;
const mismatches = [];
for (let rowIndex = 1; rowIndex < values.length; rowIndex += 1) {
  const row = values[rowIndex];
  const expected = Number(row[6] ?? 0);
  const actual = row.slice(7, 15).reduce((sum, value) => sum + Number(value ?? 0), 0);
  const delta = Math.round((actual - expected) * 100) / 100;
  if (Math.abs(delta) > 0.01) {
    mismatches.push({
      row: rowIndex + 1,
      content: row[2],
      expected,
      actual: Math.round(actual * 100) / 100,
      delta,
    });
  }
}
console.log(JSON.stringify({ rowTotalDifferences: mismatches }, null, 2));
}

try {
  await main();
} catch (error) {
  console.error(error instanceof Error ? error.stack : String(error));
  process.exitCode = 1;
}
