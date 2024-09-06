# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, utils, errors, Button
import re
from collections.abc import Sequence

import util
from util.log import logger
from util.data import MessageData
from plugin import handler


def override_message_spoiler(message, spoiler: bool):
  media = utils.get_input_media(message.media)
  media.spoiler = spoiler
  return media


@handler('mark', info='给回复媒体添加遮罩', pattern=re.compile('^/(mark|spoiler)'))
async def _mark(event, spoiler=True):
  if not (reply_message := await event.message.get_reply_message()):
    return await event.reply('请用命令回复一条消息')
  if reply_message.media is None:
    return await event.respond('回复的信息没有媒体')

  if reply_message.grouped_id is None:
    if getattr(reply_message.media, 'spoiler', False) is spoiler:
      return await event.respond('该媒体已经有遮罩了' if spoiler else '该媒体没有遮罩')
    media = override_message_spoiler(reply_message, spoiler)
    caption = reply_message.text
  else:
    ids = util.data.MessageData.get_group(reply_message.grouped_id)
    logger.info(ids)
    messages = await bot.get_messages(reply_message.peer_id, ids=ids)
    if (spoiler and all(getattr(i.media, 'spoiler', False) for i in messages)) or (
      not spoiler and not any(getattr(i.media, 'spoiler', False) for i in messages)
    ):
      return await event.respond(
        '这组媒体都有遮罩' if spoiler else '这组媒体都没有遮罩'
      )

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


_mark_button_pattern = re.compile(
  rb'mark_([\x00-\xff]{4,4})(?:~([\x00-\xff]{6,6}))?$'
).match


@bot.on(events.CallbackQuery(pattern=_mark_button_pattern))
async def _mark_button(event):
  """
  mark_{message_id}~{sender_id}
  添加/移除遮罩按钮回调
  """
  peer = event.query.peer

  match = event.pattern_match
  message_id = int.from_bytes(match.group(1), 'big')
  sender_id = None
  if t := match.group(2):
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

  mid_bytes = event.messages[0].id.to_bytes(4, 'big')
  buttons.append(Button.inline('合并图片', data=b'amerge_' + mid_bytes))
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


@bot.on(events.CallbackQuery(pattern=smark_button_pattern))
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
    caption=[m.message for m in messages],
    reply_to=btn_message.reply_to.reply_to_msg_id,
  )
  await m[0].reply(
    '操作完成',
    buttons=Button.inline('添加遮罩', data=b'mark_' + m[0].id.to_bytes(4, 'big')),
  )

  # 处理完毕修改按钮
  buttons = btn_message.buttons
  for i, ai in enumerate(buttons[0]):
    if ai.data == match.group(0):
      buttons[0].pop(i)
      break
  try:
    await event.edit(buttons=finish_buttons(buttons))
  except errors.MessageNotModifiedError:
    pass
  await event.answer()


