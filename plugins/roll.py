# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, types
import re
import random

from plugin import Command, InlineCommand
from util.log import logger
import filters


_p = r'[ \[\(\{]*(-?\d{1,3})? *(?:(?:[\/~d,:-]|to) *(-?\d{1,3})?[ \]\)\}]*)?$'
_pattern = re.compile((r'/?roll(?:@%s)?' % bot.me.username) + _p).match
_query_pattern = re.compile(_p).match


@Command(
  'roll',
  info='生成随机数 /roll [min=0] [max=9]',
  pattern=_pattern,
  filter=filters.ONLYTEXT,
)
async def roll(event):
  if event.message.media:
    return
  _min, _max = getMinMax(event.pattern_match)
  res = random.randint(_min, _max)
  msg = f'🎲 骰到了 {res} ({_min} ~ {_max})'
  if not event.is_private:
    user_id = event.sender_id
    chat = await bot.get_entity(user_id)
    name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
    if t := getattr(chat, 'last_name', None):
      name += ' ' + t
    msg = f'[{name}](tg://user?id={user_id}) {msg}'
  await event.reply(msg)
  raise events.StopPropagation


@InlineCommand(_query_pattern)
async def _(event):
  builder = event.builder
  _min, _max = getMinMax(event.pattern_match)
  res = random.randint(_min, _max)
  logger.info(f'{res} {_min} ~ {_max}')
  return [
    builder.article(
      title='投骰子',
      description=f'在 {_min} ~ {_max} 之中生成随机数',
      text=f'🎲 骰到了 {res} ({_min} ~ {_max})',
      thumb=types.InputWebDocument(
        url='https://i.postimg.cc/VsR2Dp6K/image.png',
        size=21790,
        mime_type='image/jpeg',
        attributes=[types.DocumentAttributeImageSize(w=180, h=180)],
      ),
    ),
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
