# feishu-sheet-reader

读取飞书电子表格数据的 Skill。根据自然语言指令，自动定位表格、Sheet、列和行，返回目标数据。

## 触发条件

用户想要读取飞书表格中的数据时触发，典型指令模式：

- `读取 {表格名}/{Sheet名}/{列名} {行条件}`
- `查一下飞书表格xxx的xxx`
- `飞书表格 xxx 第x行数据`
- `读取飞书表格的xxx`

**触发关键词**：飞书表格、读取表格、查表格、sheet、电子表格

## 前置条件

### 必须安装 lark-cli

```bash
npm install -g @larksuite/cli
```

### 必须配置应用凭证

首次使用需配置飞书应用凭证（非交互式）：

```bash
echo APP_SECRET | lark-cli config init --app-id APP_ID --app-secret-stdin --brand feishu
```

### 必须开通的权限

在飞书开放平台给应用开通以下权限：
- `wiki:node:read` — 解析 Wiki 链接
- `sheets:spreadsheet:read` — 读取电子表格

### Bot 必须能访问目标表格

如果表格在知识库中，需确保 Bot 有权访问该知识库节点。

## 执行流程

当用户发出读取指令时，按以下流程执行：

### Step 1: 解析用户指令

从用户指令中提取四个关键参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| `表格名` | 电子表格标题 | 小龙虾自动化 |
| `Sheet名` | 工作表名称 | Sheet1 |
| `列名` | 目标列的表头名 | 任务2 |
| `行条件` | 定位行的条件 | 当天第1行 / 4月26日 / 第3行 |

**解析规则**：
- 用 `/` 分隔时：`表格名/Sheet名/列名`
- 省略 Sheet名 时默认为 `Sheet1`
- 列名可以省略，表示读取整行
- 行条件可以是：
  - `当天` / `今天` / `今日` → 今天日期的行
  - `昨天` / `昨日` → 昨天日期的行
  - `YYYY-MM-DD` 或 `M月D日` → 指定日期
  - `第N行` → 指定行号（数据行，不含表头）
  - 省略时默认为"当天"

### Step 2: 定位表格

按以下优先级定位 spreadsheet_token：

1. **通过 Wiki 链接**：如果用户提供了 wiki URL，用 `lark-cli wiki spaces get_node --params '{"token":"WIKI_TOKEN"}' --as bot` 解析
2. **通过表格名搜索**：用 `lark-cli drive +search` 搜索表格名
3. **通过已知 token**：如果之前读取过该表格，复用 spreadsheet_token

### Step 3: 定位 Sheet

```bash
lark-cli sheets +info --spreadsheet-token TOKEN --as bot
```

从返回的 sheets 列表中，用 Sheet 名称匹配 `sheet_id`。

### Step 4: 定位列

```bash
lark-cli sheets +read --spreadsheet-token TOKEN --range "SHEET_ID!1:1" --as bot --value-render-option FormattedValue
```

读取第1行（表头行），匹配列名到列号（A=0, B=1, ...）。

### Step 5: 定位行

- **按日期定位**：读取日期列（通常为A列）全部值，找到匹配日期的行号
- **按行号定位**：直接计算（表头为第1行，数据从第2行开始，"第1行数据"=第2行）

```bash
lark-cli sheets +read --spreadsheet-token TOKEN --range "SHEET_ID!A2:A500" --as bot --value-render-option FormattedValue
```

### Step 6: 读取并返回数据

```bash
lark-cli sheets +read --spreadsheet-token TOKEN --range "SHEET_ID!A{ROW}:{END_COL}{ROW}" --as bot --value-render-option FormattedValue
```

**返回格式**：

将读取到的数据整理为易读的结构返回给用户：

```
📋 飞书表格「表格名」读取结果
Sheet: Sheet1 | 行: 第N行 | 日期: YYYY-MM-DD

| 列名 | 值 |
|------|-----|
| 日期 | 2026-05-02 |
| 任务2 | (内容摘要，超长截断) |
```

如果目标单元格为空，明确提示"该单元格为空"。

## 错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| lark-cli 未安装 | 提示安装命令 |
| 凭证未配置 | 提示配置命令 |
| 权限不足 | 提示需要在开放平台开通权限 |
| 表格名未找到 | 提示确认表格名或提供 wiki 链接 |
| Sheet 名未找到 | 列出可用的 Sheet 名称 |
| 列名未找到 | 列出可用的列名 |
| 日期行未找到 | 提示该日期不存在，列出已有日期范围 |
| 单元格为空 | 明确提示为空 |

## 已知限制

- 飞书表格富文本单元格（含链接、@提及等）返回的是结构化 JSON 而非纯文本，需要解析
- 日期格式依赖表格中的实际存储格式
- 一次最多读取 500 行用于定位

## 命令速查

```bash
# 安装
npm install -g @larksuite/cli

# 配置凭证
echo SECRET | lark-cli config init --app-id APP_ID --app-secret-stdin --brand feishu

# 解析 wiki 链接
lark-cli wiki spaces get_node --params '{"token":"TOKEN"}' --as bot

# 查看表格信息（获取 sheet 列表）
lark-cli sheets +info --spreadsheet-token TOKEN --as bot

# 读取数据
lark-cli sheets +read --spreadsheet-token TOKEN --range "SHEET_ID!A1:C1" --as bot --value-render-option FormattedValue
```
