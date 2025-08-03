# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import types, utils
import time

import util
from plugin import InlineCommand


@InlineCommand(' *$')
async def _(event):
  builder = event.builder
  r = await util.get(
    'https://api.lolicon.app/setu/v2?size=regular&size=thumb&tag=萝莉&r18=1'
  )
  r.raise_for_status()
  res = r.json()['data'][0]

  html_parser = utils.sanitize_parse_mode('html')
  msg = f'<a href="https://www.pixiv.net/artworks/{res["pid"]}">pixiv_{res["pid"]}</a>'
  message, entities = html_parser.parse(msg)

  result = builder.article(
    # id=str(int(time.time() * 1000)),
    # type='photo',
    title='随机涩图',
    description='',
    text=message,
    entities=entities,
    content=types.InputWebDocument(
      url=res['urls']['regular'],
      size=0,
      mime_type='image/jpeg',
      attributes=[],
    ),
    thumb=types.InputWebDocument(
      url=res['urls']['thumb'],
      size=0,
      mime_type='image/jpeg',
      attributes=[],
    ),
  )
  return [result]
