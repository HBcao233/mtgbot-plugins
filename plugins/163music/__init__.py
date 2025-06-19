# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : 网易云音乐解析
"""requirement
pycryptodome
"""

""".env.example
# cookie 中的 csrf_token
163music_csrf_token =
163music_cookie = ""
"""

import re
from telethon import Button

from plugin import Command
from .data_source import (
  get_song_detail,
  parse_song_detail,
  get_song_url,
  get_try_url,
  general_search,
  parse_search,
  getImg
)
import filters
import util
from util.log import logger


_pattern = re.compile(
  r'(?:(?:(?:https?://)?(?:y\.)?music\.163\.com/[#m]/song\?id=)([0-9]{3,12})|(?:163cn\.tv/([0-9a-zA-Z]{7,7}))|^/163music(?!_))'
).search


@Command(
  '163music',
  pattern=_pattern,
  info='网易云音乐链接解析',
  filter=filters.ONLYTEXT & filters.PRIVATE,
)
async def _song(event, mid=''):
  if not mid:
    match = event.pattern_match
    if (mid := match.group(1)) is None and match.group(2) is None:
      return await event.reply(
        '用法: /163music <url/id>',
      )

    if match.group(2):
      r = await util.get('http://163cn.tv/' + match.group(2))
      # logger.info(r.url)
      text = str(r.url)
      match = _pattern(text)
      mid = match.group(1)
      await event.reply(
        f'https://music.163.com/#/song?id={mid}',
      )

  res = await get_song_detail(mid)
  msg = parse_song_detail(res)

  key = f'163music_{mid}'
  singers = '、'.join([i['name'] for i in res['ar']])
  name = f'{res["name"]} - {singers}'
  if not (img := util.data.Audios()[key]):
    url, ext = await get_song_url(mid)
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
      img = await getImg(url, saveas=name, ext=ext)
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
  '163music_search',
  info='网易云音乐搜索',
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
  if not res:
    return await event.respond('搜索获取失败, 请检查配置')
  msg, buttons = parse_search(res)
  await mid.delete()
  await event.reply(
    msg,
    parse_mode='html',
    buttons=buttons,
  )


@Command('start', pattern=r'/start 163music_([0-9]{3,8})')
async def _(event):
  match = event.pattern_match
  mid = match.group(1)
  await _song(event, mid)
