#!/usr/bin/env python3
"""
feishu_sheet_reader.py - 飞书表格数据读取器

根据指令参数自动定位并读取飞书电子表格数据。

用法:
    python feishu_sheet_reader.py --sheet-name "小龙虾自动化" --tab "Sheet1" --column "任务2" --row-condition "当天"
    python feishu_sheet_reader.py --sheet-name "小龙虾自动化" --column "任务1" --row-condition "2026-04-26"
    python feishu_sheet_reader.py --wiki-url "https://my.feishu.cn/wiki/xxx" --column "任务2" --row-condition "今天"
    python feishu_sheet_reader.py --spreadsheet-token "Y38OsRv1yhMe55tTcI8c0RLznTh" --column "任务2" --row-condition "当天第1行"

行条件格式:
    "当天" / "今天" / "今日"  → 今天的日期
    "昨天" / "昨日"           → 昨天的日期
    "YYYY-MM-DD"              → 指定日期
    "M月D日"                  → 指定日期（中文格式）
    "第N行"                   → 指定数据行号（1-based，不含表头）
    "当天第N行"               → 今天的第N个匹配行
    "全部" / "所有"           → 返回所有数据行
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta


def run_lark_cli(*args, identity="bot"):
    """运行 lark-cli 命令并返回 JSON 结果"""
    # Windows 上 lark-cli 是 .cmd 文件，需要 shell=True 或完整路径
    cmd = ["lark-cli"] + list(args) + ["--as", identity]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8", shell=True)
        output = result.stdout.strip()
        stderr = result.stderr.strip()

        # Windows PowerShell 会用 CLIXML 包裹输出，需要提取其中的纯文本
        # CLIXML 格式: #< CLIXML\r\n<Objs...>实际JSON输出</Objs>
        # lark-cli 在 PowerShell 中可能把 JSON 输出到 stdout，被 CLIXML 包裹
        # 也可能部分输出到 stderr

        # 合并 stdout 和 stderr 来找 JSON
        combined = output + "\n" + stderr if stderr else output

        # 尝试从输出中提取完整的 JSON 对象
        # 找到第一个 { 开始的 JSON
        json_str = extract_json(combined)

        if json_str:
            return json.loads(json_str)

        if not output and not stderr:
            return {"ok": False, "error": "lark-cli 返回为空"}

        return {"ok": False, "error": f"lark-cli 返回无有效 JSON", "stdout": output[:300], "stderr": stderr[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "lark-cli 命令超时"}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"JSON 解析失败: {e}"}
    except FileNotFoundError:
        return {"ok": False, "error": "lark-cli 未安装，请运行: npm install -g @larksuite/cli"}


def extract_json(text):
    """从可能包含 CLIXML 等干扰的文本中提取第一个完整的 JSON 对象"""
    # 找到第一个 {
    idx = text.find("{")
    if idx < 0:
        return None

    # 从第一个 { 开始，匹配到对应的 }
    brace_count = 0
    in_string = False
    escape_next = False

    for i in range(idx, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == '\\' and in_string:
            escape_next = True
            continue

        if ch == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == '{':
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[idx:i+1]

    return None


def resolve_wiki_token(wiki_url):
    """从 wiki URL 中提取 token 并解析为 spreadsheet_token"""
    # 从 URL 提取 token
    # 支持格式: https://my.feishu.cn/wiki/TOKEN 或 https://xxx.feishu.cn/wiki/TOKEN?xxx
    match = re.search(r"/wiki/([A-Za-z0-9]+)", wiki_url)
    if not match:
        return None, None, "无法从 URL 中提取 wiki token"
    wiki_token = match.group(1)

    result = run_lark_cli("wiki", "spaces", "get_node", '--params', json.dumps({"token": wiki_token}))
    if result.get("ok") is False and "code" not in result:
        # 可能返回格式不同
        data = result.get("data", result.get("error", {}))
        if isinstance(data, dict) and "node" in data:
            node = data["node"]
        else:
            return None, None, f"Wiki 解析失败: {result.get('error', result.get('message', str(result)))}"
    else:
        data = result.get("data", {})
        node = data.get("node", {})

    obj_type = node.get("obj_type", "")
    obj_token = node.get("obj_token", "")
    title = node.get("title", "")

    if obj_type != "sheet":
        return None, None, f"Wiki 节点类型为 {obj_type}，不是电子表格(sheet)"

    return obj_token, title, None


def search_spreadsheet_by_name(name):
    """通过名称搜索电子表格"""
    result = run_lark_cli("drive", "+search", "--query", name)
    if result.get("ok") is False:
        # 尝试用 user 身份搜索
        result = run_lark_cli("drive", "+search", "--query", name, identity="user")

    # 解析搜索结果
    data = result.get("data", {})
    items = data.get("items", [])
    for item in items:
        if item.get("type") == "sheet" and name in item.get("name", ""):
            return item.get("token"), item.get("name")

    return None, None


def get_spreadsheet_info(spreadsheet_token):
    """获取表格信息（sheet 列表等）"""
    result = run_lark_cli("sheets", "+info", "--spreadsheet-token", spreadsheet_token)

    # lark-cli 返回可能有两种格式:
    # 1. {"ok": true, "data": {"spreadsheet": {...}, "sheets": {...}}}
    # 2. {"code": 0, "data": {"spreadsheet": {...}, "sheets": {...}}}
    ok = result.get("ok", False) or result.get("code") == 0
    if not ok:
        return {"title": "", "token": spreadsheet_token, "sheets": []}

    data = result.get("data", result)

    # 提取 spreadsheet 信息
    spread_info = data.get("spreadsheet", {}).get("spreadsheet", {})
    title = spread_info.get("title", "")
    token = spread_info.get("token", spreadsheet_token)

    # 提取 sheets 列表
    sheets_data = data.get("sheets", {}).get("sheets", [])
    if not sheets_data:
        # 有些返回格式 sheets 直接在 data 下
        sheets_data = data.get("sheets", [])

    sheets = []
    for s in sheets_data:
        if not isinstance(s, dict):
            continue
        sheets.append({
            "sheet_id": s.get("sheet_id", ""),
            "title": s.get("title", ""),
            "row_count": s.get("grid_properties", {}).get("row_count", 0) if isinstance(s.get("grid_properties"), dict) else 0,
            "col_count": s.get("grid_properties", {}).get("column_count", 0) if isinstance(s.get("grid_properties"), dict) else 0,
            "frozen_row_count": s.get("grid_properties", {}).get("frozen_row_count", 0) if isinstance(s.get("grid_properties"), dict) else 0,
            "index": s.get("index", 0),
        })

    return {"title": title, "token": token, "sheets": sheets}


def col_index_to_letter(index):
    """将列索引(0-based)转换为字母(A, B, ..., Z, AA, AB, ...)"""
    result = ""
    index += 1  # 1-based
    while index > 0:
        index -= 1
        result = chr(65 + index % 26) + result
        index //= 26
    return result


def letter_to_col_index(letter):
    """将列字母转换为索引(0-based)"""
    result = 0
    for ch in letter.upper():
        result = result * 26 + (ord(ch) - 64)
    return result - 1


def read_range(spreadsheet_token, sheet_id, range_str, value_render="FormattedValue"):
    """读取指定范围的数据"""
    result = run_lark_cli(
        "sheets", "+read",
        "--spreadsheet-token", spreadsheet_token,
        "--range", f"{sheet_id}!{range_str}",
        "--value-render-option", value_render,
    )
    data = result.get("data", result)
    values = data.get("valueRange", {}).get("values", [])
    return values


def parse_row_condition(condition, today=None):
    """解析行条件，返回 (日期字符串 or None, 行号 or None, 是否全部)"""
    if today is None:
        today = datetime.now()

    condition = condition.strip()

    # 全部
    if condition in ("全部", "所有", "all"):
        return None, None, True

    # 第N行
    match = re.match(r"第(\d+)行", condition)
    if match:
        return None, int(match.group(1)), False

    # 当天第N行
    match = re.match(r"(?:当天|今天|今日)第(\d+)行", condition)
    if match:
        return today.strftime("%Y-%m-%d"), int(match.group(1)), False

    # 当天/今天/今日
    if condition in ("当天", "今天", "今日", "today"):
        return today.strftime("%Y-%m-%d"), 1, False

    # 昨天/昨日
    if condition in ("昨天", "昨日", "yesterday"):
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d"), 1, False

    # YYYY-MM-DD
    match = re.match(r"(\d{4}-\d{2}-\d{2})", condition)
    if match:
        return match.group(1), 1, False

    # M月D日
    match = re.match(r"(\d{1,2})月(\d{1,2})日?", condition)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        return f"{today.year}-{month:02d}-{day:02d}", 1, False

    # 默认当作当天
    return today.strftime("%Y-%m-%d"), 1, False


def parse_rich_text(cell_value):
    """解析飞书富文本单元格，提取纯文本"""
    if cell_value is None:
        return "(空)"
    if isinstance(cell_value, str):
        return cell_value
    if isinstance(cell_value, list):
        # 富文本格式: [{"text": "...", "type": "text"}, {"text": "...", "link": "...", "type": "url"}, ...]
        parts = []
        for item in cell_value:
            if isinstance(item, dict):
                text = item.get("text", "")
                link = item.get("link", "")
                if link:
                    parts.append(f"{text}[{link}]")
                else:
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return str(cell_value)


def truncate_text(text, max_len=200):
    """截断过长文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def find_date_row(values, target_date, occurrence=1):
    """在日期列中查找目标日期的行号（在 values 数组中的索引）"""
    found = 0
    for i, row in enumerate(values):
        if row and len(row) > 0:
            date_val = row[0]
            if isinstance(date_val, str) and date_val == target_date:
                found += 1
                if found == occurrence:
                    return i
    return -1


