import scrapy
from yahoo_crawler.items import YahooCrawlerItem
from datetime import datetime, timedelta, timezone
import re
import json
import os
import requests


class YahooSpiderSpider(scrapy.Spider):
    name = "yahoo_spider"
    allowed_domains = ["tw.news.yahoo.com", "tw.stock.yahoo.com", "news.tvbs.com.tw"]

    start_urls = [
        "https://tw.news.yahoo.com/rss",
        "https://tw.news.yahoo.com/rss/politics",
        "https://tw.news.yahoo.com/rss/world",
        "https://tw.news.yahoo.com/rss/finance",
        "https://tw.news.yahoo.com/rss/society",
        "https://tw.news.yahoo.com/rss/tech",
        "https://tw.stock.yahoo.com/rss",
    ]

    # ==========================
    # 初始化
    # ==========================
    def __init__(self):
        taiwan_tz = timezone(timedelta(hours=8))
        self.now_tw = datetime.now(taiwan_tz).replace(tzinfo=None)
        self.one_hour_ago = self.now_tw - timedelta(hours=1)

        print(f"\n⚡ 抓取時間區間：{self.one_hour_ago} ~ {self.now_tw}\n")

        os.makedirs("logs", exist_ok=True)

        # 去重（依網址）
        self.visited_urls = set()

        # ★ URL 縮網址 cache（避免重複呼叫 API）
        self.url_cache = {}

    # ==========================
    # RSS
    # ==========================
    def parse(self, response):
        items = response.xpath("//item")
        print(f"RSS 取得新聞數：{len(items)} 來源：{response.url}")

        for node in items:
            title = node.xpath("title/text()").get()
            link = node.xpath("link/text()").get()

            if not link:
                continue

            # ★ 去重（依 URL）
            if link in self.visited_urls:
                continue
            self.visited_urls.add(link)

            yield scrapy.Request(
                link,
                callback=self.parse_detail,
                meta={"title": title, "original_link": link},
                dont_filter=True
            )

    # ==========================
    # Yahoo 內頁
    # ==========================
    def parse_detail(self, response):
        self.current_response = response

        title = response.meta["title"]
        original_link = response.meta["original_link"]

        # ---- 時間 ----
        time_str = response.css("time::attr(datetime)").get()
        if not time_str:
            return

        try:
            dt_utc = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            publish_time_tw = dt_utc.astimezone(
                timezone(timedelta(hours=8))
            ).replace(tzinfo=None)
        except:
            return

        # ★ 嚴格 60 分鐘內（你的 A-1）
        if not (self.one_hour_ago <= publish_time_tw <= self.now_tw):
            return

        # ---- 來源 ----
        source = self.extract_media(response)

        # ---- TVBS 需跳原文 ----
        if source == "TVBS":
            tvbs_url = self.extract_tvbs_original_url(response)
            if tvbs_url:
                return scrapy.Request(
                    tvbs_url,
                    callback=self.parse_tvbs,
                    meta={
                        "title": title,
                        "original_link": original_link,
                        "publish_time": publish_time_tw
                    },
                    dont_filter=True
                )

        # ---- 作者 ----
        author = self.extract_author(response, source)

        return self.return_item(title, original_link, author, publish_time_tw)

    # ==========================
    # TVBS 原站
    # ==========================
    def parse_tvbs(self, response):
        self.current_response = response
        title = response.meta["title"]
        original_link = response.meta["original_link"]
        publish_time_tw = response.meta["publish_time"]

        author = response.css("div.author a::text").get()
        if not author:
            author = response.css("span.author-name::text").get()

        author = author.strip() if author else "TVBS 新聞中心"

        return self.return_item(title, original_link, author, publish_time_tw)

    # ==========================
    # 來源判斷（不輸出 CSV）
    # ==========================
    def extract_media(self, response):
        media = response.css("div.caas-attr-provider-logo img::attr(alt)").get()
        if media:
            return media.strip()

        meta = response.css("div.caas-attr-meta::text").get()
        if meta:
            meta = meta.strip()
            if "｜" in meta:
                return meta.split("｜")[-1].strip()
            return meta

        url = response.url.lower()
        mapping = {
            "ettoday": "ETtoday",
            "setn": "三立新聞",
            "ftnn": "FTNN",
            "ltn": "自由時報",
            "tvbs": "TVBS",
            "udn": "聯合報",
            "/stock/": "Yahoo股市",
            "/entertainment/": "Yahoo名人娛樂",
        }
        for k, v in mapping.items():
            if k in url:
                return v

        return "未知來源"

    # ==========================
    # TVBS 原文 URL
    # ==========================
    def extract_tvbs_original_url(self, response):
        for url in response.css("a::attr(href)").getall():
            if url and "news.tvbs.com.tw" in url:
                return url
        return None

    # ==========================
    # 作者解析（JSON-LD + fallback）
    # ==========================
    def extract_author(self, response, source):
        debug = f"[作者] {response.url}"

        # --- JSON-LD ---
        json_blocks = response.xpath(
            '//script[@type="application/ld+json"]/text()'
        ).getall()

        for block in json_blocks:
            try:
                data = json.loads(block)

                if isinstance(data, dict) and "author" in data:
                    author_data = data["author"]

                    # list
                    if isinstance(author_data, list) and len(author_data) > 0:
                        name = author_data[0].get("name")
                        if name:
                            print(f"{debug} JSON-LD：{name}")
                            return name.strip()

                    # dict
                    if isinstance(author_data, dict):
                        name = author_data.get("name")
                        if name:
                            print(f"{debug} JSON-LD：{name}")
                            return name.strip()

            except:
                pass

        # --- caas-author-name ---
        author = response.css("span.caas-author-name::text").get()
        if author:
            return author.strip()

        # --- meta ---
        meta_author = response.css("meta[name='author']::attr(content)").get()
        if meta_author:
            return meta_author.strip()

        # --- 正文 regex ---
        body = response.css(".caas-body").xpath("string(.)").get()
        if body:
            text = body.replace(" ", "").replace("\n", "")
            patterns = [
                r"(記者[\u4e00-\u9fa5]{2,3})[／/]",
                r"([\u4e00-\u9fa5]{2,3})／綜合報導",
                r"(編譯[\u4e00-\u9fa5]{2,3})"
            ]
            for p in patterns:
                m = re.search(p, text)
                if m:
                    return m.group(1)

        # --- Dump HTML ---
        dump = f"logs/no_author_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(dump, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"{debug} ❌ 作者找不到 → {dump}")

        fallback_map = {
            "三立新聞": "三立新聞中心",
            "ETtoday": "ETtoday 新聞雲中心",
            "TVBS": "TVBS 新聞中心",
            "中央社": "中央社",
            "聯合報": "聯合報中心",
            "FTNN": "FTNN 新聞組",
            "Yahoo股市": "Yahoo 股市編輯部",
            "Yahoo名人娛樂": "Yahoo 名人娛樂編輯部"
        }

        return fallback_map.get(source, f"{source} 新聞中心")

    # ==========================
    # ★★★ 最終版縮網址（TinyURL → is.gd → 原始網址）
    # ==========================
    def shorten_url(self, long_url):

        if long_url in self.url_cache:
            return self.url_cache[long_url]

        # TinyURL
        try:
            tiny = f"https://tinyurl.com/api-create.php?url={long_url}"
            r = requests.get(tiny, timeout=4)
            if r.status_code == 200:
                url = r.text.strip()
                if url.startswith("http"):
                    self.url_cache[long_url] = url
                    return url
        except:
            pass

        # is.gd
        try:
            isgd = f"https://is.gd/create.php?format=simple&url={long_url}"
            r = requests.get(isgd, timeout=4)
            if r.status_code == 200:
                url = r.text.strip()
                if url.startswith("http"):
                    self.url_cache[long_url] = url
                    return url
        except:
            pass

        # fallback
        self.url_cache[long_url] = long_url
        return long_url

    # ==========================
    # 輸出 item（固定欄位順序）
    # ==========================
    def return_item(self, title, original_link, author, publish_time_tw):
        item = YahooCrawlerItem()
        item["標題"] = title
        item["連結"] = self.shorten_url(original_link)
        item["作者"] = author
        item["日期"] = publish_time_tw.strftime("%Y-%m-%d %H:%M")
        return item
