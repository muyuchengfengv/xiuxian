# 字体安装说明

卡片生成功能需要中文字体才能正常显示文字。如果生产环境没有中文字体，请按照以下步骤安装。

## 方法一：使用自动下载脚本（推荐）

### Python 脚本
```bash
cd astrbot_plugin_xiuxian/assets/fonts
python3 download_fonts.py
```

### Bash 脚本
```bash
cd astrbot_plugin_xiuxian/assets/fonts
bash download_fonts.sh
```

脚本会自动下载 **Noto Sans CJK**（思源黑体）字体到当前目录。

---

## 方法二：手动下载字体

1. 访问 [Noto CJK 字体下载页面](https://github.com/googlefonts/noto-cjk/releases)

2. 下载 **NotoSansCJK-Regular.ttc** 文件（约 15-20 MB）

3. 将文件放到：
   ```
   astrbot_plugin_xiuxian/assets/fonts/NotoSansCJK-Regular.ttc
   ```

---

## 方法三：安装系统字体

如果有 root 权限，可以直接安装系统字体：

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install fonts-noto-cjk
```

### CentOS / RHEL
```bash
sudo yum install google-noto-sans-cjk-fonts
```

### Arch Linux
```bash
sudo pacman -S noto-fonts-cjk
```

---

## 验证字体安装

运行以下命令检查字体是否正常加载：

```bash
python3 -c "
from astrbot_plugin_xiuxian.core.card_generator import CardGenerator
generator = CardGenerator()
print('字体状态：', generator.font_path_used)
"
```

如果显示字体路径（而不是 "default"），说明字体安装成功。

---

## 故障排除

### 问题 1：卡片中文显示为方块或乱码
**原因**：没有安装中文字体

**解决**：按照上述方法安装字体

### 问题 2：字体下载失败
**原因**：网络问题或 GitHub 访问受限

**解决**：
1. 使用代理或VPN
2. 从其他源下载（如 jsDelivr CDN）
3. 使用方法三安装系统字体

### 问题 3：仍然显示警告
**原因**：字体文件路径不正确

**解决**：确保字体文件名为 `NotoSansCJK-Regular.ttc` 并放在正确位置

---

## 字体信息

**使用字体**：Noto Sans CJK (思源黑体)

**许可协议**：SIL Open Font License 1.1

**字体特点**：
- 开源免费
- 完整支持中日韩文字
- 优秀的显示效果
- 广泛使用

**字体来源**：Google Fonts & Adobe

**GitHub**：https://github.com/googlefonts/noto-cjk
