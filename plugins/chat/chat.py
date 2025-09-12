from telethon import errors
from google import genai
from google.genai import types
from datetime import datetime
import openai
import json
import re
import time


import util
from util.log import logger
from .data_source import (
  Sessions,
  system_prompt,
  clean_html,
  get_image,
  gemini_token,
  api_url,
  api_key,
  model,
  max_tokens,
)


progress_chars = '-/-|-\\'


class Chat:
  def __init__(self, event):
    self.event = event
    # 获取调用者 ID
    self.user_id = event.sender_id
    self.user_message = ''
    parts = self.event.raw_text.split(maxsplit=1)
    if len(parts) > 1:
      self.user_message = parts[1]
    self.raw_text = self.user_message or ''
    self.mid = None
    self.reply = None
    self.photo = None
    self.photo_caption = None
    self.inline_mode = event.message is None
    self.nickname = ''

  async def main(self):
    # 如果没输入内容，提示并退出
    if not self.user_message:
      await self.event.respond(
        '❗️ 请输入要对小派魔说的话，例如 `/chat 你是谁`。插件作者：@nyan2022。后端由Deepseek R1模型支持'
      )
      return

    if not self.event.is_private:
      chat = await bot.get_entity(self.user_id)
      name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
      if t := getattr(chat, 'last_name', None):
        name += ' ' + t
      self.nickname = f'<a href="tg://user?id={self.user_id}">{name}</a> '

    if self.event.message:
      self.reply = await self.event.message.get_reply_message()
    if gemini_token and self.reply and self.reply.photo:
      ok = await self.parse_reply()
      if not ok:
        return

    logger.info(self.user_message)
    sessions = Sessions(self.user_id)
    history = sessions.current_historys
    if len(history) > 10:
      history = history[0:1] + history[-9:]
    self.msgs = (
      [{'role': 'system', 'content': system_prompt}]
      + history
      + [{'role': 'user', 'content': self.user_message}]
    )
    if self.inline_mode:
      self.resp = self.event
    elif self.mid:
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
      except openai.APITimeoutError:
        await self.request_timeeout()
      except Exception as e:
        logger.exception('Chat API 调用失败')
        await self.request_fail(e)
        return

    with sessions:
      sessions.add_history(
        [
          {'role': 'user', 'content': self.user_message},
          {'role': 'assistant', 'content': self.content.strip()},
        ]
      )
    clean_html()

  async def parse_reply(self):
    self.mid = await self.event.respond(
      '小派魔正在查看图片中...', reply_to=self.reply.id
    )
    try:
      await self.get_photo()
    except Exception:
      logger.error('调用gemini识图失败', exc_info=1)
      await self.mid.edit('调用gemini识图失败，可能是限额了或者使用了违规图片')
      return False

    if not self.photo_caption:
      await self.mid.edit('调用gemini识图失败，可能是限额了或者使用了违规图片')
      return False
    self.user_message = json.dumps(
      [
        {'type': 'image', 'image': self.photo_caption},
        {'type': 'text', 'text': self.user_message},
      ],
      ensure_ascii=0,
    )
    return True

  async def get_photo(self):
    self.photo = await get_image(self.reply)
    with open(self.photo, 'rb') as f:
      img_bytes = f.read()
    await self.get_photo_caption(img_bytes)

  async def get_photo_caption(self, img_bytes):
    client = genai.Client(api_key=gemini_token)
    r = client.models.generate_content(
      model='gemini-2.0-flash',
      contents=[
        types.Part.from_bytes(
          data=img_bytes,
          mime_type='image/jpeg',
        ),
        '请用中文描述这张图片。',
      ],
      config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        system_instruction="""请以总-分-总格式描述图片（总述图片大致内容-分开具体描述角色样貌特征、背景特征等-总结图片色调背景氛围感受等），例如：
这张图片描绘了两个卡通化的裸体猫女。

左边的猫女有橙色的头发，戴着猫耳朵，眼睛是绿色的。她微微一笑，脸颊泛红，似乎正在出汗或流口水。她举起一只手臂，用另一只手略微遮住自己的胸部。
右边的猫女头发是蓝色的，同样戴着猫耳朵，眼睛是绿色的。她伸出舌头，脸颊泛红。她和她的伴侣一样，也举起一只手臂，并用另一只手略微遮住自己的胸部。

这两个角色彼此靠近地站立，似乎在触碰。图片使用了柔和的粉色和蓝色色调，并且具有梦幻般的氛围。背景是纯白色，这有助于将注意力集中在这两个角色身上。""",
        safety_settings=[
          types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
          ),
          types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
          ),
          types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
          ),
          types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
          ),
        ],
      ),
    )
    self.photo_caption = r.text

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
      text = self.parse_display(self.reasoning_content, self.content)[:1000]
      msg = f'{type(e).__name__}：{e}'
      if getattr(e, 'code', '') == 'data_inspection_failed':
        msg = '内容审查错误: 请使用 /chat_clear 清除聊天记录后重试'
      await self.resp.edit(
        text + f'\n\n⚠️ > 与 Chat API 通信出现错误 - {msg}',
        parse_mode='html',
      )
    except (errors.MessageEmptyError, errors.MessageNotModifiedError):
      pass

  async def request_openai(self):
    client = openai.AsyncOpenAI(
      base_url=f'{api_url}',
      api_key=f'{api_key}',
      timeout=openai.Timeout(60.0, connect=60.0),
    )

    self.content = ''
    self.reasoning_content = ''
    self.contents = []
    self.reasoning_contents = []
    self.first_piece = True
    self.last_edit = time.monotonic() - 5
    self.count = 0
    self.now = 0

    g = self.interval()
    # 流式调用
    stream = await client.chat.completions.create(
      model=f'{model}',
      messages=self.msgs,
      max_tokens=max_tokens,
      stream=True,
      temperature=0.6,
      top_p=0.7,
    )
    async for chunk in stream:
      # logger.debug(chunk)
      if not chunk.choices:
        if self.content != '' and not self.content.endswith('\n'):
          self.content += '\n'
        self.content += '非常抱歉，作为一个AI助手，我无法回答该问题，请使用 /chat_clear 清除聊天记录后重试'
        break

      delta = chunk.choices[0].delta
      logger.debug(f'[CHAT] delta: {delta}')
      if not delta:
        if hasattr(chunk.choices[0], 'message'):
          self.content += chunk.choices[0].message['content']
          break
        continue

      if c := getattr(delta, 'content', ''):
        self.content += c
      elif rc := getattr(delta, 'reasoning_content', ''):
        self.reasoning_content += rc
      else:
        continue

      self.now = time.monotonic()
      if self.now - self.last_edit >= next(g):
        await self.send_piece()

    # 最终补刀
    await self.send_piece()

    if not self.inline_mode:
      if self.content:
        self.contents.append(self.content)
        self.content = ''.join(self.contents)
      if self.reasoning_content:
        self.reasoning_contents.append(self.reasoning_content)
        self.reasoning_content = ''.join(self.reasoning_contents)

    file = self.summon_html(self.reasoning_content, self.content)
    if not self.first_piece and not self.inline_mode:
      await bot.send_file(self.event.chat_id, file=file)
    elif self.inline_mode:
      m = None if self.first_piece else f'$ {self.raw_text}\n(内容过长已输出至文件)'
      await self.resp.edit(
        m,
        parse_mode='html',
        file=file,
      )

  def parse_display(self, reasoning_content, content):
    display = ''
    if self.first_piece:
      m = model.split('/')[-1]
      if self.photo:
        m = f'gemini-2.0-flash + {m} 多模态'
      else:
        m += ' 模型'
      display = f'$ {self.nickname}{self.raw_text} ({m})\n'

    expandable = ''
    if content:
      expandable = ' expandable'
    display += f'<blockquote{expandable}>内心OS\n{reasoning_content}</blockquote>'
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

  def summon_html(self, reasoning_content, content):
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
        + self.parse_display(reasoning_content, content)
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
    if self.first_piece or not self.inline_mode:
      await self.resp.edit(
        self.parse_display(self.reasoning_content, self.content),
        parse_mode='html',
      )
      return

    file = self.summon_html(self.reasoning_content, self.content)
    await self.resp.edit(
      f'$ {self.raw_text}\n(内容过长已输出至文件)',
      parse_mode='html',
      file=file,
    )

  async def piece_too_loog(self):
    self.first_piece = False
    if self.inline_mode:
      return
    if self.content:
      t = 0
      if len(self.contents) == 0:
        t = len(self.reasoning_content)
        if len(self.reasoning_contents) != 0:
          t = len(self.reasoning_contents[-1])
      self.contents.append(self.content[: 4096 - t])
      self.content = self.content[4096 - t :]
    else:
      self.reasoning_contents.append(self.reasoning_content[:4096])
      self.reasoning_content = self.reasoning_content[4096:]

    self.resp = await self.resp.respond(
      self.parse_display(self.reasoning_content, self.content),
      parse_mode='html',
      reply_to=self.resp,
    )
    self.last_edit = self.now
