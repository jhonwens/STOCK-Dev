#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A股全市场股票列表爬取

import os
import sys
import yaml
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import baostock as bs
except:
    print("请安装baostock: pip3 install baostock")
    sys.exit(1)

from db_manager import DBManager


class StockListUpdater:
    def __init__(self, db_path):
        self.db = DBManager(db_path)
        self.list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resource', 'stock_list.yaml')
    
    def fetch_stock_list(self):
        """获取A股全市场股票列表"""
        lg = bs.login()
        if lg.error_code != '0':
            print(f"登录失败: {lg.error_msg}")
            return []
        
        print("获取A股股票列表...")
        
        rs = bs.query_all_stock(day="2026-05-07")
        
        stocks = []
        while rs.next():
            row = rs.get_row_data()
            code = row[0]
            name = row[1]
            status = row[2]
            
            if status == '1':
                stock_code = code.split('.')[1]
                stocks.append({
                    'code': stock_code,
                    'name': name,
                    'industry': '其他'
                })
        
        bs.logout()
        return stocks
    
    def update_stock_list(self):
        """更新股票列表到配置文件"""
        stocks = self.fetch_stock_list()
        
        if not stocks:
            print("未获取到股票列表")
            return
        
        data = {'stocks': stocks}
        
        with open(self.list_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True)
        
        print(f"✅ 已更新股票列表，共 {len(stocks)} 只股票")
        print(f"   保存到: {self.list_path}")
        
        return stocks


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    db_path = config.get('database', {}).get('path', '')
    
    updater = StockListUpdater(db_path)
    updater.update_stock_list()


if __name__ == "__main__":
    main()