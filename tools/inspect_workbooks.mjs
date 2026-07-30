import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = "C:/Users/JM042403/Downloads/内容任务耗时统计.xlsx";
const targetPath = "C:/Users/JM042403/Downloads/按模块区分.xlsx";

async function inspectWorkbook(label, filePath) {
  if (typeof label !== "string" || label.length === 0) {
    throw new TypeError("label must be a non-empty string");
  }
  if (typeof filePath !== "string" || filePath.length === 0) {
    throw new TypeError("filePath must be a non-empty string");
  }

  const input = await FileBlob.load(filePath);
  const workbook = await SpreadsheetFile.importXlsx(input);
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table,region",
    maxChars: 12000,
    tableMaxRows: 12,
    tableMaxCols: 20,
    tableMaxCellChars: 120,
  });

  console.log(`## ${label}`);
  console.log(summary.ndjson);
}

await inspectWorkbook("source", sourcePath);
await inspectWorkbook("target", targetPath);
