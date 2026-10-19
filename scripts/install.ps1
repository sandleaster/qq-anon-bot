# 安装脚本模板（按需修改路径）
# 1) 安装 uv（如果没有）
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2) 安装 AstrBot
uv tool install astrbot --python 3.12
$INSTALL = "D:\qqaibot"
$env:ASTRBOT_ROOT = "$INSTALL\astrbot"
[Environment]::SetEnvironmentVariable("ASTRBOT_ROOT", $env:ASTRBOT_ROOT, "User")

# 3) 初始化数据目录（必须在目标目录下执行）
New-Item -ItemType Directory -Force -Path $INSTALL\astrbot | Out-Null
Set-Location $INSTALL\astrbot
& "$env:USERPROFILE\.local\bin\astrbot.exe" init -y

# 4) 放置插件（先自行 clone 上游插件）
$PLUGINS = "$INSTALL\astrbot\data\plugins"
# git clone <group_chat_plus> $PLUGINS\astrbot_plugin_group_chat_plus
# git clone <music>         $PLUGINS\astrbot_plugin_music
# git clone <companion>     $PLUGINS\astrbot_plugin_companion-kit-dream
Copy-Item .\plugins\gacha $PLUGINS\gacha -Recurse

# 5) 配置 cmd_config.json（API key、admins_id），这一步请手动填，不要提交密钥

# 6) NapCatQQ：下载官方 OneKey 包并安装，然后扫码登录

# 7) 启动
Write-Host "配置完成后运行 AstrBot 并在 NapCat 窗口扫码"
