#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
二维码生成脚本 v1.0.0

功能：
  将链接/文本生成为二维码图片，支持中间嵌入Logo。

用法：
  # 基本用法（默认8cm边长，PNG格式，嵌入默认Logo）
  python generate_qrcode.py "https://example.com"

  # 指定输出路径
  python generate_qrcode.py "https://example.com" -o my_qr.png

  # 不嵌入Logo
  python generate_qrcode.py "https://example.com" --no-logo

  # 自定义Logo
  python generate_qrcode.py "https://example.com" --logo "D:\\my_logo.png"

  # 指定边长和格式
  python generate_qrcode.py "https://example.com" --size 10cm --format svg

  # 完整参数示例
  python generate_qrcode.py "https://example.com" -o qr.png --logo logo.png --size 12cm --format png --border 2 --fg-color "#000000" --bg-color "#FFFFFF"

依赖：
  pip install qrcode[pil] pillow

踩坑经验：
  - Python 3.14 需设置 $env:PYTHONIOENCODING="utf-8" 避免 GBK 编码错误
  - Logo 图片不存在时不会报错，仅跳过 Logo 嵌入
  - SVG 格式不支持 Logo 嵌入（SVG 是矢量格式），会自动跳过
"""
from pathlib import Path
import os
import sys
import re
import argparse

# 强制 UTF-8 编码输出（兼容 Python 3.14）
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ── 默认配置 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DEFAULT_LOGO_PATH = fr"{BASE_DIR}\logo.png"
print(DEFAULT_LOGO_PATH)
DEFAULT_SIZE_CM = 8
DEFAULT_FORMAT = "png"
DEFAULT_BORDER = 2
DEFAULT_FG_COLOR = "#000000"
DEFAULT_BG_COLOR = "#FFFFFF"
SUPPORTED_FORMATS = ("png", "jpg", "jpeg", "bmp", "svg", "webp")

# 1 英寸 = 2.54 厘米；屏幕 DPI 默认 300（高清打印质量）
DPI = 300


# ── 工具函数 ──────────────────────────────────────────────

def parse_cm_to_pixels(size_str: str) -> int:
    """
    将尺寸字符串解析为像素值。
    支持格式：'8cm'、'8 cm'、'8'（默认cm）、'300px'、'300 px'。
    """
    size_str = size_str.strip()
    cm_match = re.match(r'^(\d+(?:\.\d+)?)\s*cm$', size_str, re.IGNORECASE)
    px_match = re.match(r'^(\d+(?:\.\d+)?)\s*px$', size_str, re.IGNORECASE)
    num_match = re.match(r'^(\d+(?:\.\d+)?)$', size_str)

    if cm_match:
        cm_val = float(cm_match.group(1))
        return int(cm_val / 2.54 * DPI)
    elif px_match:
        return int(float(px_match.group(1)))
    elif num_match:
        cm_val = float(num_match.group(1))
        return int(cm_val / 2.54 * DPI)
    else:
        raise ValueError(
            f"无法解析尺寸 '{size_str}'，支持格式：'8cm'、'300px'、'8'（默认cm）"
        )


def parse_color(color_str: str) -> tuple:
    """
    将颜色字符串解析为 RGB 元组。
    支持格式：'#RRGGBB'、'RRGGBB'、'rgb(R,G,B)'、
    颜色名称（如 'red'、'blue'）通过 PIL.ImageColor 解析。
    """
    color_str = color_str.strip()
    try:
        from PIL import ImageColor
        return ImageColor.getrgb(color_str)
    except ValueError:
        raise ValueError(
            f"无法解析颜色 '{color_str}'，支持格式：'#RRGGBB'、'red'、'rgb(255,0,0)'"
        )


def ensure_output_dir(output_path: str) -> None:
    """确保输出目录存在。"""
    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)


# ── 核心逻辑 ──────────────────────────────────────────────

def generate_qrcode(
    data: str,
    output: str,
    logo_path: str = None,
    no_logo: bool = False,
    size_cm: str = f"{DEFAULT_SIZE_CM}cm",
    fmt: str = DEFAULT_FORMAT,
    border: int = DEFAULT_BORDER,
    fg_color: str = DEFAULT_FG_COLOR,
    bg_color: str = DEFAULT_BG_COLOR,
    logo_ratio: float = 0.25,
    logo_padding: int = 8,
    logo_border_radius: int = 0,
) -> str:
    """
    生成二维码图片。

    Args:
        data:               要编码的链接或文本
        output:             输出文件路径
        logo_path:          Logo 图片路径，None 则使用默认路径
        no_logo:            是否禁用 Logo
        size_cm:            二维码边长（如 '8cm'、'300px'）
        fmt:                输出图片格式（png/jpg/bmp/svg/webp）
        border:             二维码边框模块数
        fg_color:           前景色
        bg_color:           背景色
        logo_ratio:         Logo 占二维码的比例（0.2 = 20%）
        logo_padding:       Logo 与背景之间的内边距像素
        logo_border_radius: Logo 圆角半径（0=直角）

    Returns:
        输出文件的绝对路径
    """
    import qrcode
    from PIL import Image

    fmt = fmt.lower().strip()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"不支持的格式 '{fmt}'，支持：{', '.join(SUPPORTED_FORMATS)}")

    # 解析颜色
    fg_rgb = parse_color(fg_color)
    bg_rgb = parse_color(bg_color)

    # ── SVG 特殊处理 ──
    if fmt == "svg":
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        import qrcode.image.svg
        svg_img = qr.make_image(
            image_factory=qrcode.image.svg.SvgImage,
            fillcolor=fg_color,
            back_color=bg_color,
        )

        # 确保输出路径以 .svg 结尾
        if not output.lower().endswith('.svg'):
            output = os.path.splitext(output)[0] + '.svg'

        ensure_output_dir(output)
        with open(output, 'wb') as f:
            svg_img.save(f)

        abs_path = os.path.abspath(output)
        print(f"✅ 二维码已生成（SVG）: {abs_path}")
        print(f"   内容: {data[:80]}{'...' if len(data) > 80 else ''}")
        print(f"   ⚠️ SVG 格式不支持嵌入 Logo")
        return abs_path

    # ── 位图格式处理 ──

    # 解析尺寸
    pixel_size = parse_cm_to_pixels(size_cm)

    # 创建 QRCode 实例
    # 如果需要嵌入 Logo，使用高容错等级
    use_logo = (not no_logo)
    effective_logo_path = None

    if use_logo:
        # 确定使用的 Logo 路径
        if logo_path:
            effective_logo_path = logo_path
        else:
            effective_logo_path = DEFAULT_LOGO_PATH

        # 检查 Logo 文件是否存在
        if not os.path.isfile(effective_logo_path):
            print(f"⚠️ Logo 文件不存在: {effective_logo_path}，将跳过 Logo 嵌入")
            effective_logo_path = None
            use_logo = False

    error_correction = qrcode.constants.ERROR_CORRECT_H if use_logo else qrcode.constants.ERROR_CORRECT_M

    qr = qrcode.QRCode(
        version=1,
        error_correction=error_correction,
        box_size=10,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fg_rgb, back_color=bg_rgb).convert('RGB')

    # ── 调整尺寸 ──
    img = img.resize((pixel_size, pixel_size), Image.LANCZOS)

    # ── 嵌入 Logo ──
    if use_logo and effective_logo_path:
        try:
            logo = Image.open(effective_logo_path).convert("RGBA")

            # 计算 Logo 尺寸
            logo_size = int(pixel_size * logo_ratio)
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

            # 创建 Logo 背景（带圆角可选）
            bg_size = logo_size + logo_padding * 2
            logo_bg = Image.new("RGBA", (bg_size, bg_size), (255, 255, 255, 240))

            if logo_border_radius > 0:
                # 圆角处理
                from PIL import ImageDraw
                mask = Image.new("L", (bg_size, bg_size), 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle(
                    [(0, 0), (bg_size - 1, bg_size - 1)],
                    radius=logo_border_radius,
                    fill=255,
                )
                rounded_bg = Image.new("RGBA", (bg_size, bg_size), (0, 0, 0, 0))
                rounded_bg.paste(logo_bg, (0, 0), mask)
                logo_bg = rounded_bg

            # 将 Logo 粘贴到背景上
            logo_bg.paste(logo, (logo_padding, logo_padding), logo)

            # 计算居中位置
            qr_center = pixel_size // 2
            bg_half = bg_size // 2
            paste_pos = (qr_center - bg_half, qr_center - bg_half)

            # 将 Logo+背景 粘贴到二维码上
            # 需要将二维码转为 RGBA 以支持透明合成
            img_rgba = img.convert("RGBA")
            img_rgba.paste(logo_bg, paste_pos, logo_bg)
            img = img_rgba.convert("RGB")

            print(f"   🖼️ 已嵌入 Logo: {effective_logo_path}")

        except Exception as e:
            print(f"⚠️ Logo 嵌入失败: {e}，将使用无 Logo 版本")

    # ── 确保输出格式正确 ──
    ext = os.path.splitext(output)[1].lower().lstrip('.')
    if not ext or ext != fmt:
        output = os.path.splitext(output)[0] + f'.{fmt}'

    # JPEG 不支持 RGBA，确保是 RGB
    if fmt in ('jpg', 'jpeg'):
        img = img.convert('RGB')

    ensure_output_dir(output)
    img.save(output, format=fmt.upper() if fmt != 'jpg' else 'JPEG', dpi=(DPI, DPI))

    abs_path = os.path.abspath(output)
    size_info = f"{size_cm}" if 'cm' in str(size_cm).lower() or not any(c in str(size_cm) for c in ['p', 'x']) else f"{pixel_size}px"
    print(f"✅ 二维码已生成: {abs_path}")
    print(f"   内容: {data[:80]}{'...' if len(data) > 80 else ''}")
    print(f"   边长: {size_info}（{pixel_size}px）")
    print(f"   格式: {fmt.upper()}")
    print(f"   边框: {border} 模块")
    print(f"   前景色: {fg_color} | 背景色: {bg_color}")
    if use_logo and effective_logo_path:
        print(f"   Logo: {effective_logo_path}")
    else:
        print(f"   Logo: 无")

    return abs_path


# ── 命令行入口 ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="二维码生成工具 — 将链接/文本转为二维码图片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认参数（8cm, PNG, 嵌入默认Logo）
  python generate_qrcode.py "https://example.com"

  # 不嵌入Logo
  python generate_qrcode.py "https://example.com" --no-logo

  # 自定义Logo和尺寸
  python generate_qrcode.py "https://example.com" --logo my_logo.png --size 10cm

  # SVG 格式
  python generate_qrcode.py "https://example.com" --format svg

  # 完整自定义
  python generate_qrcode.py "https://example.com" -o qr.png --size 12cm --border 3 --fg-color "#1a5276" --bg-color "#FFFFFF"
        """,
    )

    parser.add_argument(
        "data",
        help="要编码的链接或文本",
    )

    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出文件路径（默认：当前目录下 qrcode_<时间戳>.png）",
    )

    # Logo 相关
    logo_group = parser.add_mutually_exclusive_group()
    logo_group.add_argument(
        "--logo",
        default=None,
        help=f"Logo 图片路径（默认: {DEFAULT_LOGO_PATH}）",
    )
    logo_group.add_argument(
        "--no-logo",
        action="store_true",
        help="不嵌入 Logo",
    )

    # 尺寸与格式
    parser.add_argument(
        "--size",
        default=f"{DEFAULT_SIZE_CM}cm",
        help=f"二维码边长，支持 cm/px（默认: {DEFAULT_SIZE_CM}cm）",
    )
    parser.add_argument(
        "--format",
        default=DEFAULT_FORMAT,
        choices=SUPPORTED_FORMATS,
        help=f"输出图片格式（默认: {DEFAULT_FORMAT}）",
    )

    # 外观
    parser.add_argument(
        "--border",
        type=int,
        default=DEFAULT_BORDER,
        help=f"二维码边框模块数（默认: {DEFAULT_BORDER}）",
    )
    parser.add_argument(
        "--fg-color",
        default=DEFAULT_FG_COLOR,
        help=f"前景色（默认: {DEFAULT_FG_COLOR}）",
    )
    parser.add_argument(
        "--bg-color",
        default=DEFAULT_BG_COLOR,
        help=f"背景色（默认: {DEFAULT_BG_COLOR}）",
    )

    # Logo 高级参数
    parser.add_argument(
        "--logo-ratio",
        type=float,
        default=0.25,
        help="Logo 占二维码的比例（默认: 0.25，即25%%）",
    )
    parser.add_argument(
        "--logo-padding",
        type=int,
        default=8,
        help="Logo 内边距像素（默认: 8）",
    )
    parser.add_argument(
        "--logo-border-radius",
        type=int,
        default=0,
        help="Logo 背景圆角半径（默认: 0，即直角）",
    )

    args = parser.parse_args()

    # 如果未指定输出路径，生成默认文件名
    if args.output is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"qrcode_{timestamp}.{args.format}"

    try:
        result = generate_qrcode(
            data=args.data,
            output=args.output,
            logo_path=args.logo,
            no_logo=args.no_logo,
            size_cm=args.size,
            fmt=args.format,
            border=args.border,
            fg_color=args.fg_color,
            bg_color=args.bg_color,
            logo_ratio=args.logo_ratio,
            logo_padding=args.logo_padding,
            logo_border_radius=args.logo_border_radius,
        )
        return 0
    except ValueError as e:
        print(f"❌ 参数错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 生成失败: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
