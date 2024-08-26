# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
''' .env.example
# ehentai cookie中的 ipb_member_id, ipb_pass_hash, igneous 三项
ex_ipb_member_id = 
ex_ipb_pass_hash = 
ex_igneous =
'''

from telethon import types
import re
import traceback
import asyncio
import ujson as json
from datetime import datetime

import util
from util.log import logger
from plugin import handler
from .data_source import (
  get, getImg, PluginException,
  page_info, gallery_info, get_telegraph
)


_pattern = re.compile(r'^/?(?:eid)? ?(?:https?://)?(e[x-])hentai\.org/([sg])/([0-9a-z]+)/([0-9a-z-]+)|^/eid').match
@handler('eid',
  pattern=_pattern,
  info="e站爬取 /eid <url> [hide] [mark]"
)
async def eid(event, text):
  if (
    not event.message.is_private or 
    event.message.photo or 
    event.message.video
  ): 
    return
  match = event.pattern_match
  arr = [match.group(i) for i in range(1, 5)]
  if arr[1] not in ['s', 'g']:
    return await event.reply("请输入e站 url")
  
  options = util.string.Options(text, nocache=())
  
  # 单页图片
  if arr[1] == "s":
    try:
      r = await get(text)
    except PluginException as e:
      return await mid.edit(str(e))
    msg, imgurl = page_info(text, r.text)
    async with bot.action(event.peer_id, 'photo'):
      img = await getImg(imgurl, ext=True)
      await bot.send_file(
        event.peer_id,
        img,
        caption=msg,
        parse_mode="HTML",
        reply_to=event.message,
      )

  # 画廊
  if arr[1] == "g":
    mid = await event.reply("请等待...")
    try:
      title, num, magnets, tags = await gallery_info(arr[2], arr[3])
    except PluginException as e:
      return await mid.edit(str(e))
    
    now = datetime.now()
    key = f'eg{arr[2]}-{now:%m-%d}'
    if not (url := util.Data('urls')[key]) or options.nocache:
      url = await get_telegraph(arr, title, num, options.nocache, mid)
      if not url:
        return await mid.edit('获取失败')
      with util.Data('urls') as data:
        data[key] = url
        
    await mid.delete()
    eurl = f"https://{arr[0]}hentai.org/g/{arr[2]}/{arr[3]}"
    msg = (
      f'标题: <code>{title}</code>\n'
      f'{tags}'
      f"数量: {num}\n" 
      f"{magnets}"
      f'<a href="{url}">预览</a> / <a href="{eurl}">原链接</a>'
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
