# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com

from telethon import events, types, utils
from util.log import logger
from plugin import handler


@handler('info')
async def _(event):
  message = event.message
  if reply_message := await event.message.get_reply_message():
    message = reply_message
  logger.info(message)
  m = await event.respond(await get_info(message), reply_to=message)
  bot.schedule_delete_messages(30, m.peer_id, [m.id, event.message.id])
  raise events.StopPropagation


async def get_info(message):
  info = []

  def to_str(info):
    return '\n'.join(info)

  def indent(info, times=1):
    return ('  ' * (times - 1) + '- ' + i for i in info)

  async def get_chat_info(peer):
    chat = await bot.get_entity(peer)
    logger.info(chat)
    _type = 'Unkown'
    if isinstance(peer, types.PeerUser):
      if chat.bot:
        _type = 'Bot'
      else:
        _type = 'User'
    elif isinstance(peer, types.PeerChat) or (
      isinstance(peer, types.PeerChannel)
      and not getattr(chat, 'broadcast', False)
    ):
      _type = 'Group'
    elif isinstance(peer, types.PeerChannel):
      _type = 'Channel'

    name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
    if t := getattr(chat, 'last_name', None):
      name += ' ' + t
    info = [
      f'type: {_type}',
      f'name: `{name}`',
      f'id: `{chat.id}`',
    ]
    if getattr(chat, 'username', None):
      info.append(f'username: @{chat.username}')
    if _type == 'Group':
      info.extend(
        [
          f'megagroup: {getattr(chat, "megagroup", False)}',
          f'gigagroup: {getattr(chat, "gigagroup", False)}',
          f'forum: {getattr(chat, "forum", False)}',
        ]
      )
    return info

  info = [
    f'message_id: `{message.id}`',
  ]
  if message.message:
    text = message.message
    text_raw = None
    if message.text != message.message:
      text = message.text
      text_raw = message.message

    text = '\n```' + text + '```'
    if text_raw is None:
      info.append(f'text: {text}')
    else:
      text_raw = '\n```' + text_raw + '```'
      info.extend([f'text: {text}', f'text_raw: {text_raw}'])
  info.extend(['chat: ', to_str(indent(await get_chat_info(message.peer_id)))])
  if message.from_id:
    info.extend(
      [
        'sender: ',
        to_str(indent(await get_chat_info(message.from_id))),
      ]
    )
  if message.fwd_from:
    if message.fwd_from.from_id:
      if message.fwd_from.from_id == message.from_id:
        info.append('forward_from: =sender')
      else:
        info.extend(
          [
            'forward_from: ',
            to_str(indent(await get_chat_info(message.fwd_from.from_id))),
          ]
        )
    else:
      info.extend(
        [
          'forward_from: ',
          f'- name: {message.fwd_from.from_name}',
          '- id: Hide',
        ]
      )
  if message.media:
    _type = 'Document'
    file_id = utils.pack_bot_file_id(message.media)
    mime_type = 'application/octet-stream'
    if isinstance(message.media, types.MessageMediaPhoto):
      mime_type = 'image/jpeg'
    elif isinstance(message.media, types.MessageMediaDocument):
      mime_type = message.media.document.mime_type
    if utils.is_image(message.media):
      _type = 'Photo'
    elif utils.is_gif(message.media):
      _type = 'Gif'
    elif utils.is_video(message.media):
      _type = 'Video'
    elif utils.is_audio(message.media):
      _type = 'Audio'
    info.append('media: ')
    info.extend(
      indent(
        [
          f'type: {_type}',
          f'file_id: `{file_id}`',
          f'mime_type: {mime_type}',
        ]
      )
    )
  return to_str(info)
