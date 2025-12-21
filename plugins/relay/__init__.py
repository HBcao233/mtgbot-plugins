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
from util.log import logger
from .data_source import (
  echo_chat_id,
  EchoedMessage,
  isVerify,
  createVerify,
)
import util
import re 


@Command(pattern=r'^(?!/).*')
async def _forward_message(event):
  """
  转发所有消息
  """
  message = event.message
  if echo_chat_id == 0:
    return
  sender_id = event.message.sender_id
  if sender_id in util.get_blacklist():
    return
  if util.ad_pattern(event.message.message):
    logger.info(f'{sender_id} 触发屏蔽规则, 消息: {event.message.message}')
    return
  
  # echo_chat_id 主人的消息, 必须指定回复的人
  if sender_id == echo_chat_id:
    reply_message = await event.message.get_reply_message()
    if not reply_message:
      return
    res = EchoedMessage.get_origin(reply_message)
    m = await bot.send_message(
      res.chat_id,
      message,
      reply_to=res.message_id,
    )
    EchoedMessage.add_echo(echo_chat_id, message.id, res.chat_id, m.id)
    return
  
  # 别人的消息
  sender = await bot.get_entity(sender_id)
  if event.message.media and not getattr(chat, 'username', None):
    return await event.respond('未设置用户名无法发送媒体消息，请先设置用户名\n\nYou cannot send media messages without setting a username. Please set a username first.')
    
  if isVerify(sender_id):
    logger.info(f'{sender_id} 已授权')
    await forward2master(event)
    return
  logger.info('未授权, 发送确认按钮')
  message_id = event.message.id
  message_id_bytes = message_id.to_bytes(4, 'big', signed=False)
  await event.reply(
    '请点击按钮确定发送',
    buttons=Button.inline(
      '确定发送',
      b'confirm_relay_' + message_id_bytes,
    ),
  )
  return 



_button_pattern = re.compile(
  rb'confirm_relay_([\x00-\xff]{4,4})$'
).match


@bot.on(events.CallbackQuery(pattern=_button_pattern))
async def _confirm_relay(event):
  peer = event.query.peer
  sender_id = peer.user_id
  createVerify(sender_id)
  await event.delete()
  
  match = event.pattern_match
  message_id = int.from_bytes(match.group(1), 'big')
  m = await bot.get_messages(peer, ids=message_id)
  if not m:
    return
  event.message = m
  await forward2master(event)


async def forward2master(event):
  message = event.message 
  sender_id = message.sender_id
  sender = await message.get_sender()
  name = getattr(sender, 'first_name', '')
  if t := getattr(sender, 'last_name', ''):
    name += ' ' + t
  name += f' ({sender.id})'
  url = f'tg://user?id={sender.id}'
  if getattr(sender, 'username', ''):
    url = f'https://t.me/{sender.username}'
  logger.info(f'转发 {name} 的消息给主人')
  
  reply_to = None
  reply_message = await message.get_reply_message()
  if reply_message:
    reply_to = EchoedMessage.get_origin(reply_message).message_id

  m = await bot.send_message(
    echo_chat_id,
    message,
    buttons=Button.url(name, url),
    reply_to=reply_to,
  )
  EchoedMessage.add_echo(sender_id, message.id, echo_chat_id, m.id)


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
