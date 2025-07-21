# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
"""requirement
gmssl
pydantic
"""

from telethon import Button
import re

import util
from util.log import logger
from plugin import Command, Scope
import filters
from .data_source import (
  get_aweme_detail,
  parse_aweme_detail,
)


_pattern = re.compile(
  r'(?:(?:/douyin ?)?(?:https?://)?(?:www\.)(?:ies)?douyin\.com/(?:video/|.*?modal_id=)?([0-9]{12,20})|(?:v\.douyin\.com/([0-9a-zA-Z_]{5,14}))|^/douyin(?!_))'
).search


@Command(
  'douyin',
  pattern=_pattern,
  info='抖音视频解析',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
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

  logger.info(f'aid: {aid}')
  options = util.string.Options(event.raw_text, nocache=(), mask=('spoiler', '遮罩'))

  mid = await event.reply('请等待...')
  res = await get_aweme_detail(aid)
  if isinstance(res, str):
    return await mid.edit(res)
  msg = parse_aweme_detail(res)

  url = res['video']['play_addr']['url_list'][-1]
  logger.info(url)
  key = f'douyin_{aid}'
  data = util.Videos()
  bar = util.progress.Progress(mid)
  async with bot.action(event.peer_id, 'video'):
    if (file_id := data.get(key)) and not options.nocache:
      media = util.media.file_id_to_media(file_id, options.mask)
    else:
      await mid.edit('下载中...')
      bar.set_prefix('下载中...')
      img = await util.getImg(url, saveas=key, ext='mp4', progress_callback=bar.update)
      await mid.edit('上传中...')
      bar.set_prefix('上传中...')
      media = await util.media.file_to_media(
        img, options.mask, progress_callback=bar.update
      )

    m = await bot.send_file(
      event.peer_id,
      file=media,
      caption=msg,
      parse_mode='html',
      buttons=Button.inline(
        '移除遮罩' if options.mask else '添加遮罩',
        b'mask',
      ),
    )
    await mid.delete()
  with data:
    data[key] = m
