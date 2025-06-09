# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com 
# @Info    : qq音乐解析
""".env.example
# 运行 get_credential.py 扫描登录获取
qqmusic_musicid =
qqmusic_musickey =
qqmusic_refresh_key =
qqmusic_refresh_token =
qqmusic_encrypt_uin =
"""

import re

from plugin import Command
from .data_source import (
  get_song_info, 
  parse_song_info,
  get_song_url,
)
import filters
import util


_pattern = re.compile(
  r'(?:(?:(?:https?://)?y\.qq\.com/n/ryqq/songDetail/)([0-9a-zA-Z]{12,16})|(?:c6\.y\.qq\.com/base/fcgi-bin/u\?__=/([0-9a-zA-Z]{7,7}))|^/qqmusic_song)'
).search


@Command(
  'qqmusic_song',
  pattern=_pattern,
  info='qq音乐链接解析',
  filter=filters.ONLYTEXT,
)
async def _song(event):
  match = event.pattern_match
  if (mid := match.group(1)) is None and match.group(2):
    return await event.reply(
      '用法: /qqmusic_song <url>',
    )
  
  if match.group(2):
    r = await util.get('https://6.y.qq.com/base/fcgi-bin/u?__=' + match.group(2))
    text = str(r.url)
    match = _pattern(text.split('?')[0])
    mid = match.group(1)
    await event.reply(
      f'https://y.qq.com/n/ryqq/songDetail/{mid}',
    )
  
  res = await get_song_info(mid)
  msg = parse_song_info(res)
  
  if not (img := util.data.Audios()[f'qqmusic_{mid}']):
    url = await get_song_url(mid)
    if not url:
      return await event.reply(
        msg,
        parse_mode='html',
      )
      
    img = await util.getImg(url, saveas=mid, ext='mp3')
  m = await bot.send_file(
    event.peer_id,
    file=img,
    caption=msg,
    parse_mode='html',
  )
  with util.data.Audios() as data:
    data[f'qqmusic_{mid}'] = m

