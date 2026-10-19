# 点歌插件改动说明

基于 [astrbot_plugin_music v2.2.0](https://github.com/Zhalslar/astrbot_plugin_music)（MIT）。

## 1. 发送顺序：语音条 + 网易云卡片

`core/sender.py` 的 `_send_record_local`：语音发送成功后补发 `type=163` 卡片。

## 2. 副歌截取 + 响度归一

下载整首后解码 8kHz 单声道 PCM，按 1 秒 RMS 能量找最响的 8 秒窗口作为副歌起点，
从该处截 55 秒，`loudnorm=I=-16:TP=-1.5:LRA=11`，24kHz / 96kbps 单声道。

## 3. 仅中文歌变声（按歌词）

- 取歌词：`song.lyrics` 若是 URL，先用 `resolve_lyrics` 拉正文，再 `fetch_lyrics` 兜底
- 判定：假名 ÷（假名+汉字）> 15% → 日语 → 原声；否则汉字 ≥ 2 → 中文 → 变声
- 取不到歌词 → 按非中文处理

## 4. 只变人声 + 去伴奏

`tools/cover_one.py`：UVR5 分离人声/伴奏 → 只对人声做 RVC → **只输出人声**（不混伴奏）。

## 5. 命令

`main.py`：`filter.command("点歌", alias={..., "dg", ...})`，
并在 `on_search_song` 中把 `dg` 与 `点歌` 同等对待。

## 6. 国歌/红歌黑名单

`main.py` 顶部 `BLOCK_TERMS`，命中关键词或搜索结果标题即拒绝。

> 以上改动均为对 MIT 插件的本地修改，保留原作者版权声明。
