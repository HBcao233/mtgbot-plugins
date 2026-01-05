from telethon import events, errors
from util.log import logger
from plugin import Command
import filters
import util
import asyncio


@Command(
  'shikan',
  info='视奸群友',
)
async def _shikan(event):
  if not event.is_group:
    return

  reply_message = await event.message.get_reply_message()
  logger.info(f'shikan reply_message: {reply_message}')
  if not reply_message:
    m = await event.reply('请用命令回复一条消息')
    if not event.is_private:
      bot.schedule_delete_messages(3, event.peer_id, m.id)
    return

  sender_id = event.message.sender_id
  if not util.data.MessageData.has_chat(sender_id):
    m = await event.reply('请先私聊小派魔一次，这样小派魔才能给你发送消息')
    if not event.is_private:
      bot.schedule_delete_messages(3, event.peer_id, m.id)
    return

  sender = await event.message.get_sender()
  sender_name = getattr(sender, 'first_name', None) or getattr(sender, 'title', None)
  if t := getattr(sender, 'last_name', None):
    sender_name += ' ' + t
  sender_url = f'tg://user?id={sender.id}'
  if getattr(sender, 'username', None):
    sender_url = f'https://t.me/{sender.username}'

  chat_id = event.message.chat_id
  chat = await event.message.get_chat()
  chat_name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    chat_name += ' ' + t
  chat_url = f'https://t.me/c/{chat.id}/1'
  if getattr(chat, 'username', None):
    chat_url = f'https://t.me/{chat.username}'

  target_id = reply_message.sender_id
  target = await reply_message.get_sender()
  logger.info(f'shikan target: {target}')
  target_name = getattr(target, 'first_name', None) or getattr(target, 'title', None)
  if t := getattr(target, 'last_name', None):
    target_name += ' ' + t
  target_url = f'tg://user?id={target.id}'
  if getattr(target, 'username', None):
    target_url = f'https://t.me/{target.username}'

  with util.Data('shikan') as data:
    if f'{chat_id}' not in data:
      data[f'{chat_id}'] = {}
    if f'{target_id}' not in data[f'{chat_id}']:
      data[f'{chat_id}'][f'{target_id}'] = []
    if sender_id not in data[f'{chat_id}'][f'{target_id}']:
      data[f'{chat_id}'][f'{target_id}'].append(sender_id)

  msg = f'[{sender_name}]({sender_url}) 开始视奸 [{target_name}]({target_url})！ \nTA 在群聊 [{chat_name}]({chat_url}) 发送的图片和视频消息将会转发给您\n取消视奸请私聊小派魔输入 /shikan_list'
  logger.info(msg)
  await event.reply(msg, link_preview=False)


@bot.on(events.NewMessage)
@bot.on(events.Album)
async def _(event):
  if not event.is_group:
    return
  messages = getattr(event, 'messages', None)
  if not messages:
    if event.message.grouped_id:
      return
    messages = [event.message]
  if messages[0].sticker:
    return
  if any(not m.media for m in messages):
    return
  
  chat_id = messages[0].chat_id
  data = util.Data('shikan')
  if f'{chat_id}' not in data:
    return
  target_id = messages[0].sender_id
  if f'{target_id}' not in data[f'{chat_id}']:
    return
  
  users = data[f'{chat_id}'][f'{target_id}']
  if len(users) == 0:
    return
  
  chat = await bot.get_entity(int(chat_id))
  chat_name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    chat_name += ' ' + t
  chat_url = f'https://t.me/c/{chat.id}/{messages[0].id}'
  if getattr(chat, 'username', None):
    chat_url = f'https://t.me/{chat.username}'

  target = await bot.get_entity(int(target_id))
  target_name = getattr(target, 'first_name', None) or getattr(target, 'title', None)
  if t := getattr(target, 'last_name', None):
    target_name += ' ' + t
  target_url = f'tg://user?id={target.id}'
  if getattr(target, 'username', None):
    target_url = f'https://t.me/{target.username}'
  
  msg = f'视奸 <a href="{target_url}">{target_name}</a> 在群聊 <a href="{chat_url}">{chat_name}</a> 发的 {len(messages)} 条消息'
  logger.info(f'视奸 {target_name} ({target_id}) in {chat_name} ({chat_id}) 的 {len(messages)} 条消息')

  need_delete = []
  for i in users:  # {
    try:
      await bot.send_message(
        i,
        msg,
        link_preview=False,
        parse_mode='html',
      )
      await bot.forward_messages(
        i,
        messages=messages,
        from_peer=chat_id,
      )
    except (errors.InputUserDeactivatedError, errors.UserIsBlockedError):
      need_delete.append(i)
    except Exception:
      logger.exception(f'{i} 用户订阅的 {chat_id}-{target_id} 视奸消息发送失败')
  
  if need_delete:
    with data:
      data[f'{chat_id}'][f'{target_id}'] = [i for i in users if i not in need_delete]


