# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, utils, errors, Button
import re
import os
import asyncio

import util
import filters
from util.log import logger
from plugin import Command, Scope


def override_message_spoiler(message, spoiler: bool):
  media = utils.get_input_media(message.media)
  media.spoiler = spoiler
  return media


@Command(
  'mask',
  info='给回复媒体添加遮罩',
  pattern=re.compile('^/(mask|spoiler)'),
  filter=filters.PRIVATE & filters.ONLYTEXT,
  scope=Scope.private(),
)
async def _mask(event, spoiler=True):
  if not (reply_message := await event.message.get_reply_message()):
    return await event.reply('请用命令回复一条消息')
  if reply_message.media is None:
    return await event.respond('回复的信息没有媒体')

  if reply_message.grouped_id is None:
    if getattr(reply_message.media, 'spoiler', False) is spoiler:
      return await event.respond('该媒体已经有遮罩了' if spoiler else '该媒体没有遮罩')
    media = override_message_spoiler(reply_message, spoiler)
    caption = reply_message.message
    entities = reply_message.entities
  else:
    ids = util.data.MessageData.get_group(reply_message.grouped_id)
    # logger.info(ids)
    messages = await bot.get_messages(reply_message.peer_id, ids=ids)
    if (spoiler and all(getattr(i.media, 'spoiler', False) for i in messages)) or (
      not spoiler and not any(getattr(i.media, 'spoiler', False) for i in messages)
    ):
      return await event.respond(
        '这组媒体都有遮罩' if spoiler else '这组媒体都没有遮罩'
      )

    media = [override_message_spoiler(i, spoiler) for i in messages]
    caption = [i.message for i in messages]
    entities = [i.entities for i in messages]

  await bot.send_file(
    reply_message.peer_id, 
    media, 
    caption=caption,
    formatting_entities=entities,
  )
  raise events.StopPropagation


@Command(
  'unmask',
  info='去掉回复媒体的遮罩',
  pattern=re.compile(r'^/(unmask|unspoiler)'),
  filter=filters.PRIVATE & filters.ONLYTEXT,
  scope=Scope.private(),
)
async def _unmask(event):
  return await _mask(event, False)


mask_button_pattern = re.compile(
  rb'mask(?:_([\x00-\xff]{4,4}))?(?:~([\x00-\xff]{6,6}))?$'
).match


@bot.on(events.CallbackQuery(pattern=mask_button_pattern))
async def mask_button(event):
  """
  mask_{message_id}~{sender_id}
  编辑消息遮罩按钮回调
  """
  peer = event.query.peer
  data = event.query.data

  match = event.pattern_match
  message_id = event.query.msg_id
  if t := match.group(1):
    message_id = int.from_bytes(t, 'big')
  sender_id = None
  if t := match.group(2):
    sender_id = int.from_bytes(t, 'big')
  logger.info(f'{message_id=}, {sender_id=}, {event.sender_id=}')

  if sender_id and event.sender_id and sender_id != event.sender_id:
    participant = await bot.get_permissions(peer, event.sender_id)
    if not participant.delete_messages:
      return await event.answer('只有消息发送者可以修改', alert=True)

  message = await bot.get_messages(peer, ids=message_id)
  if message is None:
    await event.answer('消息不存在', alert=True)
    await event.delete()
    return
  mask = not message.media.spoiler

  messages = [message]
  if message.grouped_id:
    ids = util.data.MessageData.get_group(message.grouped_id)
    messages = await bot.get_messages(peer, ids=ids)

  # 修改按钮
  text = '移除遮罩' if mask else '添加遮罩'
  btn = Button.inline(text, data)
  buttons = message.buttons
  index_i = 0
  index_j = 0
  if buttons:
    for i, ai in enumerate(buttons):
      for j, aj in enumerate(ai):
        if mask_button_pattern(aj.data):
          index_i = i
          index_j = j
          break
    buttons[index_i][index_j] = btn
  else:
    buttons = btn

  for i, m in enumerate(messages):
    file = override_message_spoiler(m, mask)
    try:
      if i == 0 and not match.group(1):
        await bot.edit_message(peer, m, file=file, buttons=buttons)
      else:
        await bot.edit_message(peer, m, file=file)

    except errors.MessageNotModifiedError:
      pass

  if match.group(1):
    if m := (await event.get_message()):
      buttons = m.buttons
      index_i = 0
      index_j = 0
      if buttons:
        for i, ai in enumerate(buttons):
          for j, aj in enumerate(ai):
            if mask_button_pattern(aj.data):
              index_i = i
              index_j = j
              break
        buttons[index_i][index_j] = btn
      else:
        buttons = btn
      try:
        await m.edit(buttons=buttons)
      except errors.MessageNotModifiedError:
        pass

  await event.answer()


