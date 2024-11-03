from telethon import events, Button, errors
import re

from plugin import handler
from .gauss_elimination import gen_matrix, gauss_elimination


caption = '来用小方块填满我吧❤️～\n'
solve_tip = '杂鱼~才这种难度就不行了吗~让小派魔教你吧，每个星星点一遍就可以过关哦'


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

  if row == 255:  # 求解按钮
    row = len(buttons[0])
    mat = gen_matrix(row)
    res = gauss_elimination(mat)
    for k in range(row * row):
      i = int(k / row)
      j = k % row
      buttons[i][j] = Button.inline(
        '\u2605' if (res >> i * row + j) & 1 else '\u3000', buttons[i][j].data
      )
    await event.answer(solve_tip, alert=True)
    try:
      await event.edit(buttons=buttons)
    except errors.MessageNotModifiedError:
      pass
    return
  elif row == 254:  # 重置按钮
    await event.edit(buttons=gen_buttons(len(buttons[0])))
    return
  elif row == 253:  # 增大按钮
    if len(buttons[0]) >= 8:
      return await event.answer('最大为8', alert=True)
    await event.edit(
      caption + f'当前大小: {len(buttons[0])+1}',
      buttons=gen_buttons(len(buttons[0]) + 1),
    )
    return
  elif row == 252:  # 减小按钮
    if len(buttons[0]) <= 1:
      return await event.answer('最小为1', alert=True)
    await event.edit(
      caption + f'当前大小: {len(buttons[0])-1}',
      buttons=gen_buttons(len(buttons[0]) - 1),
    )
    return

  # 其他按钮
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
    await event.answer('你赢啦！', alert=True)
  else:
    await event.answer()

  try:
    await event.edit(buttons=buttons)
  except errors.MessageNotModifiedError:
    pass


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
