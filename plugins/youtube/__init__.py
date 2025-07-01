# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : youtube 爬取
"""requirement
yt-dlp
"""

""".env
# cookie 中的 __Secure-3PSID
youtube_token = 
# 可选, 获取 r-18 视频时需要, headers 中的 Authorization, 以 SAPISIDHASH 开头
youtube_auth = 
# 可选, 获取 r-18 视频时需要, cookie 中的 __Secure-3PSIDTS 和 __Secure-3PAPISID
youtube_3PSIDTS = 
youtube_3PAPISID = 
"""

import re
import os
import asyncio
from asyncio.subprocess import PIPE, STDOUT

import util
import filters
from util.log import logger
from util.progress import Progress
from plugin import Command, Scope
from .data_source import get_info, parse_info, cookies_path


_pattern = re.compile(
  r'(?:(?:(?:https?://)?(?:.\.)*(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/))([0-9a-zA-Z]{3,12})|^/youtube(?!_))'
).search


@Command(
  'youtube',
  pattern=_pattern,
  info='YouTuBe 解析',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _youtube(event, video_id=''):
  match = event.pattern_match
  if event.raw_text.startswith('/'):
    text = event.raw_text[8:].strip()
    match = _pattern(text)

  if not video_id:
    if (video_id := match and match.group(1)) is None:
      return await event.reply(
        '用法: /youtube <url/video_id>',
      )

  logger.info(f'video_id: {video_id}')
  mid = await event.reply('请等待...')
  res = await get_info(video_id)
  if isinstance(res, str):
    await mid.edit(f'错误: {res}')
    return
  msg = parse_info(res)

  bar = Progress(mid)
  key = f'yt_{video_id}'
  data = util.Videos()
  async with bot.action(event.peer_id, 'video'):
    if not (img := data[key]):
      img = util.getCache(f'{key}.mp4')
      if not os.path.isfile(img):
        await mid.edit('下载中...')
        bar.set_prefix('下载中...')
        proc = await asyncio.create_subprocess_exec(
          *[
            'yt-dlp',
            '-t',
            'mp4',
            '-o',
            img,
            '--cookies',
            cookies_path,
            f'https://www.youtube.com/watch?v={video_id}',
          ],
          stdout=PIPE,
          stderr=STDOUT,
        )
        await proc.wait()
        if proc.returncode != 0:
          stdout = await proc.stdout.read()
          stdout = stdout.decode().strip()
          logger.info(stdout)
          await mid.edit('下载失败')
          return

      await mid.edit('上传中...')
      bar.set_prefix('上传中...')
      img = await util.media.file_to_media(img, False, progress_callback=bar.update)

    m = await bot.send_file(
      event.peer_id,
      file=img,
      caption=msg,
      parse_mode='html',
      reply_to=event.message,
    )
    with data:
      data[key] = m
    await mid.delete()
