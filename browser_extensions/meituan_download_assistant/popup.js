const statusBox = document.getElementById("status");
const DAILY_FILE_TYPES = ["product_order", "store_finance", "store_traffic"];

const METRICS_BY_FILE_TYPE = {
  product_order: [
    "日期",
    "订单编号",
    "下单时间",
    "店铺名称",
    "店铺ID",
    "店铺所在城市",
    "订单状态",
    "订单总金额",
    "订单折扣后金额",
    "商品分类",
    "商品名称",
    "UPC码",
    "商品SKU码",
    "商品销售数量",
    "商品实付销售额",
    "商品总补贴金额",
    "商品商家补贴金额",
    "商品平台补贴金额",
    "是否部分退款商品",
    "部分退款商品数量",
    "部分退款商品金额"
  ],
  store_finance: [
    "商家ID",
    "商家名称",
    "省份",
    "城市",
    "收入",
    "商品原价",
    "包装费",
    "顾客配送费",
    "营业支出",
    "商家补贴金额",
    "公益捐款",
    "其他费用",
    "营业额",
    "实付交易额",
    "有效订单数",
    "实付单均价",
    "佣金",
    "配送服务费",
    "已取消订单数",
    "已取消订单损失金额"
  ],
  store_traffic: [
    "商家ID",
    "商家名称",
    "省份",
    "城市",
    "曝光人数",
    "曝光次数",
    "入店人数",
    "入店次数",
    "下单人数",
    "下单次数",
    "入店转化率",
    "下单转化率",
    "曝光新客",
    "入店新客",
    "下单新客",
    "新客入店转化率",
    "新客下单转化率",
    "曝光老客",
    "入店老客",
    "下单老客",
    "老客入店转化率",
    "老客下单转化率"
  ],
  service_review: [
    "评价提交日期",
    "评价提交时间",
    "店铺名称",
    "店铺ID",
    "店铺所在城市",
    "订单总金额",
    "订单折扣后金额",
    "订单商品",
    "用户评价",
    "用户追评",
    "用户追评时间",
    "商家回复",
    "商家回复时间",
    "商家评分",
    "子维度评分",
    "配送评分",
    "订单商品点赞率",
    "是否部分退款商品"
  ]
};

function toCompactDate(value) {
  if (!value) {
    throw new Error("date is required");
  }
  return value.replaceAll("-", "");
}

function selectedMetrics(fileType) {
  const selected = Array.from(document.querySelectorAll("#metricPanel input[type='checkbox']:checked"))
    .map((item) => item.value)
    .filter(Boolean);
  if (selected.length) {
    return selected;
  }
  return METRICS_BY_FILE_TYPE[fileType] || [];
}

function buildTask(fileType) {
  const task = {
    businessUnit: document.getElementById("businessUnit").value.trim(),
    brandId: document.getElementById("brandId").value.trim(),
    platform: "meituan",
    channel: "instant_retail",
    fileType,
    startDate: toCompactDate(document.getElementById("startDate").value),
    endDate: toCompactDate(document.getElementById("endDate").value),
    metrics: fileType === document.getElementById("fileType").value ? selectedMetrics(fileType) : METRICS_BY_FILE_TYPE[fileType],
    createdAt: new Date().toISOString()
  };
  if (!task.businessUnit || !task.brandId || !task.fileType) {
    throw new Error("businessUnit, brandId and fileType are required");
  }
  return task;
}

function readTask() {
  return buildTask(document.getElementById("fileType").value);
}

function renderMetrics() {
  const fileType = document.getElementById("fileType").value;
  const metrics = METRICS_BY_FILE_TYPE[fileType] || [];
  const panel = document.getElementById("metricPanel");
  panel.innerHTML = "";
  for (const metric of metrics) {
    const label = document.createElement("label");
    label.className = "metric-option";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = metric;
    input.checked = true;
    label.append(input, document.createTextNode(metric));
    panel.append(label);
  }
}

function selectAllMetrics() {
  for (const input of document.querySelectorAll("#metricPanel input[type='checkbox']")) {
    input.checked = true;
  }
}

function setStatus(message) {
  statusBox.textContent = message;
}

