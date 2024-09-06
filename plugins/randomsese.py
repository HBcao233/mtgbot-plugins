# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import types
import time

import util
from plugin import InlineCommand


url = 'https://api.lolicon.app/setu/v2?size=regular&size=thumb&tag=萝莉&r18=1'


@InlineCommand(' *$')
async def _(event):
  r = await util.get(url)
  r.raise_for_status()
  res = r.json()['data'][0]
  res = types.InputBotInlineResult(
    id=str(time.time()),
    type='photo',
    thumb=types.InputWebDocument(
      url=res['urls']['thumb'],
      size=0,
      mime_type='image/jpeg',
      attributes=[],
    ),
    content=types.InputWebDocument(
      url=res['urls']['regular'],
      size=0,
      mime_type='image/jpeg',
      attributes=[],
    ),
    send_message=types.InputBotInlineMessageMediaAuto(
      message=str(res['pid']),
    ),
    title='随机涩图',
    description='',
  )
  return [res]
