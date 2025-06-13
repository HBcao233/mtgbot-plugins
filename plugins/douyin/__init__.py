# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
"""requirement
gmssl
pydantic
"""

import re

import util
from util.log import logger
from plugin import Command
import filters
from .data_source import (
  get_aweme_detail,
  parse_aweme_detail,
)


_pattern = re.compile(
  r'(?:(?:https?://)?(?:www\.)douyin\.com/video/([0-9a-zA-Z]{12,20})|(?:v\.douyin\.com/([0-9a-zA-Z]{5,10}))|^/douyin(?!_))'
).search


@Command(
  'douyin',
  pattern=_pattern,
  info='抖音视频解析',
  filter=filters.ONLYTEXT & filters.PRIVATE,
)
async def _douyin(event):
  match = event.pattern_match
  if (aid := match.group(1)) is None and match.group(2) is None:
    return await event.reply(
      '用法: /douyin <url/aid>',
    )
  
  if match.group(2) is not None:
    r = await util.get('https://v.douyin.com/' + match.group(2))
    text = str(r.url)
    match = _pattern(text)
    aid = match.group(1)
    await event.reply(
      f'https://www.douyin.com/video/{aid}',
    )
  
  # logger.info(aid)
  res = await get_aweme_detail(aid)
  if not res:
    return await event.reply('获取失败')
  msg = parse_aweme_detail(res)
  
  urls = res['video']['download_addr']['url_list']
  url = urls[0]
  key = f'douyin_{aid}'
  data = util.Videos()
  if not (img := data.get(key, '')):
    async with bot.action(event.peer_id, 'record-video'):
      img = await util.getImg(url, saveas=key, ext='mp4')
    
  async with bot.action(event.peer_id, 'video'):
    m = await bot.send_file(
      event.peer_id,
      file=img,
      caption=msg,
      parse_mode='html',
    )
  with data:
    data[key] = m
    