# anon-qq-bot

> 一个以《BanG Dream! It's MyGO!!!!!》**千早爱音**为群友人设的 QQ AI 机器人。
> **非官方二次创作，仅供学习交流，禁止商用。**

## 功能

- **群聊读空气**：不 @ 也有概率自然接话（[astrbot_plugin_group_chat_plus](https://github.com/Him666233/astrbot_plugin_group_chat_plus)）
- **抽卡**：从 AniList 人气榜（按收藏数）**前 500** 随机抽一名角色，带**中文译名 + 出处 + 角色图**
  - 每个 QQ 号每天限抽一次，当天重复抽只显示第一次结果
  - 图片走 URL 在线直发，不落地
- **点歌**：`/dg 歌名`（网易云）
  - 自动定位副歌，截 55 秒
  - 中文歌可选 RVC 换成千早爱音音色（**只变人声，去掉伴奏**）
  - 发送「语音条 + 网易云 163 卡片」
- **陪伴增强**：按人记忆、日记、受控唤醒（[companion-kit-dream](https://github.com/DreamsTOF/astrbot_plugin_companion-kit-dream)）
- **表情包**：回复时按概率附加爱音表情包（语义匹配）

## 架构

```
QQ 客户端 / 手机
   │ 扫码登录
   ▼
NapCatQQ（OneBot v11 协议端）
   │ 反向 WebSocket  ws://127.0.0.1:6199/ws
   ▼
AstrBot 4.29+
   ├─ astrbot_plugin_group_chat_plus   读空气 / 触发词 / 黑名单
   ├─ astrbot_plugin_music             网易云点歌（含本仓库补丁）
   ├─ astrbot_plugin_companion_kit     陪伴增强
   ├─ gacha                            抽卡（本仓库）
   └─ anon_sticker                     表情包（本仓库）
```

## 依赖

| 组件 | 版本 | 说明 |
|---|---|---|
| [AstrBot](https://github.com/AstrBotDevs/AstrBot) | >= 4.29 | LLM 管家，`uv tool install astrbot --python 3.12` |
| [NapCatQQ](https://github.com/NapNeko/NapCatQQ) | 最新 OneKey | QQ 协议端，**请自行从官方 Release 下载** |
| [group_chat_plus](https://github.com/Him666233/astrbot_plugin_group_chat_plus) | 最新 | 读空气插件 |
| [astrbot_plugin_music](https://github.com/Zhalslar/astrbot_plugin_music) | v2.2.0 | 点歌插件（本仓库提供补丁说明） |
| [companion-kit-dream](https://github.com/DreamsTOF/astrbot_plugin_companion-kit-dream) | v0.1.0 | 陪伴增强 |

> NapCatQQ 使用**自定义许可**（允许转载但修改版不得公开、禁止商用），因此本仓库**不包含**它的任何代码或二进制。

## 安装

```powershell
# 1. AstrBot
uv tool install astrbot --python 3.12
$env:ASTRBOT_ROOT = "D:\qqaibot\astrbot"

# 2. NapCatQQ
#    到 https://github.com/NapNeko/NapCatQQ/releases 下载
#    NapCat.Shell.Windows.OneKey.zip，解压后运行安装器

# 3. 插件（放进 AstrBot 的 data/plugins/）
git clone https://github.com/Him666233/astrbot_plugin_group_chat_plus
git clone https://github.com/Zhalslar/astrbot_plugin_music
git clone https://github.com/DreamsTOF/astrbot_plugin_companion-kit-dream

# 4. 本仓库的插件
Copy-Item .\plugins\gacha  <ASTRBOT_ROOT>\data\plugins\ -Recurse

# 5. 人格卡
#    把 persona/persona_anon.md 的内容写入 AstrBot 的 personas 表，
#    persona_id 与 cmd_config.json 中 agent_runner.config.persona.persona_id 保持一致
```

详细步骤见 [scripts/install.ps1](scripts/install.ps1) 与 [patches/music_plugin_changes.md](patches/music_plugin_changes.md)。

## 必须自己填的配置（不要提交）

| 配置 | 位置 | 说明 |
|---|---|---|
| 大模型 API key | AstrBot `data/cmd_config.json` → `provider_sources[0].key` | 任何 OpenAI 兼容服务 |
| 管理员 QQ | `cmd_config.json` → `admins_id` | 你的大号，不是 bot 号 |
| bot QQ | NapCat 扫码后自动生成 | 不要写进仓库 |
| 代理 | `cmd_config.json` → `http_proxy` | 可选 |

## 目录结构

```
.
├─ README.md
├─ LICENSE
├─ THIRD_PARTY_LICENSES.md
├─ config/
│  └─ config.example.md
├─ patches/
│  └─ music_plugin_changes.md
├─ persona/
│  └─ persona_anon.md
├─ plugins/
│  └─ gacha/                 # 抽卡插件
├─ scripts/
│  └─ install.ps1
└─ tools/
   └─ cover_one.py           # 人声分离 + RVC 变声
```

## 免责声明

1. **角色版权**：千早爱音及《BanG Dream! It's MyGO!!!!!》版权归 Bushiroad 所有。本仓库的人格卡属于粉丝二次创作，不代表官方。
2. **声音克隆**：本仓库**不包含任何 RVC 模型权重**。音色模型涉及声优声音权，请勿公开分发或商用。
3. **QQ 协议端**：NapCatQQ 为第三方协议实现，使用非官方客户端存在账号风控、冻结、封禁风险，请务必使用小号。
4. **合规**：请遵守所在地法律法规与腾讯软件许可协议，仅用于个人学习交流。

## License

本仓库自有代码采用 [MIT](LICENSE) 许可证；第三方组件遵循各自许可证，见 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)。
