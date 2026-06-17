#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 涨停数据爬取脚本 - 从历史K线中识别涨停

import os
import sys
import yaml
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import baostock as bs
except:
    print("请安装baostock: pip3 install baostock")
    sys.exit(1)

from db_manager import DBManager


class LimitUpFinder:
    def __init__(self, db_path):
        self.db = DBManager(db_path)
    
    def get_code_with_exchange(self, code):
        """转换股票代码为baostock格式"""
        if code.startswith('6'):
            return f"sh.{code}"
        else:
            return f"sz.{code}"
    
    def find_limit_ups(self, code, name="", days=20):
        """查找20日内的涨停日"""
        try:
            bs_code = self.get_code_with_exchange(code)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days+10)).strftime('%Y-%m-%d')
            
            rs = bs.query_history_k_data_plus(bs_code, "date,close,preclose",
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2")
            
            if rs.error_code != '0':
                return []
            
            limit_ups = []
            while rs.next():
                row = rs.get_row_data()
                if row[0] and row[1] and row[2]:
                    try:
                        close = float(row[1])
                        preclose = float(row[2])
                        if preclose > 0:
                            change_pct = (close - preclose) / preclose * 100
                            if change_pct >= 9.9:
                                limit_ups.append({
                                    'code': code,
                                    'name': name,
                                    'limit_date': row[0],
                                    'limit_price': close,
                                    'close_price': close,
                                    'change_pct': change_pct
                                })
                    except:
                        pass
            
            return limit_ups
        except Exception as e:
            print(f"  查询 {code} 失败: {e}")
            return []
    
    def scan_all_stocks(self, days=20):
        """扫描所有股票查找涨停"""
        lg = bs.login()
        if lg.error_code != '0':
            print(f"登录失败: {lg.error_msg}")
            return []
        
        conn = self.db.db_path
        import sqlite3
        c = sqlite3.connect(conn).cursor()
        c.execute("SELECT DISTINCT code FROM stock_history")
        codes = [r[0] for r in c.fetchall()]
        
        print(f"将扫描 {len(codes)} 只股票的涨停记录...")
        
        all_limit_ups = []
        for i, code in enumerate(codes, 1):
            print(f"[{i}/{len(codes)}] 扫描 {code}...")
            limit_ups = self.find_limit_ups(code, days=days)
            all_limit_ups.extend(limit_ups)
            if limit_ups:
                print(f"  找到 {len(limit_ups)} 次涨停")
        
        if all_limit_ups:
            self.db.insert_limit_up(all_limit_ups)
            print(f"\n✅ 共发现 {len(all_limit_ups)} 条涨停记录")
        
        bs.logout()
        return all_limit_ups


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    db_path = config.get('database', {}).get('path', '')
    
    finder = LimitUpFinder(db_path)
    finder.scan_all_stocks(days=20)


if __name__ == "__main__":
    main()