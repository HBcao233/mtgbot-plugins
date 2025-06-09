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