# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : 搜图
""".env.example
# saucenao.com 申请的中的 api_key
saucenao_api_key =
"""

from telethon import events, Button
from urllib.parse import quote

import util
import filters
from util.log import logger
from plugin import Command, import_plugin
from .data_source import to_img, saucenao_search, esearch

try:
  hosting = import_plugin('hosting')
except ModuleNotFoundError:
  hosting = None


@Command(
  'soutu',
  info='搜图',
)
async def _soutu(event):
  message = None
  if event.message.file:
    message = event.message
  if (
    not (message or (message := await event.message.get_reply_message()))
    or not message.file
  ):
    return await event.reply('请用命令回复一张图片')

  if message.photo:
    _id = message.photo.id
  elif message.document:
    _id = message.document.id
  data = util.Data('urls')
  if not (url := data.get(str(_id))):
    img = await get_image(message)
    url = await hosting.get_url(img)
    with data:
      data[str(_id)] = url

  safe_chars = "A-Za-z0-9-_.~!*'()"
  url = quote(url, safe=safe_chars)
  buttons = [
    [
      Button.url(
        'Google旧版', f'https://www.google.com/searchbyimage?client=app&image_url={url}'
      ),
      Button.url('GoogleLens', f'https://lens.google.com/uploadbyurl?url={url}'),
    ],
    [
      Button.url(
        'Yandex.ru', f'https://yandex.ru/images/search?url={url}&rpt=imageview'
      ),
      Button.url(
        'Yandex.com (锁区)', f'https://yandex.com/images/search?url={url}&rpt=imageview'
      ),
    ],
    [
      Button.url('SauceNAO', f'https://saucenao.com/search.php?url={url}'),
      Button.url('ascii2d', f'https://ascii2d.net/search/url/{url}'),
      Button.url('WAIT (动画)', f'https://trace.moe/?auto&url={url}'),
    ],
    [
      Button.url('IQDB', f'http://iqdb.org/?url={url}'),
      Button.url('3D-IQDB', f'http://3d.iqdb.org/?url={url}'),
      Button.url('TinEye', f'https://tineye.com/search?url={url}'),
      Button.url(
        'Bing',
        f'https://www.bing.com/images/search?q=imgurl:{url}&view=detailv2&iss=sbi',
      ),
    ],
  ]
  m = await bot.get_messages(event.peer_id, ids=[event.message.id])
  reply_to = event.message.id
  if m[0] is None:
    reply_to = message.id
  await event.respond(
    '请点击以下链接手动搜图\n或使用 /saucenao 命令搜图',
    buttons=buttons,
    reply_to=reply_to,
  )


async def get_image(message, _ext='jpg'):
  file = message.file
  ext = file.ext
  mime_type = file.mime_type
  if 'image' not in mime_type and 'video' not in mime_type:
    return await event.reply('回复的文件不是图片')

  if message.photo:
    _id = message.photo.id
  elif message.document:
    _id = message.document.id
  name = f'{_id}{ext}'
  img = util.getCache(name)
  await message.download_media(file=img)
  if 'video' in mime_type or ext == 'gif':
    img = await to_img(img, _ext)

  return img


@Command(
  'saucenao',
  info='SauceNAO 搜图',
)
async def _saucenao(event):
  message = None
  if event.message.file:
    message = event.message
  if (
    not (message or (message := await event.message.get_reply_message()))
    or not message.file
  ):
    return await event.reply('请用命令回复一张图片')

  img = await get_image(message)
  res = await saucenao_search(img)
  if isinstance(res, str):
    msg = '错误: ' + res
  else:
    msg = '\n\n'.join(res)
  
  m = await bot.get_messages(event.peer_id, ids=[event.message.id])
  reply_to = event.message.id
  if m[0] is None:
    reply_to = message.id
  await event.respond(
    msg, 
    parse_mode='html',
    reply_to=reply_to,
  )


@Command(
  'esearch',
  info='e站搜图',
)
async def _esearch(event):
  message = None
  if event.message.file:
    message = event.message
  if (
    not (message or (message := await event.message.get_reply_message()))
    or not message.file
  ):
    return await event.reply('请用命令回复一张图片')

  img = await get_image(message, 'webp')
  res = await esearch(img)
  if isinstance(res, str):
    msg = res
  else:
    msg = '\n\n'.join(res)
  await event.reply(msg, parse_mode='html')
