#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 财务指标获取模块（使用腾讯实时API扩展）

import requests
from datetime import datetime

class FinanceFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

    def get_finance_data(self, stock_code):
        """从腾讯实时API获取财务指标"""
        try:
            market = 'sh' if stock_code.startswith('6') else 'sz'
            url = f'http://qt.gtimg.cn/q={market}{stock_code}'
            
            resp = requests.get(url, timeout=10, headers=self.headers)
            text = resp.text
            
            if '=' in text:
                import re
                m = re.search(r'=(.+)', text)
                if not m:
                    return None
                data = m.group(1).rstrip(';').strip('"')
                fields = data.split('~')
                
                if len(fields) < 40:
                    return None
                
                # 从实时数据中提取
                pe = float(fields[38]) if fields[38] else 0  # 市盈率
                pb = float(fields[39]) if fields[39] else 0  # 市净率
                total_mv = float(fields[36]) if fields[36] else 0  # 总市值(亿元)
                circ_mv = float(fields[37]) if fields[37] else 0  # 流通市值(亿元)
                
                return {
                    'code': stock_code,
                    'name': fields[1],
                    'roe': 0,  # 需要专门API
                    'revenue': total_mv,  # 简化为市值
                    'profit': circ_mv,
                    'eps': 0,
                    'bvps': 0,
                    'pe': pe,
                    'pb': pb,
                    'report_date': datetime.now().strftime('%Y-%m-%d'),
                }
        except Exception as e:
            print(f"获取{stock_code}财务数据失败: {e}")
        
        return None

    def batch_fetch(self, stock_codes):
        """批量获取财务数据"""
        results = []
        for code in stock_codes:
            data = self.get_finance_data(code)
            if data:
                results.append(data)
            else:
                results.append({
                    'code': code,
                    'name': '',
                    'roe': 0,
                    'revenue': 0,
                    'profit': 0,
                    'eps': 0,
                    'bvps': 0,
                    'report_date': datetime.now().strftime('%Y-%m-%d')
                })
        return results


if __name__ == "__main__":
    fetcher = FinanceFetcher()
    test_codes = ['600519', '000651', '002475']
    
    print("=== 财务指标 ===")
    for code in test_codes:
        data = fetcher.get_finance_data(code)
        if data:
            print(f"{code}: PE={data.get('pe')}, PB={data.get('pb')}, 市值={data.get('revenue')}亿")