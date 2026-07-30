# 内网自动化工作台

这是第一版内网试点模型，先覆盖四类入口：

- 博西短彩信数据处理，归类为 `01_data_processing`
- 安踏周报/月报，归类为 `01_data_processing`，优先级 `P1`
- 安踏即时零售，归类为 `03_config_automation_materials`，优先级 `P3`
- AI选品辅助，归类为 `02_brand_content_materials`
- 文案内容辅助，归类为 `02_brand_content_materials`

## 使用方式

在项目根目录运行：

```powershell
python -m intranet_app.app
```

浏览器打开：

```text
http://127.0.0.1:8785
```

如果要让同一局域网里的业务同事访问，运行：

```powershell
start_intranet_lan.bat
```

启动时输入一个正式管理员密码，至少 10 位，不能使用 `admin123`。然后把你电脑的局域网地址发给同事，格式类似：

```text
http://你的电脑局域网IP:8785
```

注意：

- 你的电脑必须和业务同事在同一个局域网或 VPN 内。
- 你的电脑需要保持开机，工作台窗口不能关闭。
- Windows 防火墙如果弹出允许访问，需要允许专用网络访问。
- 如果同事打不开，通常是防火墙、端口占用、网络不在同一网段导致。

本机试点默认账号：

```text
账号：admin
密码：admin123
```

局域网共享时仍使用账号 `admin`，密码是启动 `start_intranet_lan.bat` 时你输入的正式密码。

## 安踏即时零售网页

安踏即时零售已有独立网页工具，为避免重复开发和口径不一致，主工作台先以项目入口方式连接过去；黑名单筛选先接在主工作台的安踏项目页内上传处理。

先启动主工作台，再运行：

```powershell
start_anta_retail_web.bat
```

安踏网页默认地址：

```text
http://127.0.0.1:8766
```

如果要让同一局域网里的业务同事也能打开安踏网页，运行：

```powershell
start_anta_retail_lan.bat
```

同事从主工作台进入 `安踏即时零售` 后，按钮会自动使用同一台电脑的局域网地址和 `8766` 端口。

主工作台首页点击 `安踏即时零售` 后，会进入项目说明页，并提供打开安踏网页的按钮；黑名单筛选可在该页面下方直接上传处理。

当前安踏即时零售统一承接：

- 上下架筛选：官网货盘、美团商品原表、京东商品原表
- 素材筛选：待上架清单、素材索引或素材目录、必要时提供素材站 Cookie
- 黑名单筛选：黑名单明细、美团商品表、京东商品表、门店信息汇总，旧版美团黑名单可选

## 数据保存

系统会自动生成本地运行目录：

```text
intranet_app/runtime
```

其中：

- `intranet.sqlite3` 保存账号、登录会话、处理记录
- `uploads` 保存业务上传的原始文件
- `results` 保存系统生成的结果 CSV

## 提交文件夹自动归档

业务方不需要手动逐层归纳资料。统一把文件放到：

```text
ai_report_config_materials/00_intake/01_pending
```

然后在首页点击 `扫描并归档`。系统会自动判断：

```text
P1-P4、项目、品牌、平台、素材类型
```

并完成三件事：

- 复制文件到对应资料目录
- 把提交原件移动到 `00_intake/02_processed`
- 更新 `00_index_dictionary/archive_index.csv` 和 `00_index_dictionary/data_dictionary.csv`

首页的 `资料台账` 区域可以直接打开：

- `资料索引`
- `数据字典`

两个页面都支持网页查看和下载 CSV。

无法判断的文件会移动到：

```text
ai_report_config_materials/00_intake/03_unresolved
```

把文件名补充为 `品牌_平台_项目_资料类型_日期范围.xlsx` 后，再放回待处理文件夹重新扫描。

## 上传格式

当前支持 `.csv` 和 `.xlsx`。业务方可以先按资料包里的标准模板填写，再上传处理。

样例文件在：

```text
intranet_app/samples
```

## 已接入模块

### 博西短彩信数据处理

必填字段：

```text
品牌、发送日期、活动名称、渠道、发送量、到达量、点击量、订单量、成交金额
```

系统输出：

```text
到达率、点击率、转化率、单次发送产出、汇总指标、异常提醒
```

### 安踏即时零售

安踏即时零售是 P3 配置自动化项目。上下架筛选和素材筛选连接到现有成熟网页工具，黑名单筛选在主工作台项目页内上传处理。

子能力：

```text
上下架筛选、素材筛选、黑名单筛选
```

资料归档位置：

```text
ai_report_config_materials/03_config_automation_materials/03-1_anta_instant_retail
```

### 安踏周报/月报

安踏周报/月报是 P1 数据处理项目，目前先生成 CSV 初稿：

- 周报：自动读取 `01_data_processing/01-3_weekly_report/anta_weekly_report/01_raw_data` 中最新的美团、京东数据。
- 月报：自动读取 `01_data_processing/01-4_monthly_report/anta_monthly_report/01_raw_data` 中的商品数据、门店信息汇总、门店财务明细。

系统输出：

```text
核心销售指标、订单/销量汇总、门店/财务指标、TOP商品
```

后续可以在这套结果基础上继续升级为 PPT 或 Excel 模板成品。

### AI选品辅助

必填字段：

```text
页面先选择项目：通用选品 / 安踏儿童

通用选品字段：品牌、平台、商品ID、商品名称、类目、售价、近30天销量、库存、毛利率、活动匹配度

安踏儿童字段：平台、款号、商品名称、大类、类目、近7天销量、近7天销售额、近30天销量、库存、场景主题、选品角色、活动匹配度
```

系统输出：

```text
AI选品分、推荐优先级、推荐理由、人工复核提醒
```

当前规则不调用外部 API。通用选品按销量、库存、毛利率、活动匹配度评分；安踏儿童按周报/选品素材口径，结合近7天销量、近7天销售额、近30天销量、库存、选品角色和活动匹配度评分。安踏周报、月报、AI选品的补全资料在：

```text
ai_report_config_materials/02_brand_content_materials/anta_project_enrichment/anta_weekly_monthly_ai_selection_materials.xlsx
```

选品样例文件：

```text
intranet_app/samples/ai_selection_generic_sample.csv
intranet_app/samples/ai_selection_anta_sample.csv
```

### 文案内容辅助

必填字段：

```text
品牌、平台、内容类型、商品名称、核心卖点、目标人群、活动利益点、品牌调性、禁用词、内容主题、开场文案、使用场景、品牌背书
```

系统输出：

```text
AI标题建议、AI正文建议、禁用词命中结果、人工复核提醒
```

当前规则不调用外部 API，通过结构化模板生成带场景开头、商品定位、分段卖点、品牌收尾和活动提示的成品文案，并做禁用词初检。商品功效、材料、技术、优惠和品牌背书必须由业务提供并确认。

## 后续要补的能力

- 账号密码修改和角色权限配置
- Excel 结果直接导出为平台模板
- 日报、周报、月报处理入口
- 品牌内容资料库检索与复用
- 页面巡检复盘入口
- 共享内网地址和多人并发访问验证
