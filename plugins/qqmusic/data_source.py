import qqmusic_api
import util
import config
from util.log import logger


musicid = config.env.get('qqmusic_musicid', '')
musickey = config.env.get('qqmusic_musickey', '')
refresh_key = config.env.get('qqmusic_refresh_key', '')
refresh_token = config.env.get('qqmusic_refresh_token', '')
encrypt_uin = config.env.get('qqmusic_encrypt_uin', '')
credential = qqmusic_api.Credential(
  musicid=musicid,
  musickey=musickey,
  refresh_key=refresh_key,
  refresh_token=refresh_token,
  encrypt_uin=encrypt_uin,
)


async def get_song_info(mid):
  res = await qqmusic_api.song.query_song(value=[mid], credential=credential)
  if len(res) == 0:
    return '获取失败'
  res = res[0]
  res['album']['picUrl'] = qqmusic_api.album.get_cover(res['album']['mid'])
  return res


def parse_song_info(res):
  mid = res['mid']
  url = f'https://y.qq.com/n/ryqq/songDetail/{mid}'
  title = res['title']
  subtitle = res['subtitle']
  if subtitle:
    subtitle = f' ({subtitle})'

  def parse_singer(s):
    name = s['name']
    mid = s['mid']
    url = f'https://y.qq.com/n/ryqq/singer/{mid}'
    return f'<a href="{url}">{name}</a>'

  singers = map(parse_singer, res['singer'])
  singers = '、'.join(singers)

  msg = (
    f'<a href="{url}">{title}</a>{subtitle} - {singers} #qqmusic\n via @%s'
    % bot.me.username
  )
  metainfo = {
    'sid': mid,
    'coverUrl': res['album']['picUrl'],
    'title': title + subtitle,
    'singers': '、'.join(i['name'] for i in res['singer']),
    'album': res['album']['name'],
  }
  return msg, metainfo


async def add_metadata(img, ext, metainfo):
  sid = metainfo['sid']
  cover_name = f'qqmusic_{sid}_cover'
  cover_url = metainfo['coverUrl']
  cover = await util.getImg(
    cover_url,
    saveas=cover_name,
    ext=True,
  )
  resimg_name = f'qqmusic_{sid}_meta.{ext}'
  resimg = util.getCacheFile(resimg_name)
  title = metainfo['title']
  singers = metainfo['singers']
  album = metainfo['album']
  returncode, stdout = await util.media.ffmpeg(
    [
      'ffmpeg',
      '-i',
      cover,
      '-i',
      img,
      '-c',
      'copy',
      '-map',
      '0:v',
      '-map',
      '1:a',
      '-metadata',
      f'title={title}',
      '-metadata',
      f'artist={singers}',
      '-metadata',
      f'album={album}',
      '-metadata:s:v',
      'title=Front cover',
      '-metadata:s:v',
      'comment=Cover (front)',
      '-y',
      resimg,
    ]
  )
  if returncode != 0:
    logger.warning(stdout)
    return img
  return resimg


async def get_song_url(mid):
  r = await util.post(
    'https://api.toubiec.cn/api/qqmusic.php',
    data={
      'url': f'https://y.qq.com/n/ryqq/songDetail/{mid}',
      'level': 128,
    },
  )
  if r.status_code != 200:
    return False
  res = r.json()
  if 'error' in res:
    logger.warning(f'获取歌曲url失败: {res}')
    return False
  url = res['data']['music_url']['128']['url']
  return url


async def general_search(keyword):
  res = await qqmusic_api.search.general_search(
    keyword, page=1, highlight=False, credential=credential
  )
  res = res['body']['item_song']['items']
  result = [
    {k: v for k, v in d.items() if k in ['mid', 'title', 'singer']} for d in res
  ]
  return result


def parse_search(res):
  from telethon import Button

  icons = [f'{i}\ufe0f\u20e3' for i in range(1, 10)] + ['\U0001f51f']

  arr = [
    f'{icons[i]} <a href="https://t.me/{bot.me.username}?start=qqmusic_{res[i]["mid"]}">{res[i]["title"]}</a> - '
    + '、'.join([j['name'] for j in res[i]['singer']])
    for i in range(10)
  ]

  icon = '\U0001f3b5'
  urls = [f'https://t.me/{bot.me.username}?start=qqmusic_{i["mid"]}' for i in res]
  btns = [Button.url(f'{i + 1} {icon}', urls[i]) for i in range(10)]
  buttons = [btns[i : i + 5] for i in range(0, 10, 5)]
  return '\n'.join(arr), buttons


async def get_try_url(res):
  url = await qqmusic_api.song.get_try_url(
    res['mid'],
    vs=res['vs'][0],
    credential=credential,
  )
  logger.info(f'尝试获取试听url: {url}')
  return url
