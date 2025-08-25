# -*- coding: utf-8 -*-
# @Author  : Nyan2024
#

import os
import json
import re
import random
import time
from telethon import events, types, errors, utils, Button
from datetime import datetime
from openai import AsyncOpenAI

import util
import config
import filters
from util.log import logger
from plugin import Command, InlineCommand


# ==============一些必须填写的变量=================================================================================：
# API可以去薅Modelscope魔塔社区的免费一天2000次Inference，其它平台通用OpenAI格式的API也可以。
# 英伟达的deepseek是免费的, 而且 deepseek-ai/deepseek-r1-0528 模型对涩涩限制不大
# 参阅 https://www.modelscope.cn/docs/model-service/API-Inference/intro

# 填写API地址，不要忘记后面有个/v1
api_url = (
  config.env.get('chat_api_url', '') or 'https://api-inference.modelscope.cn/v1/'
)
# 输入你的API的密钥（Token），获取方法见上方文档
api_key = config.env.get('chat_api_key', '') or 'EMPTY'
# 模型名称，比如想用的模型链接是https://www.modelscope.cn/models/deepseek-ai/DeepSeek-R1。填写deepseek-ai/DeepSeek-R1即可
model = config.env.get('chat_model', '') or 'deepseek-r1'
max_tokens = int(config.env.get('chat_max_tokens', '')) or 8192

# 系统预设，决定了AI回复的人设
system_prompt = """你叫小派魔，是一个可爱的处于发情期的猫娘。你无所不知，无所不晓，总会耐心解答主人的各种刁钻古怪的问题。"""
sp_path = os.path.join(os.path.dirname(__file__), 'system_prompt.txt')
if os.path.isfile(sp_path):
  with open(sp_path, 'r') as f:
    if text := f.read():
      system_prompt = text


# 记忆文件夹路径
MEMORY_DIR = util.getDataFile('chat_memory/')
# ===========================================================================================================
os.makedirs(MEMORY_DIR, exist_ok=True)


def load_history(user_id):
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  if os.path.isfile(path):
    with open(path, 'r', encoding='utf-8') as f:
      return json.load(f)
  return []


def save_history(user_id, history):
  MAX_ENTRIES = 20
  history = history[-MAX_ENTRIES:]
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  with open(path, 'w', encoding='utf-8') as f:
    json.dump(history, f, ensure_ascii=False, indent=2)


