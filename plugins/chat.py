# -*- coding: utf-8 -*-
# @Author  : Nyan2024
#

import os
import json
import re
import openai
import random
import time
from datetime import datetime
from telethon import events, types, errors, Button

import config
import util
from plugin import handler, InlineCommand
from util.log import logger

# ==============一些必须填写的变量=================================================================================：
# API可以去薅Modelscope魔塔社区的免费一天2000次Inference，其它平台通用OpenAI格式的API也可以。
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


@handler('chat', info='与小派魔聊天')
async def _chat(event):
  # 获取调用者 ID
  user_id = event.sender_id

  # 提取用户消息，回复优先
  if event.message and (reply := await event.message.get_reply_message()):
    user_message = reply.message or reply.text or ''
  else:
    parts = event.raw_text.split(maxsplit=1)
    user_message = parts[1] if len(parts) > 1 else ''

  # 如果没输入内容，提示并退出
  if not user_message:
    await event.respond(
      '❗️ 请输入要对派魔说的话，例如 `/chat 你是谁`。插件作者：@nyan2022。后端由Deepseek R1模型支持'
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
  logger.debug(f'[CHAT] messages to API: {msgs!r}')

  # 发送占位消息
  inline_mode = event.message is None
  resp = (
    await event.respond('派魔正在思考中...', reply_to=event.message)
    if not inline_mode
    else event
  )
  client = openai.Client(base_url=f'{api_url}', api_key=f'{api_key}')

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
    # 流式调用
    for chunk in client.chat.completions.create(
      model=f'{model}',
      messages=msgs,
      temperature=0.2,
      max_tokens=max_tokens,
      stream=True,
    ):
      logger.info(chunk)
      delta = chunk.choices[0].delta
      if not delta:
        if hasattr(chunk.choices[0], 'message'):
          content += chunk.choices[0].message['content']
          break
        continue
      c = delta.content or ''
      rc = delta.reasoning_content or ''
      if c:
        content += c
      elif rc:
        reasoning_content += rc
      else:
        continue

      now = time.monotonic()
      if now - last_edit >= 5:
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
      await resp.edit(
        m.text + f'\n\n⚠️ > 与 Chat API 通信出现错误 {type(e).__name__}：{e}'
      )
    except (errors.MessageEmptyError, errors.MessageNotModifiedError):
      pass
    # logger.info(f'content: {content}')

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


@handler('clear', info='清除上下文记忆')
async def _(event):
  # 清除指定用户的上下文记忆
  user_id = event.sender_id
  path = os.path.join(MEMORY_DIR, f'{user_id}.json')
  if os.path.isfile(path):
    os.remove(path)
    await event.respond('✅ 已清除你的对话上下文记忆。')
  else:
    await event.respond('ℹ️ 你的对话上下文为空，无需清除。')
  raise events.StopPropagation
