# 生产环境部署指南

## 问题现象
- 中文显示为方块
- 字体大小没有更新

## 解决步骤

### 1. 清理Python缓存（重要！）

```bash
# 进入插件目录
cd /home/AstrBot/data/plugins/xiuxian

# 清理所有Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo "✅ 缓存已清理"
```

### 2. 验证字体文件

```bash
# 检查字体文件是否存在
ls -lh /home/AstrBot/data/plugins/xiuxian/assets/fonts/NotoSansCJK-Regular.ttc

# 应该看到类似输出：
# -rw-r--r-- 1 user user 16M Nov 11 15:00 NotoSansCJK-Regular.ttc
```

如果字体文件不存在，运行下载脚本：
```bash
cd /home/AstrBot/data/plugins/xiuxian/assets/fonts
python3 download_fonts.py
```

### 3. 测试字体加载

```bash
cd /home/AstrBot/data/plugins/xiuxian

python3 << 'EOF'
from core.card_generator import CardGenerator
generator = CardGenerator()
print(f"字体状态: {generator.font_path_used}")
EOF
```

### 4. 重启AstrBot

```bash
# 方法1：使用systemd（如果配置了服务）
sudo systemctl restart astrbot

# 方法2：手动重启
# 先停止AstrBot进程，然后重新启动
```

### 5. 测试卡片生成

重启后，发送命令测试：
```
/属性
```

查看：
- 中文是否正常显示
- 字体大小是否变大（1000x700，字体64/40/36/32px）

## 如果字体还是有问题

### 方案A：安装系统字体（推荐）

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install fonts-noto-cjk

# CentOS/RHEL
sudo yum install google-noto-sans-cjk-fonts

# 安装后重启AstrBot
```

### 方案B：检查字体文件权限

```bash
# 确保字体文件可读
chmod 644 /home/AstrBot/data/plugins/xiuxian/assets/fonts/NotoSansCJK-Regular.ttc

# 检查文件完整性（应该是15-20MB）
du -h /home/AstrBot/data/plugins/xiuxian/assets/fonts/NotoSansCJK-Regular.ttc
```

### 方案C：重新下载字体

```bash
cd /home/AstrBot/data/plugins/xiuxian/assets/fonts

# 删除旧文件
rm NotoSansCJK-Regular.ttc

# 重新下载
python3 download_fonts.py
```

## 验证修复

1. **查看AstrBot日志**，应该看到：
   ```
   [FontLoader] ✅ 成功加载项目字体!
   路径: /home/AstrBot/data/plugins/xiuxian/assets/fonts/NotoSansCJK-Regular.ttc
   ```

2. **测试命令** `/属性`，卡片应该：
   - 尺寸：1000x700 像素
   - 中文正常显示
   - 字体大而清晰

## 常见错误

### 错误1：字体加载失败
```
[FontLoader] ⚠️ 警告：未找到任何中文字体！
```
**解决**：按照"方案A"安装系统字体

### 错误2：仍然显示旧样式
**原因**：Python缓存未清理
**解决**：重新执行步骤1（清理缓存）+ 步骤4（重启）

### 错误3：权限被拒绝
**原因**：字体文件权限不对
**解决**：执行步骤"方案B"

## 技术说明

本次更新修改：
- 卡片尺寸：800x600 → **1000x700**
- 角色名称：48px → **64px**
- 境界信息：32px → **40px**
- 灵根信息：28px → **36px**
- 属性数值：24px → **32px**
- 进度条：30px → **40px高度**
- 头像：100x100 → **120x120**

**重要**：必须清理Python缓存并重启AstrBot才能生效！
