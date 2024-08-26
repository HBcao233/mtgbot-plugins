# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, types
import re
import random

from util import logger
from plugin import handler, InlineCommand


_p = r'[ \[\(\{]*(-?\d{1,3})? *(?:[\/~d,:-]|to)*? *(-?\d{1,3})?[ \]\)\}]*$'
_pattern = re.compile((r'/?roll(?:@%s)?' % bot.me.username) + _p).match
_query_pattern = re.compile(_p).match
@handler('roll', info='生成随机数 /roll [min=0] [max=9]', pattern=_pattern)
async def roll(event):
  if event.message.media:
    return
  _min, _max = getMinMax(event.pattern_match)
  res = random.randint(_min, _max)
  msg = f'🎲 骰到了 {res} ({_min} ~ {_max})' 
  await event.reply(msg)
  raise events.StopPropagation


@InlineCommand(_query_pattern)
async def _(event):
  builder = event.builder
  _min, _max = getMinMax(event.pattern_match)
  res = random.randint(_min, _max)
  msg = f'🎲 骰到了 {res} ({_min} ~ {_max})' 
  return [
    builder.article(
      title='投骰子',
      description=f'在 {_min} ~ {_max} 之中生成随机数', 
      text=msg,
      thumb=types.InputWebDocument(
        url='https://i.postimg.cc/VsR2Dp6K/image.png',
        size=21790,
        mime_type='image/jpeg',
        attributes=[
          types.DocumentAttributeImageSize(w=180, h=180)
        ],
      )
    )
  ]
  
  
def getMinMax(match):
  _min = 1
  _max = 10
  if t := match.group(1):
    _min = int(t)
  if t := match.group(2):
    _max = int(t)
  if _min > _max: 
    _min, _max = _max, _min
  return _min, _max
  