from telethon import events, utils, types
import re

import config
import util
from util.log import logger


bot = config.bot
@bot.on(events.NewMessage)
async def _(event):
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
  await bot.send_message(
    event.messages[0].peer_id,
    "\n".join('`' + (
      utils.pack_bot_file_id(m.photo)
      if m.photo else 
      utils.pack_bot_file_id(m.document)
    ) + '`' for m in event.messages), 
    reply_to=event.messages[0].id,
  )
    
    
caption = 'This message will delete in 60 seconds'
_pattern = re.compile("([a-zA-Z0-9-_]{31,34})")
@bot.on(events.NewMessage(
  pattern=_pattern.search
))
async def file(event):
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
    await bot.send_file(event.peer_id, medias)
  if documents: 
    await bot.send_file(event.peer_id, documents)
  for i in others:
    await bot.send_file(event.peer_id, i)
