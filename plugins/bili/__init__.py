# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
""".env.example
# bilibili cookie中的 SESSDATA
bili_SESSDATA =
"""

from telethon import Button
import re

import util
from util.log import logger
from plugin import Command, Scope
import filters
from .data_source import get_bili, parse_msg, get_video

_p = r'(?:^|^/bili |(?:https?://)?bilibili\.com/video/)(av\d{2,11}|(?:BV|bv)[0-9a-zA-Z]{8,12})|(?:b23\.tv\\?/((?![0-9]{7,7})[0-9a-zA-Z]{7,7}))|^/bili(?![^ ])'
_pattern = re.compile(_p).search


@Command(
  'bili',
  pattern=_pattern,
  info='av号或bv号获取视频',
  filter=filters.ONLYTEXT & filters.PRIVATE,
  scope=Scope.private(),
)
async def _(event, text):
  match = event.pattern_match
  if match.group(1) is None and match.group(2) is None:
    return await event.reply(
      '用法: /bill <aid/bvid>',
    )
  options = util.string.Options(text, nocache=(), mask=('spoiler', '遮罩'))

  flag = False
  if match.group(2):
    r = await util.get('https://b23.tv/' + match.group(2))
    text = str(r.url)
    match = _pattern(text.split('?')[0])
    flag = True

  p = 1
  g = match.group(1)
  aid = ''
  bvid = ''
  if g.startswith('av'):
    aid = g.replace('av', '')
  else:
    bvid = g

  if match1 := re.search(r'(?:\?|&)p=(\d+)', text):
    if (_p := int(match1.group(1))) > 1:
      p = _p

  logger.info(f'bvid: {bvid}, aid: {aid}, options: {options}')
  if flag:
    await event.reply(
      f'https://www.bilibili.com/video/{bvid}' + ('?p=' + str(p) if p > 1 else ''),
    )

  mid = await event.reply('请等待...')
  info = await get_bili(bvid, aid)
  if isinstance(info, str):
    return await mid.edit('视频不存在')
  bvid, aid, cid, title, msg = parse_msg(info, p)
  logger.info(f'{bvid} av{aid} P{p} cid: {cid}')

  data = util.Videos()
  key = bvid
  if p > 1:
    key += '_p' + str(p)
  bar = util.progress.Progress(mid, '发送中')
  async with bot.action(event.peer_id, 'video'):
    if (file_id := data.get(key)) and not options.nocache:
      media = util.media.file_id_to_media(file_id, options.mask)
    else:
      await mid.edit('下载中...')
      bar.set_prefix('下载中...')
      file = await get_video(bvid, aid, cid, bar)
      if file is None:
        return await mid.edit('获取失败, 请重试')
      await mid.edit('上传中...')
      bar.set_prefix('上传中...')
      media = await util.media.file_to_media(
        file, options.mask, progress_callback=bar.update
      )

    m = await bot.send_file(
      event.peer_id,
      media,
      reply_to=event.message,
      caption=msg,
      parse_mode='HTML',
      buttons=Button.inline(
        '移除遮罩' if options.mask else '添加遮罩',
        b'mask',
      ),
    )
    await mid.delete()
  with data:
    data[key] = m

  key = f'{bvid}_pic'
  data = util.Photos()
  async with bot.action(event.peer_id, 'photo'):
    if (file_id := data.get(key)) and not options.nocache:
      media = util.media.file_id_to_media(file_id, options.mask)
    else:
      img = await util.getImg(
        info['pic'],
        headers={'referer': 'https://www.bilibili.com/'},
        saveas=key,
        ext=True,
      )
      media = await util.media.file_to_media(
        img, options.mask, progress_callback=bar.update
      )
    m = await bot.send_file(
      event.peer_id,
      media,
      reply_to=event.message,
      buttons=Button.inline(
        '移除遮罩' if options.mask else '添加遮罩',
        b'mask',
      ),
    )
  with data:
    data[key] = m
