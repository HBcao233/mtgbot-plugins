# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, utils, types
import re
from util.log import logger
from plugin import handler
import filters


del_time = 30
caption = f'This message will delete in {del_time} seconds'
file_pattern = re.compile('([a-zA-Z0-9-_]{31,34})')


@bot.on(events.NewMessage)
async def media2code(event):
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
async def medias2code(event):
  if not event.is_private:
    return
  await bot.send_message(
    event.messages[0].peer_id,
    '\n'.join(
      '`'
      + (
        utils.pack_bot_file_id(m.photo)
        if m.photo
        else utils.pack_bot_file_id(m.document)
      )
      + '`'
      for m in event.messages
    ),
    reply_to=event.messages[0].id,
  )


@handler(pattern=file_pattern.search, enable=True, filter=filters.PRIVATE)
@handler(
  'file',
  pattern=file_pattern.search,
  enable=False,
  filter=(
    filters.PRIVATE
    & filters.Filter(lambda event: event.message.message.startswith('/file '))
    & (~filters.MEDIA)
  ),
)
async def file(event):
  medias = []
  documents = []
  others = []
  for i in file_pattern.findall(event.message.message):
    logger.info(f'file_id: {i}')
    t = utils.resolve_bot_file_id(i)
    if t is None:
      continue
    add = utils.get_input_media(t)
    if isinstance(t, types.Photo):
      medias.append(add)
    elif isinstance(t, types.Document):
      if (
        (
          any(
            isinstance((attr := j), types.DocumentAttributeVideo) for j in t.attributes
          )
        )
        or (
          any(
            isinstance((attr := j), types.DocumentAttributeAudio) for j in t.attributes
          )
          and attr.voice
        )
        or any(isinstance(j, types.DocumentAttributeSticker) for j in t.attributes)
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
    ms = await bot.send_file(
      event.peer_id, medias, caption=caption, reply_to=event.message
    )
    bot.schedule_delete_messages(del_time, event.peer_id, ms)

  if documents:
    ms = await bot.send_file(
      event.peer_id, documents, caption=caption, reply_to=event.message
    )
    bot.schedule(del_time, bot.delete_messages(event.peer_id, ms))

  for i in others:
    ms = await bot.send_file(event.peer_id, i, caption=caption, reply_to=event.message)
    bot.schedule(del_time, bot.delete_messages(event.peer_id, ms))
