# CentOS 生产环境配置指南

## 问题分析

如果字体显示不了中文 + 字体大小没有变化，可能的原因：

1. **代码没有真正更新到生产环境**（最可能）
2. **Python缓存导致旧代码仍在运行**
3. **字体文件问题**

---

## 快速诊断

```bash
cd /home/AstrBot/data/plugins/xiuxian
bash diagnose.sh
```

这个脚本会自动检查：
- 代码是否已更新
- Python缓存是否存在
- 字体文件是否正常
- AstrBot进程状态

---

## 完整修复步骤

### 第1步：确认代码已同步到生产环境

**检查关键文件的修改时间：**
```bash
cd /home/AstrBot/data/plugins/xiuxian
ls -lh core/card_generator.py core/image_generator.py
```

如果修改时间不是最新的（今天），说明代码没有同步！

**手动检查代码内容：**
```bash
# 检查卡片尺寸是否为1000x700
grep "width, height = 1000, 700" core/card_generator.py

# 应该输出：
# width, height = 1000, 700

# 检查是否有64px的字体
grep "get_font(64)" core/card_generator.py

# 应该输出包含：
# font_name = self.get_font(64)
```

**如果没有输出或输出不对，说明代码没更新！**

### 第2步：清理Python缓存（重要！）

```bash
cd /home/AstrBot/data/plugins/xiuxian

# 方法1：使用脚本
bash clear_cache.sh

# 方法2：手动清理
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
```

**验证缓存已清理：**
```bash
find . -name "*.pyc"
find . -type d -name "__pycache__"
# 应该没有任何输出
```

### 第3步：安装中文字体（CentOS）

我使用的是 **Noto Sans CJK** 字体。

**方案A：安装 Google Noto CJK 字体（推荐）**
```bash
sudo yum install -y google-noto-sans-cjk-fonts
```

**方案B：安装文泉驿字体**
```bash
sudo yum install -y wqy-zenhei-fonts
```

**方案C：手动安装项目字体**
```bash
cd /home/AstrBot/data/plugins/xiuxian/assets/fonts
python3 download_fonts.py

# 验证字体文件
ls -lh NotoSansCJK-Regular.ttc
# 应该显示15-20MB的文件

# 确保权限正确
chmod 644 NotoSansCJK-Regular.ttc
```

**验证字体安装：**
```bash
# 查找系统中文字体
fc-list :lang=zh | grep -i noto
# 或
fc-list :lang=zh | grep -i wqy
```

### 第4步：测试字体加载

```bash
cd /home/AstrBot/data/plugins/xiuxian

python3 << 'EOF'
from core.card_generator import CardGenerator
generator = CardGenerator()
print(f"字体路径: {generator.font_path_used}")
print(f"64px字体: {64 in generator.fonts}")
print(f"40px字体: {40 in generator.fonts}")
EOF
```

**预期输出：**
```
字体路径: /home/AstrBot/data/plugins/xiuxian/assets/fonts/NotoSansCJK-Regular.ttc
64px字体: True
40px字体: True
```

或者（如果使用系统字体）：
```
字体路径: /usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc
64px字体: True
40px字体: True
```

**如果输出包含"PIL默认字体"，说明字体加载失败！**

### 第5步：重启AstrBot（必须！）

**方法1：systemd服务**
```bash
sudo systemctl restart astrbot
sudo systemctl status astrbot
```

**方法2：手动重启**
```bash
# 找到AstrBot进程
ps aux | grep astrbot

# 杀死进程（替换<PID>为实际进程ID）
kill <PID>

# 重新启动AstrBot
# （根据你的启动方式）
```

**方法3：强制重启**
```bash
pkill -f astrbot
# 然后重新启动
```

### 第6步：测试卡片生成

发送命令：`/属性`

**检查清单：**
- [ ] 中文是否正常显示（不是方块）
- [ ] 卡片尺寸是否变大（1000x700）
- [ ] 字体是否明显变大

---

## 常见问题排查

### Q1: 代码确认已更新，但字体大小还是没变？

**可能原因：Python缓存或AstrBot没重启**

```bash
# 1. 彻底清理缓存
cd /home/AstrBot/data/plugins/xiuxian
find . -type d -name "__pycache__" -print -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -print -delete 2>/dev/null

# 2. 强制重启AstrBot
sudo systemctl restart astrbot
# 或
pkill -9 -f astrbot && sleep 2 && <你的启动命令>

# 3. 查看日志确认加载了新代码
# 应该看到 [FontLoader] 开头的调试信息
```

### Q2: 中文显示为方块？

**可能原因：字体加载失败**

```bash
# 1. 确认字体已安装
fc-list :lang=zh

# 2. 如果没有中文字体，安装：
sudo yum install -y google-noto-sans-cjk-fonts

# 3. 刷新字体缓存
fc-cache -fv

# 4. 重启AstrBot
sudo systemctl restart astrbot
```

### Q3: 诊断脚本显示"字体加载成功"，但卡片还是有问题？

**可能原因：AstrBot使用的是旧进程**

```bash
# 1. 查看AstrBot进程启动时间
ps aux | grep astrbot

# 2. 如果启动时间早于你重启的时间，说明重启失败
#    强制杀死并重启：
pkill -9 -f astrbot

# 3. 确认进程已结束
ps aux | grep astrbot

# 4. 重新启动AstrBot
```

### Q4: 如何确认代码确实更新了？

```bash
cd /home/AstrBot/data/plugins/xiuxian

# 检查关键代码片段
echo "=== 检查卡片尺寸 ==="
grep -n "width, height" core/card_generator.py | grep 1000

echo "=== 检查字体大小 ==="
grep -n "get_font(64)" core/card_generator.py

echo "=== 检查文件修改时间 ==="
stat core/card_generator.py | grep Modify
```

---

## 字体信息

我在代码中使用的字体（按优先级）：

1. **项目字体**（优先级最高）
   - `assets/fonts/NotoSansCJK-Regular.ttc`

2. **CentOS系统字体**
   - `/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc`（google-noto-sans-cjk-fonts包）
   - `/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc`（wqy-zenhei-fonts包）

3. **字体尺寸**
   - 支持 12px 到 80px
   - 卡片中使用：64px（名称）、40px（境界）、36px（灵根）、32px（属性）

---

## 最终验证清单

在执行完所有步骤后，确认：

```bash
cd /home/AstrBot/data/plugins/xiuxian

# ✓ 代码已更新
grep "1000, 700" core/card_generator.py

# ✓ 无Python缓存
find . -name "*.pyc" | wc -l  # 应该输出 0

# ✓ 字体已安装
fc-list :lang=zh | wc -l  # 应该 > 0

# ✓ 字体加载成功
python3 -c "from core.card_generator import CardGenerator; g=CardGenerator(); print(g.font_path_used)"

# ✓ AstrBot已重启
ps aux | grep astrbot | grep -v grep
```

---

## 仍然有问题？

如果按照以上步骤操作后仍然有问题，请执行诊断脚本并发送输出：

```bash
cd /home/AstrBot/data/plugins/xiuxian
bash diagnose.sh > diagnostic_output.txt 2>&1
cat diagnostic_output.txt
```

将输出结果发送给开发者进行进一步分析。
