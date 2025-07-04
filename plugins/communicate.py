# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, types, utils, functions
from telethon.custom import Button

import config
from util import logger
from plugin import Command
from util.data import MessageData


echo_chat_id = int(x) if (x := config.env.get('echo_chat_id', '')) else 0
if echo_chat_id == 0:
  logger.warn('communicate 插件并未生效: 配置项 echo_chat_id 未设置或设置错误')


def to_bytes(i):
  return i.to_bytes(4, 'big')


def from_bytes(b):
  return int.from_bytes(b, 'big')


class EchoedMessage(MessageData):
  inited = False

  @classmethod
  def init(cls):
    MessageData.init()
    if EchoedMessage.inited:
      return
    cls._conn.execute(
      'CREATE TABLE if not exists echoed_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, mid int NOT NULL, echo_mid int NOT NULL)'
    )
    cls._conn.execute(
      'CREATE UNIQUE INDEX if not exists id_index ON echoed_messages (id)'
    )
    cls._conn.commit()
    EchoedMessage.inited = True

  @classmethod
  def add_echo(cls, chat_id, message_id, echo_chat_id, echo_message_id):
    cls.init()
    m = cls.get_message(chat_id, message_id)
    echo_m = cls.get_message(echo_chat_id, echo_message_id)
    logger.debug(f'add_echo mid: {m.id} echo_mid: {echo_m.id}')

    cursor = cls._conn.cursor()
    cursor.execute(
      'insert into echoed_messages(mid, echo_mid) values(?,?)', (m.id, echo_m.id)
    )
    cls._conn.commit()
    return cursor.lastrowid

  @classmethod
  def get_echo(cls, chat_id, message_id=None):
    cls.init()
    m = cls.get_message(chat_id, message_id)
    r = cls._conn.execute('SELECT echo_mid FROM echoed_messages WHERE mid=?', (m.id,))
    if res := r.fetchone():
      return cls.get_message_by_rid(res[0])
    return None

  @classmethod
  def get_origin(cls, chat_id, message_id=None):
    cls.init()
    m = cls.get_message(chat_id, message_id)
    r = cls._conn.execute('SELECT mid FROM echoed_messages WHERE echo_mid=?', (m.id,))
    if res := r.fetchone():
      return cls.get_message_by_rid(res[0])
    return None


@Command(pattern=r'^(?!/).*')
async def _(event):
  message = event.message
  if echo_chat_id == 0:
    return

  peer_id = utils.get_peer_id(event.message.peer_id)
  chat = await bot.get_entity(event.message.peer_id)
  name = getattr(chat, 'first_name', '')

  reply_message = await event.message.get_reply_message()
  if t := getattr(chat, 'last_name', ''):
    name += ' ' + t

  if peer_id != echo_chat_id:
    buttons = [
      [Button.url(name, url=f'tg://user?id={chat.id}')],
    ]
    reply_to = None
    if reply_message:
      reply_to = EchoedMessage.get_origin(reply_message).message_id

    m = await bot.send_message(
      echo_chat_id,
      message,
      buttons=buttons,
      reply_to=reply_to,
    )
    EchoedMessage.add_echo(peer_id, message.id, echo_chat_id, m.id)
    return

  if reply_message:
    res = EchoedMessage.get_origin(reply_message)
    m = await bot.send_message(
      res.chat_id,
      message,
      reply_to=res.message_id,
    )
    EchoedMessage.add_echo(echo_chat_id, message.id, res.chat_id, m.id)


# 转发表情回应
@bot.on(events.Raw)
async def _(update):
  if not isinstance(update, types.UpdateBotMessageReaction):
    return
  logger.debug(update.stringify())

  message = (await bot.get_messages(update.peer, ids=[update.msg_id]))[0]
  if message and utils.get_peer_id(message.from_id) == bot.me.id:
    res = EchoedMessage.get_origin(update.peer, update.msg_id)
  else:
    res = EchoedMessage.get_echo(update.peer, update.msg_id)
  if not res:
    return

  await bot(
    functions.messages.SendReactionRequest(
      peer=res.chat_id,
      msg_id=res.message_id,
      reaction=update.new_reactions,
      big=True,
      add_to_recent=False,
    )
  )
