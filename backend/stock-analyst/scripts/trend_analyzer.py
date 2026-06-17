#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 趋势分析模块

import sqlite3
from datetime import datetime

class TrendAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def analyze_trend(self, stock_code):
        """分析股票趋势"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取最近4个季度的财务数据
            cursor.execute('''
                SELECT revenue, profit, eps, report_date FROM stock_finance
                WHERE code = ? ORDER BY report_date DESC LIMIT 4
            ''', (stock_code,))
            
            results = cursor.fetchall()
            conn.close()
            
            if len(results) < 2:
                return {
                    'code': stock_code,
                    'rev_growth': 0,
                    'profit_growth': 0,
                    'eps_growth': 0,
                    'trend_signal': '数据不足',
                    'update_date': datetime.now().strftime('%Y-%m-%d')
                }
            
            # 计算同比增长（当前季度 vs 去年同期）
            current = results[0]
            # 找到去年同期
            last_year_same = None
            for r in results[1:]:
                if r[3][:7] == current[3][:7]:  # 同月
                    last_year_same = r
                    break
            
            if last_year_same:
                rev_growth = ((current[0] - last_year_same[0]) / last_year_same[0] * 100) if last_year_same[0] else 0
                profit_growth = ((current[1] - last_year_same[1]) / last_year_same[1] * 100) if last_year_same[1] else 0
                eps_growth = ((current[2] - last_year_same[2]) / last_year_same[2] * 100) if last_year_same[2] else 0
            else:
                # 使用环比
                if len(results) >= 2:
                    prev = results[1]
                    rev_growth = ((current[0] - prev[0]) / prev[0] * 100) if prev[0] else 0
                    profit_growth = ((current[1] - prev[1]) / prev[1] * 100) if prev[1] else 0
                    eps_growth = ((current[2] - prev[2]) / prev[2] * 100) if prev[2] else 0
                else:
                    rev_growth = profit_growth = eps_growth = 0
            
            # 生成趋势信号
            signal = '平稳'
            if rev_growth > 30 and profit_growth > 30:
                signal = '强劲增长'
            elif rev_growth > 10 and profit_growth > 10:
                signal = '稳健增长'
            elif rev_growth < -10 or profit_growth < -10:
                signal = '下滑'
            elif rev_growth > 5 and profit_growth > 5:
                signal = '温和增长'
            
            return {
                'code': stock_code,
                'rev_growth': round(rev_growth, 2),
                'profit_growth': round(profit_growth, 2),
                'eps_growth': round(eps_growth, 2),
                'trend_signal': signal,
                'update_date': datetime.now().strftime('%Y-%m-%d')
            }
        except Exception as e:
            print(f"分析{stock_code}趋势失败: {e}")
            return {
                'code': stock_code,
                'rev_growth': 0,
                'profit_growth': 0,
                'eps_growth': 0,
                'trend_signal': '分析失败',
                'update_date': datetime.now().strftime('%Y-%m-%d')
            }
    
    def batch_analyze(self, stock_codes):
        """批量趋势分析"""
        results = []
        for code in stock_codes:
            result = self.analyze_trend(code)
            results.append(result)
        return results


if __name__ == "__main__":
    # 测试
    analyzer = TrendAnalyzer("../data/stock_data.db")
    test_codes = ['600519', '000858']
    
    print("=== 趋势分析 ===")
    for code in test_codes:
        result = analyzer.analyze_trend(code)
        print(f"{code}: {result}")