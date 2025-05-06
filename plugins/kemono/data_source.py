from urllib.parse import unquote

import util


async def get_info(source, uid, pid):
  r = await util.get(f'https://kemono.su/api/v1/{source}/user/{uid}/post/{pid}')
  if r.status_code != 200:
    return False
  info = r.json()
  info['source'] = source
  r1 = await util.get(f'https://kemono.su/api/v1/{source}/user/{uid}/profile')
  if r.status_code != 200:
    return False
  info['author'] = r1.json();
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
