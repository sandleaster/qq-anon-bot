"""抽卡插件（在线检索版，每号每天一次）

有人发「抽卡」→ 从 AniList 人气榜（按收藏数排序）前 500 名里随机抽一个，
并附上角色图。图片只发 URL，不下载到本地：
  1) 先尝试萌娘百科角色页主图（通常 1000~1600px，尽量高清）
  2) 查不到再用 AniList 自带的图

AniList 榜单常驻内存，12 小时自动刷新；接口挂了就用本地兜底池
（D:\\qqaibot\\gacha\\manifest.json 里已有的 28 个角色）。
抽卡记录：D:\\qqaibot\\gacha\\users.json（每号每天一次）。
"""

import asyncio
import datetime
import io
import json
import os
import random
import time
import urllib.parse
import urllib.request

import astrbot.api.message_components as Comp
from astrbot.api import logger, star
from astrbot.api.event import AstrMessageEvent, filter

POOL_DIR = r"D:\qqaibot\gacha"
LOCAL_MANIFEST = os.path.join(POOL_DIR, "manifest.json")
STORE = os.path.join(POOL_DIR, "users.json")
ZH_CACHE_FILE = os.path.join(POOL_DIR, "zh_cache.json")
CMD_CONFIG = r"D:\qqaibot\astrbot\data\cmd_config.json"
TRIGGERS = ("抽卡", "抽个卡", "抽一发", "来一发抽卡")

ANILIST = "https://graphql.anilist.co/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")
POOL_TTL = 12 * 3600
TOTAL = 500
PER_PAGE = 50

QUERY = """
query($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    characters(sort: FAVOURITES_DESC) {
      id
      name { full native }
      favourites
      image { large }
      media(perPage: 1) { nodes { title { native romaji } } }
    }
  }
}
"""


def has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff" for ch in s)


