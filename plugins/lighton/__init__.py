from telethon import events, Button, errors
import re

from util.log import logger
from plugin import handler
from .gauss_elimination import gen_matrix, gauss_elimination


caption = '来用小方块填满我吧❤️～\n'


@handler('lighton', info='点灯游戏')
async def _(event, text):
  try:
    row = int(text)
  except Exception:
    row = 2
  if row > 8 or row < 1:
    return await event.reply('最大为8')
  await event.reply(caption + f'当前大小: {row}', buttons=gen_buttons(row))
  raise events.StopPropagation


_button_pattern = re.compile(rb'light_([\x00-\xff]{1,1})([\x00-\xff]{2,2})$').match


@bot.on(events.CallbackQuery(pattern=_button_pattern))
async def _event(event):
  match = event.pattern_match
  row = int.from_bytes(match.group(1), 'big')
  ij = int.from_bytes(match.group(2), 'big')
  message = await event.get_message()
  buttons = message.buttons
  if row == 255:
    row = len(buttons[0])
    mat = gen_matrix(row)
    res = gauss_elimination(mat)
    for k in range(row * row):
      i = int(k / row)
      j = k % row
      buttons[i][j] = Button.inline(
        '\u2605' if (res >> i * row + j) & 1 else '\u3000', buttons[i][j].data
      )
    await event.edit(buttons=buttons)
  elif row == 254:
    await event.edit(buttons=gen_buttons(len(buttons[0])))
  elif row == 253:
    if len(buttons[0]) >= 8:
      return await event.answer('最大为8', alert=True)
    await event.edit(
      caption + f'当前大小: {len(buttons[0])+1}',
      buttons=gen_buttons(len(buttons[0]) + 1),
    )
  elif row == 252:
    if len(buttons[0]) <= 1:
      return await event.answer('最小为1', alert=True)
    await event.edit(
      caption + f'当前大小: {len(buttons[0])-1}',
      buttons=gen_buttons(len(buttons[0]) - 1),
    )
  else:
    for k in [ij, ij + 1, ij - 1, ij + row, ij - row]:
      i = int(k / row)
      j = k % row
      if (
        0 <= k < row * row
        and (ij % row != 0 or k != ij - 1)
        and (ij % row != row - 1 or k != ij + 1)
      ):
        buttons[i][j] = Button.inline(
          '\u3000' if buttons[i][j].text == '\u2588' else '\u2588', buttons[i][j].data
        )
    if all(buttons[int(k / row)][k % row].text == '\u2588' for k in range(row * row)):
      logger.info('won')
      await event.answer('你赢啦！', alert=True)

    try:
      await event.edit(buttons=buttons)
    except errors.MessageNotModifiedError:
      pass

  await event.answer()


def gen_buttons(row):
  row_bytes = row.to_bytes(1, 'big')
  buttons = [
    [
      Button.inline('\u3000', b'light_' + row_bytes + (i * row + j).to_bytes(2, 'big'))
      for j in range(row)
    ]
    for i in range(row)
  ]
  buttons.extend(
    (
      [
        Button.inline('减小', b'light_\xfc\x00\x00'),
        Button.inline('增大', b'light_\xfd\x00\x00'),
      ],
      [
        Button.inline('重置', b'light_\xfe\x00\x00'),
        Button.inline('求解', b'light_\xff\x00\x00'),
      ],
    )
  )
  return buttons
