#!/usr/bin/env python3
"""
字体下载工具
下载思源黑体（Noto Sans CJK SC）用于卡片生成
"""

import urllib.request
import sys
from pathlib import Path


def download_font():
    """下载字体文件"""
    font_dir = Path(__file__).parent
    font_file = font_dir / "NotoSansCJK-Regular.ttc"

    print("=" * 60)
    print("  修仙插件 - 字体下载工具")
    print("=" * 60)

    # 检查字体是否已存在
    if font_file.exists():
        file_size = font_file.stat().st_size / (1024 * 1024)
        print(f"✅ 字体文件已存在: {font_file}")
        print(f"   文件大小: {file_size:.1f} MB")
        print("   如需重新下载，请先删除该文件")
        return True

    print("📥 开始下载 Noto Sans CJK (思源黑体)...")
    print("   文件较大（约 15-20 MB），请耐心等待...")
    print()

    # 字体下载URL（使用 GitHub 镜像）
    urls = [
        "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTC/NotoSansCJK-Regular.ttc",
        "https://cdn.jsdelivr.net/gh/googlefonts/noto-cjk/Sans/OTC/NotoSansCJK-Regular.ttc",
    ]

    for i, url in enumerate(urls, 1):
        try:
            print(f"[{i}/{len(urls)}] 尝试从源 {i} 下载...")

            # 下载字体
            def progress_callback(block_count, block_size, total_size):
                if total_size > 0:
                    percent = min(100, block_count * block_size * 100 / total_size)
                    downloaded = min(total_size, block_count * block_size) / (1024 * 1024)
                    total = total_size / (1024 * 1024)
                    print(f"\r   进度: {percent:.1f}% ({downloaded:.1f}/{total:.1f} MB)", end="")

            urllib.request.urlretrieve(url, font_file, progress_callback)
            print()  # 换行

            # 验证文件
            if font_file.exists() and font_file.stat().st_size > 1024 * 1024:  # 至少 1MB
                file_size = font_file.stat().st_size / (1024 * 1024)
                print()
                print("✅ 字体下载成功！")
                print(f"   文件路径: {font_file}")
                print(f"   文件大小: {file_size:.1f} MB")
                print()
                print("💡 字体将自动用于生成卡片图片")
                return True
            else:
                print("   文件验证失败，尝试下一个源...")
                font_file.unlink(missing_ok=True)

        except Exception as e:
            print(f"   下载失败: {e}")
            font_file.unlink(missing_ok=True)
            if i < len(urls):
                print("   尝试下一个源...")
            continue

    # 所有下载源都失败
    print()
    print("❌ 所有下载源均失败")
    print()
    print("请尝试手动下载：")
    print("1. 访问: https://github.com/googlefonts/noto-cjk/releases")
    print("2. 下载 Noto Sans CJK (NotoSansCJK-Regular.ttc)")
    print(f"3. 将文件放到: {font_dir}")
    print()
    print("或者安装系统字体：")
    print("  Ubuntu/Debian: sudo apt install fonts-noto-cjk")
    print("  CentOS/RHEL:   sudo yum install google-noto-sans-cjk-fonts")
    return False


if __name__ == "__main__":
    try:
        success = download_font()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  下载已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
