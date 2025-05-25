# -*- coding: utf-8 -*-
# @Author  : HBcao
# @Email   : hbcaoqaq@gmail.com
# @Name    : randcat
# @Info    : 随机猫狗

from telethon import types, utils
import time
import os 
import mimetypes

import util
from plugin import InlineCommand


@InlineCommand(' *$')
async def _cat(event):
  r = await util.get('https://cataas.com/cat?json=true')
  if r.status_code != 200:
    return 
  res = r.json()
  
  html_parser = utils.sanitize_parse_mode('html')
  msg = f'猫猫 <a href="https://cataas.com/cat/{res["id"]}">{res["id"]}</a>'
  message, entities = html_parser.parse(msg)
  
  result = types.InputBotInlineResult(
    id=str(time.time()),
    type='photo',
    thumb=types.InputWebDocument(
      url=res['url'],
      size=0,
      mime_type=res['mimetype'],
      attributes=[],
    ),
    content=types.InputWebDocument(
      url=res['url'],
      size=0,
      mime_type=res['mimetype'],
      attributes=[],
    ),
    send_message=types.InputBotInlineMessageMediaAuto(
      message=message,
      entities=entities,
    ),
    title='随机猫猫',
    description='',
  )
  return [result]


@InlineCommand(' *$')
async def _cat(event):
  r = await util.get('https://dog.ceo/api/breeds/image/random')
  if r.status_code != 200:
    return 
  res = r.json()
  
  url = res['message']
  _, name = os.path.split(url)
  _name, _ext = os.path.splitext(name)
  mime_type = mimetypes.guess_type(url)[0]
  html_parser = utils.sanitize_parse_mode('html')
  msg = f'狗狗 <a href="{url}">{_name}</a>'
  message, entities = html_parser.parse(msg)
  
  result = types.InputBotInlineResult(
    id=str(time.time()),
    type='photo',
    thumb=types.InputWebDocument(
      url=url,
      size=0,
      mime_type=mime_type,
      attributes=[],
    ),
    content=types.InputWebDocument(
      url=url,
      size=0,
      mime_type=mime_type,
      attributes=[],
    ),
    send_message=types.InputBotInlineMessageMediaAuto(
      message=message,
      entities=entities,
    ),
    title='随机狗狗',
    description='',
  )
  return [result]
