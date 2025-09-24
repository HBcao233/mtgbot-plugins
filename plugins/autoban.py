# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Info    : 自动封禁名字带有 '翻墙' '免费' '直连' '直接登录' 的用户
from telethon import events, types
from util.log import logger


@bot.on(events.ChatAction)
async def _(event):
  logger.debug(f'ChatAction: {event}')
  # logger.info(f'ChatAction: {format_chat_action(event)}')
  if not event.action_message:
    return

  if isinstance(
    event.action_message.action,
    (
      types.MessageActionChatAddUser,
      types.MessageActionChatDeleteUser,
      types.MessageActionChatJoinedByLink,
    ),
  ):
    await bot.delete_messages(
      event.action_message.peer_id,
      event.action_message.id,
    )

  user = await event.get_user()
  name = getattr(user, 'first_name', None) or getattr(user, 'title', None)
  if t := getattr(user, 'last_name', None):
    name += ' ' + t

  if any(i in name for i in ('翻墙', '直连', '免费', '直接登录')):
    logger.info(f'尝试封禁用户 "{name}"({user.id})')
    await bot.edit_permissions(
      event.action_message.peer_id,
      user,
      view_messages=False,
    )


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
