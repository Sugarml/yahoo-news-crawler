# Yahoo News Crawler
2025/11/24 13:40完成開發

這是一個 Scrapy 專案，用於爬取 Yahoo 奇摩新聞、Yahoo 股市新聞，
並自動解析：
- 新聞標題
- 新聞原始連結（含自動縮網址）
- 作者（含 TVBS 原站自動跳轉）
- 發布時間（限最近一小時）

並輸出結果給 pipelines 進行後處理（如儲存 CSV）。

---

## 🚀 功能特色

### ✓ 自動偵測來源媒體  
（ETtoday、三立、自由、TVBS、UDN、Yahoo 股市、Yahoo 名人娛樂…）

### ✓ TVBS 自動跳回原站抓取正確作者

### ✓ JSON-LD 作者解析  
優先使用 `<script type="application/ld+json">` 抓取作者姓名。

### ✓ 自動縮網址  
依序嘗試：
1. TinyURL  
2. is.gd  
3. 若失敗 → 使用原始網址

### ✓ 時間篩選：僅抓「最近 1 小時內發布」的新聞

---

## 📂 專案結構

yahoo-news-crawler/
│ scrapy.cfg
│ requirements.txt
│ README.md
│ .gitignore
│
└─yahoo_crawler/
│ items.py
│ pipelines.py
│ settings.py
│
└─spiders/
yahoo_spider.py

⚠ `.venv/` 請勿上傳！已列入 .gitignore。

---

## 📦 安裝環境

建立虛擬環境：

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

安裝套件：pip install -r requirements.txt

scrapy crawl yahoo_spider -o results.csv
