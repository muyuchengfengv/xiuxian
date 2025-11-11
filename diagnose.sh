#!/bin/bash
# 生产环境诊断脚本 - 检查字体和代码更新状态

echo "========================================"
echo "  修仙插件诊断工具 (CentOS)"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "插件目录: $SCRIPT_DIR"
echo ""

echo "========== 1. 检查代码更新状态 =========="
echo ""

# 检查关键文件的修改时间
echo "关键文件修改时间："
ls -lh "$SCRIPT_DIR/core/card_generator.py" 2>/dev/null | awk '{print "  card_generator.py: " $6 " " $7 " " $8}'
ls -lh "$SCRIPT_DIR/core/image_generator.py" 2>/dev/null | awk '{print "  image_generator.py: " $6 " " $7 " " $8}'
echo ""

# 检查是否有Python缓存
echo "Python缓存检查："
PYCACHE_COUNT=$(find "$SCRIPT_DIR" -type d -name "__pycache__" 2>/dev/null | wc -l)
PYC_COUNT=$(find "$SCRIPT_DIR" -name "*.pyc" 2>/dev/null | wc -l)
if [ $PYCACHE_COUNT -gt 0 ] || [ $PYC_COUNT -gt 0 ]; then
    echo "  ⚠️  发现Python缓存: $PYCACHE_COUNT 个__pycache__目录, $PYC_COUNT 个.pyc文件"
    echo "  建议执行: bash clear_cache.sh"
else
    echo "  ✓ 无Python缓存"
fi
echo ""

# 检查card_generator.py中的关键尺寸参数
echo "检查card_generator.py中的卡片尺寸参数："
if grep -q "width, height = 1000, 700" "$SCRIPT_DIR/core/card_generator.py" 2>/dev/null; then
    echo "  ✓ 卡片尺寸已更新为 1000x700"
else
    echo "  ✗ 卡片尺寸未更新（应该是1000x700）"
fi

if grep -q "self.get_font(64)" "$SCRIPT_DIR/core/card_generator.py" 2>/dev/null; then
    echo "  ✓ 字体尺寸已更新（包含64px）"
else
    echo "  ✗ 字体尺寸未更新（应该包含64px）"
fi
echo ""

echo "========== 2. 检查字体文件 =========="
echo ""

# 检查项目字体
PROJECT_FONT="$SCRIPT_DIR/assets/fonts/NotoSansCJK-Regular.ttc"
if [ -f "$PROJECT_FONT" ]; then
    SIZE=$(du -h "$PROJECT_FONT" | cut -f1)
    echo "  ✓ 项目字体存在: $PROJECT_FONT"
    echo "    大小: $SIZE"

    # 检查权限
    PERMS=$(stat -c "%a" "$PROJECT_FONT" 2>/dev/null || stat -f "%p" "$PROJECT_FONT" 2>/dev/null)
    echo "    权限: $PERMS"

    # 检查是否可读
    if [ -r "$PROJECT_FONT" ]; then
        echo "    ✓ 文件可读"
    else
        echo "    ✗ 文件不可读，请执行: chmod 644 $PROJECT_FONT"
    fi
else
    echo "  ✗ 项目字体不存在: $PROJECT_FONT"
fi
echo ""

# 检查系统中文字体
echo "检查系统中文字体："
SYSTEM_FONTS=(
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc"
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"
)

FOUND_SYSTEM_FONT=0
for font in "${SYSTEM_FONTS[@]}"; do
    if [ -f "$font" ]; then
        echo "  ✓ 找到系统字体: $font"
        FOUND_SYSTEM_FONT=1
    fi
done

if [ $FOUND_SYSTEM_FONT -eq 0 ]; then
    echo "  ✗ 未找到系统中文字体"
    echo ""
    echo "  CentOS安装中文字体："
    echo "    sudo yum install -y google-noto-sans-cjk-fonts"
    echo "    或"
    echo "    sudo yum install -y wqy-zenhei-fonts"
fi
echo ""

echo "========== 3. 测试字体加载 =========="
echo ""

# 尝试用Python测试字体加载
python3 << 'PYTHON_EOF'
import sys
from pathlib import Path

# 添加插件目录到路径
plugin_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd()
sys.path.insert(0, str(plugin_dir))

try:
    print("导入CardGenerator...")
    from core.card_generator import CardGenerator

    print("初始化CardGenerator...")
    generator = CardGenerator()

    print("")
    print("字体加载状态：")
    print(f"  使用的字体路径: {generator.font_path_used}")

    # 检查是否加载了大字号字体
    if 64 in generator.fonts:
        print(f"  ✓ 64px字体已加载: {generator.fonts[64]}")
    else:
        print(f"  ✗ 64px字体未加载")

    if 40 in generator.fonts:
        print(f"  ✓ 40px字体已加载")
    else:
        print(f"  ✗ 40px字体未加载")

    # 检查字体是否支持中文
    if "PIL默认字体" in str(generator.font_path_used):
        print("")
        print("  ⚠️  警告：当前使用PIL默认字体，不支持中文！")
    elif generator.font_path_used:
        print("")
        print("  ✓ 字体加载成功")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

PYTHON_EOF

echo ""
echo "========== 4. AstrBot进程检查 =========="
echo ""

# 检查AstrBot是否在运行
if pgrep -f "astrbot" > /dev/null; then
    echo "  ✓ AstrBot进程正在运行"
    echo ""
    echo "  进程信息："
    ps aux | grep -i astrbot | grep -v grep | awk '{print "    PID: " $2 ", 启动时间: " $9}'
    echo ""
    echo "  如果代码已更新，需要重启AstrBot才能生效！"
else
    echo "  ✗ AstrBot进程未运行"
fi
echo ""

echo "========== 诊断建议 =========="
echo ""

# 根据检查结果给出建议
if [ $PYCACHE_COUNT -gt 0 ] || [ $PYC_COUNT -gt 0 ]; then
    echo "1. 清理Python缓存："
    echo "   bash clear_cache.sh"
    echo ""
fi

if [ ! -f "$PROJECT_FONT" ] && [ $FOUND_SYSTEM_FONT -eq 0 ]; then
    echo "2. 安装中文字体："
    echo "   sudo yum install -y google-noto-sans-cjk-fonts"
    echo ""
fi

if pgrep -f "astrbot" > /dev/null; then
    echo "3. 重启AstrBot（必须！）："
    echo "   # 根据你的启动方式重启，例如："
    echo "   sudo systemctl restart astrbot"
    echo "   # 或手动重启"
    echo ""
fi

echo "4. 测试卡片生成："
echo "   发送命令: /属性"
echo ""

echo "========================================"
echo "如果问题仍然存在，请将此诊断结果发送给开发者"
echo "========================================"
