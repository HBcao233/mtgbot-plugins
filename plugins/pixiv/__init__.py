# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Info    : pixiv爬取
""".env.example
# pixiv cookie中的 PHPSESSID
pixiv_PHPSESSID =
"""

from telethon import types, events, errors, Button
import re
import asyncio
import httpx

import util
from util.log import logger
from util.progress import Progress
from plugin import Command, Scope
import filters
from .data_source import PixivClient, parse_msg, get_telegraph


cmd_header_pattern = re.compile(r'/?pid')
_p = r"""(?:^|(?#
  cmd)^(?:/?pid) ?|(?#
  url)(?:https?://)?(?:www\.)?(?:pixiv\.net/(?:member_illust\.php\?.*illust_id=|artworks/|i/))(?#
))(?#
)(\d{6,12})(?:[^a-zA-Z0-9\n].*)?$|^/pid"""
_pattern = re.compile(_p).search


class Pixiv:
  @staticmethod
  @Command(
    'pid',
    pattern=_pattern,
    info='获取p站作品 /pid <url/pid> [hide] [mark]',
    filter=filters.ONLYTEXT & filters.PRIVATE,
    scope=Scope.private(),
  )
  async def _pixiv(event, text=''):
    await Pixiv(event).main(text)

  def __init__(self, event):
    self.event = event

  async def main(self, text):
    """
    主逻辑
    """
    text = cmd_header_pattern.sub('', text).strip()
    match = _pattern(text)
    if match is None or not (pid := match.group(1)):
      return await self.event.reply(
        '用法: /pid <url/pid> [options]\n'
        '获取p站图片\n'
        '- <url/pid>: p站链接或pid\n'
        '- [hide/省略]: 省略图片说明\n'
        '- [mark/遮罩]: 给图片添加遮罩\n'
        '- [origin/原图]: 发送原图\n'
      )

    self.pid = pid
    self.options = util.string.Options(
      text, hide=('简略', '省略'), mark=('spoiler', '遮罩'), origin='原图'
    )
    logger.info(f'pid: {self.pid}, options: {self.options}')
    self.mid = await self.event.reply('请等待...')

    async with PixivClient(
      self.pid,
      timeout=60,
    ) as client:
      self.res = await client.get_pixiv()
      if isinstance(self.res, str):
        return await self.mid.edit(self.res)
      self.msg, self.tags = parse_msg(self.res, self.options.hide)
      if self.res['illustType'] == 2:
        return await self.send_animation(client)

      self.count = self.res['pageCount']
      if self.count > 10:
        return await self.send_telegraph(client)
      m = await self.send_photos(client)
      if isinstance(m, str):
        return await self.mid.edit(m)

    if not self.options.origin:
      await self.send_buttons(m)

  async def send_buttons(self, m):
    """
    发送按钮
    """
    message_id_bytes = m[0].id.to_bytes(4, 'big')
    sender_bytes = b'~' + self.event.sender_id.to_bytes(6, 'big', signed=True)
    pid_bytes = int(self.pid).to_bytes(4, 'big')
    await self.event.reply(
      '获取完成',
      buttons=[
        [
          Button.inline(
            '移除遮罩' if self.options.mark else '添加遮罩',
            b'mark_' + message_id_bytes + sender_bytes,
          ),
          Button.inline(
            '详细描述' if self.options.hide else '简略描述',
            b'pid_' + message_id_bytes + b'_' + pid_bytes + sender_bytes,
          ),
        ],
        [Button.inline('获取原图', b'pidori_' + pid_bytes)],
        [Button.inline('关闭面板', b'delete' + sender_bytes)],
      ],
    )

  async def send_animation(self, client):
    """
    发送动图
    """
    async with bot.action(self.event.peer_id, 'file'):
      data = util.Animations()
      await self.mid.edit('生成动图中...')
      if not (file := data[self.pid]):
        file = await client.get_anime()
        if not file:
          return await self.event.reply('生成动图失败')

      bar = Progress(self.mid, prefix='上传中...')
      res = await bot.send_file(
        self.event.peer_id,
        file,
        reply_to=self.event.message,
        caption=self.msg,
        parse_mode='html',
        force_document=False,
        attributes=[types.DocumentAttributeAnimated()],
        progress_callback=bar.update,
      )
      with data:
        data[self.pid] = res
      await self.mid.delete()

  async def send_telegraph(self, client):
    """
    发送telegraph
    """
    url, msg = await get_telegraph(self.res, self.tags, client, self.mid)
    if isinstance(url, dict):
      await self.mid.reply(f'生成 telegraph 失败: {url["message"]}')
      return
    await self.mid.delete()
    await bot.send_file(
      self.event.peer_id,
      caption=msg,
      parse_mode='HTML',
      file=types.InputMediaWebPage(
        url=url,
        force_large_media=True,
        optional=True,
      ),
      reply_to=self.event.message,
    )

  class GetImageError(Exception):
    pass

  async def send_photos(self, client):
    """
    发送图片
    """
    data = util.Documents() if self.options.origin else util.Photos()
    prefix = f'正在获取 p1 ~ {self.count}'
    await self.mid.edit(prefix)
    self.bar = Progress(
      self.mid,
      total=self.count,
      prefix=prefix,
    )

    try:
      tasks = [self.get_img(i, client, data) for i in range(self.count)]
      gather_task = asyncio.gather(*tasks)
      result = await gather_task
    except Pixiv.GetImageError as e:
      gather_task.cancel()
      logger.error(str(e))
      return str(e)

    if any((p := i) is None for i in result):
      return f'p{p} 获取失败'

    async with bot.action(self.event.peer_id, 'photo'):
      self.bar.set_prefix('上传中...')
      m = await bot.send_file(
        self.event.peer_id,
        result,
        caption=self.msg,
        parse_mode='html',
        reply_to=self.event.message,
        progress_callback=self.bar.update,
      )

    with data:
      for i in range(self.count):
        key = f'{self.pid}_p{i}' + ('' if self.options.origin else '_regular')
        data[key] = m[i]
    await self.mid.delete()
    return m

  async def get_img(self, i, client, data):
    """
    获取图片
    """
    key = f'{self.pid}_p{i}' + ('' if self.options.origin else '_regular')
    if file_id := data[key]:
      return util.media.file_id_to_media(file_id, self.options.mark)
    
    imgUrl = (
      self.res['urls']['original']
      if self.options.origin
      else self.res['urls']['regular']
    )
    url = imgUrl.replace('_p0', f'_p{i}')
    url = url.replace('i.pximg.net', 'i.pixiv.cat')

    try:
      logger.info(f'GET {util.curl.logless(url)}')
      img = await client.getImg(url, saveas=key, ext=True)
    except httpx.ConnectError:
      raise Pixiv.GetImageError(f'p{i} 图片获取失败')

    await self.bar.add(1)
    return await util.media.file_to_media(
      img,
      self.options.mark,
      force_document=self.options.origin,
    )


