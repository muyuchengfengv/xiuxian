#!/bin/bash
# Python缓存清理脚本

echo "=================================="
echo "  Python缓存清理工具"
echo "=================================="
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "插件目录: $SCRIPT_DIR"
echo ""

echo "正在清理Python缓存..."

# 清理__pycache__目录
PYCACHE_COUNT=$(find "$SCRIPT_DIR" -type d -name "__pycache__" 2>/dev/null | wc -l)
find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo "  ✓ 已删除 $PYCACHE_COUNT 个 __pycache__ 目录"

# 清理.pyc文件
PYC_COUNT=$(find "$SCRIPT_DIR" -name "*.pyc" 2>/dev/null | wc -l)
find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null
echo "  ✓ 已删除 $PYC_COUNT 个 .pyc 文件"

echo ""
echo "✅ 缓存清理完成！"
echo ""
echo "下一步："
echo "  1. 重启AstrBot服务"
echo "  2. 测试卡片生成功能"
echo ""
