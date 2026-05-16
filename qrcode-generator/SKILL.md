---
name: qrcode-generator
description: |
  将链接或文本生成为二维码图片。支持中间嵌入Logo、自定义尺寸/格式/颜色。触发词包括但不限于：生成二维码、二维码、qr code、qrcode、转二维码、链接转二维码、做个二维码、生成qr。
version: 1.0.0
allowed-tools: Bash, Read, Write
---

# 二维码生成器

将链接/文本转为二维码图片，支持Logo嵌入、尺寸/格式/颜色自定义。

---

## 一、核心流程

```
用户提供链接/文本 → 解析参数 → 生成二维码 → 嵌入Logo（可选）→ 输出图片
```

### 步骤详解

1. **接收输入**：用户提供一个链接或文本
2. **确认参数**：按需确认以下参数（用户未指定则使用默认值）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Logo | `D:\词元抖动\logo\logo-小.png` | 中间嵌入的Logo图片，`--no-logo` 禁用 |
| 边长 | 8cm | 二维码边长，支持 `cm`/`px` |
| 格式 | png | 输出格式：png/jpg/bmp/svg/webp |
| 边框 | 2 | 二维码边框模块数 |
| 前景色 | #000000 | 二维码黑色部分 |
| 背景色 | #FFFFFF | 二维码白色部分 |

3. **执行生成**：调用脚本生成二维码图片
4. **输出结果**：返回图片路径

---

## 二、执行命令

### 标准命令模板

```bash
python "${SKILL_DIR}/scripts/generate_qrcode.py" "<链接或文本>" [选项]
```

### 常用场景

**场景1：默认生成（8cm PNG + 默认Logo）**
```bash
python "${SKILL_DIR}/scripts/generate_qrcode.py" "https://example.com"
```

**场景2：不嵌入Logo**
```bash
python "${SKILL_DIR}/scripts/generate_qrcode.py" "https://example.com" --no-logo
```

**场景3：自定义Logo**
```bash
python "${SKILL_DIR}/scripts/generate_qrcode.py" "https://example.com" --logo "D:\my_logo.png"
```

**场景4：指定输出路径和尺寸**
```bash
python "${SKILL_DIR}/scripts/generate_qrcode.py" "https://example.com" -o "D:\output\my_qr.png" --size 10cm
```

**场景5：SVG矢量格式**
```bash
python "${SKILL_DIR}/scripts/generate_qrcode.py" "https://example.com" --format svg
```

**场景6：完整自定义**
```bash
python "${SKILL_DIR}/scripts/generate_qrcode.py" "https://example.com" \
  -o qr.png \
  --logo logo.png \
  --size 12cm \
  --format png \
  --border 3 \
  --fg-color "#1a5276" \
  --bg-color "#FFFFFF" \
  --logo-ratio 0.3 \
  --logo-padding 10 \
  --logo-border-radius 12
```

---

## 三、完整参数说明

| 参数 | 短选项 | 默认值 | 说明 |
|------|--------|--------|------|
| `data` | — | 必填 | 要编码的链接或文本 |
| `--output` | `-o` | 自动生成 | 输出文件路径 |
| `--logo` | — | 默认Logo | Logo图片路径 |
| `--no-logo` | — | False | 不嵌入Logo |
| `--size` | — | 8cm | 二维码边长（cm/px） |
| `--format` | — | png | 输出格式：png/jpg/bmp/svg/webp |
| `--border` | — | 2 | 边框模块数 |
| `--fg-color` | — | #000000 | 前景色 |
| `--bg-color` | — | #FFFFFF | 背景色 |
| `--logo-ratio` | — | 0.25 | Logo占比（0.2=20%） |
| `--logo-padding` | — | 8 | Logo内边距(px) |
| `--logo-border-radius` | — | 0 | Logo背景圆角 |

> **注意**：`--logo` 和 `--no-logo` 互斥，不能同时使用。

---

## 四、尺寸说明

| 尺寸参数 | 含义 | 示例 |
|----------|------|------|
| `8cm` | 8厘米边长（≈945px@300DPI） | 打印用 |
| `10cm` | 10厘米边长（≈1181px@300DPI） | 大尺寸打印 |
| `600px` | 600像素边长 | 屏幕显示 |
| `8` | 等同于8cm | 简写 |

---

## 五、格式说明

| 格式 | 特点 | 适用场景 |
|------|------|----------|
| png | 无损、支持透明 | 通用、打印 |
| jpg/jpeg | 有损压缩 | 网页展示 |
| svg | 矢量、无限放大 | 印刷、大尺寸展示 |
| bmp | 无压缩 | 特殊软件需求 |
| webp | 高压缩比 | 网页优化 |

> ⚠️ **SVG格式不支持Logo嵌入**，因为SVG是矢量格式，嵌入位图Logo会导致体积膨胀且失去矢量优势。

---

## 六、注意事项

1. **Logo文件不存在**：脚本不会报错，仅跳过Logo嵌入并提示
2. **SVG + Logo**：SVG格式自动跳过Logo嵌入
3. **编码问题**：Python 3.14需设置 `$env:PYTHONIOENCODING="utf-8"`
4. **长链接**：链接过长会导致二维码密度过高，影响扫描；建议使用短链接
5. **容错等级**：嵌入Logo时自动使用H级（30%容错），无Logo时使用M级（15%容错）

---

## 七、依赖安装

```bash
pip install qrcode[pil] pillow
```

---

## 八、踩坑经验

（以下由 AI 在实际调用中自动积累，请勿手动删除）
