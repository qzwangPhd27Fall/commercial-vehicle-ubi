# -*- coding: utf-8 -*-
"""用 Playwright 查证对标公司 + 市场规模公开数据"""
import json, sys
from playwright.sync_api import sync_playwright

OUT = {}

def grab(page, url, wait=2500):
    try:
        page.goto(url, timeout=40000, wait_until='domcontentloaded')
        page.wait_for_timeout(wait)
        return page.inner_text('body')[:4000]
    except Exception as e:
        return f'[ERR] {e}'

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36', locale='en-US')
    page = ctx.new_page()

    # 1. Samsara 财务概览
    print('=== Samsara ===')
    t = grab(page, 'https://stockanalysis.com/stocks/IOT/')
    print(t[:2000])

    # 2. Samsara 财务年报
    print('\n=== Samsara financials ===')
    t = grab(page, 'https://stockanalysis.com/stocks/IOT/financials/')
    print(t[:2000])

    b.close()
