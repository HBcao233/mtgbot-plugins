# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : qq音乐解析
"""requirement
qqmusic-api-python
"""

""".env.example
# 运行 get_credential.py 扫描登录获取
qqmusic_musicid =
qqmusic_musickey =
qqmusic_refresh_key =
qqmusic_refresh_token =
qqmusic_encrypt_uin =
"""

import re
from telethon import Button, types

from plugin import Command, Scope
from .data_source import (
  get_song_info,
  parse_song_info,
  get_song_url,
  general_search,
  parse_search,
  get_try_url,
)
import filters
import util


_pattern = re.compile(
  r'(?:(?:(?:https?://)?i\.y\.qq\.com/(?:n/ryqq/songDetail/|(?:.*?songmid=)))([0-9a-zA-Z]{12,16})|(?:c6\.y\.qq\.com/base/fcgi-bin/u\?__=([0-9a-zA-Z]{7,14}))|^/qqmusic(?!_))'
).search


@Command(
  'qqmusic',
  pattern=_pattern,
  info='qq音乐链接解析',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _song(event, mid=''):
  if not mid:
    match = event.pattern_match
    if (mid := match.group(1)) is None and match.group(2) is None:
      return await event.reply(
        '用法: /qqmusic_song <url>',
      )

    if match.group(2):
      r = await util.get('https://c6.y.qq.com/base/fcgi-bin/u?__=' + match.group(2))
      text = str(r.url)
      match = _pattern(text)
      mid = match.group(1)
      await event.reply(
        f'https://y.qq.com/n/ryqq/songDetail/{mid}',
      )

  res = await get_song_info(mid)
  msg = parse_song_info(res)

  key = f'qqmusic_{mid}'
  singers = [i['name'] for i in res['singer']]
  singers = '、'.join(singers)
  name = f'{res["title"]} - {singers}'
  if not (img := util.data.Audios()[key]):
    url = await get_song_url(mid)
    img = None
    if not url:
      url = await get_try_url(res)
      key += '_try'
      name = '(试听) ' + name
      if key in util.data.Audios():
        img = util.data.Audios()[key]
    if not url:
      return await event.reply(
        msg,
        parse_mode='html',
      )

    if not img:
      img = await util.getImg(url, saveas=name, ext='mp3')
  async with bot.action(event.peer_id, 'audio'):
    m = await bot.send_file(
      event.peer_id,
      file=img,
      caption=msg,
      parse_mode='html',
    )
  with util.data.Audios() as data:
    data[key] = m


@Command(
  'qqmusic_search',
  info='qq音乐搜索',
  filter=filters.ONLYTEXT & filters.PRIVATE,
)
async def _search(event):
  keyword = ''
  arr = event.raw_text.split(' ')
  if len(arr) > 1:
    keyword = arr[1]

  if not keyword:
    async with bot.conversation(event.chat_id) as conv:
      mid = await conv.send_message(
        '请在 60 秒内发送您想要搜索的关键词',
        buttons=Button.text('取消', single_use=True),
      )

      try:
        message = await conv.get_response()
      except asyncio.TimeoutError:
        pass
      if message.message == '取消':
        return await mid.respond('操作取消', buttons=Button.clear())
      if (
        not message.message
        or message.message.startswith('/')
        or len(message.message) > 64
      ):
        return await mid.respond('输入有误', buttons=Button.clear())
      keyword = message.message.strip()

  mid = await event.respond('请稍后...', buttons=Button.clear())
  res = await general_search(keyword)
  msg, buttons = parse_search(res)
  await mid.delete()
  await event.reply(
    msg,
    parse_mode='html',
    buttons=buttons,
  )


@Command('start', pattern=r'/start qqmusic_([0-9a-zA-Z]{14,14})')
async def _(event):
  match = event.pattern_match
  mid = match.group(1)
  await _song(event, mid)
