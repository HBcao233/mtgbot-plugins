from bs4 import BeautifulSoup
from urllib.parse import unquote

import util


def parse_msg(kid, _html):
  soup = BeautifulSoup(_html, 'html.parser')
  try:
    p = soup.select('.post__user .post__user-name')
    user_name = p[0].text.strip()
    user_u: str = p[0].attrs['href']
    user_uid = user_u.split('/')[-1]
    user_url = f'https://www.pixiv.net/fanbox/creator/{user_uid}'

    title = soup.select('.post__info .post__title span')[0].text.strip()
    # published_time = soup.select(".post__published")[0].text.strip().split()[1]
  except Exception:
    raise Exception('解析错误, 请检查链接')

  attachments = ''
  _attachments = soup.select('.site-section--post .post__body .post__attachments li')
  if len(_attachments) > 0:
    attachments += '文件列表: '
  for i in _attachments:
    add = f"\n<code>{unquote(i.select('a')[0].attrs['download'])}</code>: {i.select('a')[0].attrs['href']}"
    attachments += add

  files = []
  _files = soup.select(
    '.site-section--post .post__body .post__files .post__thumbnail a'
  )
  for i, ai in enumerate(_files):
    url = ai.attrs['href']
    ext = url.split('.')[-1]
    if len(ai.select('img')) > 0:
      files.append(
        {
          'name': f'{i}.{ext}',
          'type': 'image',
          'url': url,
          'thumbnail': 'https:' + ai.select('img')[0].attrs['src'],
        }
      )

  return title, user_name, user_url, attachments, files


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
