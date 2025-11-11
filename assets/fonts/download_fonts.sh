#!/bin/bash
# 字体下载脚本
# 下载思源黑体（Noto Sans CJK SC）用于卡片生成

FONT_DIR="$(cd "$(dirname "$0")" && pwd)"
FONT_FILE="$FONT_DIR/NotoSansCJK-Regular.ttc"

echo "================================================"
echo "  修仙插件 - 字体下载工具"
echo "================================================"

# 检查字体是否已存在
if [ -f "$FONT_FILE" ]; then
    echo "✅ 字体文件已存在: $FONT_FILE"
    echo "   如需重新下载，请先删除该文件"
    exit 0
fi

echo "📥 开始下载 Noto Sans CJK (思源黑体)..."
echo "   这可能需要几分钟，请耐心等待..."

# 下载字体（使用 GitHub Release）
DOWNLOAD_URL="https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTC/NotoSansCJK-Regular.ttc"

# 尝试使用 wget
if command -v wget &> /dev/null; then
    echo "   使用 wget 下载..."
    wget -O "$FONT_FILE" "$DOWNLOAD_URL"
# 尝试使用 curl
elif command -v curl &> /dev/null; then
    echo "   使用 curl 下载..."
    curl -L -o "$FONT_FILE" "$DOWNLOAD_URL"
else
    echo "❌ 错误：未找到 wget 或 curl 命令"
    echo "   请安装其中一个："
    echo "   Ubuntu/Debian: sudo apt install wget"
    echo "   CentOS/RHEL:   sudo yum install wget"
    exit 1
fi

# 检查下载是否成功
if [ -f "$FONT_FILE" ]; then
    FILE_SIZE=$(du -h "$FONT_FILE" | cut -f1)
    echo ""
    echo "✅ 字体下载成功！"
    echo "   文件路径: $FONT_FILE"
    echo "   文件大小: $FILE_SIZE"
    echo ""
    echo "💡 字体将自动用于生成卡片图片"
else
    echo ""
    echo "❌ 字体下载失败"
    echo ""
    echo "请尝试手动下载："
    echo "1. 访问: https://github.com/googlefonts/noto-cjk/releases"
    echo "2. 下载 NotoSansCJK-Regular.ttc"
    echo "3. 将文件放到: $FONT_DIR"
    exit 1
fi
