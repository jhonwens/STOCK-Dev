#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 历史K线数据爬取脚本

import os
import sys
import yaml
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import baostock as bs
except:
    print("请安装baostock: pip3 install baostock")
    sys.exit(1)

from db_manager import DBManager


class HistoryCrawler:
    def __init__(self, db_path):
        self.db = DBManager(db_path)
        self._login()
    
    def _login(self):
        """登录baostock"""
        lg = bs.login()
        if lg.error_code != '0':
            print(f"登录失败: {lg.error_msg}")
    
    def get_code_with_exchange(self, code):
        """转换股票代码为baostock格式"""
        if code.startswith('6'):
            return f"sh.{code}"
        else:
            return f"sz.{code}"
    
    def fetch_history(self, code, years=5):
        """获取历史K线数据"""
        try:
            bs_code = self.get_code_with_exchange(code)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - relativedelta(years=years)).strftime('%Y-%m-%d')
            
            fields = "date,open,high,low,close,volume,amount,turn"
            rs = bs.query_history_k_data_plus(bs_code, fields,
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2")
            
            if rs.error_code != '0':
                print(f"  查询失败: {rs.error_msg}")
                return []
            
            data_list = []
            while rs.next():
                row = rs.get_row_data()
                if row[0]:
                    change_pct = 0
                    change_amt = 0
                    if len(row) >= 5 and row[4] and row[3]:
                        try:
                            prev_close = float(row[3])
                            close = float(row[4])
                            if prev_close > 0:
                                change_pct = (close - prev_close) / prev_close * 100
                                change_amt = close - prev_close
                        except:
                            pass
                    
                    amplitude = 0
                    if len(row) >= 4 and row[2] and row[1]:
                        try:
                            high = float(row[2])
                            low = float(row[1])
                            if low > 0:
                                amplitude = (high - low) / low * 100
                        except:
                            pass
                    
                    data_list.append({
                        'code': code,
                        'trade_date': row[0],
                        'open': float(row[1]) if row[1] else 0,
                        'high': float(row[2]) if row[2] else 0,
                        'low': float(row[3]) if row[3] else 0,
                        'close': float(row[4]) if row[4] else 0,
                        'volume': int(float(row[5])) if row[5] else 0,
                        'amount': float(row[6]) if row[6] else 0,
                        'amplitude': amplitude,
                        'change_pct': change_pct,
                        'change_amt': change_amt,
                        'turnover': float(row[7]) if row[7] else 0
                    })
            
            return data_list
        except Exception as e:
            print(f"  获取 {code} 失败: {e}")
            return []
    
    def batch_crawl(self, stock_codes, years=5):
        """批量获取历史数据"""
        all_data = []
        total = len(stock_codes)
        
        for i, code in enumerate(stock_codes, 1):
            print(f"[{i}/{total}] 正在获取 {code} ...")
            data = self.fetch_history(code, years)
            if data:
                all_data.extend(data)
                print(f"  完成: {len(data)} 条")
            else:
                print(f"  无数据")
        
        return all_data


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yaml')
    list_path = os.path.join(base_dir, '..', 'resource', 'stock_list.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    db_path = config.get('database', {}).get('path', '')
    
    with open(list_path, 'r', encoding='utf-8') as f:
        stock_data = yaml.safe_load(f)
    
    stocks = stock_data.get('stocks', [])
    if not stocks:
        print("股票列表为空")
        return
    
    stock_codes = [s.get('code') for s in stocks]
    
    print(f"将获取 {len(stock_codes)} 只股票的历史数据")
    years = 5
    print(f"时间范围: 最近 {years} 年")
    print("-" * 50)
    
    crawler = HistoryCrawler(db_path)
    data = crawler.batch_crawl(stock_codes, years)
    
    if data:
        crawler.db.insert_history(data)
        print(f"\n总获取: {len(data)} 条历史K线数据")
    else:
        print("\n未获取到任何数据")
    
    bs.logout()


if __name__ == "__main__":
    main()