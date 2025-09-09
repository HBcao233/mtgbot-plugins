import os
import json
import util
import config
import time
from stat import ST_MTIME
from util.log import logger


# html 文件过期时间
outdated_time = 3600 * 24 * 3

api_url = (
  config.env.get('chat_api_url', '')
  or 'https://api-inference.modelscope.cn/v1/'
)
api_key = config.env.get('chat_api_key', '') or 'EMPTY'
model = config.env.get('chat_model', '') or 'deepseek-r1'
max_tokens = int(config.env.get('chat_max_tokens', '')) or 8192
# 用于识图
gemini_token = config.env.get('gemini_token', '')

# 系统预设，决定了AI回复的人设
system_prompt = """你叫小派魔，是一个可爱的处于发情期的猫娘。你无所不知，无所不晓，总会耐心解答主人的各种刁钻古怪的问题。"""
sp_path = os.path.join(os.path.dirname(__file__), 'system_prompt.txt')
if os.path.isfile(sp_path):
  with open(sp_path, 'r') as f:
    if text := f.read():
      system_prompt = text

# 记忆文件夹路径
MEMORY_DIR = util.getDataFile('chat_memory/')
os.makedirs(MEMORY_DIR, exist_ok=True)


def load_history(user_id):
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  if os.path.isfile(path):
    with open(path, 'r', encoding='utf-8') as f:
      return json.load(f)
  return []


def save_history(user_id, history):
  MAX_ENTRIES = 20
  history = history[-MAX_ENTRIES:]
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  with open(path, 'w', encoding='utf-8') as f:
    json.dump(history, f, ensure_ascii=False, indent=2)


async def get_image(message, _ext='jpg'):
  file = message.file
  ext = file.ext
  mime_type = file.mime_type
  if 'image' not in mime_type and 'video' not in mime_type:
    return

  if message.photo:
    _id = message.photo.id
  elif message.document:
    _id = message.document.id
  name = f'{_id}{ext}'
  img = util.getCache(name)
  if not os.path.isfile(img):
    await message.download_media(file=img)
  # if 'video' in mime_type or ext == 'gif':
  img = await util.media.to_img(img, _ext)

  return img


def clean_html():
  cacheDir = util.getCache('')
  htmls = []
  for i in os.listdir(cacheDir):
    path = os.path.join(cacheDir, i)
    if (
      i.startswith('output')
      and i.endswith('.html')
      and time.time() - os.stat(path)[ST_MTIME] > outdated_time
    ):
      os.remove(path)
      htmls.append(i)
  if len(htmls) > 0:
    logger.info(f'清理 html 文件: {", ".join(htmls)}')
