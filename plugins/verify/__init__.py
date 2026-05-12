from datetime import datetime
import re
import html
from telethon import events, Button

from core import GroupConfig, GroupConfigSwitch
from util.log import logger


verify_limit_time = 60 * 5
verify_config_key = 'enter_verify'
GroupConfigSwitch.add(verify_config_key, '群聊验证')


async def approve(chat_id, user_id):
  GroupConfig.set_config(chat_id, f'verify_{user_id}', 'Verified')
  await bot.edit_permissions(
    chat_id,
    user=user_id,
    send_messages=True,
    send_media=True,
    send_stickers=True,
    send_gifs=True,
    send_games=True,
    send_inline=True,
    send_polls=True,
  )


@bot.interval(1)
async def _verify_interval():
  for res in GroupConfig.iter_config_by_prefix('verify_'):
    chat_id = res['chat_id']
    config_key = res['config_key']
    
    val = res['config_value']
    if val == 'Verified':
      continue
    
    user_id = int(config_key.removeprefix('verify_'))
    [enter_time, mid] = val.split('_')
    enter_time = int(enter_time)
    mid = int(mid)
    
    now = int(datetime.now().timestamp())
    if now - enter_time > verify_limit_time:
      try:
        await bot.delete_messages(chat_id, mid)
      except Exception:
        logger.error('删除验证消息失败')
      
      GroupConfig.remove_config(chat_id, f'verify_{user_id}')
      
      try:
        await bot.kick_participant(chat_id, user_id)
        await bot.edit_permissions(chat_id, user_id, view_messages=True)
      except Exception:
        logger.error('踢出超时验证成员失败')


@bot.on(events.ChatAction)
async def _(event):
  if not event.user_joined:
    return
  
  chat_id = event.chat_id
  config_value = GroupConfig.get_config(chat_id, verify_config_key)
  if config_value != '1':
    return
  
  chat_id = event.chat_id
  user = await event.get_user()
  user_id = user.id
  
  val = GroupConfig.get_config(chat_id, f'verify_{user_id}')
  if val == 'Verified':
    return
  
  await bot.edit_permissions(
    chat_id,
    user=user_id,
    send_messages=False,
    send_media=False,
    send_stickers=False,
    send_gifs=False,
    send_games=False,
    send_inline=False,
    send_polls=False,
  )
  
  name = ' '.join(filter(None, [
    getattr(user, 'first_name', ''),
    getattr(user, 'last_name', '')
  ]))
  nickname = f'<a href="tg://user?id={user_id}">{html.escape(name)}</a> '
  
  user_bytes = user_id.to_bytes(8, 'big', signed=True)
  buttons = [
    [
      Button.inline('✅ 我是真人', b'verify_' + user_bytes),
    ],
    [
      Button.inline('放行（管理员）', b'admin_verify_' + user_bytes),
      Button.inline('踢出（管理员）', b'kick_' + user_bytes),
    ]
  ]
  m = await event.reply(
    f'{nickname}请在 <b>{verify_limit_time}秒</b> 内点击以下按钮完成入群验证。',
    parse_mode='html',
    buttons=buttons,
  )
  now = int(datetime.now().timestamp())
  GroupConfig.set_config(chat_id, f'verify_{user_id}', f'{now}_{str(m.id)}')


verify_pattern = re.compile(b'^verify_([\x00-\xff]{8,8})$').match
admin_verify_pattern = re.compile(b'^admin_verify_([\x00-\xff]{8,8})$').match
kick_pattern = re.compile(b'^kick_([\x00-\xff]{8,8})$').match


@bot.on(events.CallbackQuery(data=verify_pattern))
async def _verify(event):
  match = event.data_match
  user_id = int.from_bytes(match.group(1), 'big')
  sender_id = event.sender_id
  if user_id != sender_id:
    await event.answer('这是别人的入群验证啦', alert=True)
    return
  
  now = int(datetime.now().timestamp())
  [enter_time, mid] = val.split('_')
  enter_time = int(enter_time)
  mid = int(mid)
  if now - enter_time > verify_limit_time:
    await event.answer('验证已超时', alert=True)
    GroupConfig.remove_config(chat_id, f'verify_{user_id}')
    await bot.kick_participant(chat_id, user_id)
    await bot.edit_permissions(chat_id, user_id, view_messages=True)
    return
  
  chat_id = event.chat_id 
  await approve(chat_id, user_id)
  
  await event.answer('✅ 验证通过', alert=True)
  await event.delete()
  

@bot.on(events.CallbackQuery(data=admin_verify_pattern))
async def _admin_verify(event):
  match = event.data_match
  user_id = int.from_bytes(match.group(1), 'big')
  sender_id = event.sender_id
  
  chat_id = event.chat_id
  sender_permissions = await bot.get_permissions(chat_id, sender_id)
  if not sender_permissions.ban_users:
    await event.answer('放行失败。你没有封禁用户权限。', alert=True)
    return
  
  await approve(chat_id, user_id)
  
  await event.answer()


@bot.on(events.CallbackQuery(data=kick_pattern))
async def _kick(event):
  match = event.data_match
  user_id = int.from_bytes(match.group(1), 'big')
  sender_id = event.sender_id
  
  chat_id = event.chat_id
  sender_permissions = await bot.get_permissions(chat_id, sender_id)
  if not sender_permissions.ban_users:
    await event.answer('踢出失败。你没有封禁用户权限。', alert=True)
    return
  
  GroupConfig.remove_config(chat_id, f'verify_{user_id}')
  await bot.kick_participant(chat_id, user_id)
  await bot.edit_permissions(chat_id, user_id, view_messages=True)
  
  await event.answer()