class DelayMedia:
  _instances = {}

  @staticmethod
  @bot.on(events.NewMessage)
  @bot.on(events.Album)
  async def _(event):
    if not event.is_private:
      return
    if not getattr(event, 'messages', None):
      if event.message.grouped_id:
        return
      event.messages = [event.message]
    if any(not (m.photo or m.video) for m in event.messages):
      return

    if not (ins := DelayMedia._instances.get(event.chat_id, None)):
      ins = DelayMedia()
      DelayMedia._instances[event.chat_id] = ins

    ins.append(event)
    # 延迟回调以接收全部媒体
    await asyncio.sleep(0.25)
    await ins.delay_callback(event)

  def __init__(self):
    self.events = []

  def append(self, event):
    self.events.append(event)

  async def delay_callback(self, event):
    if id(max(self.events, key=lambda e: e.messages[0].id)) != id(event):
      return

    if len(self.events) == 1:
      self.messages = event.messages
    else:
      self.messages = []
      for i in self.events:
        self.messages.extend(i.messages)
      sorted(self.messages, key=lambda m: m.id)

    try:
      buttons = self.get_buttons(event)
      await bot.send_message(
        event.chat_id,
        f'收到 {len(self.messages)} 个媒体',
        buttons=buttons,
        reply_to=self.messages[0],
      )
    finally:
      self.events = []

  def get_buttons(self, event):
    start_mid = self.messages[0].id.to_bytes(4, 'big')
    end_mid = self.messages[-1].id.to_bytes(4, 'big')
    add_bytes = start_mid + b'_' + end_mid
    buttons = []
    if any(not m.media.spoiler for m in self.messages):
      buttons.append(Button.inline('添加遮罩', b'smask_1_' + add_bytes))
    if any(m.media.spoiler for m in self.messages):
      buttons.append(Button.inline('移除遮罩', b'smask_0_' + add_bytes))
    return [buttons]


smask_button_pattern = re.compile(
  rb'smask_([01])_([\x00-\xff]{4,4})_([\x00-\xff]{4,4})$'
).match


@bot.on(events.CallbackQuery(pattern=smask_button_pattern))
async def smask_button(event):
  """
  收到媒体时发送的遮罩按钮点击回调
  """
  peer = event.query.peer
  match = event.pattern_match
  if match.group(1) == b'1':
    mask = True
  else:
    mask = False
  logger.info(f'mask: {mask}')

  start_mid = int.from_bytes(match.group(2), 'big')
  end_mid = int.from_bytes(match.group(3), 'big')
  if start_mid == end_mid:
    ids = [start_mid]
  else:
    ids = [i for i in range(start_mid, end_mid + 1)]
  messages = await bot.get_messages(peer, ids=ids)
  if all(m is None for m in messages):
    await event.answer('消息不存在', alert=True)
    await event.delete()
    return

  btn_message = await event.get_message()
  files = [override_message_spoiler(i, mask) for i in messages]
  caption = [m.message for m in messages]
  entities = [m.entities for m in messages]
  reply_to = btn_message.reply_to and btn_message.reply_to.reply_to_msg_id
  
  try:
    m = await bot.send_file(
      peer,
      files,
      caption=caption,
      formatting_entities=entities,
      reply_to=reply_to,
    )
  except errors.MediaEmptyError:
    logger.info('发送失败, 尝试下载后发送')
    m = await download_mask(event, mask, messages, btn_message)
  await m[0].reply(
    '操作完成',
    buttons=Button.inline(
      '添加遮罩' if not mask else '移除遮罩',
      b'mask_' + m[0].id.to_bytes(4, 'big'),
    ),
  )

  await event.answer()


async def download_mask(event, mask, messages, btn_message):
  peer = event.query.peer
  medias = []
  for i in messages:
    _id = i.document.id if i.document else i.photo.id
    name = str(_id) + i.file.ext
    img = util.getCache(name)
    if not os.path.isfile(img):
      await i.download_media(file=img)
    media = await util.media.file_to_media(img, mask, nosound_video=True)
    medias.append(media)

  caption = [m.message for m in messages]
  entities = [m.entities for m in messages]
  reply_to = btn_message.reply_to and btn_message.reply_to.reply_to_msg_id
  m = await bot.send_file(
    peer,
    medias,
    caption=caption,
    formatting_entities=entities,
    reply_to=reply_to,
  )
  
  # 检查是否添加遮罩成功
  if mask and m:
    for i in m:
      try:
        await i.edit(
          file=override_message_spoiler(i, mask),
        )
      except errors.MessageNotModifiedError:
        pass
  
  return m
