# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : instagram 解析
""".env.example
# cookie 中的 csrftoken sessionid
instagram_csrftoken =
instagram_sessionid =
"""

from telethon import Button
import re

import util
import filters
from util.log import logger
from util.progress import Progress
from plugin import Command, Scope
from .data_source import gheaders, media_info, parse_info, parse_medias


_p = r'(?:^/ig +)?(?:https?://)?[a-z\.]*?instagram\.com/(?:p|reel)/([a-zA-Z0-9_]{11,11})|^/ig(?![^ ])'
_pattern = re.compile(_p).search


@Command(
  'ig',
  pattern=_pattern,
  info='获取instagram /ig <url/shortcode> [hide] [mask]',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _ig(event, text):
  match = event.pattern_match
  if (shortcode := match.group(1)) is None:
    return await event.reply(
      '用法: /ig <url/shortcode> [options]:\n'
      '获取instagram\n'
      '- <url/shortcode>: 推文链接或 shortcode\n'
      '- [hide/简略]: 获取简略信息\n'
      '- [mask/遮罩]: 添加遮罩'
    )

  options = util.string.Options(
    text, hide=('简略', '省略'), mask=('spoiler', '遮罩')
  )
  logger.info(f'shortcode: {shortcode}, options: {options}')
  mid = await event.reply('请等待...')

  res = await media_info(shortcode)
  if isinstance(res, str):
    return await mid.edit(res)

  msg = parse_info(res)
  medias_info = parse_medias(res)
  logger.info(medias_info)
  photos = util.Photos()
  videos = util.Videos()
  bar = Progress(mid, prefix='下载中...')
  medias = []
  async with bot.action(event.peer_id, medias_info[0]['type']):
    for i, ai in enumerate(medias_info):
      key = ai['key']
      name = f'ig_{shortcode}_{i}'
      ext = ai['ext']
      url = ai['url']
      t = photos if ai['type'] == 'photo' else videos
      if file_id := t.get(key):
        media = util.media.file_id_to_media(file_id, options.mask)
      else:
        file = await util.getImg(
          url,
          headers=gheaders,
          saveas=name,
          ext=ext,
          progress_callback=bar.update if len(medias_info) == 1 else None,
        )
        if ai['type'] == 'video':
          file = await util.media.video2mp4(file)
        if len(medias_info) == 1:
          bar.set_prefix('上传中...')
        media = await util.media.file_to_media(
          file,
          options.mask,
          progress_callback=bar.update if len(medias_info) == 1 else None,
          as_image=True if ext == '.webp' else False,
        )
      medias.append(media)
      if len(medias_info) > 1:
        await bar.add(1)
    logger.info(medias)
    m = await bot.send_file(
      event.peer_id,
      medias,
      reply_to=event.message,
      caption=msg,
      parse_mode='HTML',
    )
  await mid.delete()

  with photos:
    with videos:
      for i, ai in enumerate(m):
        t = photos if ai.photo else videos
        t[medias_info[i]['key']] = ai

  message_id_bytes = m[0].id.to_bytes(4, 'big')
  sender_bytes = b'~' + event.sender_id.to_bytes(6, 'big', signed=True)
  shortcode_bytes = shortcode.encode()
  await event.reply(
    '获取完成',
    buttons=[
      [
        Button.inline(
          '移除遮罩' if options.mask else '添加遮罩',
          b'mask_' + message_id_bytes + sender_bytes,
        ),
        Button.inline(
          '详细描述' if options.hide else '简略描述',
          b'ig_' + message_id_bytes + b'_' + shortcode_bytes,
        ),
      ],
      # [Button.inline('关闭面板', b'delete' + sender_bytes)],
    ],
  )
