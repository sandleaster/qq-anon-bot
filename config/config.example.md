# 配置说明（示例）

## AstrBot `data/cmd_config.json`

```jsonc
{
  "provider_sources": [
    { "provider": "deepseek", "key": ["<YOUR_API_KEY>"], "api_base": "https://api.deepseek.com" }
  ],
  "admins_id": ["<YOUR_QQ_NUMBER>"],
  "dashboard": { "username": "astrbot", "password": "" }
}
```

## group_chat_plus 常用项

| 键 | 建议 |
|---|---|
| `trigger_keywords` | 爱音 / 千早爱音 / Anon |
| `keyword_smart_mode` | false（触发词必回） |
| `blacklist_keywords` | 自己维护 |
| `initial_probability` | 0.1 |

## 点歌

- 命令：`/dg 歌名`
- 发送顺序：语音条（副歌 55 秒）→ 163 卡片
- 仅中文歌词才会做爱音变声（见 `patches/music_plugin_changes.md`）

## 人设卡占位符

`persona/persona_anon.md` 里的 `<BEST_FRIEND_QQ>` 需要替换成你自己的大号 QQ（只写进人设卡，不会用于登录）。
