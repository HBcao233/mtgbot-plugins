# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Require Plugin: mark

from telethon import types, events, utils, errors, Button
from collections.abc import Sequence
import asyncio
import re

import util
from util.data import MessageData
from plugin import import_plugin


mark = import_plugin('mark')
try:
  hosting = import_plugin('hosting')
except ModuleNotFoundError:
  hosting = None
_get_buttons = mark.DelayMedia.get_buttons


def get_buttons(self, event):
  buttons = _get_buttons(self, event)
  if all(i.photo for i in event.messages):
    start_mid = self.messages[0].id.to_bytes(4, 'big')
    end_mid = self.messages[-1].id.to_bytes(4, 'big')
    add_bytes = start_mid + b'_' + end_mid
    buttons.append(Button.inline('合并图片', data=b'amerge_' + add_bytes))
  return buttons


mark.DelayMedia.get_buttons = get_buttons


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


amerge_button_pattern = re.compile(
  rb'^amerge_([\x00-\xff]{4,4})_([\x00-\xff]{4,4})$'
).match


@bot.on(events.CallbackQuery(pattern=amerge_button_pattern))
async def add_merge_button(event):
  peer = event.query.peer
  match = event.pattern_match
  btn_message = await event.get_message()

  start_mid = int.from_bytes(match.group(1), 'big')
  end_mid = int.from_bytes(match.group(2), 'big')
  if start_mid == end_mid:
    ids = [start_mid]
  else:
    ids = [i for i in range(start_mid, end_mid + 1)]

  buttons = [
    [Button.inline('完成合并', data=b'fmerge')],
    [Button.inline('创建Telegraph', data=b'tmerge')],
  ]
  reply_to = btn_message.reply_to and btn_message.reply_to.reply_to_msg_id
  future = event.respond(
    f'已添加 {len(ids)} 条媒体',
    buttons=buttons,
    reply_to=reply_to,
  )
  if not MergeData.has_merge(peer):
    m = await future
    MergeData.add_merge(peer, ids, m.id)
    m = await m.pin()
    await m.delete()
  else:
    res = MergeData.get_merge(peer)
    ids = res.mids + ids
    m = await future
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
  """
  完成合并
  """
  peer = event.query.peer
  if not MergeData.has_merge(peer):
    return await event.delete()

  res = MergeData.get_merge(peer)
  messages = await bot.get_messages(peer, ids=res.mids)
  if any(m is None for m in messages):
    await event.answer('待合并媒体被删除', alert=True)
  else:
    await bot.send_file(peer, messages, caption=[i.text for i in messages])

  MergeData.delete_merge(peer)
  try:
    await bot.delete_messages(peer, res.pin_mids)
  except errors.MessageIdInvalidError:
    pass


class Tmerge:
  pattern = re.compile(rb'^tmerge$').match

  @staticmethod
  @bot.on(events.CallbackQuery(pattern=pattern))
  async def button(event):
    async with Tmerge(event) as t:
      await t.main()

  def __init__(self, event):
    self.event = event
    self.peer = event.query.peer

  async def __aenter__(self):
    return self

  async def __aexit__(self, type, value, trace):
    if type is None:
      return await self.event.answer()
    return await self.event.answer('错误', alert=True)

  async def main(self):
    if not MergeData.has_merge(self.peer):
      return await self.event.delete()

    self.res = MergeData.get_merge(self.peer)
    self.messages = await bot.get_messages(self.peer, ids=self.res.mids)
    if any(m is None for m in self.messages):
      return await self.event.answer('待合并媒体被删除', alert=True)
    if any(not m.photo for m in self.messages):
      return await self.event.answer('telegraph 合并暂时仅支持图片', alert=True)
    await self.get_title()
    self.mid = await bot.send_message(self.peer, '请等待', buttons=Button.clear())
    self.bar = util.progress.Progress(self.mid, len(self.res.mids), '上传中...', False)

    with util.Data('urls') as data:
      tasks = [self.parse(m, data) for m in self.messages]
      result = await asyncio.gather(*tasks)

    content = [
      {
        'tag': 'img',
        'attrs': {'src': url},
      }
      for url in result
    ]
    page = await util.telegraph.createPage(self.title, content)
    await bot.send_file(
      self.peer,
      caption=f'已创建 telegraph: {page}',
      file=types.InputMediaWebPage(
        url=page,
        force_large_media=True,
        optional=True,
      ),
    )
    MergeData.delete_merge(self.peer)
    try:
      await bot.delete_messages(self.peer, self.res.pin_mids)
    except errors.MessageIdInvalidError:
      pass

  async def get_title(self):
    async with bot.conversation(self.event.chat_id) as conv:
      mid = await conv.send_message(
        '请在 60 秒内发送您想要设置的 telegraph 标题',
        buttons=Button.text('取消', single_use=True),
      )
      try:
        message = await conv.get_response()
      except asyncio.TimeoutError:
        return await self.event.respond(
          '设置超时', buttons=Button.clear(), reply_to=self.mid
        )
      if message.message == '取消':
        return await self.event.respond(
          '设置取消', buttons=Button.clear(), reply_to=self.mid
        )
      self.title = message.message
      await bot.delete_messages(self.peer, mid)

  async def _parse(self, m, data):
    key = str(m.media.photo.id)
    if url := data.get(key):
      return url
    img = util.getCache(key + '.jpg')
    await m.download_media(file=img)
    url = hosting.get_url(img)
    data[key] = url
    return url

  async def parse(self, m, data):
    url = await self._parse(m, data)
    await self.bar.add(1)
    return url
