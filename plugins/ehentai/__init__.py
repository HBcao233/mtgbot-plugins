# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
"""requirement
bs4
"""

""".env.example
# ehentai cookie中的 ipb_member_id, ipb_pass_hash, igneous 三项
ex_ipb_member_id =
ex_ipb_pass_hash =
ex_igneous =
"""

from telethon import types
import re
from datetime import datetime

import util
import filters
from util.log import logger
from plugin import Command, Scope
from .data_source import (
  get,
  getImg,
  PluginException,
  page_info,
  gallery_info,
  get_telegraph,
)


_pattern = re.compile(
  r'^(?:/eid)? ?(?:https?://)?(e[x-])hentai\.org/([sg])/([0-9a-z]+)/([0-9a-z-]+)|^/eid(?![^ ])'
).match


@Command(
  'eid',
  pattern=_pattern,
  info='e站爬取 /eid <url> [hide] [mask]',
  filter=filters.PRIVATE & filters.ONLYTEXT,
  scope=Scope.private(),
)
async def _eid(event, text):
  if not event.message.is_private or event.message.photo or event.message.video:
    return
  match = event.pattern_match
  arr = [match.group(i) for i in range(1, 5)]
  if arr[1] not in ['s', 'g']:
    return await event.reply('请输入e站 url')

  options = util.string.Options(text, nocache=())
  logger.info(f'arr: {arr} {options}')

  # 单页图片
  if arr[1] == 's':
    url = f'https://{arr[0]}hentai.org/s/{arr[2]}/{arr[3]}'
    try:
      r = await get(url)
    except PluginException as e:
      return await event.reply(str(e))
    msg, imgurl = page_info(url, r.text)
    async with bot.action(event.peer_id, 'photo'):
      img = await getImg(imgurl, ext=True)
      await bot.send_file(
        event.peer_id,
        img,
        caption=msg,
        parse_mode='HTML',
        reply_to=event.message,
      )

  # 画廊
  if arr[1] == 'g':
    await send_gallery(event, arr, options)


async def send_gallery(event, arr, options):
  mid = await event.reply('请等待...')
  eh = arr[0]
  gid = arr[2]
  gtoken = arr[3]
  try:
    info = await gallery_info(gid, gtoken)
  except PluginException as e:
    return await mid.edit(str(e))

  title = info['title']
  num = info['num']
  magnets = info['magnets']
  tags = info['tags']
  now = datetime.now()
  key = f'eg{gid}-{now:%m-%d}'
  if not (url := util.Data('urls')[key]) or options.nocache:
    url = await get_telegraph(arr, title, num, options.nocache, mid)
    if isinstance(url, dict):
      return await mid.edit(f'生成 telegraph 失败: {url["message"]}')
    with util.Data('urls') as data:
      data[key] = url

  title_jpn = ''
  if info['title_jpn']:
    title_jpn = f'日语标题: <code>{info["title_jpn"]}</code>\n'
  eurl = f'https://{eh}hentai.org/g/{gid}/{gtoken}'
  msg = (
    f'标题: <code>{title}</code>\n'
    f'{title_jpn}'
    f'{tags}'
    f'数量: {num}\n'
    f'{magnets}'
    f'<a href="{url}">预览</a> / <a href="{eurl}">原链接</a>'
  )
  await bot.send_file(
    event.peer_id,
    caption=msg,
    reply_to=event.message,
    parse_mode='HTML',
    file=types.InputMediaWebPage(
      url=url,
      force_large_media=True,
      optional=True,
    ),
  )
  await mid.delete()