class MergeData(MessageData):
  inited = False

  @classmethod
  def init(cls):
    MessageData.init()
    if MergeData.inited:
      return
    cls._conn.execute(
      'CREATE TABLE if not exists merge(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, mids BLOB NOT NULL, pin_mids BLOB)'
    )
    cls._conn.execute('CREATE UNIQUE INDEX if not exists id_index ON merge (id)')
    cls._conn.commit()
    MergeData.inited = True

  @staticmethod
  def encode_mids(message_ids: Sequence[int]) -> bytes:
    return b''.join(i.to_bytes(4, 'big') for i in message_ids)

  @staticmethod
  def decode_mids(mids: bytes) -> list[int]:
    ids = re.findall(rb'[\x00-\xff]{4,4}', mids)
    return [int.from_bytes(i, 'big') for i in ids]

  @classmethod
  def add_merge(cls, chat_id: int, message_ids: Sequence[int], pin_mid: int) -> int:
    cls.init()
    chat_id = utils.get_peer_id(chat_id)
    mids = MergeData.encode_mids(message_ids)
    pin_mids = MergeData.encode_mids([pin_mid])
    if not cls.has_merge(chat_id):
      cursor = cls._conn.cursor()
      cursor.execute(
        'INSERT INTO merge(chat_id, mids, pin_mids) values(?, ?, ?)',
        (chat_id, mids, pin_mids),
      )
      cls._conn.commit()
      return cursor.lastrowid

  @classmethod
  def update_merge(
    cls, chat_id: int, message_ids: Sequence[int], pin_mids: Sequence[int]
  ) -> None:
    cls.init()
    chat_id = utils.get_peer_id(chat_id)
    mids = MergeData.encode_mids(message_ids)
    pin_mids = MergeData.encode_mids(pin_mids)
    cls._conn.execute(
      'UPDATE merge SET mids=?, pin_mids=? WHERE chat_id=?', (mids, pin_mids, chat_id)
    )
    cls._conn.commit()

  @classmethod
  def has_merge(cls, chat_id) -> bool:
    cls.init()
    chat_id = utils.get_peer_id(chat_id)
    r = cls._conn.execute('SELECT id FROM merge where chat_id=?', (chat_id,))
    if r.fetchone():
      return True
    return False

  @classmethod
  def get_merge(cls, chat_id):
    cls.init()
    chat_id = utils.get_peer_id(chat_id)
    r = cls._conn.execute('SELECT * FROM merge where chat_id=?', (chat_id,))
    if res := r.fetchone():
      return res._replace(
        mids=MergeData.decode_mids(res.mids),
        pin_mids=MergeData.decode_mids(res.pin_mids),
      )
    return None

  @classmethod
  def delete_merge(cls, chat_id):
    cls.init()
    chat_id = utils.get_peer_id(chat_id)
    cls._conn.execute('DELETE FROM merge where chat_id=?', (chat_id,))
    cls._conn.commit()


add_merge_button_pattern = re.compile(rb'^amerge_([\x00-\xff]{4,4})$').match


@bot.on(events.CallbackQuery(pattern=add_merge_button_pattern))
async def add_merge_button(event):
  peer = event.query.peer
  match = event.pattern_match
  btn_message = await event.get_message()
  ids = [int.from_bytes(match.group(1), 'big')]
  res = MessageData.get_message(peer, ids[0])
  if res.grouped_id:
    ids = MessageData.get_group(res.grouped_id)

  if not MergeData.has_merge(peer):
    m = await event.respond(
      f'已添加 {len(ids)} 条媒体',
      buttons=Button.inline('完成合并', data=b'fmerge'),
      reply_to=btn_message.reply_to.reply_to_msg_id,
    )
    MergeData.add_merge(peer, ids, m.id)
    m = await m.pin()
    await m.delete()
  else:
    res = MergeData.get_merge(peer)
    ids = res.mids + ids
    m = await event.respond(
      f'已添加 {len(ids)} 条媒体',
      buttons=Button.inline('完成合并', data=b'fmerge'),
      reply_to=btn_message.reply_to.reply_to_msg_id,
    )
    for i in res.pin_mids:
      try:
        await bot.edit_message(peer, i, buttons=None)
      except errors.MessageNotModifiedError:
        pass
    MergeData.update_merge(peer, ids, res.pin_mids + [m.id])
    m = await m.pin()
    await m.delete()

  await event.answer()


finish_merge_button_pattern = re.compile(rb'^fmerge$').match


@bot.on(events.CallbackQuery(pattern=finish_merge_button_pattern))
async def finish_merge_button(event):
  peer = event.query.peer
  if not MergeData.has_merge(peer):
    return await event.delete()

  res = MergeData.get_merge(peer)
  messages = await bot.get_messages(peer, ids=res.mids)
  if any(m is None for m in messages):
    await event.answer('待合并媒体被删除', alert=True)
  else:
    await bot.send_file(peer, messages)

  MergeData.delete_merge(peer)
  try:
    await bot.delete_messages(peer, res.pin_mids)
  except errors.MessageIdInvalidError:
    pass
