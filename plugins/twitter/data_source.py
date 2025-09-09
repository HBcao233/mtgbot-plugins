import re
import httpx
import json
from datetime import datetime

import config
import util
from util.log import logger
from util.log import timezone


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
  url = 'https://twitter.com/i/api/graphql/u5Tij6ERlSH2LZvCUqallw/TweetDetail'
  variables = {
    'focalTweetId': str(tid),
    'with_rux_injections': False,
    'rankingMode': 'Relevance',
    'includePromotedContent': True,
    'withCommunity': True,
    'withQuickPromoteEligibilityTweetFields': True,
    'withBirdwatchNotes': True,
    'withVoice': True,
  }
  try:
    r = await util.get(
      url,
      params={
        'variables': json.dumps(variables),
        'features': '{"rweb_video_screen_enabled":false,"payments_enabled":false,"rweb_xchat_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_show_grok_translated_post":false,"responsive_web_grok_analysis_button_from_backend":false,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_grok_imagine_annotation_enabled":true,"responsive_web_grok_community_note_auto_translation_is_enabled":false,"responsive_web_enhance_cards_enabled":false}',
        'fieldToggles': '{"withArticleRichContentState":true,"withArticlePlainText":false,"withGrokAnalyze":false,"withDisallowedReplyControls":false}',
      },
      headers=gheaders,
    )
    try:
      res = r.json()
    except json.JSONDecodeError:
      return '解析失败，可能是老马又更新了接口'
    if 'errors' in res and len(res['errors']) > 0:
      if res['errors'][0]['code'] == 144:
        return '推文不存在'
      return res['errors'][0]['message']

    try:
      any(
        (entries := i)['type'] == 'TimelineAddEntries'
        for i in res['data']['threaded_conversation_with_injections_v2'][
          'instructions'
        ]
      )
      entries = entries['entries']
    except (KeyError, IndexError):
      logger.warn(f'解析失败: {res}', exc_info=1)
      return '解析失败'
    tweet_entrie = [
      i
      for i in entries
      if i['entryId'] == f'Tweet-{tid}' or i['entryId'] == f'tweet-{tid}'
    ]
    if len(tweet_entrie) == 0:
      return '解析失败'
    tweet_result = tweet_entrie[0]['content']['itemContent']['tweet_results'][
      'result'
    ]
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


def replace_unsupported_characters(t):
  return t.replace('\u17b5', '\\u17b5')


def parse_msg(res):
  user = res['core']['user_results']['result']['core']
  nickname = replace_unsupported_characters(user['name'])
  username = user['screen_name']

  tweet = res['legacy']
  tid = tweet['id_str']
  full_text = replace_unsupported_characters(tweet['full_text'])
  if 'urls' in tweet['entities'].keys():
    for i in tweet['entities']['urls']:
      full_text = full_text.replace(i['url'], i['expanded_url'])
  full_text = re.sub(r'\s*https:\/\/t\.co\/\w+$', '', full_text)
  full_text = re.sub(
    r'#([^ \n#]+)', r'<a href="https://x.com/hashtag/\1">#\1</a>', full_text
  )
  full_text = re.sub(
    r'([^@]*[^/@]+)@([0-9a-zA-Z_]*)',
    r'\1<a href="https://x.com/\2">@\2</a>',
    full_text,
  )
  if ('暗号' in full_text or '暗语' in full_text) and (
    't.me' in full_text
    or '通道' in full_text
    or '直通' in full_text
    or '领取' in full_text
    or '联系' in full_text
    or '渠道' in full_text
    or '进群' in full_text
    or '飞机' in full_text
  ):
    full_text = f'\u26a0推文内容疑似推广诈骗，请注意甄别\n\n{full_text}'

  created_at = datetime.strptime(
    tweet['created_at'], r'%a %b %d %H:%M:%S %z %Y'
  )
  created_at.astimezone(timezone)
  created_at = created_at.strftime('%Y年%m月%d日 %H:%M:%S')

  msg = (
    f'<a href="https://x.com/{username}/status/{tid}">{tid}</a>'
    f' | <a href="https://x.com/{username}">{nickname}</a> #X'
  )
  if full_text:
    msg += f':\n<blockquote expandable>{full_text}\n{created_at}</blockquote>'
  else:
    msg += f'\n{created_at}'
  return msg, full_text, created_at


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
      variants = list(
        filter(lambda x: x['content_type'] == 'video/mp4', variants)
      )
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
