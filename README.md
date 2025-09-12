# mtgbot-plugins
[mtgbot](https://github.com/HBcao233/mtgbot) 框架下的一些 plugins

| 插件名 | 功能 | 依赖 | 配置项 | 
| :----: | :----: | :----: | :----: |
| soutu | 搜图 | | `saucenao_api_key` |
| mark | 给媒体添加遮罩 | | |
| merge <br> (依赖`mark`插件) | 合并媒体 | | |
| info | 查看消息详细信息 | |
| roll | 投骰子| | |
| guess | 猜点数 | | |
| gif | 视频/动图/贴纸格式转换 | | |
| communicate | 传话机器人 | | `echo_chat_id` |
| telegraph_setting | 提供用户自定义 telegraph作者配置项 | | |
|||||
| pixiv | pixiv爬取 | | `pixiv_PHPSESSID` |
| twitter | X爬取 | | `twitter_csrf_token`, `twitter_auth_token` |
| misskey | misskey get note | | `misskey_token` |
| bili | bili爬取 | | `bili_SESSDATA` |
| kemono | kemono爬取 | |
| ehentai | ehentai爬取 | `bs4` | `ex_ipb_member_id`, `ex_ipb_pass_hash`, `ex_igneous` |
| fanbox | fanbox爬取 | | |
| nhentai | nhentai 爬取 (tags中文依赖于 `ehentai/ehtags-cn.json`) | | |
| douyin | 抖音解析 | |
| youtube | youtube解析 | `yt-dlp` | `youtube_token` |
| qqmusic | QQ音乐解析 | `qqmusic-api-python` | `qqmusic_musicid`, `qqmusic_musickey`, `qqmusic_refresh_key`, `qqmusic_refresh_token`, `qqmusic_encrypt_uin`|
| 163music | 网易云音乐解析 | `pycryptodome` | `163music_csrf_token`, `163music_u` |
| instagram | instagram解析 || `instagram_csrftoken`, `instagram_sessionid` | |
|||||
| keyword | 关键词回复 | | `superadmin` |
| pan | tg网盘 | | |
| lighton | 点灯游戏 | | |
| randomsese | 随机涩图 | | |
| bookkeeping | 小记账本 | | |
| randcat | 随机猫狗 | | |
| chat | Deepseek 聊天 | `openai` | |
| autoban | 自动封禁名字带有 '翻墙' '免费' '直连' '直接登录' 的用户 | | |