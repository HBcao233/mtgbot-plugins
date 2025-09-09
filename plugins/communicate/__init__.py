# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : 传话机器人
""".env.example
# 转发给哪个用户的 id
echo_chat_id =
"""

from telethon import events, types, utils, functions, Button
from plugin import Command
from util import logger
from .data_source import (
  echo_chat_id,
  EchoedMessage,
)


@Command(pattern=r'^(?!/).*')
async def _forward_message(event):
  """
  转发所有消息
  """
  message = event.message
  if echo_chat_id == 0:
    return

  peer_id = utils.get_peer_id(event.message.peer_id)
  chat = await bot.get_entity(event.message.peer_id)
  name = getattr(chat, 'first_name', '')

  reply_message = await event.message.get_reply_message()
  if t := getattr(chat, 'last_name', ''):
    name += ' ' + t

  url = f'tg://user?id={chat.id}'
  if getattr(chat, 'username', ''):
    url = f'https://t.me/{chat.username}'

  # 其他人的消息
  if peer_id != echo_chat_id:
    buttons = [
      [Button.url(name, url)],
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

  # echo_chat_id 的消息
  if reply_message:
    res = EchoedMessage.get_origin(reply_message)
    m = await bot.send_message(
      res.chat_id,
      message,
      reply_to=res.message_id,
    )
    EchoedMessage.add_echo(echo_chat_id, message.id, res.chat_id, m.id)


@bot.on(events.Raw)
async def _forward_reaction(update):
  """
  转发表情回应
  """
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
