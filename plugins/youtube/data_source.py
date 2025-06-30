import ujson as json
import util
import config
from util.log import logger


# cookie 中的 __Secure-3PSID
token = config.env.get('youtube_token', '')
gheaders = {
  'content-type': 'application/json',
  'origin': 'https://www.youtube.com',
  'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
  'cookie': f'__Secure-3PSID={token}',
  'referer': f'https://www.youtube.com/',
}


async def get_info(video_id):
  r = await util.post(
    'https://www.youtube.com/youtubei/v1/player',
    headers=gheaders,
    params={
      'prettyPrint': 'false',
    },
    data=json.dumps(
      {
        'playbackContext': {
          'contentPlaybackContext': {'html5Preference': 'HTML5_PREF_WANTS'}
        },
        'contentCheckOk': True,
        'racyCheckOk': True,
        'context': {
          'client': {
            'clientName': 'WEB',
            'clientVersion': '2.20250620.01.00',
            'hl': 'zh-CN',
          },
          'thirdParty': {'embedUrl': 'https://google.com'},
        },
        'videoId': video_id,
      }
    ),
  )
  if r.status_code != 200:
    return '请求失败'

  res = r.json()
  if 'playabilityStatus' in res:
    if res['playabilityStatus']['status'] == 'ERROR':
      reason = res['playabilityStatus']['reason']
      if reason == 'This video is unavailable':
        reason = '视频不可用'
      return reason
  if 'videoDetails' not in res:
    logger.info(r.text)
    return '解析失败'
  if 'streamingData' not in res:
    return '视频解析失败'
  return res['videoDetails']


def parse_info(res):
  vid = res['videoId']
  title = res['title']
  author = res['author']
  uid = res['channelId']
  msg = (
    f'<a href="https://youtube.com/watch?v={vid}">{title}</a> - <a href="https://youtube.com/channel/{uid}">{author}</a> #YouTuBe\nvia @%s'
    % bot.me.username
  )
  return msg
