from telethon import events, Button
import os 
import re 

import util
import filters
from plugin import Command, Scope, import_plugin
from .data_source import add_glow_watermark


mask = import_plugin('mask')
try:
  hosting = import_plugin('hosting')
except ModuleNotFoundError:
  hosting = None
_get_buttons = mask.DelayMedia.get_buttons

def get_buttons(self, event):
  buttons = _get_buttons(self, event)
  if len(self.messages) == 1 and self.messages[0].photo:
    mid = self.messages[0].id.to_bytes(4, 'big')

    text = '添加水印'
    buttons.append([
      Button.inline(text, data=b'ai_watermark_' + mid),
    ])
  return buttons


mask.DelayMedia.get_buttons = get_buttons


@Command(
  'ai_watermask',
  info='添加AI生成水印',
  filter=filters.PRIVATE,
  scope=Scope.private(),
)
async def _ai_watermask(event):
  message = None
  if event.message.file:
    message = event.message
  if (
    not (message or (message := await event.message.get_reply_message()))
    or not message.file
  ):
    m = await event.reply('请用命令回复一张图片')
    if not event.is_private:
      bot.schedule_delete_messages(3, event.peer_id, m.id)
    return
  
  img = await get_image(message)
  if not img:
    await event.reply('回复的文件不是图片')
    return
  
  text = 'AI生成'
  parts = event.raw_text.split(maxsplit=1)
  if len(parts) > 1:
    text = parts[1]
  
  filename = os.path.basename(img)
  name, ext = os.path.splitext(filename)
  output = util.getCache(f'{name}_watermask{ext}')
  add_glow_watermark(
    image_path=img,
    text=text,
    output_path=output,
  )
  
  await bot.send_file(
    event.message.chat_id,
    output,
    reply_to=message.id,
  )


button_pattern = re.compile(
  rb'^ai_watermark_([\x00-\xff]{4,4})$'
).match


@bot.on(events.CallbackQuery(pattern=button_pattern))
async def add_merge_button(event):
  peer = event.query.peer
  match = event.pattern_match
  # btn_message = await event.get_message()
  
  mid = int.from_bytes(match.group(1), 'big')
  message = await bot.get_messages(peer, ids=mid)
  event.message = message
  event.raw_text = '/ai_watermark'
  await _ai_watermask(event)
  
  await event.answer()
  


async def get_image(message, _ext='jpg'):
  file = message.file
  ext = file.ext
  mime_type = file.mime_type
  if 'image' not in mime_type and 'video' not in mime_type:
    return

  if message.photo:
    _id = message.photo.id
  elif message.document:
    _id = message.document.id
  name = f'{_id}{ext}'
  img = util.getCache(name)
  if not os.path.isfile(img):
    await message.download_media(file=img)
  img = await util.media.to_img(img, _ext)

  return img