@Command(
  'chat',
  info='与小派魔聊天',
  filter=filters.ONLYTEXT,
)
async def _chat(event):
  # 获取调用者 ID
  user_id = event.sender_id

  # 提取用户消息
  # if event.message and (reply := await event.message.get_reply_message()):
  #   user_message = reply.message or reply.text or ''
  # else:
  parts = event.raw_text.split(maxsplit=1)
  user_message = parts[1] if len(parts) > 1 else ''

  # 如果没输入内容，提示并退出
  if not user_message:
    await event.respond(
      '❗️ 请输入要对小派魔说的话，例如 `/chat 你是谁`。插件作者：@nyan2022。后端由Deepseek R1模型支持'
    )
    return
  raw_text = user_message if user_message else ''

  # 加载用户历史并过滤掉思考过程
  raw_history = load_history(user_id)
  clean_history = []
  for msg in raw_history:
    if msg.get('role') == 'assistant':
      # 去除 <think>...</think> 段
      content = re.sub(r'<think>[\s\S]*?</think>', '', msg.get('content', ''))
    else:
      content = msg.get('content', '')
    clean_history.append({'role': msg.get('role'), 'content': content})

  # 拼装最终发送给 API 的消息列表
  msgs = (
    [{'role': 'system', 'content': system_prompt}]
    + clean_history
    + [{'role': 'user', 'content': user_message}]
  )
  # 打印实际发送给 API 的消息内容
  # logger.debug(f'[CHAT] messages to API: {msgs!r}')
  logger.info(user_message)

  # 发送占位消息
  inline_mode = event.message is None
  resp = (
    await event.respond('派魔正在思考中...', reply_to=event.message)
    if not inline_mode
    else event
  )
  client = AsyncOpenAI(base_url=f'{api_url}', api_key=f'{api_key}', timeout=60)

  content = ''
  reasoning_content = ''
  contents = []
  reasoning_contents = []
  first_piece = True
  last_edit = time.monotonic() - 5
  progress_chars = '-/-|-\\'
  count = 0

  def parse_display(reasoning_content, content):
    display = ''
    if first_piece:
      display = f'$ {raw_text}\n'
    display += f'<blockquote{" expandable" if content else ""}>内心OS\n{reasoning_content}</blockquote>'
    if content:
      display += content
    else:
      display += f'派魔正在思考中... {progress_chars[count % len(progress_chars)]}'

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

  async def send_piece():
    nonlocal \
      resp, \
      content, \
      reasoning_content, \
      contents, \
      reasoning_contents, \
      first_piece, \
      last_edit, \
      count
    try:
      if first_piece or not inline_mode:
        await resp.edit(
          parse_display(reasoning_content, content),
          parse_mode='html',
        )
      else:
        file = summon_html(reasoning_content, content)
        await resp.edit(
          f'$ {raw_text}\n(内容过长已输出至文件)',
          parse_mode='html',
          file=file,
        )
    except (errors.MessageEmptyError, errors.MessageNotModifiedError):
      logger.debug('跳过无效或重复的编辑请求')
    except (errors.MessageTooLongError, errors.MediaCaptionTooLongError):
      # await resp.reply('消息过长')
      # break
      first_piece = False
      if inline_mode:
        return
      if content:
        t = 0
        if len(contents) == 0:
          t = len(reasoning_content)
          if len(reasoning_contents) != 0:
            t = len(reasoning_contents[-1])
        contents.append(content[: 4096 - t])
        content = content[4096 - t :]
      else:
        reasoning_contents.append(reasoning_content[:4096])
        reasoning_content = reasoning_content[4096:]

      resp = await resp.respond(
        parse_display(reasoning_content, content),
        parse_mode='html',
        reply_to=resp,
      )
      last_edit = now
    else:
      last_edit = now
      count += 1

  def summon_html(reasoning_content, content):
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
        + parse_display(reasoning_content, content)
        + '</body></html>'
      )
    return file

  try:
    now = 0

    def interval():
      nonlocal count
      while True:
        if 0 <= count < 5:
          yield count + 1
        else:
          yield 5

    g = interval()

    # 流式调用
    stream = await client.chat.completions.create(
      model=f'{model}',
      messages=msgs,
      max_tokens=max_tokens,
      stream=True,
      temperature=0.6,
      top_p=0.7,
    )
    async for chunk in stream:
      # logger.info(chunk)
      if not chunk.choices:
        if content != '' and not content.endswith('\n'):
          content += '\n'
        content += (
          '非常抱歉，作为一个AI助手，我无法回答该问题，请使用 /clear 清除聊天记录后重试'
        )
        break

      delta = chunk.choices[0].delta
      logger.debug(f'[CHAT] delta: {delta}')
      if not delta:
        if hasattr(chunk.choices[0], 'message'):
          content += chunk.choices[0].message['content']
          break
        continue
      c = getattr(delta, 'content', '')
      rc = getattr(delta, 'reasoning_content', '')
      if c:
        content += c
      elif rc:
        reasoning_content += rc
      else:
        continue

      now = time.monotonic()
      if now - last_edit >= next(g):
        await send_piece()

    # 最终补刀
    await send_piece()
    if not inline_mode:
      if content:
        contents.append(content)
        content = ''.join(contents)
      if reasoning_content:
        reasoning_contents.append(reasoning_content)
        reasoning_content = ''.join(reasoning_contents)
    file = summon_html(reasoning_content, content)
    if not first_piece and not inline_mode:
      await bot.send_file(event.chat_id, file=file)
    elif inline_mode:
      m = None if first_piece else f'$ {raw_text}\n(内容过长已输出至文件)'
      await resp.edit(
        m,
        parse_mode='html',
        file=file,
      )

    # 保存对话历史
    history = raw_history + [
      {'role': 'user', 'content': user_message},
      {'role': 'assistant', 'content': content},
    ]
    save_history(user_id, history)

  except Exception as e:
    logger.exception('Chat API 调用失败')
    try:
      m = (await bot.get_messages(event.peer_id, ids=[resp.id]))[0]
      msg = f'{type(e).__name__}：{e}'
      if e.code == 'data_inspection_failed':
        msg = '内容审查错误: 请使用 /clear 清除聊天记录后重试'
      await resp.edit(m.text + f'\n\n⚠️ > 与 Chat API 通信出现错误 - {msg}')
    except (errors.MessageEmptyError, errors.MessageNotModifiedError):
      pass
    # logger.info(f'content: {content}')

  cacheDir = util.getCache('')
  htmls = []
  for i in os.listdir(cacheDir):
    path = os.path.join(cacheDir, i)
    if i.startswith('output') and i.endswith('.html'):
      os.remove(path)
      htmls.append(i)
  if len(htmls) > 0:
    logger.info(f'清理 html 文件: {", ".join(htmls)}')

  # 停止进一步处理
  raise events.StopPropagation


deepseek_texts = {}


@InlineCommand(r'[^ ].*')
async def _(event):
  builder = event.builder
  msg = f'$ {event.text}'
  did = random.randrange(4_294_967_296)
  deepseek_texts[did] = msg
  did_bytes = int(did).to_bytes(4, 'big')
  return [
    builder.document(
      title='问问小派魔',
      description=msg,
      text=msg,
      buttons=Button.inline('点击召唤Deepseek', b'deepseek_' + did_bytes),
      file=b'<html></html>',
      attributes=[types.DocumentAttributeFilename('output.html')],
    ),
  ]


@bot.on(events.CallbackQuery(pattern=b'deepseek_([\x00-\xff]{4,4})$'))
async def _(event):
  try:
    await event.edit(buttons=[])
  except errors.MessageNotModifiedError:
    pass
  await event.answer()
  match = event.pattern_match
  did = int.from_bytes(match.group(1), 'big')
  event.raw_text = deepseek_texts[did]
  del deepseek_texts[did]
  event.message = None
  event.peer_id = event.query.user_id
  await _chat(event)


@Command('clear', info='清除上下文记忆')
async def _(event):
  # 清除指定用户的上下文记忆
  user_id = event.sender_id
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  
  chat = await bot.get_entity(event.peer_id)
  name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
  if t := getattr(chat, 'last_name', None):
    name += ' ' + t
  
  peer_id = utils.get_peer_id(event.peer_id)
  url = f'tg://user?id={peer_id}'
  name = f'[{util.string.markdown_escape(name)}]({url})'
  
  if os.path.isfile(path):
    os.remove(path)
    m = await event.respond(f'✅ {name} 已清除你的对话上下文记忆。')
  else:
    m = await event.respond(f'ℹ️ {name} 你的对话上下文为空，无需清除。')
  if not event.is_private:
    try:
      await bot.delete_messages(event.peer_id, event.message.id)
    except errors.MessageDeleteForbiddenError:
      pass
    bot.schedule_delete_messages(10, event.peer_id, m.id)
