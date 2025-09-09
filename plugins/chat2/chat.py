from telethon import errors
from datetime import datetime
import httpx
import json
import re
import time
import base64

import util
from util.log import logger
from .data_source import (
  load_history,
  save_history,
  system_prompt,
  clean_html,
  get_image,
  api_url,
  api_key,
  model,
)


progress_chars = '-/-|-\\'
gheaders = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer',
  'HTTP-Referer': 'https://ultimumai.com',
  'X-Title': 'UltimumAI',
  'Referer': 'https://ultimumai.com',
  'origin': 'https://ultimumai.com',
  'cookie': f'__Secure-better-auth.session_token={api_key}',
}


class Chat:
  def __init__(self, event):
    self.event = event
    # 获取调用者 ID
    self.user_id = event.sender_id
    self.user_message = []
    self.raw_text = ''
    parts = self.event.raw_text.split(maxsplit=1)
    if len(parts) > 1:
      self.raw_text = parts[1]

    self.mid = None
    self.reply = None
    self.photo = None
    self.image_url = None
    self.nickname = ''

  async def main(self):
    # 如果没输入内容，提示并退出
    if not self.raw_text:
      await self.event.respond('❗️ 请输入要对小派魔说的话，例如 `/chat2 你是谁`')
      return

    if not self.event.is_private:
      chat = await bot.get_entity(self.user_id)
      name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
      if t := getattr(chat, 'last_name', None):
        name += ' ' + t
      self.nickname = f'<a href="tg://user?id={self.user_id}">{name}</a> '

    if self.event.message:
      self.reply = await self.event.message.get_reply_message()
    if self.reply and self.reply.photo:
      await self.parse_reply()

    if self.image_url:
      self.user_message = [{'type': 'image_url', 'image_url': {'url': self.image_url}}]
    self.user_message.append({'type': 'text', 'text': self.raw_text})

    logger.info(self.raw_text)
    history = load_history(self.user_id)
    self.msgs = (
      [{'role': 'system', 'content': [{'type': 'text', 'text': system_prompt}]}]
      + history
      + [{'role': 'user', 'content': self.user_message}]
    )
    if self.mid:
      self.resp = self.mid
    else:
      reply_to = self.event.message.id
      if self.reply:
        reply_to = self.reply.id
      self.resp = await self.event.respond(
        '派魔正在思考中...',
        reply_to=reply_to,
      )

    for i in range(3):
      try:
        await self.request_openai()
        break
      except httpx.TimeoutException:
        await self.request_timeeout()
      except Exception as e:
        logger.exception('Chat API 调用失败')
        await self.request_fail(e)
        return

    history = history + [
      {'role': 'user', 'content': self.user_message},
      {'role': 'assistant', 'content': self.content.strip()},
    ]
    save_history(self.user_id, history)
    clean_html()

  async def parse_reply(self):
    self.mid = await self.event.respond(
      '小派魔正在查看图片中...', reply_to=self.reply.id
    )
    self.photo = await get_image(self.reply)
    with open(self.photo, 'rb') as f:
      img_bytes = f.read()
    img_data = base64.b64encode(img_bytes).decode()
    self.image_url = f'data:image/jpeg;base64,{img_data}'

  def interval(self):
    while True:
      if 0 <= self.count < 5:
        yield self.count + 1
      else:
        yield 5

  async def request_timeeout(self):
    try:
      await self.resp.edit(
        self.parse_display('', '⚠️ > 与 Chat API 通信出现超时，正在重试...'),
        parse_mode='html',
      )
    except (errors.MessageEmptyError, errors.MessageNotModifiedError):
      pass

  async def request_fail(self, e):
    try:
      text = self.parse_display(self.content)[:1000]
      msg = f'{type(e).__name__}：{e}'
      if getattr(e, 'code', '') == 'data_inspection_failed':
        msg = '内容审查错误: 请使用 /clear 清除聊天记录后重试'
      await self.resp.edit(
        text + f'\n\n⚠️ > 与 Chat API 通信出现错误 - {msg}',
        parse_mode='html',
      )
    except (errors.MessageEmptyError, errors.MessageNotModifiedError):
      pass

  async def request_openai(self):
    self.content = ''
    self.contents = []
    self.first_piece = True
    self.last_edit = time.monotonic() - 5
    self.count = 0
    self.now = 0

    g = self.interval()
    async with util.curl.Client(
      timeout=httpx.Timeout(60.0, connect=60.0),
    ) as client:
      async with client.stream(
        'POST',
        api_url,
        headers=gheaders,
        data=json.dumps(
          {
            'messages': self.msgs,
            'model': model,
            'usage': {
              'include': True,
            },
            'stream': True,
          }
        ),
      ) as r:
        async for chunk in r.aiter_lines():
          # logger.info(chunk)
          if '"error"' in chunk:
            raise Exception('请求失败')
          if not chunk.startswith('data: '):
            continue
          chunk = chunk[6:]
          if chunk == '[DONE]':
            break
          try:
            choices = json.loads(chunk.replace('data: ', '')).get('choices', [])
            if not choices:
              if self.content != '' and not self.content.endswith('\n'):
                self.content += '\n'
              self.content += '非常抱歉，作为一个AI助手，我无法回答该问题，请使用 /clear 清除聊天记录后重试'
              break
            delta = choices[0].get('delta', {})
            if not delta:
              if choices[0].get('message'):
                self.content += choices[0]['message']['content']
                break
              continue

            if c := delta.get('content', ''):
              self.content += c
            else:
              continue
          except json.JSONDecodeError:
            logger.warning(f'json解析失败, {chunk}')

          self.now = time.monotonic()
          if self.now - self.last_edit >= next(g):
            await self.send_piece()

    # 最终补刀
    await self.send_piece()
    if self.content:
      self.contents.append(self.content)
      self.content = ''.join(self.contents)

    file = self.summon_html(self.content)
    if not self.first_piece:
      await bot.send_file(self.event.chat_id, file=file)

  def parse_display(self, content):
    display = ''
    if self.first_piece:
      m = model.split('/')[-1].replace(':free', '')
      display = f'$ {self.nickname}{self.raw_text} ({m} 模型)\n'

    if content:
      display += content
    else:
      display += (
        f'小派魔正在思考中... {progress_chars[self.count % len(progress_chars)]}'
      )

    display = re.sub(
      r'```(\w+?)\n([\s\S]*?)```',
      r'<pre><code class="language-\1">\2</code></pre>',
      display,
    )
    display = re.sub(r'```([\s\S]*?)```', r'<pre><code>\1</code></pre>', display)
    display = re.sub(r'`([\s\S]*?)`', r'<code>\1</code>', display)
    display = re.sub(r'\*\*([\s\S]*?)\*\*', r'<b>\1</b>', display)
    display = re.sub(r'\[([\s\S]*?)\]\(([\s\S]*?)\)', r'<a href="\2">\1</a>', display)

    return display

  def summon_html(self, content):
    file = util.file.getCache(
      f'output_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.html'
    )
    with open(file, 'w') as f:
      f.write(
        """<html><meta charset="utf-8"><title>小派魔的回答</title><head><style>
  body {
  width: 100vw;
  margin: 2px;
  word-wrap: break-word;
  white-space: pre-wrap;
  margin-top: 20px;
  margin-bottom: 100px;
  }
  blockquote {
  position: relative;
  margin: 1.5em 10px;
  padding: 0.5em 10px;
  border-left: 10px solid #ccc;
  background-color: #f9f9f9;
  }
  blockquote::after {
  content: "\\201D";
  font-family: Georgia, serif;
  font-size: 60px;
  font-weight: bold;
  color: #ccc;
  position: absolute;
  right: 10px;
  top:5px;
  }
  </style></head><body>"""
        + self.parse_display(content)
        + '</body></html>'
      )
    return file

  async def send_piece(self):
    try:
      await self.piece()
    except (errors.MessageEmptyError, errors.MessageNotModifiedError):
      pass
    except (errors.MessageTooLongError, errors.MediaCaptionTooLongError):
      await self.piece_too_loog()
    else:
      self.last_edit = self.now
      self.count += 1

  async def piece(self):
    if self.first_piece:
      await self.resp.edit(
        self.parse_display(self.content),
        parse_mode='html',
      )
      return

    file = self.summon_html(self.content)
    await self.resp.edit(
      f'$ {self.raw_text}\n(内容过长已输出至文件)',
      parse_mode='html',
      file=file,
    )

  async def piece_too_loog(self):
    self.first_piece = False
    if self.content:
      self.contents.append(self.content[:4096])
      self.content = self.content[4096:]

    self.resp = await self.resp.respond(
      self.parse_display(self.content),
      parse_mode='html',
      reply_to=self.resp,
    )
    self.last_edit = self.now
