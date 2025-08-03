from telethon import events, types, errors, Button
import re
import random
import time
import functools

from plugin import Command, InlineCommand
from util.log import logger
import util


objects = [f'{i}\u20e3' for i in range(1, 10)]
objects.extend(('\U0001f51f', '1\u20e31\u20e3', '1\u20e32\u20e3'))


@InlineCommand(r' *(\d*) *$')
async def _(event):
  builder = event.builder
  match = event.pattern_match
  if match is None or not match.group(1):
    count = 6
  else:
    count = int(match.group(1))
    if count > 12:
      count = 10

  create_time = int(time.time() * 1000)
  res = random.randint(1, count)
  with util.Data('guess') as data:
    data[str(create_time)] = {
      'count': count,
      'res': res,
      'guess': [],
    }
  buttons = get_buttons(count, create_time)

  return [
    builder.article(
      title='猜点数',
      description=f'在 1 ~ {count} 之中猜点数',
      text=f'🎲 猜点数 (1 ~ {count})',
      buttons=buttons,
      thumb=types.InputWebDocument(
        url='https://i.postimg.cc/VsR2Dp6K/image.png',
        size=21790,
        mime_type='image/jpeg',
        attributes=[types.DocumentAttributeImageSize(w=180, h=180)],
      ),
    ),
  ]


_bp = b'guess_([\x00-\xff]{6,6})_([\x00-\xff])'
_button_pattern = re.compile(_bp).match


@bot.on(events.CallbackQuery(pattern=_button_pattern))
async def _(event):
  user_id = event.query.user_id
  match = event.pattern_match
  create_time = int.from_bytes(match.group(1), 'big')
  guess = int.from_bytes(match.group(2), 'big')
  data = util.Data('guess')
  count = functools.reduce(
    lambda num, i: num + 1 if i['user_id'] == user_id else num,
    data[str(create_time)]['guess'],
    0,
  )
  logger.info(f'user_id: {user_id}, guess: {guess}, count: {count}')
  if count >= 3:
    return await event.answer('你已经猜了三次了，不许再猜了！', alert=True)

  with data:
    data[str(create_time)]['guess'].append(
      {
        'user_id': user_id,
        'guess': guess,
      }
    )
  res = data[str(create_time)]

  right = res['res'] == guess
  right1 = '对' if right else '错'
  right2 = '\U0001f389' if right else '\u2620'
  result = f'{right2}你猜{right1}啦！'
  await event.answer(result, alert=True)

  msg = [f'🎲 猜点数 (1 ~ {res["count"]})']
  for i in res['guess'][-20:]:
    chat = await bot.get_entity(i['user_id'])
    name = getattr(chat, 'first_name', None) or getattr(chat, 'title', None)
    if t := getattr(chat, 'last_name', None):
      name += ' ' + t
    if len(name) > 10:
      name = name[:10] + '...'

    right = res['res'] == i['guess']
    right1 = '对' if right else '错'
    right2 = '\U0001f389' if right else '\u2620'
    msg.append(
      f'\u25cf<a href="tg://user?id={i["user_id"]}">{name} </a>猜{right1}了{right2}'
    )

  buttons = get_buttons(res['count'], create_time)
  try:
    await event.edit(
      '\n'.join(msg),
      parse_mode='html',
      buttons=buttons,
    )
  except errors.MessageNotModifiedError:
    pass


def get_buttons(count, create_time):
  buttons = []
  row = (count - 1) // 6 + 1
  column = (count - 1) // row + 1
  create_time_bytes = create_time.to_bytes(6, 'big')
  for i in range(row):
    buttons.append([])
    for j in range(i * column, i * column + column):
      j_bytes = int(j + 1).to_bytes(1, 'big')
      if j < count:
        btn = Button.inline(
          f'{objects[j]}', b'guess_' + create_time_bytes + b'_' + j_bytes
        )
      else:
        btn = Button.inline('　', b'')
      buttons[i].append(btn)
  return buttons
