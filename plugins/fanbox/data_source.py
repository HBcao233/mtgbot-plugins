import traceback
import re
import json

import util
from util import logger

try:
  import curl_cffi
except ImportError:
  curl_cffi = None
  logger.warn('Plugin fanbox requires the curl_cffi pip-library')

class PluginException(Exception):
  pass


async def get_post(pid, creatorId):
  try:
    headers = {
      'origin': 'https://www.fanbox.cc',
      'referer': f'https://{creatorId}.fanbox.cc/',
      'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
    }
    url = f'https://api.fanbox.cc/post.info?postId={pid}'
    async with curl_cffi.requests.AsyncSession(
      headers=headers, 
      impersonate='chrome116',
    ) as session:
      session.cookies.set('p_ab_id', '0')
      r = await session.get(url)
  except Exception:
    logger.exception('[fanbox] 连接错误')
    raise PluginException('连接错误')
  try:
    res = r.json()
  except json.JSONDecodeError:
    logger.info(f'[fanbox] 解析失败: {r.text}')
    raise PluginException('解析失败') 
  
  if res.get('error', None):
    logger.error(r.text)
    raise PluginException(res['error'])
  return res['body']


def parse_msg(res, hide=False):
  pid = res['id']
  title = res['title']
  creatorId = res['creatorId']
  # uid = res['user']['userId']
  username = res['user']['name']
  msg = f'<a href="https://{creatorId}.fanbox.cc/posts/{pid}">{title}</a> - <a href="https://{creatorId}.fanbox.cc">{username}</a>'

  body = res.get('body', None) if res.get('body', None) else {}
  if hide:
    return msg
  text = (
    body.get('text', '')
    .replace('<br />', '\n')
    .replace('<br/>', '\n')
    .replace('<br>', '\n')
    .replace(' target="_blank"', '')
  )
  if not text and body.get('blocks', []):
    length = 0
    texts = [i['text'] for i in body['blocks'] if i['type'] == 'p']
    index = 0
    while index < len(texts) and (new_length := length + len(texts[index])) < 400:
      index += 1
      length = new_length
    text = '\n'.join(texts[:index])
    if index < len(texts) - 1:
      text += '\n......'
  text = re.sub(r'<span[^>]*>(((?!</span>).)*)</span>', r'\1', text)
  if text:
    msg += ': \n' + text
  return msg


def parse_medias(res):
  medias = []
  body = res.get('body', {}) 
  for i in body.get('images', []) + list(body.get('imageMap', {}).values()):
    media = {
      'type': 'image',
      'ext': i['extension'],
      'name': i['id'],
      'url': i['originalUrl'],
      'thumbnail': i['thumbnailUrl'],
    }
    medias.append(media)
  return medias
