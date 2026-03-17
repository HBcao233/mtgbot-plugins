# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Info    : 自动封禁名字带有 '翻墙' '免费' '直连' '直接登录' 的用户
from telethon import events, types, errors, utils
from util.log import logger
import config


@bot.on(events.ChatAction)
async def _(event):
  # logger.debug(f'ChatAction: {event}')
  # logger.info(f'ChatAction: {format_chat_action(event)}')
  if not event.action_message:
    return
  peer_id = utils.get_peer_id(event.action_message.peer_id)

  # 删除加群消息
  if isinstance(
    event.action_message.action,
    (
      types.MessageActionChatAddUser,
      types.MessageActionChatDeleteUser,
      types.MessageActionChatJoinedByLink,
    ),
  ):
    try:
      await bot.delete_messages(
        event.action_message.peer_id,
        event.action_message.id,
      )
    except errors.MessageDeleteForbiddenError:
      pass

  user = await event.get_user()
  if not user:
    return
  # 封禁死号
  if user.deleted:
    await bot.edit_permissions(
      event.action_message.peer_id,
      user,
      view_messages=False,
    )
    return
  
  name = getattr(user, 'first_name', '') or getattr(user, 'title', '')
  if t := getattr(user, 'last_name', ''):
    name += ' ' + t

  # 检查名字进行封禁
  if any(i in name for i in ('翻墙', '直连', '免费', '直接登录')):
    logger.info(f'尝试封禁用户 "{name}"({user.id})')
    await bot.edit_permissions(
      event.action_message.peer_id,
      user,
      view_messages=False,
    )
    return
  
  if username := getattr(user, 'username', ''):
    url = f'https://t.me/{username}'
  else:
    url = f'tg://user?id={peer_id}'
  
  # 欢迎新成员
  if isinstance(
    event.action_message.action,
    (
      types.MessageActionChatAddUser,
      types.MessageActionChatJoinedByLink,
    ),
  ):
    await bot.send_message(
        event.action_message.peer_id,
        f'欢迎新成员 [{name}]({url}) 入群！',
        link_preview=False,
      )


@bot.on(events.NewMessage)
async def _(event):
  """人机验证"""
  if not event.is_group:
    return
  
  if event.chat_id != -1002543592800:
    return
  
  # 删除联系人消息
  if isinstance(event.message.media, types.MessageMediaContact):
    await event.message.delete()
  
  # chat_id = event.message.chat_id
  # full_chat = await bot.get_full_chat(chat_id)
  # logger.info(full_chat)
  reply_to = event.message.reply_to
  if reply_to is None:
    return

  # logger.info(reply_to)
  # 删除回复消息不是群内的消息
  if isinstance(reply_to.reply_to_peer_id, types.PeerChannel) and reply_to.reply_to_peer_id.channel_id not in [1975979052, 2543592800]:
    await event.message.delete()


def format_chat_action(event):
  _type = ''
  for i in [
    'user_added',
    'user_joined',
    'user_left',
    'user_kicked',
    'new_pin',
    'new_photo',
    'new_title',
    'new_score',
  ]:
    if getattr(event, i, None):
      _type = i
      break
  return (
    f'ChatAction.Event({_type}'
    f', original_update={format_update(event.original_update)}'
    f', action_message={format_action_message(event.action_message)}'
    ')'
  )


def format_update(update):
  return (
    f'{type(update).__name__}('
    f'channel_id={getattr(update, "channel_id", None)}'
    f', actor_id={getattr(update, "actor_id", None)}'
    f', user_id={getattr(update, "user_id", None)}'
    ')'
  )


def format_action_message(m):
  return (
    f'{type(m).__name__}('
    f'peer_id={getattr(m, "peer_id", None)}'
    f', action={getattr(m, "action", None)}'
    f', from_id={getattr(m, "from_id", None)}'
    ')'
  )
