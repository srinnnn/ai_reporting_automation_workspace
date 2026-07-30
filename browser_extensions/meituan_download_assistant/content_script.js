const BLOCKED_ACTION_TEXT = [
  "保存",
  "提交",
  "确认修改",
  "发布",
  "上架",
  "下架",
  "删除",
  "配置",
  "编辑",
  "新增",
  "启用",
  "停用"
];

const REPORT_RULES = {
  product_order: {
    tabText: "订单数据",
    dataTypeText: "商品数据",
    queryButtonText: ["查询", "搜索"],
    createReportText: ["创建报表", "导出", "下载", "报表下载"],
    expectedFilenameText: ["商品数据"]
  },
  store_finance: {
    tabText: "交易数据",
    dataTypeText: "门店财务明细",
    queryButtonText: ["查询", "搜索"],
    createReportText: ["创建报表", "导出", "下载", "报表下载"],
    expectedFilenameText: ["门店财务明细"]
  },
  store_traffic: {
    tabText: "流量数据",
    dataTypeText: "门店流量明细",
    queryButtonText: ["查询", "搜索"],
    createReportText: ["创建报表", "导出", "下载", "报表下载"],
    expectedFilenameText: ["门店流量明细"]
  },
  service_review: {
    tabText: "服务数据",
    dataTypeText: "评价数据",
    queryButtonText: ["查询", "搜索"],
    createReportText: ["创建报表", "导出", "下载", "报表下载"],
    expectedFilenameText: ["评价分析明细", "评价数据"]
  }
};

function normalizedText(node) {
  return (node.innerText || node.textContent || node.value || "").replace(/\s+/g, " ").trim();
}

function visibleElements() {
  return Array.from(document.querySelectorAll(
    "button, a, label, span, li, div[role='button'], div[class*='btn'], input[type='radio'] + span, input[type='checkbox'] + span"
  )).filter((node) => {
    const rect = node.getBoundingClientRect();
    const style = window.getComputedStyle(node);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  });
}

function visibleInputs() {
  return Array.from(document.querySelectorAll("input")).filter((node) => {
    const rect = node.getBoundingClientRect();
    const style = window.getComputedStyle(node);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  });
}

function containsBlockedAction(text) {
  return BLOCKED_ACTION_TEXT.some((blocked) => text.includes(blocked));
}

function clickByText(candidates) {
  if (!Array.isArray(candidates) || !candidates.length) {
    throw new Error("candidates must not be empty");
  }
  const target = visibleElements().find((node) => {
    const text = normalizedText(node);
    return text && candidates.some((candidate) => text.includes(candidate)) && !containsBlockedAction(text);
  });
  if (!target) {
    return false;
  }
  target.click();
  return true;
}

function setNativeValue(input, value) {
  const wasReadonly = input.hasAttribute("readonly");
  if (wasReadonly) {
    input.removeAttribute("readonly");
  }
  const prototype = Object.getPrototypeOf(input);
  const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
  const tracker = input._valueTracker;
  if (tracker) {
    tracker.setValue("");
  }
  if (descriptor && descriptor.set) {
    descriptor.set.call(input, value);
  } else {
    input.value = value;
  }
  input.dispatchEvent(new Event("focus", { bubbles: true }));
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", bubbles: true }));
  input.dispatchEvent(new Event("blur", { bubbles: true }));
  if (wasReadonly) {
    input.setAttribute("readonly", "true");
  }
}

function inputValue(input) {
  return (input.value || input.getAttribute("value") || "").trim();
}

function compactToIsoDate(value) {
  if (!/^\d{8}$/.test(value || "")) {
    throw new Error("date must be yyyymmdd");
  }
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
}

function applyDateRange(task) {
  const inputs = visibleInputs();
  const dateInputs = inputs.filter((input) => {
    const text = `${input.type || ""} ${input.placeholder || ""} ${input.getAttribute("aria-label") || ""}`;
    return input.type === "date" || /日期|时间|date|time/i.test(text);
  });
  if (!dateInputs.length) {
    return 0;
  }
  const start = compactToIsoDate(task.startDate);
  const end = compactToIsoDate(task.endDate);
  if (dateInputs.length >= 2) {
    setNativeValue(dateInputs[0], start);
    setNativeValue(dateInputs[1], end);
    if (inputValue(dateInputs[0]) !== start || inputValue(dateInputs[1]) !== end) {
      throw new Error(`日期选择失败：页面日期仍为 ${inputValue(dateInputs[0])} ~ ${inputValue(dateInputs[1])}，目标日期为 ${start} ~ ${end}`);
    }
    return 2;
  }
  setNativeValue(dateInputs[0], start === end ? start : `${start} ~ ${end}`);
  if (!inputValue(dateInputs[0]).includes(start) || !inputValue(dateInputs[0]).includes(end)) {
    throw new Error(`日期选择失败：页面日期仍为 ${inputValue(dateInputs[0])}，目标日期为 ${start} ~ ${end}`);
  }
  return 1;
}

