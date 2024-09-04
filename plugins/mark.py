# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, utils, errors, functions, Button
import re 

import util
from util.log import logger
from util.data import MessageData
from plugin import handler


def override_message_spoiler(message, spoiler: bool):
  media = utils.get_input_media(message.media)
  media.spoiler = spoiler
  return media


@handler('mark', 
  info='给回复媒体添加遮罩',
  pattern=re.compile('^/(mark|spoiler)')
)
async def _mark(event, spoiler=True):
  if not (reply_message := await event.message.get_reply_message()):
    return await event.reply('请用命令回复一条消息')
  if reply_message.media is None:
    return await event.respond('回复的信息没有媒体')
    
  if reply_message.grouped_id is None:
    if (
      getattr(reply_message.media, 'spoiler', False) is spoiler
    ):
      return await event.respond('该媒体已经有遮罩了' if spoiler else '该媒体没有遮罩')
    media = override_message_spoiler(reply_message, spoiler)
    caption = reply_message.text
  else:
    ids = util.data.MessageData.get_group(reply_message.grouped_id)
    logger.info(ids)
    messages = await bot.get_messages(reply_message.peer_id, ids=ids)
    if (
      (spoiler and all(getattr(i.media, 'spoiler', False) for i in messages)) or 
      (not spoiler and not any(getattr(i.media, 'spoiler', False) for i in messages))
    ):
      return await event.respond('这组媒体都有遮罩' if spoiler else '这组媒体都没有遮罩')
    
    media = [override_message_spoiler(i, spoiler) for i in messages]
    caption = [i.text for i in messages]
    
  await bot.send_file(reply_message.peer_id, media, caption=caption)
  raise events.StopPropagation
  
  
@handler(
  'unmark', 
  info='去掉回复媒体的遮罩',
  pattern=re.compile(r'^/(unmark|unspoiler)'),
)
async def _unmark(event):
  return await _mark(event, False)
    

_mark_button_pattern = re.compile(rb'mark_([\x00-\xff]{4,4})(?:~([\x00-\xff]{6,6}))?$').match
@bot.on(events.CallbackQuery(
  pattern=_mark_button_pattern
))
async def _mark_button(event):
  """
  mark_{message_id}~{sender_id} 
  添加/移除遮罩按钮回调
  """
  peer = event.query.peer
  
  match = event.pattern_match
  message_id = int.from_bytes(match.group(1), 'big')
  sender_id = None 
  if (t := match.group(2)):
    sender_id = int.from_bytes(t, 'big')
  logger.info(f'{message_id=}, {sender_id=}, {event.sender_id=}')

  if sender_id and event.sender_id and sender_id != event.sender_id:
    participant = await bot.get_permissions(peer, event.sender_id)
    if not participant.delete_messages:
      return await event.answer('只有消息发送者可以修改', alert=True)

  message = await bot.get_messages(peer, ids=message_id)
  mark = not message.media.spoiler
  if message is None:
    return await event.answer('消息被删除', alert=True)

  messages = [message]
  if message.grouped_id:
    ids = util.data.MessageData.get_group(message.grouped_id)
    messages = await bot.get_messages(peer, ids=ids)
  
  for m in messages:
    file = override_message_spoiler(m, mark)
    try:
      await bot.edit_message(peer, m, file=file)
    except errors.MessageNotModifiedError:
      pass

  # 处理完毕修改按钮
  message = await event.get_message()
  buttons = message.buttons
  text = '移除遮罩' if mark else '添加遮罩'
  index = 0
  for i, ai in enumerate(buttons[0]):
    if _mark_button_pattern(ai.data):
      index = i
      data = ai.data
      break
  buttons[0][index] = Button.inline(text, data)

  try:
    await event.edit(buttons=buttons)
  except errors.MessageNotModifiedError:
    pass
  await event.answer()


@bot.on(events.NewMessage)
@bot.on(events.Album)
async def _(event):
  """
  收到媒体时发送按钮面板
  """
  if not event.is_private:
    return
  if not getattr(event, 'messages', None):
    event.messages = [event.message]
    if event.message.grouped_id:
      return
  if any(not (m.photo or m.video) for m in event.messages):
    return

  buttons = []
  if any(not (mid := m).media.spoiler for m in event.messages):
    mid_bytes = mid.id.to_bytes(4, 'big')
    buttons.append(Button.inline('添加遮罩', b'smark_' + mid_bytes))
  if any((mid := m).media.spoiler for m in event.messages):
    mid_bytes = mid.id.to_bytes(4, 'big')
    buttons.append(Button.inline('移除遮罩', b'smark_' + mid_bytes))

  # mid_bytes = event.messages[0].id.to_bytes(4, 'big')
  # buttons.append('合并图片', data=b'merge_')
  await event.reply(
    f'收到 {len(event.messages)} 个媒体',
    buttons=buttons, 
  )


def finish_buttons(buttons):
  for i, ai in enumerate(reversed(buttons)):
    if len(ai) == 0:
      buttons.pop(i)
  if len(buttons) == 0:
    return None
  return buttons


smark_button_pattern = re.compile(rb'smark_([\x00-\xff]{4,4})$').match
@bot.on(events.CallbackQuery(
  pattern=smark_button_pattern
))
async def smark_button(event):
  """
  接收媒体遮罩按钮回调
  """
  peer = event.query.peer
  match = event.pattern_match
  message_id = int.from_bytes(match.group(1), 'big')
  message = await bot.get_messages(peer, ids=message_id)
  if message is None:
    return await event.answer('消息被删除', alert=True)
  
  messages = [message]
  if message.grouped_id:
    ids = util.data.MessageData.get_group(message.grouped_id)
    messages = await bot.get_messages(peer, ids=ids)
    
  mark = not message.media.spoiler
  btn_message = await event.get_message()
  m = await bot.send_file(
    peer, 
    [override_message_spoiler(m, mark) for m in messages],
    reply_to=btn_message.reply_to.reply_to_msg_id
  )
  await m[0].reply(
    '操作完成', 
    buttons=Button.inline('添加遮罩', data=b'mark_' + m[0].id.to_bytes(4, 'big')),
  )

  # 处理完毕修改按钮
  buttons = btn_message.buttons
  for i, ai in enumerate(buttons[0]):
    if smark_button_pattern(ai.data):
      buttons[0].pop(i)
      break

  try:
    await event.edit(buttons=finish_buttons(buttons))
  except errors.MessageNotModifiedError:
    pass
  await event.answer()
