# 图形化界面集成指南

## 概述

本指南说明如何将图片卡片生成功能集成到现有的修仙插件命令中。

## 环境准备

### 1. 安装依赖

```bash
pip3 install Pillow
```

### 2. 下载字体

```bash
cd /home/astrbot/astrbot_plugin_xiuxian/assets
python3 download_fonts.py
```

## 集成步骤

### 1. 在插件初始化中添加卡片生成器

在 `main.py` 的 `__init__` 方法中添加：

```python
from .core.card_generator import CardGenerator

class XiuxianPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # ... 现有代码 ...

        # 初始化卡片生成器
        self.card_generator = None  # 懒加载
```

在 `_ensure_initialized` 方法中添加：

```python
async def _ensure_initialized(self):
    # ... 现有代码 ...

    # 初始化卡片生成器
    logger.info("🎨 正在初始化图片生成器...")
    self.card_generator = CardGenerator()
    logger.info("✓ 图片生成器初始化完成")
```

### 2. 修改命令以支持图片输出

#### 示例1：角色属性命令 (`/属性`)

修改 `show_status` 方法：

```python
@filter.command("属性", alias={"角色信息", "信息"})
async def show_status(self, event: AstrMessageEvent):
    """查看角色属性"""
    user_id = event.get_sender_id()

    try:
        # 确保插件已初始化
        if not await self._ensure_initialized():
            yield event.plain_result("❌ 修仙世界初始化失败")
            return

        # 获取玩家信息
        player = await self.player_mgr.get_player_or_error(user_id)

        # 准备卡片数据
        player_data = {
            'name': player.name,
            'realm': player.realm,
            'realm_level': player.realm_level,
            'cultivation': player.cultivation,
            'max_cultivation': player.cultivation_required,
            'hp': player.hp,
            'max_hp': player.max_hp,
            'mp': player.mp,
            'max_mp': player.max_mp,
            'attack': player.attack,
            'defense': player.defense,
            'spirit_root': player.spirit_root,
            'spirit_root_quality': player.spirit_root_quality,
        }

        # 生成卡片
        card_image = self.card_generator.generate_player_card(player_data)

        # 保存图片
        import time
        filename = f"player_card_{user_id}_{int(time.time())}.png"
        filepath = self.card_generator.save_image(card_image, filename)

        # 发送图片（使用 AstrBot 的图片发送API）
        yield event.image_result(str(filepath))

    except PlayerNotFoundError as e:
        yield event.plain_result(str(e))
    except Exception as e:
        logger.error(f"查看属性失败: {e}", exc_info=True)
        yield event.plain_result(f"查看属性失败：{str(e)}")
```

#### 示例2：修炼命令 (`/修炼`)

修改 `cultivate_cmd` 方法：

```python
@filter.command("修炼", alias={"打坐"})
async def cultivate_cmd(self, event: AstrMessageEvent):
    """进行修炼"""
    user_id = event.get_sender_id()

    try:
        if not self._check_initialized():
            yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
            return

        # 执行修炼
        result = await self.cultivation_sys.cultivate(user_id)

        # 准备卡片数据
        cultivation_data = {
            'player_name': result.get('player_name', ''),
            'cultivation_gained': result['cultivation_gained'],
            'total_cultivation': result['total_cultivation'],
            'can_breakthrough': result['can_breakthrough'],
            'next_realm': result.get('next_realm', ''),
            'required_cultivation': result.get('required_cultivation', 0),
            'sect_bonus_rate': result.get('sect_bonus_rate', 0),
        }

        # 生成卡片
        card_image = self.card_generator.generate_cultivation_card(cultivation_data)

        # 保存图片
        import time
        filename = f"cultivation_card_{user_id}_{int(time.time())}.png"
        filepath = self.card_generator.save_image(card_image, filename)

        # 发送图片
        yield event.image_result(str(filepath))

    except Exception as e:
        logger.error(f"修炼失败: {e}", exc_info=True)
        yield event.plain_result(f"修炼失败：{str(e)}")
```

#### 示例3：装备展示命令 (`/装备详情`)

添加新命令：