_button_pattern = re.compile(
  rb'pid_([\x00-\xff]{4,4})_([\x00-\xff]{4,4})(?:~([\x00-\xff]{6,6}))?$'
).match


@bot.on(events.CallbackQuery(pattern=_button_pattern))
async def _(event):
  """
  简略描述/详细描述 按钮回调
  """
  peer = event.query.peer
  match = event.pattern_match
  message_id = int.from_bytes(match.group(1), 'big')
  pid = int.from_bytes(match.group(2), 'big')
  sender_id = None
  if t := match.group(3):
    sender_id = int.from_bytes(t, 'big')
  # logger.info(f'{message_id=}, {pid=}, {sender_id=}, {event.sender_id=}')

  if sender_id and event.sender_id and sender_id != event.sender_id:
    participant = await bot.get_permissions(peer, event.sender_id)
    if not participant.delete_messages:
      return await event.answer('只有消息发送者可以修改', alert=True)

  message = await bot.get_messages(peer, ids=message_id)
  if message is None:
    return await event.answer('消息被删除', alert=True)

  hide = any(isinstance(i, types.MessageEntityBlockquote) for i in message.entities)

  async with PixivClient(pid) as client:
    res = await client.get_pixiv()
  if isinstance(res, str):
    return await event.answer(res, alert=True)
  msg, tags = parse_msg(res, hide)
  try:
    await message.edit(msg, parse_mode='html')
  except errors.MessageNotModifiedError:
    logger.warning('MessageNotModifiedError')

  message = await event.get_message()
  buttons = message.buttons
  text = '详细描述' if hide else '简略描述'
  index = 0
  for i, ai in enumerate(buttons[0]):
    if _button_pattern(ai.data):
      index = i
      data = ai.data
      break
  buttons[0][index] = Button.inline(text, data)

  try:
    await event.edit(buttons=buttons)
  except errors.MessageNotModifiedError:
    logger.warning('MessageNotModifiedError')
  await event.answer()


_ori_pattern = re.compile(rb'pidori_([\x00-\xff]{4,4})$').match


@bot.on(events.CallbackQuery(pattern=_ori_pattern))
async def _(event):
  """
  获取原图按钮回调
  """
  peer = event.query.peer
  match = event.pattern_match
  pid = int.from_bytes(match.group(1), 'big')
  message = await event.get_message()
  buttons = message.buttons
  buttons.pop(1)
  try:
    await event.edit(buttons=buttons)
  except errors.MessageNotModifiedError:
    logger.warning('MessageNotModifiedError')

  hide = ''
  for i in buttons[0]:
    if i.text == '详细描述':
      hide = 'hide'
      break
    if i.text == '简略描述':
      break

  await event.answer()
  event.message = message
  event.peer_id = peer
  text = f'/pid {pid} origin {hide}'
  event.pattern_match = _pattern(text)
  await Pixiv(event).main(text)
