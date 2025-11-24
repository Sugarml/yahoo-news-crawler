BOT_NAME = "yahoo_crawler"

SPIDER_MODULES = ["yahoo_crawler.spiders"]
NEWSPIDER_MODULE = "yahoo_crawler.spiders"

ROBOTSTXT_OBEY = False

# 避免亂碼
FEED_EXPORT_ENCODING = "utf-8-sig"

# CSV 欄位順序
FEED_EXPORT_FIELDS = ["標題", "連結", "作者", "日期"]
