#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 股票选股筛选器 - 严格按照交易原则

import os
import sys
import yaml
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager import DBManager


class StockPicker:
    def __init__(self, db_path):
        self.db = DBManager(db_path)
        self.rules = {
            'min_limit_up_days': 20,
            'require_above_ma5': True,
            'volume_ratio_threshold': 1.2,
            'main_inflow_threshold': 1000000
        }
    
    def analyze_stock(self, metrics):
        """分析单只股票是否符合交易原则"""
        code = metrics.get('code', '')
        price = metrics.get('price', 0)
        ma5 = metrics.get('ma5', 0)
        ma10 = metrics.get('ma10', 0)
        ma20 = metrics.get('ma20', 0)
        ma200 = metrics.get('ma200', 0)
        limit_up_count = metrics.get('limit_up_count', 0)
        volume_ratio = metrics.get('volume_ratio', 1)
        volume_increasing = metrics.get('volume_increasing', False)
        main_inflow = metrics.get('main_inflow', 0)
        near_200_high = metrics.get('near_200_high', False)
        
        reasons = []
        risk_factors = []
        score = 0
        
        if limit_up_count > 0:
            score += 30
            reasons.append(f"20日内涨停{limit_up_count}次✓")
        else:
            risk_factors.append("20日内无涨停（主力已撤离）")
        
        if metrics.get('above_ma5', False):
            score += 25
            reasons.append("股价站上5日均线✓")
        else:
            risk_factors.append("股价在5日均线下方（趋势向下）")
        
        if price > ma5 > ma10 > ma20:
            score += 20
            reasons.append("均线多头排列✓")
        elif price > ma5:
            score += 10
        
        if volume_ratio >= 1.5:
            score += 15
            reasons.append(f"成交量放量({volume_ratio:.1f}倍)✓")
        elif volume_increasing:
            score += 10
            reasons.append("成交量逐步放大✓")
        
        if main_inflow > 10000000:
            score += 15
            reasons.append(f"主力净流入{main_inflow/10000:.0f}万✓")
        elif main_inflow > 0:
            score += 5
        
        if near_200_high:
            score += 10
            reasons.append("创200天新高/接近新高✓")
        
        if ma200 and price > ma200 > 0:
            score += 5
            reasons.append("股价在200日均线上方")
        
        return {
            'code': code,
            'score': score,
            'reasons': reasons,
            'risk_factors': risk_factors,
            'price': price,
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
            'ma200': round(ma200, 2) if ma200 else None,
            'limit_up_count': limit_up_count,
            'volume_ratio': round(volume_ratio, 2),
            'main_inflow': main_inflow,
            'near_200_high': near_200_high
        }
    
    def filter_stocks(self, days=20):
        """筛选符合交易原则的股票"""
        print("\n" + "="*60)
        print("股票选股筛选 - 严格按交易原则")
        print("="*60)
        
        all_metrics = self.db.get_all_stock_metrics(days)
        
        if not all_metrics:
            print("⚠️ 无历史数据可分析")
            return []
        
        results = []
        for metrics in all_metrics:
            if metrics.get('error'):
                continue
            analysis = self.analyze_stock(metrics)
            results.append(analysis)
        
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def recommend_stocks(self, top_n=10):
        """推荐最符合条件的股票"""
        stocks = self.filter_stocks()
        
        print(f"\n📊 初步筛选: {len(stocks)} 只")
        
        recommended = []
        for s in stocks:
            if s['score'] >= 30 and len(s['risk_factors']) == 0:
                recommended.append(s)
        
        if not recommended:
            for s in stocks[:5]:
                if s['score'] >= 20:
                    recommended.append(s)
        
        print(f"✅ 符合原则: {len(recommended)} 只")
        
        # 过滤掉科创板股票（688开头）
        non_kc = [s for s in recommended if not s.get('code', '').startswith('688')]
        print(f"📊 排除科创板后: {len(non_kc)} 只")
        
        return non_kc[:top_n]
    
    def print_recommendations(self, stocks):
        """打印推荐结果"""
        if not stocks:
            print("\n⚠️ 当前无符合条件的股票")
            print("\n📋 选股原则提醒:")
            print("  1. 只选20日内出现过涨停的股票")
            print("  2. 股价必须站上5日均线")
            print("  3. 成交量需要放量")
            print("  4. 趋势优先，多头排列优先")
            print("  5. 主力资金净流入优先")
            return
        
        print("\n" + "="*60)
        print("📈 符合交易原则的股票推荐")
        print("="*60)
        
        for i, s in enumerate(stocks, 1):
            print(f"\n{i}. {s['code']} (评分: {s['score']})")
            print(f"   当前价: {s['price']:.2f}")
            print(f"   均线: MA5={s['ma5']}, MA10={s['ma10']}, MA20={s['ma20']}" + 
                  (f", MA200={s['ma200']}" if s['ma200'] else ""))
            print(f"   涨停次数: {s['limit_up_count']}次(20日内)")
            print(f"   成交量比: {s['volume_ratio']}倍")
            print(f"   主力净流入: {s['main_inflow']/10000:.1f}万")
            if s['near_200_high']:
                print(f"   🚀 创200天新高/接近新高")
            print(f"   ✅ 符合: {', '.join(s['reasons']) if s['reasons'] else '暂无'}")
            if s['risk_factors']:
                print(f"   ⚠️ 风险: {', '.join(s['risk_factors'])}")
        
        print("\n" + "="*60)
        print("💡 交易建议:")
        print("  - 不冲高不卖，不跳水不买")
        print("  - 放量上涨持有，放量滞涨卖出")
        print("  - 五日线拐头向下立刻空仓")
        print("  - 学会空仓是保本金的关键")
        print("="*60)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    db_path = config.get('database', {}).get('path', '')
    
    import argparse
    parser = argparse.ArgumentParser(description='股票选股筛选器')
    parser.add_argument('--top', type=int, default=10, help='推荐数量')
    parser.add_argument('--days', type=int, default=20, help='涨停统计天数')
    args = parser.parse_args()
    
    picker = StockPicker(db_path)
    
    stocks = picker.recommend_stocks(top_n=args.top)
    picker.print_recommendations(stocks)
    
    return stocks


if __name__ == "__main__":
    main()