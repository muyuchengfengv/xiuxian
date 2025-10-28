# 修仙插件图形化资源说明

## 目录结构

```
assets/
├── fonts/              # 字体文件目录
├── images/             # 图片素材目录
├── output/             # 生成图片输出目录
└── README.md          # 本文件
```

## 字体资源

### 推荐字体

为了获得最佳的中文显示效果，建议下载并放置以下字体到 `fonts/` 目录：

1. **思源黑体（Source Han Sans）**
   - 文件名：`SourceHanSansCN-Regular.otf`
   - 下载地址：https://github.com/adobe-fonts/source-han-sans/releases
   - 说明：Adobe 开源中文字体，显示效果极佳

2. **Noto Sans CJK**
   - 文件名：`NotoSansCJK-Regular.ttc`
   - 下载地址：https://github.com/notofonts/noto-cjk/releases
   - 说明：Google 开源中文字体

### 系统字体

如果未手动下载字体，系统会自动尝试使用以下系统自带字体：

- **Linux**: `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
- **macOS**: `/System/Library/Fonts/PingFang.ttc`
- **Windows**: `C:\Windows\Fonts\msyh.ttc` (微软雅黑)

### 字体安装步骤

#### 方式一：自动下载脚本（推荐）

```bash
cd /home/astrbot/astrbot_plugin_xiuxian/assets
python3 download_fonts.py
```

#### 方式二：手动下载

1. 下载思源黑体：
   ```bash
   cd fonts
   wget https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansCN-Regular.otf
   ```

2. 或者从系统复制（Linux）：
   ```bash
   # Ubuntu/Debian
   sudo apt-get install fonts-noto-cjk
   cp /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc fonts/
   ```

## 图片素材

### 背景图片

可以在 `images/` 目录下放置以下素材：

- `background_main.png` - 主背景图
- `background_card.png` - 卡片背景图
- `realm_icons/` - 境界图标目录
- `element_icons/` - 五行元素图标目录

### 素材要求

- 格式：PNG（支持透明通道）
- 尺寸：建议 1024x1024 以下
- 风格：古风、修仙主题

## 输出目录

`output/` 目录用于存储生成的图片卡片，文件命名格式：

- `player_card_{user_id}_{timestamp}.png` - 角色卡片
- `cultivation_card_{user_id}_{timestamp}.png` - 修炼卡片
- `equipment_card_{user_id}_{timestamp}.png` - 装备卡片
- `combat_card_{user_id}_{timestamp}.png` - 战斗卡片

## 依赖安装

确保已安装 Pillow 库：

```bash
pip3 install Pillow
```

## 故障排除

### 中文显示为方框

**原因**：缺少中文字体

**解决方案**：
1. 按照上述步骤下载字体文件
2. 确保字体文件路径正确
3. 重启插件

### 图片生成失败

**原因**：权限不足或目录不存在

**解决方案**：
```bash
# 确保目录存在并有写权限
mkdir -p /home/astrbot/astrbot_plugin_xiuxian/assets/{fonts,images,output}
chmod 755 /home/astrbot/astrbot_plugin_xiuxian/assets/{fonts,images,output}
```

### 内存占用过高

**原因**：生成的图片过多未清理

**解决方案**：
```bash
# 定期清理输出目录
find /home/astrbot/astrbot_plugin_xiuxian/assets/output -name "*.png" -mtime +7 -delete
```

## 性能优化

1. **图片缓存**：对于相同数据，可以缓存生成的图片
2. **异步生成**：使用异步方式生成图片，避免阻塞
3. **定期清理**：设置定时任务清理过期图片

## 自定义样式

可以通过修改 `image_generator.py` 中的 `colors` 字典来自定义颜色方案：

```python
self.colors = {
    'bg_main': (26, 32, 44),      # 主背景色
    'text_accent': (255, 215, 0),  # 强调文字（金色）
    # ... 更多颜色
}
```

## 扩展开发

### 添加新卡片类型

1. 在 `card_generator.py` 中添加新方法
2. 定义卡片数据格式
3. 实现卡片绘制逻辑
4. 在命令处理器中调用

示例：

```python
def generate_custom_card(self, data: Dict[str, Any]) -> Image.Image:
    """生成自定义卡片"""
    width, height = 500, 300
    image = Image.new('RGB', (width, height), self.colors['bg_main'])
    draw = ImageDraw.Draw(image)
    # ... 绘制逻辑
    return image
```

## 许可证

- 图片生成代码：MIT License
- 思源黑体：SIL Open Font License 1.1
- Noto Sans CJK：SIL Open Font License 1.1
