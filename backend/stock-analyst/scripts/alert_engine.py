#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 预警引擎模块

from datetime import datetime

class AlertEngine:
    def __init__(self, config):
        self.config = config
        self.alerts = []
        
    def check_change_pct(self, data):
        """涨跌幅预警"""
        threshold = self.config.get('change_pct_threshold', 5)
        
        change_pct = abs(data.get('change_pct', 0))
        
        if change_pct > threshold:
            direction = "上涨" if data.get('change_pct', 0) > 0 else "下跌"
            return {
                'code': data.get('code'),
                'alert_type': '涨跌幅预警',
                'alert_msg': f"{data.get('name', data.get('code'))}大幅{direction}，涨幅{data.get('change_pct')}%",
                'alert_value': data.get('change_pct'),
                'threshold': threshold,
                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        return None
    
    def check_fund_flow(self, data):
        """资金流向预警"""
        threshold = self.config.get('fund_flow_threshold', 10000000)
        
        main_inflow = data.get('main_inflow', 0)
        
        if main_inflow > threshold:
            return {
                'code': data.get('code'),
                'alert_type': '资金流向预警',
                'alert_msg': f"{data.get('name', data.get('code'))}主力净流入{main_inflow/10000:.0f}万元，大额资金流入",
                'alert_value': main_inflow,
                'threshold': threshold,
                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        elif main_inflow < -threshold * 0.5:  # 流出阈值减半
            return {
                'code': data.get('code'),
                'alert_type': '资金流向预警',
                'alert_msg': f"{data.get('name', data.get('code'))}主力净流出{abs(main_inflow)/10000:.0f}万元，大额资金流出",
                'alert_value': main_inflow,
                'threshold': -threshold * 0.5,
                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        return None
    
    def check_finance(self, data):
        """基本面预警"""
        rev_threshold = self.config.get('revenue_growth_threshold', 30)
        profit_threshold = self.config.get('profit_growth_threshold', 50)
        
        rev_growth = data.get('rev_growth', 0)
        profit_growth = data.get('profit_growth', 0)
        
        alerts = []
        
        if rev_growth > rev_threshold:
            alerts.append({
                'code': data.get('code'),
                'alert_type': '基本面预警',
                'alert_msg': f"{data.get('name', data.get('code'))}营收同比增长{rev_growth}%",
                'alert_value': rev_growth,
                'threshold': rev_threshold,
                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        if profit_growth > profit_threshold:
            alerts.append({
                'code': data.get('code'),
                'alert_type': '基本面预警', 
                'alert_msg': f"{data.get('name', data.get('code'))}净利润同比增长{profit_growth}%",
                'alert_value': profit_growth,
                'threshold': profit_threshold,
                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return alerts if alerts else None
    
    def check_news(self, data):
        """资讯预警"""
        news_type = data.get('type', '中性')
        
        if news_type in ['利好', '利空']:
            return {
                'code': data.get('code'),
                'alert_type': '资讯预警',
                'alert_msg': f"{data.get('name', data.get('code'))}出现{news_type}消息: {data.get('title', '')[:50]}",
                'alert_value': news_type,
                'threshold': 0,
                'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        return None
    
    def check_all(self, realtime_data=None, fund_flow_data=None, trend_data=None, news_data=None):
        """执行所有预警检查"""
        alerts = []
        
        # 涨跌幅预警
        if realtime_data:
            for data in realtime_data:
                alert = self.check_change_pct(data)
                if alert:
                    alerts.append(alert)
        
        # 资金流向预警
        if fund_flow_data:
            for data in fund_flow_data:
                alert = self.check_fund_flow(data)
                if alert:
                    alerts.append(alert)
        
        # 基本面预警
        if trend_data:
            for data in trend_data:
                alert = self.check_finance(data)
                if alert:
                    alerts.extend(alert)
        
        # 资讯预警
        if news_data:
            for data in news_data:
                alert = self.check_news(data)
                if alert:
                    alerts.append(alert)
        
        self.alerts = alerts
        return alerts
    
    def get_alerts(self):
        """获取预警结果"""
        return self.alerts


if __name__ == "__main__":
    # 测试
    config = {
        'change_pct_threshold': 5,
        'fund_flow_threshold': 10000000,
        'revenue_growth_threshold': 30,
        'profit_growth_threshold': 50
    }
    
    engine = AlertEngine(config)
    
    # 测试涨跌幅预警
    test_data = {'code': '600519', 'name': '贵州茅台', 'change_pct': 6.5}
    alert = engine.check_change_pct(test_data)
    print(f"预警: {alert}")