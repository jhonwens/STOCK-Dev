#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 实时行情和资金流向爬取模块（腾讯财经API）

import time
import requests
from datetime import datetime

class StockCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

    def get_realtime_tencent(self, stock_code):
        """通过腾讯API获取实时行情"""
        try:
            market = 'sh' if stock_code.startswith('6') else 'sz'
            url = f'http://qt.gtimg.cn/q={market}{stock_code}'
            
            resp = requests.get(url, timeout=5)
            text = resp.text
            
            if '=' in text:
                import re
                m = re.search(r'=(.+)', text)
                if not m:
                    return None
                data = m.group(1).rstrip(';').strip('"')
                fields = data.split('~')
                
                if len(fields) < 10:
                    return None
                    
                # 修正字段索引
                price = float(fields[3]) if fields[3] else 0
                yesterday_close = float(fields[4]) if fields[4] else 0
                change_pct = 0
                if yesterday_close > 0:
                    change_pct = round((price - yesterday_close) / yesterday_close * 100, 2)
                change_amt = price - yesterday_close if price and yesterday_close else 0
                volume = int(fields[6]) if fields[6] else 0
                amount = float(fields[7]) * 1000 if fields[7] else 0  # 转成元
                turnover = float(fields[38]) if fields[38] else 0
                pe_ttm = float(fields[39]) if fields[39] else 0
                
                return {
                    'code': stock_code,
                    'name': fields[1],
                    'price': price,
                    'yesterday_close': yesterday_close,
                    'change_amt': round(change_amt, 2),
                    'change_pct': change_pct,
                    'volume': volume,
                    'amount': amount,
                    'pe': pe_ttm,
                    'pb': 0,
                    'turnover': turnover,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'trade_date': datetime.now().strftime('%Y-%m-%d')
                }
            return None
        except Exception as e:
            print(f"获取{stock_code}失败: {e}")
            return None

    def get_realtime(self, stock_code):
        """获取实时行情"""
        data = self.get_realtime_tencent(stock_code)
        
        if not data or not data.get('price'):
            return {
                'code': stock_code,
                'name': '',
                'price': 0,
                'change_pct': 0,
                'change_amt': 0,
                'volume': 0,
                'amount': 0,
                'pe': 0,
                'pb': 0,
                'turnover': 0,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'trade_date': datetime.now().strftime('%Y-%m-%d')
            }
        
        return data

    def get_fund_flow(self, stock_code):
        """获取资金流向（基于成交量估算，简单处理）"""
        try:
            market = 'sh' if stock_code.startswith('6') else 'sz'
            url = f'http://qt.gtimg.cn/q={market}{stock_code}'
            
            resp = requests.get(url, timeout=5)
            text = resp.text
            
            if '=' in text:
                import re
                m = re.search(r'=(.+)', text)
                if not m:
                    return {'code': stock_code, 'main_inflow': 0, 'update_date': datetime.now().strftime('%Y-%m-%d')}
                
                data = m.group(1).rstrip(';').strip('"')
                fields = data.split('~')
                
                if len(fields) > 10:
                    # 简单估算：成交量 * 价格 * 0.1 作为主力资金参考
                    volume = int(fields[6]) if fields[6] else 0
                    price = float(fields[3]) if fields[3] else 0
                    amount = volume * price  # 成交额(元)
                    
                    # 根据成交量估算主力净流入（假设主力占比30%）
                    main_inflow = amount * 0.3 if volume > 0 else 0
                    
                    return {
                        'code': stock_code,
                        'main_inflow': main_inflow,
                        'update_date': datetime.now().strftime('%Y-%m-%d'),
                    }
        except:
            pass
        
        return {'code': stock_code, 'main_inflow': 0, 'update_date': datetime.now().strftime('%Y-%m-%d')}

    def batch_crawl_realtime(self, stock_codes):
        """批量爬取实时行情"""
        results = []
        for code in stock_codes:
            data = self.get_realtime(code)
            results.append(data)
            time.sleep(0.15)
        return results

    def batch_crawl_fund_flow(self, stock_codes):
        """批量爬取资金流向"""
        results = []
        for code in stock_codes:
            data = self.get_fund_flow(code)
            results.append(data)
            time.sleep(0.15)
        return results


if __name__ == "__main__":
    crawler = StockCrawler()
    test_codes = ['600519', '000651', '002475']
    
    print("=== 腾讯财经API测试 ===")
    for code in test_codes:
        data = crawler.get_realtime_tencent(code)
        if data:
            print(f"{code}: {data.get('name')} 价格={data.get('price')} 涨跌幅={data.get('change_pct')}%")