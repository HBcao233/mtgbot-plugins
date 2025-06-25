from telethon import types, errors
import os.path
from asyncio import CancelledError

import util
from util import logger
from plugin import Command, Scope
from util.progress import Progress
import filters
from .data_source import video2gif, tgs2ext, video2ext


@Command(
  'gif',
  info='视频转gif',
  filter=filters.PRIVATE & filters.ONLYTEXT,
  scope=Scope.private(),
)
async def _gif(event):
  if not (reply_message := await event.message.get_reply_message()):
    return await event.reply('请用命令回复一条消息')
  logger.debug(reply_message)
  mime_type = reply_message.media.document.mime_type
  if 'video' not in mime_type and mime_type != 'application/x-tgsticker':
    return await event.reply('该消息不包含视频或动态贴纸')

  options = util.string.Options(event.message.message, force=(), nocache=())
  attributes = reply_message.media.document.attributes
  a = None
  _ext = '.cache'
  for i in attributes:
    if isinstance(i, types.DocumentAttributeVideo):
      a = i
    if isinstance(i, types.DocumentAttributeFilename):
      _ext = os.path.splitext(i.file_name)[-1]

  if a and a.duration > 60:
    await event.reply('这个视频太长了')
  if mime_type == 'image/gif':
    return await event.reply('该消息已经是 gif 格式了')

  mid = await event.reply('转换中...')
  try:
    bar = Progress(mid)
    data = util.Documents()
    document_id = reply_message.media.document.id
    key = f'{document_id}_to_gif'
    if options.nocache or not (file := data[key]):
      img = util.getCache(str(document_id) + _ext)
      if not os.path.isfile(img) or os.path.getsize(img) == 0:
        bar.set_prefix('下载中...')
        await reply_message.download_media(file=img, progress_callback=bar.update)

      if mime_type == 'application/x-tgsticker':
        res = await tgs2ext(img, 'gif')
      else:
        res = await video2gif(img, mid)
      if not res:
        return await mid.edit('转换失败')

      file = open(res, 'rb')

    bar.set_prefix('发送中...')
    try:
      res = await bot.send_file(
        entity=event.message.peer_id,
        reply_to=event.message,
        file=file,
        force_document=True,
        attributes=[types.DocumentAttributeAnimated()],
        progress_callback=bar.update,
      )
    except errors.FloodWaitError as e:
      logger.error('遇到 FloodWaitError, 请在 %s秒后重试', e.seconds)
      return await mid.edit('遇到 FloodWaitError, 请在 %s秒后重试' % e.seconds)

    await mid.delete()
    with data:
      data[key] = res
  except CancelledError as e:
    await mid.edit('任务取消')
    raise e


async def _video_convert(event, ext='mp4'):
  if not (reply_message := await event.message.get_reply_message()):
    return await event.reply('请用命令回复一条消息')
  logger.debug(reply_message)
  mime_type = reply_message.media.document.mime_type
  if 'video' not in mime_type and mime_type not in [
    'application/x-tgsticker',
    'image/gif',
  ]:
    return await event.reply('该消息不包含视频或动态贴纸')

  options = util.string.Options(event.message.message, force=())
  attributes = reply_message.media.document.attributes
  is_sticker = False
  _ext = '.cache'
  for i in attributes:
    if isinstance(i, types.DocumentAttributeSticker):
      is_sticker = True
      break
    if isinstance(i, types.DocumentAttributeFilename):
      _ext = os.path.splitext(i.file_name)[-1]

  if not options.force and not is_sticker and mime_type == 'video/' + ext:
    return await event.reply(f'该消息已经是 {ext} 格式了')

  mid = await event.reply('转换中...')
  bar = Progress(mid)
  data = util.Videos()
  document_id = reply_message.media.document.id
  key = f'{document_id}_to_{ext}'
  thumb = None
  attributes = None
  if not (file := data[key]):
    img = util.getCache(str(document_id) + _ext)
    if not os.path.isfile(img):
      bar.set_prefix('下载中...')
      await reply_message.download_media(file=img, progress_callback=bar.update)

    if mime_type == 'application/x-tgsticker':
      img = await tgs2ext(img, ext)
      if not img:
        return await mid.edit('转换失败')
    else:
      res = await video2ext(img, ext, mid)
      if not res:
        return await mid.edit('转换失败')

    file, duration, w, h, thumb = util.videoInfo(res)
    attributes = [
      types.DocumentAttributeVideo(
        duration=duration, w=int(w), h=int(h), supports_streaming=True
      ),
      types.DocumentAttributeFilename(file_name=f'{document_id}.{ext}'),
    ]

  bar.set_prefix('发送中...')
  res = await bot.send_file(
    entity=event.message.peer_id,
    reply_to=event.message,
    file=file,
    supports_streaming=True,
    thumb=thumb,
    attributes=attributes,
    progress_callback=bar.update,
  )
  logger.debug('result: %s', res)
  await mid.delete()
  with data:
    data[key] = res


@handler('mp4', info='动图转mp4')
async def _mp4(event):
  await _video_convert(event, 'mp4')


@handler('webm', info='视频转webm')
async def _webm(event):
  await _video_convert(event, 'webm')
