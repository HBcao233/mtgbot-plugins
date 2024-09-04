# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, types, utils, functions
from telethon.custom import Button
import os

import config 
from util import logger
from plugin import handler
from util.data import MessageData


def to_bytes(i):
  return i.to_bytes(4, 'big')
  
def from_bytes(b):
  return int.from_bytes(b, 'big')


class EchoedMessage(MessageData):
  inited = False
  @classmethod
  def init(cls):
    MessageData.init()
    if EchoedMessage.inited: return
    cls._conn.execute(f"CREATE TABLE if not exists echoed_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, mid int NOT NULL, echo_mid int NOT NULL)")
    cls._conn.execute(f"CREATE UNIQUE INDEX if not exists id_index ON echoed_messages (id)")
    cls._conn.commit()
    EchoedMessage.inited = True

  @classmethod
  def add_echo(cls, chat_id, message_id, echo_chat_id, echo_message_id):
    cls.init()
    mid = cls.get_message(chat_id, message_id)
    echo_mid = cls.get_message(echo_chat_id, echo_message_id)
    logger.debug(f'add_echo mid: {mid} echo_mid: {echo_mid}')

    cursor = cls._conn.cursor()
    r = cursor.execute(f"insert into echoed_messages(mid, echo_mid) values(?,?)", (mid, echo_mid))
    cls._conn.commit()
    return cursor.lastrowid

  @classmethod
  def get_echo(cls, chat_id, message_id=None):
    cls.init()
    mid = cls.get_message(chat_id, message_id)
    r = cls._conn.execute(f"SELECT echo_mid FROM echoed_messages WHERE mid='{mid}'")
    if (res := r.fetchone()):
      return cls.get_message_by_rid(res[0])
    return None
  
  @classmethod
  def get_origin(cls, chat_id, message_id=None):
    cls.init()
    mid = cls.get_message(chat_id, message_id)
    r = cls._conn.execute(f"SELECT mid FROM echoed_messages WHERE echo_mid='{mid}'")
    if (res := r.fetchone()):
      return cls.get_message_by_rid(res[0])
    return None


@bot.on(events.NewMessage(pattern=r'^(?!/).*'))
async def _(event):
  message = event.message 
  if config.echo_chat_id == 0:
    return
  
  peer_id = utils.get_peer_id(event.message.peer_id)
  chat = await bot.get_entity(event.message.peer_id)
  name = getattr(chat, 'first_name', '') 
  
  reply_message = await event.message.get_reply_message()
  if t := getattr(chat, 'last_name', ''):
    name += ' ' + t

  if peer_id != config.echo_chat_id:
    buttons = [
      [Button.url(name, url=f"tg://user?id={chat.id}")],
    ]
    reply_to = None
    if reply_message:
      reply_to = EchoedMessage.get_origin(reply_message).message_id
    
    m = await bot.send_message(
      config.echo_chat_id,
      message, 
      buttons=buttons,
      reply_to=reply_to,
    )
    EchoedMessage.add_echo(peer_id, message, config.echo_chat_id, m)
    return
  
  if reply_message:
    res = EchoedMessage.get_origin(reply_message)
    m = await bot.send_message(
      res.chat_id,
      message,
      reply_to=res.message_id,
    )
    EchoedMessage.add_echo(config.echo_chat_id, message, res.chat_id, m)

  
@bot.on(events.Raw)
async def handler(update):
  if not isinstance(update, types.UpdateBotMessageReaction):
    return
  logger.debug(update.stringify())
  
  message = (await bot.get_messages(update.peer, ids=[update.msg_id]))[0]
  if utils.get_peer_id(message.from_id) == bot.me.id:
    res = EchoedMessage.get_origin(update.peer, update.msg_id)
  else:
    res = EchoedMessage.get_echo(update.peer, update.msg_id)
  if not res:
    return
  
  await bot(functions.messages.SendReactionRequest(
    peer=res.chat_id,
    msg_id=res.message_id,
    reaction=update.new_reactions,
    big=True,
    add_to_recent=False,
  ))
  