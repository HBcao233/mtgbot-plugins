# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
"""requirement
gmssl
pydantic
"""

from telethon import types, Button
import re
import asyncio

import util
from util.log import logger
from plugin import Command, Scope
import filters
from .data_source import (
  get_aweme_detail,
  parse_aweme_detail,
)


_pattern = re.compile(
  r'(?:^/douyin |(?:/douyin ?)?(?:https?://)?(?:www\.)?(?:ies)?douyin\.com/(?:video/|note/|.*?modal_id=)?)([0-9]{12,20})|(?:v\.douyin\.com/([0-9a-zA-Z_]{5,14}))|^/douyin(?!_)'
).search


@Command(
  'douyin',
  pattern=_pattern,
  info='抖音视频解析',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _douyin(event):
  d = Douyin(event)
  await d.main()


class Douyin:
  def __init__(self, event):
    self.event = event

  async def main(self):
    match = self.event.pattern_match
    if (aid := match.group(1)) is None and match.group(2) is None:
      return await self.event.reply(
        '用法: /douyin <url/aid>',
      )
    self.aid = aid

    if match.group(2) is not None:
      r = await util.get('https://v.douyin.com/' + match.group(2))
      text = str(r.url)
      match = _pattern(text)
      self.aid = match.group(1)
      await self.event.reply(
        f'https://www.douyin.com/video/{self.aid}',
      )

    self.options = util.string.Options(
      self.event.raw_text, nocache=(), mask=('spoiler', '遮罩')
    )
    logger.info(f'aweme_id: {self.aid}, options: {self.options}')

    self.mid = await self.event.reply('请等待...')
    self.res = await get_aweme_detail(self.aid)
    if isinstance(self.res, str):
      return await self.mid.edit(self.res)
    self.msg = parse_aweme_detail(self.res)

    aweme_type = self.res['aweme_type']
    logger.info(f'aweme_type: {aweme_type}')

    if aweme_type == 68:
      return await self.send_images()

    await self.send_video()

  async def send_video(self):
    url = self.res['video']['play_addr']['url_list'][-1]
    logger.info(url)
    key = f'douyin_{self.aid}'
    data = util.Videos()
    bar = util.progress.Progress(self.mid)
    async with bot.action(self.event.peer_id, 'video'):
      if (file_id := data.get(key)) and not self.options.nocache:
        media = util.media.file_id_to_media(file_id, self.options.mask)
      else:
        await self.mid.edit('下载中...')
        bar.set_prefix('下载中...')
        img = await util.getImg(
          url,
          saveas=key,
          ext='mp4',
          progress_callback=bar.update,
        )
        await self.mid.edit('上传中...')
        bar.set_prefix('上传中...')
        media = await util.media.file_to_media(
          img, self.options.mask, progress_callback=bar.update
        )

      m = await bot.send_file(
        self.event.peer_id,
        file=media,
        caption=self.msg,
        parse_mode='html',
        buttons=Button.inline(
          '移除遮罩' if self.options.mask else '添加遮罩',
          b'mask',
        ),
      )
    await self.mid.delete()
    with data:
      data[key] = m

  async def get_image(self, i, client, photos, bar):
    url = self.urls[i]
    key = f'douyinimg_{self.aid}_{i}'
    if (file_id := photos.get(key)) and not self.options.nocache:
      media = util.media.file_id_to_media(file_id)
      await bar.add(1)
      return media

    logger.info(f'GET {util.curl.logless(url)}')
    img = await client.getImg(
      url,
      saveas=key,
      ext='jpg',
    )
    await bar.add(1)
    media = await util.media.file_to_media(
      img,
      self.options.mask,
    )
    return media

  async def send_images(self):
    url = self.res['video']['play_addr']['url_list'][-1]
    logger.info(url)
    key = f'douyin_{self.aid}'
    audios = util.Audios()
    bar = util.progress.Progress(self.mid)
    title = self.res['item_title'] or self.res['desc'] or key
    async with bot.action(self.event.peer_id, 'audio'):
      if (file_id := audios.get(key)) and not self.options.nocache:
        media = util.media.file_id_to_media(file_id)
      else:
        await self.mid.edit('下载中...')
        bar.set_prefix('下载中...')
        img = await util.getImg(
          url,
          saveas=key,
          ext='m4a',
          progress_callback=bar.update,
        )
        await self.mid.edit('上传中...')
        bar.set_prefix('上传中...')
        media = await util.media.file_to_media(
          img, 
          attributes=[
            types.DocumentAttributeFilename(
              f'{title}.m4a'
            ),
          ],
          progress_callback=bar.update,
        )

      m = await bot.send_file(
        self.event.peer_id,
        file=media,
        caption=self.msg,
        parse_mode='html',
      )
    await self.mid.delete()
    with audios:
      audios[key] = m

    self.mid = await self.event.reply('请等待...')
    photos = util.Photos()
    self.urls = [i['url_list'][-1] for i in self.res['images']]
    bar = util.progress.Progress(
      self.mid,
      total=len(self.urls),
      prefix='下载中...',
      percent=False,
    )
    async with bot.action(self.event.peer_id, 'photo'):
      async with util.curl.Client() as client:
        tasks = [self.get_image(i, client, photos, bar) for i in range(len(self.urls))]
        gather_task = asyncio.gather(*tasks)
        images = await gather_task
      m = await bot.send_file(
        self.event.peer_id,
        file=images,
        caption=self.msg,
        parse_mode='html',
      )
    await self.mid.delete()
    with photos:
      for i in range(len(self.urls)):
        key = f'douyinimg_{self.aid}_{i}'
        photos[key] = m[i]
