from PIL import Image, ImageDraw, ImageFont, ImageFilter
from util.log import logger
import os


dirname = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(dirname, '079-上首博瀚体 Regular.ttf')


def add_glow_watermark(
  image_path: str,
  text: str,
  output_path: str,
  text_color: tuple = (255, 255, 255, 240),
  # 发光颜色
  glow_color: tuple = (0, 0, 0, 40),
  # 发光半径
  glow_radius: int = 4,
  # 发光强度(模糊次数)
  glow_intensity: int = 3,
):
  """
  给图片右下角添加带外发光效果的文字水印
  
  参数:
    image_path: 输入图片路径
    text: 水印文字内容
    output_path: 输出文件路径
    text_color: 文字颜色 (R, G, B, A)
    glow_color: 发光颜色 (R, G, B, A)
    glow_radius: 发光半径
    glow_intensity: 发光强度
  """
  
  # 1. 打开原图并转换为RGBA模式
  original = Image.open(image_path).convert('RGBA')
  width, height = original.size
  
  # 2. 计算字体大小（图片较短边的 1/20）
  font_size = min(width, height) // 30
  margin = font_size  # 边距为一个字的大小
  
  # 3. 加载字体
  font = load_font(font_path, font_size)
  
  # 4. 计算文字尺寸和位置
  # 创建临时绘图对象来测量文字
  temp_img = Image.new('RGBA', (1, 1))
  temp_draw = ImageDraw.Draw(temp_img)
  bbox = temp_draw.textbbox((0, 0), text, font=font)
  text_width = bbox[2] - bbox[0]
  text_height = bbox[3] - bbox[1]
  
  # 右下角位置（距离右边和底边各一个字的距离）
  x = width - text_width - margin
  y = height - text_height - margin
  
  # 5. 创建外发光效果图层
  glow_layer = create_glow_layer(
    size=original.size,
    text=text,
    font=font,
    position=(x, y),
    glow_color=glow_color,
    glow_radius=glow_radius,
    glow_intensity=glow_intensity
  )
  
  # 6. 创建文字图层
  text_layer = Image.new('RGBA', original.size, (0, 0, 0, 0))
  text_draw = ImageDraw.Draw(text_layer)
  text_draw.text((x, y), text, font=font, fill=text_color)
  
  # 7. 合并所有图层: 原图 -> 发光层 -> 文字层
  result = Image.alpha_composite(original, glow_layer)
  result = Image.alpha_composite(result, text_layer)
  
  save_image(result, output_path)
  return result


def load_font(font_path: str, font_size: int) -> ImageFont.FreeTypeFont:
  """加载字体文件"""
  
  if font_path and os.path.exists(font_path):
    return ImageFont.truetype(font_path, font_size)
  
  # 尝试常用字体路径
  common_fonts = [
    # Windows
    "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
    "C:/Windows/Fonts/simhei.ttf",    # 黑体
    "C:/Windows/Fonts/arial.ttf",     # Arial
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/Arial.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
  ]
  
  for font_file in common_fonts:
    if os.path.exists(font_file):
      try:
        return ImageFont.truetype(font_file, font_size)
      except Exception:
        continue
  
  # 使用默认字体
  logger.warn("⚠️ 未找到合适的字体，使用默认字体")
  return ImageFont.load_default()


def create_glow_layer(
  size: tuple,
  text: str,
  font: ImageFont.FreeTypeFont,
  position: tuple,
  glow_color: tuple,
  glow_radius: int,
  glow_intensity: int
) -> Image.Image:
  """创建外发光效果图层"""
  
  x, y = position
  
  # 创建发光基础层
  glow_layer = Image.new('RGBA', size, (0, 0, 0, 0))
  glow_draw = ImageDraw.Draw(glow_layer)
  
  # 在多个偏移位置绘制文字，形成发光基础
  for offset_x in range(-glow_radius, glow_radius + 1):
    for offset_y in range(-glow_radius, glow_radius + 1):
      # 计算到中心的距离，越远透明度越低
      distance = (offset_x ** 2 + offset_y ** 2) ** 0.5
      if distance <= glow_radius:
        glow_draw.text(
          (x + offset_x, y + offset_y),
          text,
          font=font,
          fill=glow_color
        )
  
  # 多次高斯模糊增强发光效果
  for _ in range(glow_intensity):
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=15))
  
  return glow_layer


def save_image(image: Image.Image, output_path: str):
  """保存图片，根据格式自动处理"""
  
  # 确保输出目录存在
  output_dir = os.path.dirname(output_path)
  if output_dir and not os.path.exists(output_dir):
      os.makedirs(output_dir)
  
  # 根据输出格式处理
  ext = os.path.splitext(output_path)[1].lower()
  
  if ext in ['.jpg', '.jpeg']:
    # JPEG 不支持透明通道，需要转换
    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
    rgb_image.paste(image, mask=image.split()[3] if image.mode == 'RGBA' else None)
    rgb_image.save(output_path, 'JPEG', quality=95)
  else:
    image.save(output_path)