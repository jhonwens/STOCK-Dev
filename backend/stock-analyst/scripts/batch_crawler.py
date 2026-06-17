#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 分批爬取股票历史数据

import os
import sys
import yaml
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import baostock as bs
from db_manager import DBManager


class BatchCrawler:
    def __init__(self, db_path, days=60):
        self.db = DBManager(db_path)
        self.days = days
        self.batch_size = 5
    
    def get_code_with_exchange(self, code):
        if code.startswith('6'):
            return f"sh.{code}"
        else:
            return f"sz.{code}"
    
    def fetch_history(self, code, name=""):
        """获取指定股票历史数据"""
        try:
            bs_code = self.get_code_with_exchange(code)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=self.days)).strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(bs_code, "date,open,high,low,close,volume,amount,turn",
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2")
            
            if rs.error_code != '0':
                print(f"  查询失败: {rs.error_msg}")
                return []
            
            data_list = []
            while rs.next():
                row = rs.get_row_data()
                if row[0]:
                    data_list.append({
                        'code': code,
                        'trade_date': row[0],
                        'open': float(row[1]) if row[1] else 0,
                        'high': float(row[2]) if row[2] else 0,
                        'low': float(row[3]) if row[3] else 0,
                        'close': float(row[4]) if row[4] else 0,
                        'volume': int(float(row[5])) if row[5] else 0,
                        'amount': float(row[6]) if row[6] else 0,
                        'turnover': float(row[7]) if row[7] else 0,
                        'amplitude': 0,
                        'change_pct': 0,
                        'change_amt': 0
                    })
            
            return data_list
        except Exception as e:
            print(f"  获取 {code} 失败: {e}")
            return []
    
    def batch_crawl(self, stock_codes, batch_num=1, total_batches=1):
        """分批爬取"""
        lg = bs.login()
        if lg.error_code != '0':
            print(f"登录失败: {lg.error_msg}")
            return []
        
        start_idx = (batch_num - 1) * self.batch_size
        end_idx = min(start_idx + self.batch_size, len(stock_codes))
        batch_codes = stock_codes[start_idx:end_idx]
        
        print(f"\n{'='*50}")
        print(f"第 {batch_num}/{total_batches} 批，股票 {start_idx+1}-{end_idx}")
        print(f"股票: {[c['code'] for c in batch_codes]}")
        print(f"{'='*50}")
        
        all_data = []
        for i, stock in enumerate(batch_codes, 1):
            code = stock.get('code')
            name = stock.get('name', '')
            print(f"[{i}/{len(batch_codes)}] 获取 {code} {name} ...")
            data = self.fetch_history(code, name)
            if data:
                all_data.extend(data)
                print(f"  完成: {len(data)} 条")
            else:
                print(f"  无数据")
            time.sleep(0.5)
        
        if all_data:
            self.db.insert_history(all_data)
            print(f"\n本批完成: 共 {len(all_data)} 条")
        
        bs.logout()
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
    
    print(f"共 {len(stocks)} 只股票，每批 {5} 只")
    print(f"历史数据范围: 最近 {60} 天")
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=int, default=1, help='批次号')
    parser.add_argument('--days', type=int, default=60, help='历史天数')
    args = parser.parse_args()
    
    total_batches = (len(stocks) + 4) // 5
    
    crawler = BatchCrawler(db_path, days=args.days)
    crawler.batch_crawl(stocks, args.batch, total_batches)


if __name__ == "__main__":
    main()