@Command(
  'shikan_list',
  info='视奸列表',
  filter=filters.PRIVATE,
)
async def _(event):
  sender_id = event.message.sender_id
  shikan_list = []
  data = util.Data('shikan')
  for chat_id, i in data.items():
    for target_id, users in i.items():
      if sender_id in users:
        shikan_list.append([chat_id, target_id])

  if len(shikan_list) == 0:
    return await event.respond('您的视奸列表为空')

  msg = ['您的视奸列表如下:']
  count = 0
  for i, ai in enumerate(shikan_list):
    chat_id, target_id = ai
    chat = await bot.get_entity(int(chat_id))
    try:
      target = await bot.get_entity(int(target_id))
    except ValueError:
      with data:
        del data[f'{chat_id}'][f'{target_id}']
      continue
    
    count += 1

    chat_name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
    if t := getattr(chat, 'last_name', None):
      chat_name += ' ' + t
    chat_url = f'https://t.me/c/{chat.id}/1'
    if getattr(chat, 'username', None):
      chat_url = f'https://t.me/{chat.username}'

    target_name = getattr(target, 'first_name', None) or getattr(target, 'title', None)
    if t := getattr(target, 'last_name', None):
      target_name += ' ' + t
    target_url = f'tg://user?id={target.id}'
    if getattr(target, 'username', None):
      target_url = f'https://t.me/{target.username}'
    msg.append(
      f'{count}. <a href="{target_url}">{target_name}</a> in <a href="{chat_url}">{chat_name}</a>'
    )

    chat_id_bytes = int(chat_id).to_bytes(6, 'big', signed=True)
    target_id_bytes = int(target_id).to_bytes(6, 'big', signed=True)
    encoded = util.b64_encode(chat_id_bytes + target_id_bytes)
    msg.append(
      f'   - <a href="https://t.me/{bot.me.username}?start=shikan_cancel_{encoded}">[取消视奸]</a>'
    )
  msg = '\n'.join(msg)
  await event.respond(
    msg,
    link_preview=False,
    parse_mode='html',
  )


@Command('start', pattern=r'/start shikan_cancel_([0-9a-zA-Z_-]{16,16})')
async def _(event):
  await event.delete()
  sender_id = event.message.sender_id
  match = event.pattern_match
  encoded = match.group(1)
  decoded = util.b64_decode(encoded, True)
  chat_id = int.from_bytes(decoded[:6], 'big', signed=True)
  target_id = int.from_bytes(decoded[6:], 'big', signed=True)
  data = util.Data('shikan')
  if all(
    (
      f'{chat_id}' in data,
      f'{target_id}' in data[f'{chat_id}'],
      sender_id in data[f'{chat_id}'][f'{target_id}'],
    )
  ):
    with data:
      index = data[f'{chat_id}'][f'{target_id}'].index(sender_id)
      data[f'{chat_id}'][f'{target_id}'].pop(index)
    return await event.respond('视奸取消成功')
  await event.respond('取消失败: 该视奸不存在')
