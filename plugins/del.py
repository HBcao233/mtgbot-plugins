from telethon import errors
from plugin import Command, Scope

import filters


@Command(
  'del',
  pattern='^/del(?!_)',
  info='删除消息',
  scope=Scope.superadmin(),
  filter=filters.SUPERADMIN,
)
async def _del(event):
  try:
    await bot.delete_messages(event.peer_id, (event.message.id, ))
  except errors.MessageDeleteForbiddenError:
    pass
  if not (reply := await event.message.get_reply_message()):
    return
  await bot.delete_messages(event.peer_id, reply.id)