class Main(star.Star):
    def __init__(self, context: star.Context) -> None:
        self.context = context
        self.users = {}
        self.local = []
        self.pool = []
        self.pool_ts = 0.0
        self.hd_cache = {}
        self.zh = {}
        self._last = None
        self._load_users()
        self._load_zh()
        self._load_local()
        logger.info("[gacha] 已加载（在线模式），本地兜底 %d 个，抽卡记录 %d 条"
                    % (len(self.local), len(self.users)))

    # ---------- 本地状态 ----------
    def _load_users(self):
        try:
            with io.open(STORE, encoding="utf-8-sig") as f:
                self.users = json.load(f)
        except Exception:
            self.users = {}

    def _save_users(self):
        try:
            tmp = STORE + ".tmp"
            io.open(tmp, "w", encoding="utf-8").write(
                json.dumps(self.users, ensure_ascii=False, indent=1))
            os.replace(tmp, STORE)
        except Exception as e:
            logger.error("[gacha] 保存抽卡记录失败: %s" % e)

    def _load_local(self):
        try:
            with io.open(LOCAL_MANIFEST, encoding="utf-8-sig") as f:
                raw = json.load(f)
            self.local = [x for x in raw
                          if x.get("file") and os.path.isfile(os.path.join(POOL_DIR, x["file"]))]
        except Exception:
            self.local = []

    def _load_zh(self):
        try:
            with io.open(ZH_CACHE_FILE, encoding="utf-8-sig") as f:
                self.zh = json.load(f)
        except Exception:
            self.zh = {}

    def _save_zh(self):
        try:
            tmp = ZH_CACHE_FILE + ".tmp"
            io.open(tmp, "w", encoding="utf-8").write(
                json.dumps(self.zh, ensure_ascii=False, indent=1))
            os.replace(tmp, ZH_CACHE_FILE)
        except Exception as e:
            logger.warning("[gacha] 保存中文译名失败: %s" % e)

    @staticmethod
    def _api_key():
        k = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        if k:
            return k
        try:
            with io.open(CMD_CONFIG, encoding="utf-8-sig") as f:
                cfg = json.load(f)
            return (cfg["provider_sources"][0].get("key") or [""])[0]
        except Exception:
            return ""

    def _translate(self, pick):
        """返回 {name_zh, series_zh}；失败返回空 dict。"""
        key = str(pick.get("anilist_id") or pick.get("name") or "")
        if key in self.zh:
            return self.zh[key]
        api_key = self._api_key()
        if not api_key:
            return {}
        prompt = (
            "角色（罗马音/日文）：%s / %s\n所属作品（日文/罗马音）：%s\n"
            "请给出这两个名字的标准简体中文译名。"
            "只输出 JSON：{\"name_zh\":\"...\",\"series_zh\":\"...\"}。"
            "如果确实没有通行译名，就保留原文。"
            % (pick.get("name", ""), pick.get("native", ""), pick.get("series", ""))
        )
        body = {
            "model": "deepseek-flash",
            "messages": [
                {"role": "system",
                 "content": "你是动漫资料库，只输出 JSON，不要解释。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 200,
            "temperature": 0,
            "thinking": {"type": "disabled"},
        }
        try:
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Authorization": "Bearer " + api_key,
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                txt = json.loads(r.read().decode("utf-8", "replace"))
            content = txt["choices"][0]["message"]["content"]
            m = content.find("{")
            n = content.rfind("}")
            data = json.loads(content[m:n + 1]) if m >= 0 and n > m else {}
            out = {"name_zh": (data.get("name_zh") or "").strip(),
                   "series_zh": (data.get("series_zh") or "").strip()}
            if out["name_zh"] or out["series_zh"]:
                self.zh[key] = out
                self._save_zh()
            return out
        except Exception as e:
            logger.warning("[gacha] 中文译名获取失败: %s" % str(e)[:80])
            return {}

    # ---------- AniList ----------
    @staticmethod
    def _gql(page):
        body = json.dumps({"query": QUERY,
                           "variables": {"page": page, "perPage": PER_PAGE}}).encode()
        req = urllib.request.Request(ANILIST, data=body, headers={
            "User-Agent": UA, "Content-Type": "application/json",
            "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    def _fetch_pool(self):
        rows = []
        for page in range(1, TOTAL // PER_PAGE + 1):
            try:
                data = self._gql(page)
                rows.extend(data["data"]["Page"]["characters"])
            except Exception as e:
                logger.warning("[gacha] AniList 第 %d 页失败: %s" % (page, str(e)[:60]))
        out = []
        for i, c in enumerate(rows[:TOTAL], 1):
            names = c.get("name") or {}
            native = names.get("native") or ""
            full = names.get("full") or ""
            name = native if native and has_cjk(native) else (full or native)
            media = ((c.get("media") or {}).get("nodes") or [{}])[0]
            title = ((media.get("title") or {}).get("native")
                     or (media.get("title") or {}).get("romaji") or "")
            rarity = "UR" if i <= 10 else ("SSR" if i <= 50 else ("SR" if i <= 150 else "R"))
            out.append({
                "name": name, "native": native, "series": title,
                "rarity": rarity, "image": (c.get("image") or {}).get("large") or "",
                "favourites": c.get("favourites"), "rank": i,
            })
        return [x for x in out if x["image"]]

    async def _ensure_pool(self):
        if self.pool and time.time() - self.pool_ts < POOL_TTL:
            return self.pool
        try:
            pool = await asyncio.to_thread(self._fetch_pool)
            if pool:
                self.pool = pool
                self.pool_ts = time.time()
                logger.info("[gacha] AniList 榜单已刷新：%d 个角色" % len(pool))
        except Exception as e:
            logger.warning("[gacha] AniList 刷新失败：%s" % str(e)[:80])
        return self.pool

    # ---------- 高清图 ----------
    def _moegirl_hd(self, name: str) -> str:
        if not name:
            return ""
        if name in self.hd_cache:
            return self.hd_cache[name]
        url = ""
        try:
            url = self._moegirl_pageimage(name)
        except Exception:
            url = ""
        self.hd_cache[name] = url
        return url

    @staticmethod
    def _moegirl_pageimage(title: str) -> str:
        if not title:
            return ""
        try:
            api = ("https://zh.moegirl.org.cn/api.php?action=query&format=json"
                   "&prop=pageimages&piprop=original&redirects=1&titles="
                   + urllib.parse.quote(title))
            req = urllib.request.Request(api, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            for p in data.get("query", {}).get("pages", {}).values():
                src = (p.get("original") or {}).get("source") or ""
                if src:
                    return src
        except Exception:
            pass
        return ""

    # ---------- 抽卡 ----------
    @filter.event_message_type(filter.EventMessageType.ALL, priority=1)
    async def draw(self, event: AstrMessageEvent):
        text = (event.get_message_str() or "").strip()
        if not text or len(text) > 12:
            return
        if not any(t in text for t in TRIGGERS):
            return

        event.stop_event()
        uid = str(event.get_sender_id())
        today = datetime.date.today().isoformat()
        rec = self.users.get(uid)

        if rec and rec.get("date") == today and rec.get("image"):
            yield event.chain_result([
                Comp.Plain("今天抽过了：%s" % rec.get("line", "")),
                Comp.Image.fromURL(rec["image"]),
            ])
            return

        pool = await self._ensure_pool()
        pick = None
        if pool:
            pool2 = pool
            if len(pool2) > 1 and self._last:
                pool2 = [x for x in pool2 if x.get("name") != self._last] or pool2
            pick = random.choice(pool2)
            self._last = pick.get("name")
            zh = await asyncio.to_thread(self._translate, pick)
            name = zh.get("name_zh") or pick.get("name") or ""
            series = zh.get("series_zh") or pick.get("series") or ""
            # 用中文名去查萌娘百科，命中率高得多；查不到就用 AniList 图
            hd = await asyncio.to_thread(self._moegirl_hd, name) if name else ""
            image = hd or pick["image"]
            line = "【%s】%s《%s》" % (pick["rarity"], name, series)
        elif self.local:
            pick = random.choice(self.local)
            image = os.path.join(POOL_DIR, pick["file"])
            line = "【%s】%s《%s》" % (
                pick.get("rarity", ""), pick.get("name", ""), pick.get("series", ""))
        else:
            yield event.plain_result("诶——卡池暂时取不到")
            return

        self.users[uid] = {
            "date": today,
            "name": pick.get("name", ""),
            "series": pick.get("series", ""),
            "rarity": pick.get("rarity", ""),
            "line": line,
            "image": image,
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self._save_users()

        comp = (Comp.Image.fromURL(image) if image.startswith("http")
                else Comp.Image.fromFileSystem(image))
        yield event.chain_result([Comp.Plain(line), comp])