```python
@filter.command("装备详情", alias={"查看装备"})
async def equipment_detail_cmd(self, event: AstrMessageEvent):
    """查看装备详情（图形化）"""
    user_id = event.get_sender_id()
    message_text = self._get_message_text(event)

    try:
        if not self._check_initialized():
            yield event.plain_result("⚠️ 修仙世界正在初始化，请稍后再试...")
            return

        # 解析装备编号
        parts = message_text.split()
        if len(parts) < 2:
            yield event.plain_result("⚠️ 请指定装备编号\n💡 使用方法：/装备详情 [编号]")
            return

        equipment_index = int(parts[1])

        # 获取装备列表
        equipment_list = await self.equipment_sys.get_player_equipment(user_id)

        if equipment_index < 1 or equipment_index > len(equipment_list):
            yield event.plain_result(f"❌ 装备编号 {equipment_index} 不存在！")
            return

        equipment = equipment_list[equipment_index - 1]

        # 准备卡片数据
        equipment_data = {
            'name': equipment.name,
            'type': equipment.equipment_type,
            'quality': equipment.quality,
            'level': equipment.level,
            'enhance_level': equipment.enhance_level,
            'attributes': {
                'attack': equipment.attack,
                'defense': equipment.defense,
                'hp_bonus': equipment.hp_bonus,
                'mp_bonus': equipment.mp_bonus,
            }
        }

        # 生成卡片
        card_image = self.card_generator.generate_equipment_card(equipment_data)

        # 保存图片
        import time
        filename = f"equipment_card_{user_id}_{int(time.time())}.png"
        filepath = self.card_generator.save_image(card_image, filename)

        # 发送图片
        yield event.image_result(str(filepath))

    except Exception as e:
        logger.error(f"查看装备详情失败: {e}", exc_info=True)
        yield event.plain_result(f"查看装备详情失败：{str(e)}")
```

## AstrBot 图片发送API

### 方法1：使用 `event.image_result()`

```python
# 发送本地图片文件
yield event.image_result("/path/to/image.png")

# 发送图片URL
yield event.image_result("https://example.com/image.png")
```

### 方法2：使用 `MessageChain`（如果平台支持）

```python
from astrbot.api.message import MessageChain, Image

# 创建消息链
chain = MessageChain([
    Image(file=str(filepath))  # 本地文件路径
])

yield event.chain_result(chain)
```

### 方法3：使用 Base64 编码

```python
import base64

# 将图片转换为 base64
image_bytes = self.card_generator.image_to_bytes(card_image)
image_base64 = base64.b64encode(image_bytes).decode('utf-8')

# 发送（具体格式取决于平台）
yield event.image_result(f"base64://{image_base64}")
```

## 配置选项

### 启用/禁用图形化

可以添加配置项让用户选择是否使用图形化界面：

```python
# 在 __init__ 中
self.enable_graphics = True  # 从配置文件读取

# 在命令中
if self.enable_graphics:
    # 发送图片
    yield event.image_result(str(filepath))
else:
    # 发送文本
    yield event.plain_result(text_result)
```

## 性能优化

### 1. 图片缓存

```python
import hashlib

def get_cache_key(data: dict) -> str:
    """生成缓存键"""
    data_str = str(sorted(data.items()))
    return hashlib.md5(data_str.encode()).hexdigest()

# 使用缓存
cache_key = get_cache_key(player_data)
cached_file = self.output_dir / f"cache_{cache_key}.png"

if cached_file.exists():
    yield event.image_result(str(cached_file))
else:
    # 生成新图片
    card_image = self.card_generator.generate_player_card(player_data)
    filepath = self.card_generator.save_image(card_image, f"cache_{cache_key}.png")
    yield event.image_result(str(filepath))
```

### 2. 异步生成

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 创建线程池
executor = ThreadPoolExecutor(max_workers=4)

# 异步生成图片
loop = asyncio.get_event_loop()
card_image = await loop.run_in_executor(
    executor,
    self.card_generator.generate_player_card,
    player_data
)
```

### 3. 定期清理

```python
import time
from pathlib import Path

def cleanup_old_images(output_dir: Path, max_age_hours: int = 24):
    """清理旧图片"""
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    for file in output_dir.glob("*.png"):
        if file.stat().st_mtime < current_time - max_age_seconds:
            file.unlink()
```

## 故障排除

### 问题1：图片不显示

**可能原因**：
- 平台不支持本地文件路径
- 文件权限问题

**解决方案**：
- 使用绝对路径
- 使用 base64 编码
- 检查文件权限

### 问题2：中文显示为方框

**解决方案**：
- 确保已下载中文字体
- 检查字体文件路径
- 参考 `assets/README.md`

### 问题3：生成速度慢

**解决方案**：
- 使用图片缓存
- 使用异步生成
- 降低图片分辨率

## 下一步

1. ✅ 测试图片生成功能
2. ✅ 集成到常用命令
3. ⏳ 添加更多卡片类型
4. ⏳ 优化性能和缓存
5. ⏳ 添加自定义主题

## 参考资料

- [Pillow 文档](https://pillow.readthedocs.io/)
- [AstrBot 文档](https://docs.astrbot.app/)
- [修仙插件需求文档](./修仙插件需求文档.md)
