#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 资讯公告获取模块

import requests
from datetime import datetime, timedelta

class NewsFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def _convert_date(self, ts):
        """转换时间戳为日期格式"""
        if not ts:
            return datetime.now().strftime('%Y-%m-%d')
        ts_str = str(ts)
        try:
            if len(ts_str) == 13:
                return datetime.fromtimestamp(int(ts_str[:10])).strftime('%Y-%m-%d')
            elif len(ts_str) == 10:
                return datetime.fromtimestamp(int(ts_str)).strftime('%Y-%m-%d')
        except:
            pass
        return datetime.now().strftime('%Y-%m-%d')
    
    def get_announcements(self, stock_code, days=7):
        """获取上市公司公告（巨潮资讯网）"""
        try:
            url = 'http://www.cninfo.com.cn/new/hisAnnouncement/query'
            params = {
                'pageNum': 1,
                'pageSize': 20,
                'tabName': 'fulltext',
                'column': 'szse' if not stock_code.startswith('6') else 'sse',
                'seDate': f'{(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")}~{datetime.now().strftime("%Y-%m-%d")}',
                'searchKey': '',
                'secid': f'{stock_code}.{"sz" if not stock_code.startswith("6") else "sh"}',
                'category': '',
                'isHLtitle': 'true'
            }
            
            resp = requests.post(url, json=params, headers=self.headers, timeout=10)
            data = resp.json()
            
            results = []
            if data.get('announcements'):
                for item in data['announcements']:
                    # 判断利好/利空
                    title = item.get('announcementTitle', '')
                    content = item.get('contextText', '')
                    
                    # 简单判断
                    msg_type = '中性'
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ['盈利', '增长', '扭亏', '预增', '利好', '中标', '签约']):
                        msg_type = '利好'
                    elif any(kw in title_lower for kw in ['亏损', '下降', '预警', '减持', '利空', '诉讼', '风险']):
                        msg_type = '利空'
                    
                    results.append({
                        'code': stock_code,
                        'title': title[:100],
                        'type': msg_type,
                        'publish_date': self._convert_date(item.get('announcementTime', '')),
                        'source': '巨潮资讯'
                    })
            
            return results
        except Exception as e:
            print(f"获取{stock_code}公告失败: {e}")
            return []
    
    def get_stock_news(self, stock_code, days=7):
        """获取个股新闻资讯"""
        try:
            # 东財个股新闻接口
            url = 'https://guba.eastmoney.com/api'
            params = {
                'symbol': stock_code,
                'type': 'get_latest_info'
            }
            
            results = []
            try:
                resp = requests.get(url, params=params, timeout=5, headers=self.headers)
                data = resp.json()
                
                if data and data.get('data'):
                    for item in data['data'][:10]:
                        title = item.get('title', '')
                        title_lower = title.lower()
                        
                        if any(kw in title_lower for kw in ['盈利', '增长', '扭亏', '预增', '利好', '中标', '签约']):
                            msg_type = '利好'
                        elif any(kw in title_lower for kw in ['亏损', '下降', '预警', '减持', '利空', '诉讼', '风险']):
                            msg_type = '利空'
                        else:
                            msg_type = '中性'
                        
                        results.append({
                            'code': stock_code,
                            'title': title[:100],
                            'type': msg_type,
                            'publish_date': item.get('pubDate', '')[:10] if item.get('pubDate') else '',
                            'source': '东方财富'
                        })
            except:
                pass
            
            return results
        except Exception as e:
            print(f"获取{stock_code}资讯失败: {e}")
            return []
    
    def batch_fetch(self, stock_codes, days=7):
        """批量获取资讯"""
        results = []
        for code in stock_codes:
            # 获取公告
            announcements = self.get_announcements(code, days)
            results.extend(announcements)
            
            # 获取新闻（备用）
            news = self.get_stock_news(code, days)
            for n in news:
                # 避免重复
                if not any(x['title'] == n['title'] for x in results):
                    results.append(n)
        
        return results


if __name__ == "__main__":
    # 测试
    fetcher = NewsFetcher()
    test_codes = ['600519', '000858']
    
    print("=== 公告资讯 ===")
    for code in test_codes:
        data = fetcher.get_announcements(code)
        print(f"{code}: {len(data)}条公告")