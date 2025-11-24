@echo off
cd /d F:\code\yahoo_news_project\yahoo_crawler
call ..\venv\Scripts\activate

REM 自動產生 yyyy-mm-dd-hh 格式（不用中文日期）
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (
    set mm=%%a
    set dd=%%b
    set yyyy=%%c
)

for /f "tokens=1 delims=: " %%h in ('time /t') do (
    set hh=%%h
)

if "%hh:~0,1%"=="0" set hh=%hh:~1%

set filename=yahoo_%yyyy%-%mm%-%dd%-%hh%.csv

scrapy crawl yahoo_spider -O %filename%
