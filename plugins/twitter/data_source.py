import re
import time
import httpx
import ujson as json

import config
import util
from util.log import logger


env = config.env
csrf_token = env.get('twitter_csrf_token', '')
auth_token = env.get('twitter_auth_token', '')
gheaders = {
  'content-type': 'application/json; charset=utf-8',
  'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
  'x-csrf-token': csrf_token,
  'cookie': f'auth_token={auth_token}; ct0={csrf_token}',
  'X-Twitter-Client-Language': 'zh-cn',
  'X-Twitter-Active-User': 'yes',
}


async def get_twitter(tid):
  url = 'https://twitter.com/i/api/graphql/NmCeCgkVlsRGS1cAwqtgmw/TweetDetail'
  variables = {
    'focalTweetId': str(tid),
    'with_rux_injections': False,
    'includePromotedContent': True,
    'withCommunity': True,
    'withQuickPromoteEligibilityTweetFields': True,
    'withBirdwatchNotes': True,
    'withVoice': True,
    'withV2Timeline': True,
  }
  features = {
    'rweb_lists_timeline_redesign_enabled': True,
    'responsive_web_graphql_exclude_directive_enabled': True,
    'verified_phone_label_enabled': False,
    'creator_subscriptions_tweet_preview_api_enabled': True,
    'responsive_web_graphql_timeline_navigation_enabled': True,
    'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
    'tweetypie_unmention_optimization_enabled': True,
    'responsive_web_edit_tweet_api_enabled': True,
    'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
    'view_counts_everywhere_api_enabled': True,
    'longform_notetweets_consumption_enabled': True,
    'responsive_web_twitter_article_tweet_consumption_enabled': False,
    'tweet_awards_web_tipping_enabled': False,
    'freedom_of_speech_not_reach_fetch_enabled': True,
    'standardized_nudges_misinfo': True,
    'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
    'longform_notetweets_rich_text_read_enabled': True,
    'longform_notetweets_inline_media_enabled': True,
    'responsive_web_media_download_video_enabled': False,
    'responsive_web_enhance_cards_enabled': False,
  }
  try:
    r = await util.get(
      url,
      params={
        'variables': json.dumps(variables),
        'features': json.dumps(features),
      },
      headers=gheaders,
    )
    res = r.json()
    if 'errors' in res and len(res['errors']) > 0:
      if res['errors'][0]['code'] == 144:
        return '推文不存在'
      return res['errors'][0]['message']

    entries = res['data']['threaded_conversation_with_injections_v2']['instructions'][
      0
    ]['entries']
    tweet_entrie = [
      i
      for i in entries
      if i['entryId'] == f'Tweet-{tid}' or i['entryId'] == f'tweet-{tid}'
    ]
    if len(tweet_entrie) == 0:
      return '解析失败'
    tweet_result = tweet_entrie[0]['content']['itemContent']['tweet_results']['result']
    if 'tweet' in tweet_result.keys():
      return tweet_result['tweet']
    else:
      return tweet_result
  except json.JSONDecodeError:
    return f'未找到tid为{tid}的推文'
  except httpx.ConnectError:
    return '连接超时'
  except Exception:
    logger.error('未知错误: ', exc_info=1)
    return '未知错误'


def parse_msg(res):
  tweet = res['legacy']
  user = res['core']['user_results']['result']['legacy']

  tid = tweet['id_str']
  full_text = tweet['full_text']
  if 'urls' in tweet['entities'].keys():
    for i in tweet['entities']['urls']:
      full_text = full_text.replace(i['url'], i['expanded_url'])
  full_text = re.sub(r'\s*https:\/\/t\.co\/\w+$', '', full_text)
  full_text = re.sub(
    r'#([^ \n#]+)', r'<a href="https://x.com/hashtag/\1">#\1</a>', full_text
  )
  full_text = re.sub(
    r'([^@]*[^/@]+)@([0-9a-zA-Z_]*)', r'\1<a href="https://x.com/\2">@\2</a>', full_text
  )

  nickname = user['name']
  username = user['screen_name']
  utc_time = time.strptime(tweet['created_at'], r'%a %b %d %H:%M:%S %z %Y')
  local_time = time.localtime(
    time.mktime(utc_time) + utc_time.tm_gmtoff - time.timezone
  )
  create_time = time.strftime('%Y年%m月%d日 %H:%M:%S', local_time)
  msg = (
    f'<a href="https://x.com/{username}/status/{tid}">{tid}</a>'
    f' | <a href="https://x.com/{username}">{nickname}</a> #X'
    + (
      f':\n<blockquote expandable>{full_text}\n{create_time}</blockquote>'
      if full_text != ''
      else f':\n{create_time}'
    )
  )
  return msg, full_text, create_time


def parseMedias(tweet):
  if 'extended_entities' not in tweet:
    return []
  res = []
  medias = tweet['extended_entities']['media']
  for media in medias:
    if media['type'] == 'photo':
      res.append(
        {
          'type': 'photo',
          'url': media['media_url_https'] + ':orig',
          'md5': util.md5sum(media['media_url_https'] + ':orig'),
          'thumbnail_url': media['media_url_https'] + ':small',
        }
      )
    else:
      variants = media['video_info']['variants']
      variants = list(filter(lambda x: x['content_type'] == 'video/mp4', variants))
      variants.sort(key=lambda x: x['bitrate'], reverse=True)
      url = variants[1]['url'] if len(variants) > 1 else variants[0]['url']
      res.append(
        {
          'type': 'video',
          'url': url,
          'md5': util.md5sum(url),
          'thumbnail_url': variants[-1]['url'],
          'variants': variants,
        }
      )
  return res
