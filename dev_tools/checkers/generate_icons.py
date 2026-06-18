#!/usr/bin/env python3
"""
衡势价值 Logo 图标生成器
========================
基于 master SVG 生成多尺寸 PNG + favicon.ico + 浅色背景版本
输出到 src-tauri/icons/ 目录

要求：rsvg-convert (brew install librsvg), Pillow
"""
import subprocess
import sys
from pathlib import Path
from PIL import Image

# 路径
PROJECT = Path(__file__).resolve().parents[2]
LOGO_SVG = PROJECT / "reference" / "logo" / "hengshi-value-logo.svg"
LOGO_LIGHT_SVG = PROJECT / "reference" / "logo" / "hengshi-value-logo-light.svg"
OUTPUT_DIR = PROJECT / "src-tauri" / "icons"
PUBLIC_DIR = PROJECT / "public"
WEB_LOGO_DIR = PROJECT / "src" / "assets"

# macOS ICNS 多尺寸
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]
# ICO 多尺寸
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
# PNG 多尺寸
PNG_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def check_rsvg():
    """检查 rsvg-convert 是否可用"""
    try:
        subprocess.run(["rsvg-convert", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def svg_to_png(svg_path: Path, size: int, out_path: Path):
    """用 rsvg-convert 把 SVG 转成指定尺寸的 PNG"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "rsvg-convert",
        "-w", str(size),
        "-h", str(size),
        "-f", "png",
        str(svg_path),
        "-o", str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def make_ico(svg_path: Path, sizes: list, out_path: Path):
    """从 SVG 创建一个多尺寸的 .ico 文件"""
    images = []
    for s in sizes:
        png = svg_to_png(svg_path, s, out_path.parent / f"_tmp_{s}.png")
        img = Image.open(png).convert("RGBA")
        images.append(img)
    images[0].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    # 清理临时
    for s in sizes:
        (out_path.parent / f"_tmp_{s}.png").unlink()
    return out_path


def make_icns(svg_path: Path, sizes: list, out_path: Path):
    """用 macOS iconutil 把 PNG 打包成 .icns"""
    # macOS iconutil 需要标准文件名
    iconset_name = "icon.iconset"
    iconset = out_path.parent / iconset_name
    iconset.mkdir(exist_ok=True)

    # 先生成所有 PNG
    for s in sizes:
        svg_to_png(svg_path, s, iconset / f"icon_{s}x{s}.png")

    # macOS ICNS 标准命名（实际打包只需要基础尺寸）
    name_map = {
        16: "icon_16x16.png",
        32: "icon_32x32.png",
        64: "icon_32x32@2x.png",      # 64 = 32@2x
        128: "icon_128x128.png",
        256: "icon_128x128@2x.png",   # 256 = 128@2x
        512: "icon_256x256.png",      # 占位
        1024: "icon_512x512.png",     # 占位
    }
    # 重建 iconset 目录结构
    import shutil
    shutil.rmtree(iconset)
    iconset.mkdir()
    # iconutil 期望的命名: icon_16x16.png, icon_32x32.png, icon_32x32@2x.png,
    # icon_128x128.png, icon_128x128@2x.png, icon_256x256.png, icon_256x256@2x.png, icon_512x512.png, icon_512x512@2x.png
    # 16
    if 16 in sizes:
        shutil.copy(out_path.parent / f"16x16.png", iconset / "icon_16x16.png")
    # 32
    if 32 in sizes:
        shutil.copy(out_path.parent / f"32x32.png", iconset / "icon_32x32.png")
    # 64 (32@2x)
    if 64 in sizes:
        shutil.copy(out_path.parent / f"64x64.png", iconset / "icon_32x32@2x.png")
    # 128
    if 128 in sizes:
        shutil.copy(out_path.parent / f"128x128.png", iconset / "icon_128x128.png")
    # 256 (128@2x + 256)
    if 256 in sizes:
        shutil.copy(out_path.parent / f"256x256.png", iconset / "icon_128x128@2x.png")
        shutil.copy(out_path.parent / f"256x256.png", iconset / "icon_256x256.png")
    # 512 (256@2x + 512)
    if 512 in sizes:
        shutil.copy(out_path.parent / f"512x512.png", iconset / "icon_256x256@2x.png")
        shutil.copy(out_path.parent / f"512x512.png", iconset / "icon_512x512.png")
    # 1024 (512@2x)
    if 1024 in sizes:
        shutil.copy(out_path.parent / f"1024x1024.png", iconset / "icon_512x512@2x.png")

    # iconutil 必须用绝对路径，且工作目录不能是 iconset 自身
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset.absolute()), "-o", str(out_path.absolute())],
        check=True,
    )
    # 清理
    shutil.rmtree(iconset)
    return out_path


def main():
    if not LOGO_SVG.exists():
        print(f"[ERR] 找不到 SVG: {LOGO_SVG}")
        sys.exit(1)

    if not check_rsvg():
        print("[ERR] rsvg-convert 不可用，请安装: brew install librsvg")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    WEB_LOGO_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 开始生成图标（master: {LOGO_SVG.name}）")

    # 1. Tauri 标准图标（深色背景）
    print("\n[1/5] Tauri 标准 PNG (深色)")
    for s in PNG_SIZES:
        out = OUTPUT_DIR / f"{s}x{s}.png"
        svg_to_png(LOGO_SVG, s, out)
        print(f"  ✓ {out.relative_to(PROJECT)}")

    # 2. Tauri 128x128@2x.png
    print("\n[2/5] Tauri @2x 特殊尺寸")
    svg_to_png(LOGO_SVG, 256, OUTPUT_DIR / "128x128@2x.png")
    print(f"  ✓ 128x128@2x.png")

    # 3. Tauri .icns (macOS)
    print("\n[3/5] macOS .icns")
    make_icns(LOGO_SVG, ICNS_SIZES, OUTPUT_DIR / "icon.icns")
    print(f"  ✓ icon.icns")

    # 4. favicon.ico (Web) - 深色版本
    print("\n[4/5] Web favicon.ico")
    make_ico(LOGO_SVG, ICO_SIZES, PUBLIC_DIR / "favicon.ico")
    print(f"  ✓ public/favicon.ico")

    # 5. 前端 logo 资源
    print("\n[5/5] 前端 logo 资源")
    for s in [64, 128, 256]:
        svg_to_png(LOGO_SVG, s, WEB_LOGO_DIR / f"logo-{s}.png")
    svg_to_png(LOGO_SVG, 256, WEB_LOGO_DIR / "logo.png")
    print(f"  ✓ src/assets/logo-{{64,128,256}}.png")
    print(f"  ✓ src/assets/logo.png")

    # 6. 浅色背景版本（如果有）
    if LOGO_LIGHT_SVG.exists():
        print("\n[BONUS] 浅色背景版本")
        for s in [128, 256]:
            svg_to_png(LOGO_LIGHT_SVG, s, WEB_LOGO_DIR / f"logo-light-{s}.png")
        print(f"  ✓ 浅色版本已生成")

    # 7. 旧的 Tauri 占位图清理（保留以防回退）
    print("\n[INFO] 完成。检查 Tauri 配置需要的标准文件:")
    required = ["32x32.png", "128x128.png", "128x128@2x.png", "icon.icns", "icon.ico"]
    for r in required:
        path = OUTPUT_DIR / r
        status = "✓" if path.exists() else "✗"
        print(f"  {status} {r}")

    # 检查是否需要 icon.ico
    if not (OUTPUT_DIR / "icon.ico").exists():
        print("\n[EXTRA] 生成 Tauri icon.ico")
        make_ico(LOGO_SVG, ICO_SIZES, OUTPUT_DIR / "icon.ico")
        print(f"  ✓ icon.ico")


if __name__ == "__main__":
    main()
