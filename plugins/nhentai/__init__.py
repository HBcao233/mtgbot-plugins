# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
''' .env.example
'''
from telethon import types
import re
from datetime import datetime

import util
from util.log import logger
from plugin import handler
from .data_source import PluginException, gallery_info, get_telegraph


_pattern = re.compile(r'^/?(?:nid)? ?(?:https?://)?nhentai\.net/g/([0-9a-z]+)(?:/([0-9a-z]+))?|^/nid').match
@handler('nid',
  pattern=_pattern,
  info="n站爬取 /nid <url> [hide] [mark]"
)
async def nid(event, text):
  if (
    not event.message.is_private or 
    event.message.photo or 
    event.message.video
  ): 
    return
  match = event.pattern_match
  gid = match.group(1)
  
  options = util.string.Options(text, nocache=())
  
  try:
    title, num, media_id, exts, tags = await gallery_info(gid)
  except PluginException as e:
    await event.reply(str(e))
    
  if (page := match.group(2)):
    page = int(page)
    msg = (
      f"<code>{title}</code>\n"
      f"{page}/{num}\n"
      f"此页: https://nhentai.net/g/{gid}/{page}"
    )
    imgurl = f"https://i.nhentai.net/galleries/{media_id}/{page}.{exts[page - 1]}"
    async with bot.action(event.peer_id, 'photo'):
      img = await util.getImg(imgurl, ext=True, headers={ 'referer': f"https://nhentai.net/g/{gid}" })
      await bot.send_file(
        event.peer_id,
        img,
        caption=msg,
        parse_mode="HTML",
        reply_to=event.message,
      )
    return
  
  mid = await event.reply("请等待...")
  now = datetime.now()
  key = f'nhentaig{gid}-{now:%m-%d}'
  if not (url := util.Data('urls')[key]) or options.nocache:
    url, warnings = await get_telegraph(gid, title, media_id, exts, options.nocache, mid)
    if not url:
      return await mid.edit('获取失败')
    if warnings:
      await event.reply('\n'.join(warnings))
    with util.Data('urls') as data:
      data[key] = url
      
  await mid.delete()
  msg = (
    f'标题: <code>{title}</code>\n'
    f'{tags}'
    f"数量: {num}\n" 
    f'<a href="{url}">预览</a> / <a href="https://nhentai.net/g/{gid}">原链接</a>'
  )
  await bot.send_file(
    event.peer_id,
    caption=msg,
    reply_to=event.message,
    parse_mode="HTML",
    file=types.InputMediaWebPage(
      url=url,
      force_large_media=True,
      optional=True,
    ),
  )
    