function clickMetric(metric) {
  const target = visibleElements().find((node) => {
    const text = normalizedText(node);
    return text === metric || text.includes(metric);
  });
  if (!target) {
    return false;
  }
  const label = target.closest("label");
  const checkbox = (label && label.querySelector("input[type='checkbox']"))
    || target.parentElement?.querySelector?.("input[type='checkbox']")
    || target.previousElementSibling;
  if (checkbox && checkbox.type === "checkbox" && checkbox.checked) {
    return true;
  }
  target.click();
  return true;
}

function selectMetrics(metrics) {
  if (!Array.isArray(metrics) || !metrics.length) {
    return { requested: 0, clicked: 0 };
  }
  let clicked = 0;
  for (const metric of metrics) {
    if (typeof metric === "string" && metric.trim() && clickMetric(metric.trim())) {
      clicked += 1;
    }
  }
  return { requested: metrics.length, clicked };
}

function snapshot() {
  const buttons = visibleElements().map(normalizedText).filter(Boolean);
  return {
    title: document.title,
    url: location.href,
    buttonCount: buttons.length,
    visibleTexts: buttons.slice(0, 100)
  };
}

function findDownloadRow(rule, task) {
  const datePattern = task.startDate === task.endDate
    ? [task.startDate]
    : [task.startDate, task.endDate];
  const rows = Array.from(document.querySelectorAll("tr, li, div")).filter((node) => {
    const text = normalizedText(node);
    if (!text || containsBlockedAction(text)) {
      return false;
    }
    const hasName = rule.expectedFilenameText.some((name) => text.includes(name));
    const hasDate = datePattern.every((date) => text.includes(date));
    const hasDownload = text.includes("下载");
    return hasName && hasDate && hasDownload;
  });
  return rows[0] || null;
}

function clickDownloadInLatestRow(rule, task) {
  const row = findDownloadRow(rule, task);
  if (!row) {
    return false;
  }
  const target = Array.from(row.querySelectorAll("button, a, span, div[role='button']")).find((node) => {
    const text = normalizedText(node);
    return text === "下载" || text.includes("下载");
  });
  if (!target || containsBlockedAction(normalizedText(target))) {
    return false;
  }
  target.click();
  return true;
}

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function createReport(task, rule) {
  const clickedReportTab = clickByText(["报表下载"]);
  await wait(600);
  const clickedTab = clickByText([rule.tabText]);
  await wait(600);
  const clickedDataType = clickByText([rule.dataTypeText]);
  await wait(600);
  const dateInputCount = applyDateRange(task);
  await wait(400);
  const metricResult = selectMetrics(task.metrics || []);
  await wait(400);
  const clickedQuery = clickByText(rule.queryButtonText);
  await wait(1200);
  const clickedCreate = clickByText(rule.createReportText);
  const clickedExport = clickedCreate;
  return { clickedReportTab, clickedTab, clickedDataType, dateInputCount, metricResult, clickedQuery, clickedCreate, clickedExport };
}

async function downloadCreatedReport(task, rule) {
  const clickedDownloadList = clickByText(["下载列表", "我的下载", "下载专区"]);
  await wait(2000);
  const clickedRefresh = clickByText(["刷新"]);
  if (clickedRefresh) {
    await wait(1000);
  }
  for (let attempt = 0; attempt < 12; attempt += 1) {
    if (clickDownloadInLatestRow(rule, task)) {
      return { clickedDownloadList, clickedRefresh, downloaded: true, attempts: attempt + 1 };
    }
    await wait(5000);
    clickByText(["刷新"]);
  }
  return { clickedDownloadList, clickedRefresh, downloaded: false, attempts: 12 };
}

async function runDownloadTask(task) {
  if (!task || typeof task !== "object") {
    throw new Error("task is required");
  }
  const rule = REPORT_RULES[task.fileType];
  if (!rule) {
    throw new Error(`Unsupported fileType: ${task.fileType}`);
  }
  const createResult = await createReport(task, rule);
  if (!createResult.clickedCreate) {
    return {
      ok: false,
      message: `没有找到创建报表/导出按钮。报表页${createResult.clickedReportTab ? "已点击" : "未点击"}，页签${createResult.clickedTab ? "已点击" : "未点击"}，类型${createResult.clickedDataType ? "已点击" : "未点击"}，日期输入${createResult.dateInputCount}，查询${createResult.clickedQuery ? "已点击" : "未点击"}，指标${createResult.metricResult.clicked}/${createResult.metricResult.requested}。`
    };
  }
  const downloadResult = await downloadCreatedReport(task, rule);
  if (!downloadResult.downloaded) {
    return {
      ok: false,
      message: `已创建报表，但下载列表内未找到匹配 ${task.startDate}-${task.endDate} 的 ${task.fileType} 下载按钮；已轮询 ${downloadResult.attempts} 次。`
    };
  }
  return {
    ok: true,
    message: `已完成官方流程：创建报表并从下载列表下载 ${task.fileType}。`
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || typeof message !== "object") {
    return false;
  }
  if (message.type === "getPageSnapshot") {
    sendResponse(snapshot());
    return false;
  }
  if (message.type === "runDownloadTask") {
    runDownloadTask(message.task)
      .then(sendResponse)
      .catch((error) => sendResponse({ ok: false, message: error.message }));
    return true;
  }
  return false;
});

globalThis.meituanAssistantSnapshot = snapshot;
globalThis.meituanAssistantRunDownloadTask = runDownloadTask;
