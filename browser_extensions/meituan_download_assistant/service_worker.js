const DEFAULT_SUBDIR = "meituan_auto_download";
const RECENT_TASK_WINDOW_MS = 10 * 60 * 1000;

function assertTask(task) {
  if (!task || typeof task !== "object") {
    throw new Error("task must be an object");
  }
  for (const key of ["businessUnit", "brandId", "platform", "channel", "fileType", "startDate", "endDate"]) {
    if (typeof task[key] !== "string" || !task[key].trim()) {
      throw new Error(`${key} is required`);
    }
  }
}

function safeSegment(value) {
  return String(value)
    .trim()
    .replace(/[\\/:*?"<>|]+/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 80);
}

function makeFilename(downloadItem, task) {
  const original = downloadItem.filename ? downloadItem.filename.split(/[\\/]/).pop() : "meituan_report.csv";
  const dateRange = task.startDate === task.endDate ? task.startDate : `${task.startDate}_${task.endDate}`;
  return [
    DEFAULT_SUBDIR,
    safeSegment(task.brandId),
    safeSegment(task.channel),
    safeSegment(dateRange),
    safeSegment(task.fileType),
    `${safeSegment(task.platform)}_${safeSegment(task.fileType)}_${safeSegment(dateRange)}_${safeSegment(original)}`
  ].join("/");
}

async function getActiveTask() {
  const data = await chrome.storage.local.get("activeDownloadTask");
  return data.activeDownloadTask || null;
}

async function isTaskRecent(task) {
  if (!task || !task.createdAt) {
    return false;
  }
  const createdAt = Date.parse(task.createdAt);
  return Number.isFinite(createdAt) && Date.now() - createdAt <= RECENT_TASK_WINDOW_MS;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "setActiveDownloadTask") {
    return false;
  }
  try {
    assertTask(message.task);
    chrome.storage.local.set({ activeDownloadTask: message.task }, () => {
      sendResponse({ ok: true });
    });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
  return true;
});

chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  getActiveTask()
    .then(async (task) => {
      if (!(await isTaskRecent(task))) {
        suggest();
        return;
      }
      suggest({
        filename: makeFilename(downloadItem, task),
        conflictAction: "uniquify"
      });
    })
    .catch(() => suggest());
  return true;
});