async function activeTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tabs.length || !tabs[0].id) {
    throw new Error("No active tab found");
  }
  return tabs[0];
}

function isSupportedMeituanUrl(url) {
  if (!url || typeof url !== "string") {
    return false;
  }
  try {
    const parsed = new URL(url);
    return parsed.hostname.endsWith("meituan.com")
      || parsed.hostname.endsWith("waimai.meituan.com")
      || parsed.hostname.endsWith("dianping.com");
  } catch (_error) {
    return false;
  }
}

async function sendToActiveTab(message) {
  const tab = await activeTab();
  if (!isSupportedMeituanUrl(tab.url)) {
    throw new Error("请先切换到美团后台页面，再使用插件。");
  }
  try {
    const injectionResults = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      files: ["content_script.js"]
    });
    if (!Array.isArray(injectionResults)) {
      throw new Error("content script injection failed");
    }
    const runResults = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      args: [message],
      func: async (payload) => {
        if (payload.type === "getPageSnapshot" && globalThis.meituanAssistantSnapshot) {
          return globalThis.meituanAssistantSnapshot();
        }
        if (payload.type === "runDownloadTask" && globalThis.meituanAssistantRunDownloadTask) {
          return globalThis.meituanAssistantRunDownloadTask(payload.task);
        }
        return { ok: false, message: "当前 frame 未加载美团报表助手脚本。" };
      }
    });
    const values = runResults.map((item) => item.result).filter(Boolean);
    const success = values.find((item) => item.ok);
    if (success) {
      return success;
    }
    const usefulFailure = values.find((item) => item.message && !item.message.includes("当前 frame 未加载"));
    if (usefulFailure) {
      return usefulFailure;
    }
  } catch (error) {
    if (!String(error.message || "").includes("Receiving end does not exist")) {
      console.warn("all-frame execution failed, falling back to tabs.sendMessage", error);
    }
  }
  try {
    return await chrome.tabs.sendMessage(tab.id, message);
  } catch (error) {
    if (!String(error.message || "").includes("Receiving end does not exist")) {
      throw error;
    }
    await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      files: ["content_script.js"]
    });
    return chrome.tabs.sendMessage(tab.id, message);
  }
}

async function setActiveDownloadTask(task) {
  await chrome.runtime.sendMessage({ type: "setActiveDownloadTask", task });
}

function defaultDateValues() {
  const now = new Date();
  now.setDate(now.getDate() - 1);
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const value = `${yyyy}-${mm}-${dd}`;
  document.getElementById("startDate").value = value;
  document.getElementById("endDate").value = value;
}

async function runOneTask(task) {
  await setActiveDownloadTask(task);
  return sendToActiveTab({ type: "runDownloadTask", task });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

document.getElementById("manualButton").addEventListener("click", async () => {
  try {
    const task = readTask();
    await setActiveDownloadTask(task);
    setStatus("已记录。现在可以在美团后台手动点击官方下载/下载。");
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("autoButton").addEventListener("click", async () => {
  try {
    const task = readTask();
    const result = await runOneTask(task);
    setStatus(result && result.message ? result.message : "已尝试执行自动导出。");
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("autoAllButton").addEventListener("click", async () => {
  try {
    const messages = [];
    for (const fileType of DAILY_FILE_TYPES) {
      const task = buildTask(fileType);
      setStatus(`正在处理 ${fileType} ...\n${messages.join("\n")}`);
      const result = await runOneTask(task);
      messages.push(`${fileType}: ${result && result.message ? result.message : "已执行"}`);
      await sleep(2500);
    }
    setStatus(messages.join("\n"));
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("snapshotButton").addEventListener("click", async () => {
  try {
    const result = await sendToActiveTab({ type: "getPageSnapshot" });
    setStatus(`页面：${result.title || "未知"}；可见按钮 ${result.buttonCount} 个。`);
  } catch (error) {
    setStatus(error.message);
  }
});

document.getElementById("fileType").addEventListener("change", renderMetrics);
document.getElementById("selectAllMetricsButton").addEventListener("click", selectAllMetrics);

defaultDateValues();
renderMetrics();
