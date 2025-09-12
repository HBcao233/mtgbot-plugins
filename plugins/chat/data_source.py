from stat import ST_MTIME
from typing import Iterable
import os
import json
import config
import time
import re

import util
from util.log import logger


# html 文件过期时间
outdated_time = 3600 * 24 * 3

api_url = (
  config.env.get('chat_api_url', '') or 'https://api-inference.modelscope.cn/v1/'
)
api_key = config.env.get('chat_api_key', '') or 'EMPTY'
model = config.env.get('chat_model', '') or 'deepseek-r1'
max_tokens = int(config.env.get('chat_max_tokens', '8192')) or 8192
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
# 会话文件夹路径
SESSION_DIR = util.getDataFile('chat_session/')
os.makedirs(SESSION_DIR, exist_ok=True)


def load_history(user_id):
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  if os.path.isfile(path):
    with open(path, 'r', encoding='utf-8') as f:
      return json.load(f)
  return []


def length(t):
  return len(re.sub('[\x00-\xff]', '', t)) + len(re.sub('[^\x00-\xff]', '', t)) / 2


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


def format_content(content):
  try:
    content = json.loads(content)
  except json.JSONDecodeError:
    return content
  c = ''
  for j in content:
    if j['type'] == 'image':
      c += '[图片]'
    else:
      c += j['text']
  return c


class Sessions(util.Data):
  def __init__(self, user_id):
    super().__init__(f'chat_session/{user_id}')
    self.user_id = user_id
    if (
      self.data.get('current_session', None) is None
      or len(self.data.get('sessions', [])) == 0
    ):
      self.data['current_session'] = 0
      self.data['sessions'] = [
        {
          'name': '新对话',
          'historys': load_history(self.user_id),
          'delete_time': 0,
        }
      ]
      self.save()

  @property
  def current_session_index(self):
    return self.data.get('current_session', 0)

  @property
  def sessions(self):
    return self.data['sessions']

  @property
  def current_session(self):
    return self.sessions[self.current_session_index]

  @property
  def current_historys(self):
    return self.current_session['historys']

  def add_history(self, history):
    if not isinstance(history, Iterable):
      history = (history,)
    self.data['sessions'][self.current_session_index]['historys'].extend(history)
    return True

  def rename_session(self, index, name):
    if len(self.sessions) <= index:
      return False
    self.data['sessions'][index]['name'] = name
    return True

  def add_session(self, name='新对话'):
    self.data['sessions'].append(
      {
        'name': name,
        'historys': [],
        'delete_time': 0,
      }
    )
    return True

  def delete_session(self, index=None):
    if index is None:
      index = self.current_session_index
    if len(self.sessions) <= index:
      return False
    if self.sessions[index]['delete_time'] > 0:
      return False
    self.data['sessions'][index]['delete_time'] = int(time.time())
    return True

  def switch_session(self, index):
    if len(self.sessions) <= index:
      return False
    self.data['current_session'] = index
    return True

  def recycle_session(self, index):
    if len(self.sessions) <= index:
      return False
    if self.sessions[index]['delete_time'] == 0:
      return False
    self.data['sessions'][index]['delete_time'] = 0
    return True