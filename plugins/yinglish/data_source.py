import os
import json
import openai
import config
from util.log import logger


api_url = (
  config.env.get('yinglish_api_url', '')
  or config.env.get('chat_api_url', '') 
  or 'https://integrate.api.nvidia.com/v1'
)
api_key = (
  config.env.get('yinglish_api_key', '')
  or config.env.get('chat_api_key', '') 
  or 'EMPTY'
)
model = config.env.get('yinglish_model', '') or 'deepseek-ai/deepseek-v3.1'
max_tokens = config.env.get('yinglish_max_tokens', '') or 8192


system_prompt = ""
sp_path = os.path.join(os.path.dirname(__file__), 'yinglish.txt')
if os.path.isfile(sp_path):
  with open(sp_path, 'r') as f:
    if text := f.read():
      system_prompt = text.strip()
else:
  logger.warn('[淫语翻译器] 未读取到提示词文本文件，将不可用')


def fail(message):
  return {
    'code': 1,
    'message': message,
    'data': {},
  }
  
def success(data):
  return {
    'code': 0,
    'message': 'ok',
    'data': data,
  }
  
async def get_yinglish(text):
  if not system_prompt:
    logger.error('[淫语翻译器]: 系统提示词为空')
    return fail('系统配置错误')

  msgs = [
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': text},
  ]
  client = openai.AsyncOpenAI(
    base_url=f'{api_url}',
    api_key=f'{api_key}',
    timeout=openai.Timeout(60.0, connect=60.0),
  )
  content = ''
  r = await client.chat.completions.create(
    model=f'{model}',
    messages=msgs,
    max_tokens=max_tokens,
    stream=False,
    temperature=1,
    top_p=1,
  )
  try:
    content = r.choices[0].message.content
  except AttributeError:
    logger.error(f'解析错误: {r}')
    return fail('解析失败')
  
  content = content.replace('```json', '').replace('```', '').strip()
  try:
    res = json.loads(content)
  except json.JSONDecodeError:
    logger.error(f'json解析错误: {content}')
    return fail('解析错误')
  return success(res)
