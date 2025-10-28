#!/usr/bin/env python3
"""
字体下载脚本
自动下载修仙插件所需的中文字体
"""

import urllib.request
import os
from pathlib import Path


def download_file(url: str, dest_path: Path, desc: str = "文件"):
    """
    下载文件

    Args:
        url: 下载地址
        dest_path: 目标路径
        desc: 文件描述
    """
    print(f"正在下载 {desc}...")
    print(f"URL: {url}")
    print(f"目标: {dest_path}")

    try:
        # 创建目录
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # 下载文件
        urllib.request.urlretrieve(url, dest_path)
        print(f"✓ {desc} 下载完成")
        return True
    except Exception as e:
        print(f"✗ {desc} 下载失败: {e}")
        return False


def main():
    """主函数"""
    # 获取字体目录
    script_dir = Path(__file__).parent
    fonts_dir = script_dir / "fonts"
    fonts_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("修仙插件字体下载工具")
    print("=" * 60)
    print()

    # 字体列表
    fonts = [
        {
            "name": "思源黑体（Source Han Sans CN）",
            "url": "https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansCN-Regular.otf",
            "filename": "SourceHanSansCN-Regular.otf"
        },
    ]

    success_count = 0
    failed_count = 0

    for font in fonts:
        dest_path = fonts_dir / font["filename"]

        # 检查文件是否已存在
        if dest_path.exists():
            print(f"○ {font['name']} 已存在，跳过下载")
            success_count += 1
            continue

        # 下载字体
        if download_file(font["url"], dest_path, font["name"]):
            success_count += 1
        else:
            failed_count += 1

        print()

    # 汇总结果
    print("=" * 60)
    print("下载完成")
    print(f"成功: {success_count} 个")
    print(f"失败: {failed_count} 个")
    print("=" * 60)
    print()

    # 如果全部成功
    if failed_count == 0:
        print("✓ 所有字体已准备就绪！")
        print()
        print("下一步：")
        print("1. 确保已安装 Pillow: pip3 install Pillow")
        print("2. 重启 AstrBot 插件")
        print("3. 使用 /属性 等命令查看图形化界面")
    else:
        print("⚠ 部分字体下载失败")
        print()
        print("备选方案：")
        print("1. 使用系统自带字体（可能中文显示效果不佳）")
        print("2. 手动下载字体文件到 fonts/ 目录")
        print("3. 参考 README.md 中的字体安装说明")

    print()


if __name__ == "__main__":
    main()
