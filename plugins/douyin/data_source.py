# 部分代码参考了 https://github.com/Johnserf-Seed/f2/

from pydantic import BaseModel
from urllib.parse import urlencode

import util
from util.log import logger
from .abogus import ABogus


user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
cookie = 'MONITOR_WEB_ID=a0a75cdb-c044-4f33-965b-2c96e8b2543a; UIFID_TEMP=47e05068b0a7733abcb242917ae42006325e9c99f9c28424accd11477c730b0102fc181b2d67db5fc4318e0c68e133e54283edad8b3cdf0ede13fdb54a721a9e6e0b4dd41c59d3335a0469fa605beaa4; hevc_supported=true; s_v_web_id=verify_maqom34f_4CqWXVbC_9I88_4Alw_9iJ3_5guXZCuXKoas; fpk1=U2FsdGVkX1/Kj2aYTRUPzvPwKcPE1c052sltw63SIKMbtTyEwjTPKevBdXoHrLfIW18lXp40SEMxzrHuwm1Zcg==; fpk2=b837718ffb5a3b4b1d9498234a1f1b0b; odin_tt=15722bc1d9d736666ed41d73c1b05c5219cc5b233c4186fa9977556aa462b692ad0c332b6a78ee88c1c2ce4d0d5a242ef9b20c9d67864c93dbcd40522b25729844e2d095f44b20231c857ed0d9ec66be; passport_csrf_token=c54d245d2f1f708045ea3939c5ed5c44; passport_csrf_token_default=c54d245d2f1f708045ea3939c5ed5c44; __security_mc_1_s_sdk_cert_key=cae837bb-4502-913d; __security_mc_1_s_sdk_sign_data_key_web_protect=5194a426-472a-8db9; __security_mc_1_s_sdk_crypt_sdk=9d897122-4d74-b93c; bd_ticket_guard_client_web_domain=2; SEARCH_RESULT_LIST_TYPE=%22single%22; _tea_utm_cache_1243=undefined; dy_swidth=360; dy_sheight=800; enter_pc_once=1; UIFID=47e05068b0a7733abcb242917ae42006325e9c99f9c28424accd11477c730b01c21c8a712edb7373e33eeddd3c28f97cf62ff02357da085657e1202a3975a63270c9d61869478f888384e7bbd196cc96c1467982718d4bad69461e137a0f0a456bef8db0a20bc803a6e4e63261dc6905c4eda7e24f55c1d58be7a009116cef8a90ad97e2935120884ed1b728412691df18500ef98f86ca4eb839433eb6f50f67; home_can_add_dy_2_desktop=%220%22; xgplayer_user_id=343579313575; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; __security_mc_1_s_sdk_sign_data_key_sso=6518d1b0-4316-826c; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.5%7D; strategyABtestKey=%221750205684.706%22; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A360%2C%5C%22screen_height%5C%22%3A800%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A8%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; __ac_nonce=06852222e00af938ce2dc; __ac_signature=_02B4Z6wo00f01fQydTgAAIDCtcN8p.0BJF30EnGAABVg36; ttwid=1%7CnkPSEnPtqgkqkIc6H3nnW8Kmaa1fzUCKJEnmewwwXZ0%7C1750213191%7C51b160c897ae5a3edf7a64c69eaab1e4c3f8519249243d6d28a8d06da4a65a79; biz_trace_id=7fd815ed; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCQjVCbnZXUzhUdGxRZFZ3M2RkdkdhM3ZhNWU5aXN0dnpLR21tTmdCc2NGRkQvdDZDSC9lNzdlZGxNR013TkhxWm83ZVVnV2REbEtTTlV4U1l5NkREKzA9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; douyin.com; xg_device_score=7.658235294117647; device_web_cpu_core=8; device_web_memory_size=8; architecture=amd64; IsDouyinActive=false'
headers = {
  'user-agent': user_agent,
  'Referer': 'https://www.douyin.com/',
  'cookie': cookie,
}


class BaseRequestModel(BaseModel):
  device_platform: str = 'webapp'
  aid: str = '6383'
  channel: str = 'channel_pc_web'
  update_version_code: str = '170400'
  pc_client_type: int = 1
  pc_libra_divert: str = 'Linux'
  support_h265: str = '1'
  support_dash: str = '0'
  version_code: str = '190500'
  version_name: str = '19.5.0'
  cookie_enabled: str = 'true'
  screen_width: int = 360
  screen_height: int = 800
  browser_language: str = 'zh-CN'
  browser_platform: str = 'Linux'
  browser_name: str = 'Chrome'
  browser_version: str = '137.0.0.0'
  browser_online: str = 'true'
  engine_name: str = 'Blink'
  engine_version: str = '137.0.0.0'
  os_name: str = 'Linux'
  os_version: str = 'x86_64'
  cpu_core_num: int = 8
  device_memory: int = 8
  platform: str = 'PC'
  downlink: str = '10'
  effective_type: str = '4g'
  round_trip_time: str = '50'
  from_user_page: str = '1'
  webid: str = '7504995072430982665'
  uifid: str = '47e05068b0a7733abcb242917ae42006325e9c99f9c28424accd11477c730b01c21c8a712edb7373e33eeddd3c28f97cf62ff02357da085657e1202a3975a63270c9d61869478f888384e7bbd196cc96c1467982718d4bad69461e137a0f0a456bef8db0a20bc803a6e4e63261dc6905c4eda7e24f55c1d58be7a009116cef8a90ad97e2935120884ed1b728412691df18500ef98f86ca4eb839433eb6f50f67'
  verifyFp: str = 'verify_maqom34f_4CqWXVbC_9I88_4Alw_9iJ3_5guXZCuXKoas'
  fp: str = 'verify_maqom34f_4CqWXVbC_9I88_4Alw_9iJ3_5guXZCuXKoas'


class PostDetail(BaseRequestModel):
  aweme_id: str


async def get_aweme_detail(aid: str):
  params = PostDetail(aweme_id=aid).model_dump()

  a_bogus = ABogus(user_agent=user_agent).generate_abogus(urlencode(params))[1]
  # logger.info(a_bogus)

  params.update(
    {
      'a_bogus': a_bogus,
    }
  )
  r = await util.get(
    'https://www.douyin.com/aweme/v1/web/aweme/detail/',
    params=params,
    headers=headers,
  )
  if not r.text or r.status_code != 200:
    return '请求失败'
  res = r.json()
  if res['status_code'] != 0:
    return '获取失败'
  res = res['aweme_detail']
  if res is None:
    return '视频不存在'
  res = {
    k: v
    for k, v in res.items()
    if k
    in ['author', 'aweme_id', 'video', 'desc', 'region', 'preview_title', 'item_title']
  }
  return res


def parse_aweme_detail(res):
  aid = res['aweme_id']
  title = res['item_title'] or res['desc']
  url = f'https://www.douyin.com/video/{aid}'
  # uid = res['author']['uid']
  # username = res['author']['unique_id']
  nickname = res['author']['nickname']
  sec_uid = res['author']['sec_uid']
  author_url = f'https://www.douyin.com/user/{sec_uid}'
  msg = f'<a href="{url}">{title}</a> - <a href="{author_url}">{nickname}</a> #douyin\nvia @{bot.me.username}'
  return msg
