import qqmusic_api
import util
import config


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
  return res[0]

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
  
  msg = f'<a href="{url}">{title}</a>{subtitle} - {singers} #qqmusic\n via @%s' % bot.me.username
  return msg


async def get_song_url(mid):
  r = await util.post('https://api.toubiec.cn/api/qqmusic.php', data={
    'url': f'https://y.qq.com/n/ryqq/songDetail/{mid}',
    'level': 128,
  })
  if r.status_code != 200:
    return False
  res = r.json()
  if 'error' in res:
    return False
  url = res['data']['music_url']['128']['url']
  return url


async def general_search(keyword):
  res = await qqmusic_api.search.general_search(
    keyword, 
    page=1,
    highlight=False,
    credential=credential
  )
  res = res['body']['item_song']['items']
  result = [
    {
      k: v
      for k, v in d.items()
      if k in ['mid', 'title', 'singer']
    }
    for d in res
  ]
  return result


def parse_search(res):
  from telethon import Button
  
  icons = [f'{i}\ufe0f\u20e3' for i in range(1, 10)] + ['\U0001f51f']
  
  arr = [
    f'{icons[i]} <a href="https://t.me/{bot.me.username}?start=qqmusic_{res[i]["mid"]}">{res[i]["title"]}</a> - ' +
    '、'.join([
      j['name']
      for j in res[i]['singer']
    ])
    for i in range(10)
  ]
  
  icon = '\U0001f3b5'
  urls = [f'https://t.me/{bot.me.username}?start=qqmusic_{i["mid"]}' for i in res]
  btns = [
    Button.url(f'{i+1} {icon}', urls[i])
    for i in range(10)
  ]
  buttons = [btns[i:i+5] for i in range(0,10,5)]
  return '\n'.join(arr), buttons


async def get_try_url(res):
  url = await qqmusic_api.song.get_try_url(
    res['mid'], 
    vs=res['vs'][0],
    credential=credential,
  )
  return url 