def main():
    parser = argparse.ArgumentParser(description="飞书表格数据读取器")
    parser.add_argument("--sheet-name", help="电子表格名称")
    parser.add_argument("--spreadsheet-token", help="电子表格 token（优先级高于名称搜索）")
    parser.add_argument("--wiki-url", help="Wiki URL（优先级最高）")
    parser.add_argument("--tab", default="Sheet1", help="工作表名称（默认 Sheet1）")
    parser.add_argument("--column", help="目标列名（如：任务2）")
    parser.add_argument("--row-condition", default="当天", help="行条件（默认：当天）")
    parser.add_argument("--identity", default="bot", choices=["bot", "user"], help="身份类型（默认 bot）")
    args = parser.parse_args()

    # 设置 stdout 编码为 UTF-8（Windows 默认是 GBK，会导致中文乱码）
    sys.stdout.reconfigure(encoding='utf-8')

    output = {
        "success": False,
        "spreadsheet": {},
        "sheet": {},
        "data": [],
        "error": None,
    }

    # ==================== Step 1: 定位表格 ====================
    spreadsheet_token = args.spreadsheet_token
    spreadsheet_title = ""

    if args.wiki_url:
        spreadsheet_token, spreadsheet_title, err = resolve_wiki_token(args.wiki_url)
        if err:
            output["error"] = f"Wiki 解析失败: {err}"
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 1
    elif not spreadsheet_token and args.sheet_name:
        # 尝试通过名称搜索（需要 user 身份）
        spreadsheet_token, spreadsheet_title = search_spreadsheet_by_name(args.sheet_name)
        if not spreadsheet_token:
            output["error"] = f"未找到表格「{args.sheet_name}」，请提供 wiki URL 或 spreadsheet token"
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 1

    if not spreadsheet_token:
        output["error"] = "请提供 --sheet-name, --spreadsheet-token 或 --wiki-url 之一"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1

    # ==================== Step 2: 获取表格信息 ====================
    info = get_spreadsheet_info(spreadsheet_token)
    if not info.get("sheets"):
        output["error"] = f"无法获取表格信息，可能是权限不足或 token 无效: {spreadsheet_token}"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1

    spreadsheet_title = spreadsheet_title or info.get("title", "")
    output["spreadsheet"] = {"title": spreadsheet_title, "token": spreadsheet_token}

    # ==================== Step 3: 定位 Sheet ====================
    target_sheet = None
    for s in info["sheets"]:
        if s["title"].lower() == args.tab.lower():
            target_sheet = s
            break

    if not target_sheet:
        available = [s["title"] for s in info["sheets"]]
        output["error"] = f"未找到工作表「{args.tab}」，可用工作表: {available}"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1

    sheet_id = target_sheet["sheet_id"]
    row_count = target_sheet["row_count"]
    col_count = target_sheet["col_count"]
    output["sheet"] = {"title": target_sheet["title"], "sheet_id": sheet_id, "rows": row_count, "cols": col_count}

    # ==================== Step 4: 读取表头，定位列 ====================
    end_col = col_index_to_letter(col_count - 1)
    header_values = read_range(spreadsheet_token, sheet_id, f"A1:{end_col}1")
    if not header_values or not header_values[0]:
        output["error"] = "无法读取表头行"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1

    headers = header_values[0]

    # 找目标列
    target_col_indices = []  # 要读取的列索引列表
    target_col_names = []     # 对应的列名列表

    if args.column:
        # 精确匹配 + 模糊匹配
        for i, h in enumerate(headers):
            if h and isinstance(h, str) and h.strip() == args.column.strip():
                target_col_indices = [i]
                target_col_names = [h.strip()]
                break
        if not target_col_indices:
            # 模糊匹配
            for i, h in enumerate(headers):
                if h and isinstance(h, str) and args.column.strip() in h.strip():
                    target_col_indices = [i]
                    target_col_names = [h.strip()]
                    break
        if not target_col_indices:
            available = [h for h in headers if h and isinstance(h, str)]
            output["error"] = f"未找到列「{args.column}」，可用列: {available}"
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 1
    else:
        # 读取所有列
        target_col_indices = list(range(len(headers)))
        target_col_names = [h if h and isinstance(h, str) else f"列{col_index_to_letter(i)}" for i, h in enumerate(headers)]

    # ==================== Step 5: 定位行 ====================
    target_date, target_row_num, fetch_all = parse_row_condition(args.row_condition)
    data_start_row = 2  # 数据从第2行开始（第1行是表头）

    if fetch_all:
        # 读取全部数据
        target_rows = list(range(data_start_row, row_count + 1))
    elif target_row_num and not target_date:
        # 按行号
        target_rows = [data_start_row + target_row_num - 1]
    else:
        # 按日期定位
        date_values = read_range(spreadsheet_token, sheet_id, f"A{data_start_row}:A{row_count}")
        row_offset = find_date_row(date_values, target_date, occurrence=target_row_num or 1)
        if row_offset < 0:
            # 列出已有的日期范围
            dates = []
            for row in date_values:
                if row and row[0] and isinstance(row[0], str) and re.match(r"\d{4}-\d{2}-\d{2}", row[0]):
                    dates.append(row[0])
            date_range_str = f"{dates[0]} ~ {dates[-1]}" if dates else "无日期数据"
            output["error"] = f"未找到日期 {target_date} 的数据行，已有日期范围: {date_range_str}"
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 1
        actual_row = data_start_row + row_offset
        target_rows = [actual_row]

    # ==================== Step 6: 读取数据 ====================
    results = []
    for row_num in target_rows[:50]:  # 最多50行
        # 始终读取 A 列（日期列）+ 目标列
        read_col_indices = list(set([0] + target_col_indices))  # 去重，始终包含第0列
        read_col_indices.sort()

        # 构建读取范围
        start_col = col_index_to_letter(min(read_col_indices))
        end_col_letter = col_index_to_letter(max(read_col_indices))
        cell_range = f"{start_col}{row_num}:{end_col_letter}{row_num}"

        cell_values = read_range(spreadsheet_token, sheet_id, cell_range)

        row_data = {}
        row_date = None
        if cell_values and cell_values[0]:
            # 找到日期值（A列，索引0）
            if len(cell_values[0]) > 0:
                raw_date = cell_values[0][0]
                if isinstance(raw_date, str) and re.match(r"\d{4}-\d{2}-\d{2}", raw_date):
                    row_date = raw_date

            # 填充目标列数据
            for idx, col_idx in enumerate(target_col_indices):
                col_name = target_col_names[idx] if idx < len(target_col_names) else f"列{col_index_to_letter(col_idx)}"
                # 在 cell_values 中的实际位置（因为读取范围可能包含额外的列）
                value_idx = col_idx - min(read_col_indices)
                if 0 <= value_idx < len(cell_values[0]):
                    raw_val = cell_values[0][value_idx]
                    parsed = parse_rich_text(raw_val)
                    row_data[col_name] = parsed
                else:
                    row_data[col_name] = "(空)"

        results.append({
            "row": row_num,
            "date": row_date,
            "data": row_data,
        })

    output["success"] = True
    output["data"] = results
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
