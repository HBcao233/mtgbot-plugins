import os
import util

from util.log import logger


async def get_info(source, uid, pid):
  r = await util.get(f'https://kemono.su/api/v1/{source}/user/{uid}/post/{pid}')
  if r.status_code != 200:
    return False
  info = r.json()
  info['source'] = source
  r1 = await util.get(f'https://kemono.su/api/v1/{source}/user/{uid}/profile')
  if r.status_code != 200:
    return False
  info['author'] = r1.json()
  return info


async def parse_page(title, files, nocache=False):
  if not nocache:
    for i in await util.telegraph.getPageList():
      if i['title'] == title:
        return i['url']

  content = []
  for i in files:
    content.append(
      {
        'tag': 'img',
        'attrs': {
          'src': i['thumbnail'],
        },
      }
    )

  return await util.telegraph.createPage(title, content)


async def gif2mp4(path):
  dirname, name = os.path.split(path)
  name = os.path.splitext(name)[0]
  output = os.path.join(dirname, f'{name}.mp4')
  command = [
    'ffmpeg',
    '-i',
    path,
    '-pix_fmt',
    'yuv420p',
    output,
    '-y',
  ]
  returncode, stdout = await util.media.ffmpeg(command)
  if returncode != 0:
    logger.error(stdout)
    return False
  return output
