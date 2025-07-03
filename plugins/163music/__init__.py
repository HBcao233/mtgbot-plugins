# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : 网易云音乐解析
"""requirement
pycryptodome
pyexecjs
"""

""".env.example
# cookie 中的 csrf_token
163music_csrf_token =
163music_u = ""
"""

import re
from telethon import Button

import filters
import util
from plugin import Command, Scope
from util.log import logger
from util.progress import Progress
from .data_source import (
  get_song_detail,
  parse_song_detail,
  get_url,
  general_search,
  parse_search,
  getImg,
)


_pattern = re.compile(
  r'(?:(?:(?:https?://)?(?:y\.)?music\.163\.com/(?:[#m|]/)?song\?id=)([0-9]{3,12})|(?:163cn\.tv/([0-9a-zA-Z]{7,7}))|^/163music(?!_))'
).search
_pattern1 = re.compile(
  r'(?:(?:(?:https?://)?(?:y\.)?music\.163\.com/(?:[#m|]/)?song\?id=)?([0-9]{3,12})|(?:163cn\.tv/([0-9a-zA-Z]{7,7}))|^/163music(?!_))'
).search


@Command(
  '163music',
  pattern=_pattern,
  info='网易云音乐链接解析',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _song(event, sid=''):
  if not sid:
    match = event.pattern_match
    if event.raw_text.startswith('/'):
      text = event.raw_text[8:].strip()
      match = _pattern1(text)

    if (sid := match.group(1)) is None and match.group(2) is None:
      return await event.reply(
        '用法: /163music <url/id>',
      )

    if match.group(2):
      r = await util.get('http://163cn.tv/' + match.group(2))
      # logger.info(r.url)
      text = str(r.url)
      match = _pattern(text)
      sid = match.group(1)
      await event.reply(
        f'https://music.163.com/#/song?id={sid}',
      )

  mid = await event.reply('请等待...')
  res = await get_song_detail(sid)
  if isinstance(res, str):
    return await event.reply(res)
  msg = parse_song_detail(res)

  key = f'163music_{sid}'
  singers = '、'.join([i['name'] for i in res['ar']])
  name = f'{res["name"]} - {singers}'
  bar = Progress(mid)
  async with bot.action(event.peer_id, 'audio'):
    if not (img := util.data.Audios()[key]):
      await mid.edit('下载中...')
      bar.set_prefix('下载中...')
      res = await get_url(sid)
      if res is None:
        return await event.reply(
          msg,
          parse_mode='html',
        )
      url, ext = res
      img = await getImg(
        url,
        saveas=name,
        ext=ext,
        progress_callback=bar.update,
      )

    await mid.edit('上传中...')
    bar.set_prefix('上传中...')
    m = await bot.send_file(
      event.peer_id,
      file=img,
      caption=msg,
      parse_mode='html',
      progress_callback=bar.update,
    )
  with util.data.Audios() as data:
    data[key] = m


@Command(
  '163music_search',
  info='网易云音乐搜索',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
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
