# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
""".env.example"""

from telethon import types
import re
from datetime import datetime

import util
from plugin import Command, Scope
import filters
from .data_source import PluginException, gallery_info, get_telegraph


_pattern = re.compile(
  r'^/?(?:nid )?(?:https?://)?nhentai\.net/g/([0-9a-z]+)(?:/([0-9a-z]+))?|^/nid(?![^ ])'
).match


@Command(
  'nid',
  pattern=_pattern,
  info='n站爬取 /nid <url> [hide] [mask]',
  filter=filters.PRIVATE & filters.ONLYTEXT,
  scope=Scope.private(),
)
async def nid(event, text):
  match = event.pattern_match
  gid = match.group(1)

  options = util.string.Options(text, nocache=())

  try:
    title, num, media_id, exts, tags = await gallery_info(gid)
  except PluginException as e:
    await event.reply(str(e))

  if page := match.group(2):
    page = int(page)
    msg = (
      f'<code>{title}</code>\n{page}/{num}\n此页: https://nhentai.net/g/{gid}/{page}'
    )
    imgurl = f'https://i.nhentai.net/galleries/{media_id}/{page}.{exts[page - 1]}'
    async with bot.action(event.peer_id, 'photo'):
      img = await util.getImg(
        imgurl, ext=True, headers={'referer': f'https://nhentai.net/g/{gid}'}
      )
      await bot.send_file(
        event.peer_id,
        img,
        caption=msg,
        parse_mode='HTML',
        reply_to=event.message,
      )
    return

  mid = await event.reply('请等待...')
  now = datetime.now()
  key = f'nhentaig{gid}-{now:%m-%d}'
  if not (url := util.Data('urls')[key]) or options.nocache:
    url = await get_telegraph(gid, title, media_id, exts, options.nocache, mid)
    if isinstance(url, dict):
      return await mid.edit(f'生成 telegraph 失败: {url["message"]}')
    with util.Data('urls') as data:
      data[key] = url

  await mid.delete()
  msg = (
    f'标题: <code>{title}</code>\n'
    f'{tags}'
    f'数量: {num}\n'
    f'<a href="{url}">预览</a> / <a href="https://nhentai.net/g/{gid}">原链接</a>'
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
