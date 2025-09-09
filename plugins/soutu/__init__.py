# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : 搜图
""".env.example
# saucenao.com 申请的中的 api_key
saucenao_api_key =
"""

from telethon import events, utils, Button
from urllib.parse import quote
import re

import util
from plugin import Command, import_plugin
from .data_source import to_img, saucenao_search, esearch


mask = import_plugin('mask')
try:
  hosting = import_plugin('hosting')
except ModuleNotFoundError:
  hosting = None

_get_buttons = mask.DelayMedia.get_buttons


def get_buttons(self, event):
  buttons = _get_buttons(self, event)
  if all(i.photo or i.video for i in self.messages):
    mid = self.messages[0].id.to_bytes(4, 'big')
    buttons.append([Button.inline('搜图', data=b'soutu_' + mid)])
  return buttons


mask.DelayMedia.get_buttons = get_buttons


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
  await message.download_media(file=img)
  img = await to_img(img, _ext)

  return img


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
    m = await event.reply('请用命令回复一张图片')
    if not event.is_private:
      bot.schedule_delete_messages(3, event.peer_id, m.id)
    return

  if message.photo:
    _id = message.photo.id
  elif message.document:
    _id = message.document.id
  data = util.Data('urls')
  if not (url := data.get(str(_id))):
    img = await get_image(message)
    if not img:
      await event.reply('回复的文件不是图片')
      return
    url = await hosting.get_url(img)
    with data:
      data[str(_id)] = url

  safe_chars = "A-Za-z0-9-_.~!*'()"
  url = quote(url, safe=safe_chars)
  buttons = [
    [
      Button.url(
        'Google旧版',
        f'https://www.google.com/searchbyimage?client=app&image_url={url}',
      ),
      Button.url(
        'GoogleLens', f'https://lens.google.com/uploadbyurl?url={url}'
      ),
    ],
    [
      Button.url(
        'Yandex.ru', f'https://yandex.ru/images/search?url={url}&rpt=imageview'
      ),
      Button.url(
        'Yandex.com (锁区)',
        f'https://yandex.com/images/search?url={url}&rpt=imageview',
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

  await event.respond(
    '请点击以下链接手动搜图',
    buttons=buttons,
    reply_to=message.id,
  )


soutu_button_pattern = re.compile(rb'soutu_([\x00-\xff]{4,4})$').match


@bot.on(events.CallbackQuery(pattern=soutu_button_pattern))
async def soutu_button(event):
  peer = event.query.peer
  match = event.pattern_match
  mid = int.from_bytes(match.group(1), 'big')
  messages = await bot.get_messages(peer, ids=[mid])
  message = messages[0]
  if message is None:
    await event.answer('消息不存在', alert=True)
    await event.delete()
    return
  event.message = message
  event.peer_id = utils.get_peer_id(peer)
  await _soutu(event)


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
    m = await event.reply('请用命令回复一张图片')
    if not event.is_private:
      bot.schedule_delete_messages(3, event.peer_id, m.id)
    return

  img = await get_image(message)
  if not img:
    await event.reply('回复的文件不是图片')
    return
  res = await saucenao_search(img)
  if isinstance(res, str):
    msg = 'SauceNAO 搜图: ' + res
  else:
    msg = '\n\n'.join(res)

  m = await event.respond(
    msg,
    parse_mode='html',
    reply_to=message.id,
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
  if not img:
    await event.reply('回复的文件不是图片')
    return
  res = await esearch(img)
  if isinstance(res, str):
    msg = res
  else:
    msg = '\n\n'.join(res)

  await event.respond(
    msg,
    parse_mode='html',
    reply_to=message.id,
  )
