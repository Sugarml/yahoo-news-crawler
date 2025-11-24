import scrapy

class YahooCrawlerItem(scrapy.Item):
    標題 = scrapy.Field()
    連結 = scrapy.Field()
    作者 = scrapy.Field()
    日期 = scrapy.Field()
