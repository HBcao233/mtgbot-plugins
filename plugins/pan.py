# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, utils, types
import re

import config
import util
from util.log import logger


del_time = 30
caption = f'This message will delete in {del_time} seconds'
bot = config.bot


@bot.on(events.NewMessage)
async def _(event):
  if not event.is_private:
    return
  if event.message.grouped_id:
    return 
  code = None
  if event.message.photo:
    code = utils.pack_bot_file_id(event.message.photo)
  elif event.message.document:
    code = utils.pack_bot_file_id(event.message.document)
  if code:
    await event.reply(f'`{code}`')


@bot.on(events.Album)
async def _(event):
  if not event.is_private:
    return
  await bot.send_message(
    event.messages[0].peer_id,
    "\n".join('`' + (
      utils.pack_bot_file_id(m.photo)
      if m.photo else 
      utils.pack_bot_file_id(m.document)
    ) + '`' for m in event.messages), 
    reply_to=event.messages[0].id,
  )
    

_pattern = re.compile("([a-zA-Z0-9-_]{31,34})")
@bot.on(events.NewMessage(
  pattern=_pattern.search
))
async def file(event):
  if not event.is_private:
    return
  r = _pattern.findall(event.message.message)
  medias = []
  documents = []
  others = []
  for i in r:
    t = utils.resolve_bot_file_id(i)
    add = utils.get_input_media(t)
    logger.debug(t.to_dict())
    if isinstance(t, types.Photo):
      medias.append(add)
    elif isinstance(t, types.Document):
      if (
        (any(isinstance((attr:=j), types.DocumentAttributeVideo) for j in t.attributes)) or
        (any(isinstance((attr:=j), types.DocumentAttributeAudio) for j in t.attributes) and attr.voice) or
        any(isinstance(j, types.DocumentAttributeSticker) for j in t.attributes)
      ):
        others.append(add)
      elif any(isinstance(j, types.DocumentAttributeVideo) for j in t.attributes):
        medias.append(add)
      elif any(isinstance(j, types.DocumentAttributeAnimated) for j in t.attributes):
        others.append(add)
      else:
        documents.append(add)
    else:
      others.append(add)
  
  if medias: 
    ms = await bot.send_file(event.peer_id, medias, caption=caption, reply_to=event.message)
    bot.schedule_delete_messages(del_time, event.peer_id, ms)
    
  if documents: 
    ms = await bot.send_file(event.peer_id, documents, caption=caption, reply_to=event.message)
    bot.schedule(del_time, bot.delete_messages(event.peer_id, ms))
    
  for i in others:
    ms = await bot.send_file(event.peer_id, i, caption=caption, reply_to=event.message)
    bot.schedule(del_time, bot.delete_messages(event.peer_id, ms))
