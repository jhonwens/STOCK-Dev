#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import os

class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stock_realtime (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, price REAL, change_pct REAL,
            volume INTEGER, amount REAL, turnover REAL, pe REAL, pb REAL, 
            update_time TEXT, trade_date TEXT, change_amt REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS stock_fund_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, main_inflow REAL, update_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS stock_finance (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, roe REAL, revenue REAL, profit REAL,
            eps REAL, bvps REAL, report_date TEXT, UNIQUE(code, report_date))''')
        c.execute('''CREATE TABLE IF NOT EXISTS stock_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, title TEXT, type TEXT, 
            publish_date TEXT, source TEXT, UNIQUE(code, title, publish_date))''')
        c.execute('''CREATE TABLE IF NOT EXISTS stock_trend (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, rev_growth REAL, profit_growth REAL, 
            eps_growth REAL, trend_signal TEXT, update_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS stock_alert (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, alert_type TEXT, alert_msg TEXT, 
            alert_value REAL, threshold REAL, create_time TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS stock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, trade_date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume INTEGER, amount REAL, amplitude REAL, change_pct REAL,
            change_amt REAL, turnover REAL, UNIQUE(code, trade_date))''')
        c.execute('''CREATE TABLE IF NOT EXISTS stock_limit_up (
            id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, name TEXT, limit_date TEXT,
            limit_price REAL, close_price REAL, change_pct REAL, UNIQUE(code, limit_date))''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS stock_technical (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                indicators_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, created_at)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS stock_pattern (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                status TEXT DEFAULT 'detected',
                confidence REAL DEFAULT 0.0,
                description TEXT,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS stock_chan_theory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                level TEXT DEFAULT 'day',
                price REAL,
                description TEXT,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS stock_portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT,
                category TEXT DEFAULT '候选',
                cost_price REAL,
                shares INTEGER DEFAULT 0,
                add_date DATE DEFAULT (DATE('now')),
                notes TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS stock_llm_report (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,
                scope TEXT,
                content TEXT NOT NULL,
                model TEXT,
                tokens_used INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def insert_realtime(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for item in data:
            c.execute('''INSERT OR REPLACE INTO stock_realtime 
                (code, name, price, change_pct, volume, amount, turnover, pe, pb, update_time, trade_date, change_amt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (item.get('code',''),item.get('name',''),item.get('price',0),item.get('change_pct',0),
                item.get('volume',0),item.get('amount',0),item.get('turnover',0),item.get('pe',0),
                item.get('pb',0),item.get('update_time',''),item.get('trade_date',''),item.get('change',0)))
        conn.commit()
        conn.close()

    def insert_fund_flow(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for item in data:
            c.execute('''INSERT OR REPLACE INTO stock_fund_flow (code, main_inflow, update_date)
                VALUES (?, ?, ?)''',
                (item.get('code'),item.get('main_inflow',0),item.get('update_date')))
        conn.commit()
        conn.close()

    def insert_finance(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for item in data:
            c.execute('''INSERT OR REPLACE INTO stock_finance (code, roe, revenue, profit, eps, bvps, report_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (item.get('code'),item.get('roe',0),item.get('revenue',0),item.get('profit',0),
                item.get('eps',0),item.get('bvps',0),item.get('report_date')))
        conn.commit()
        conn.close()

    def insert_news(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # 清理1个月前的数据（兼容多种日期格式）
        try:
            c.execute("DELETE FROM stock_news WHERE publish_date < date('now', '-30 days')")
        except:
            c.execute("DELETE FROM stock_news WHERE publish_date < date('now', '-1 month')")
        for item in data:
            c.execute('''INSERT OR IGNORE INTO stock_news (code, title, type, publish_date, source)
                VALUES (?, ?, ?, ?, ?)''',
                (item.get('code'),item.get('title'),item.get('type'),
                item.get('publish_date'),item.get('source')))
        conn.commit()
        conn.close()

    def insert_trend(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for item in data:
            c.execute('''INSERT OR REPLACE INTO stock_trend 
                (code, rev_growth, profit_growth, eps_growth, trend_signal, update_date) VALUES (?, ?, ?, ?, ?, ?)''',
                (item.get('code'),item.get('rev_growth',0),item.get('profit_growth',0),
                item.get('eps_growth',0),item.get('trend_signal'),item.get('update_date')))
        conn.commit()
        conn.close()

    def insert_alert(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for item in data:
            c.execute('''INSERT INTO stock_alert (code, alert_type, alert_msg, alert_value, threshold, create_time)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (item.get('code'),item.get('alert_type'),item.get('alert_msg'),
                item.get('alert_value'),item.get('threshold'),item.get('create_time')))
        conn.commit()
        conn.close()

    def insert_history(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # 删除3年前的历史数据
        try:
            c.execute("DELETE FROM stock_history WHERE trade_date < date('now', '-3 years')")
        except:
            pass
        for item in data:
            c.execute('''INSERT OR REPLACE INTO stock_history 
                (code, trade_date, open, high, low, close, volume, amount, amplitude, change_pct, change_amt, turnover)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (item.get('code',''),item.get('trade_date',''),item.get('open',0),item.get('high',0),
                item.get('low',0),item.get('close',0),item.get('volume',0),item.get('amount',0),
                item.get('amplitude',0),item.get('change_pct',0),item.get('change_amt',0),item.get('turnover',0)))
        conn.commit()
        conn.close()

    def insert_limit_up(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for item in data:
            c.execute('''INSERT OR REPLACE INTO stock_limit_up 
                (code, name, limit_date, limit_price, close_price, change_pct)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (item.get('code'),item.get('name'),item.get('limit_date'),
                item.get('limit_price'),item.get('close_price'),item.get('change_pct')))
        conn.commit()
        conn.close()

    def query_history(self, code, limit=120):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT trade_date, open, high, low, close, volume
            FROM stock_history WHERE code = ?
            ORDER BY trade_date ASC LIMIT ?
        ''', (code, limit))
        rows = c.fetchall()
        conn.close()
        return [
            {"trade_date": r[0], "open": float(r[1]), "high": float(r[2]),
             "low": float(r[3]), "close": float(r[4]), "volume": float(r[5])}
            for r in rows
        ]

    def insert_technical(self, code, indicators_json):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO stock_technical (code, indicators_json)
            VALUES (?, ?)''', (code, indicators_json))
        conn.commit()
        conn.close()

    def insert_pattern(self, code, pattern_type, confidence=0.0, description=""):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO stock_pattern (code, pattern_type, confidence, description)
            VALUES (?, ?, ?, ?)''', (code, pattern_type, confidence, description))
        conn.commit()
        conn.close()

    def insert_chan_signal(self, code, signal_type, level="day", price=0.0, description=""):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO stock_chan_theory (code, signal_type, level, price, description)
            VALUES (?, ?, ?, ?, ?)''', (code, signal_type, level, price, description))
        conn.commit()
        conn.close()

    def upsert_portfolio(self, code, name="", category="候选", cost_price=0.0, shares=0, notes=""):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO stock_portfolio
            (code, name, category, cost_price, shares, notes)
            VALUES (?, ?, ?, ?, ?, ?)''', (code, name, category, cost_price, shares, notes))
        conn.commit()
        conn.close()

    def insert_llm_report(self, report_type, scope, content, model="", tokens_used=0):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO stock_llm_report (report_type, scope, content, model, tokens_used)
            VALUES (?, ?, ?, ?, ?)''', (report_type, scope, content, model, tokens_used))
        conn.commit()
        conn.close()

    def get_stock_metrics(self, code, days=20):
        """获取股票技术指标：均线、涨停次数、成交量变化"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        result = {'code': code, 'error': None}
        
        try:
            c.execute('''SELECT trade_date, close, volume FROM stock_history 
                WHERE code=? ORDER BY trade_date DESC LIMIT 250''', (code,))
            rows = c.fetchall()
            
            if not rows:
                result['error'] = '无历史数据'
                return result
            
            prices = [r[1] for r in rows]
            volumes = [r[2] for r in rows]
            
            if len(prices) < 5:
                result['error'] = '数据不足'
                return result
            
            result['price'] = prices[0]
            result['ma5'] = sum(prices[:5]) / 5
            result['ma10'] = sum(prices[:10]) / 10 if len(prices) >= 10 else result['ma5']
            result['ma20'] = sum(prices[:20]) / 20 if len(prices) >= 20 else result['ma10']
            
            if len(prices) >= 200:
                result['ma200'] = sum(prices[:200]) / 200
                result['near_200_high'] = prices[0] >= max(prices[:200]) * 0.98
            else:
                result['ma200'] = None
                result['near_200_high'] = False
            
            c.execute('''SELECT COUNT(*) FROM stock_limit_up 
                WHERE code=? AND limit_date >= date('now', '-{} days')'''.format(days), (code,))
            result['limit_up_count'] = c.fetchone()[0]
            
            if len(volumes) >= 5:
                avg_vol5 = sum(volumes[:5]) / 5
                avg_vol20 = sum(volumes[:20]) / 20 if len(volumes) >= 20 else avg_vol5
                result['volume_ratio'] = volumes[0] / avg_vol20 if avg_vol20 > 0 else 1
                result['volume_increasing'] = volumes[0] > avg_vol5
            else:
                result['volume_ratio'] = 1
                result['volume_increasing'] = False
            
            result['above_ma5'] = prices[0] > result['ma5']
            
            c.execute('''SELECT main_inflow FROM stock_fund_flow WHERE code=? ORDER BY update_date DESC LIMIT 1''', (code,))
            fund_row = c.fetchone()
            result['main_inflow'] = fund_row[0] if fund_row else 0
            
        except Exception as e:
            result['error'] = str(e)
        
        conn.close()
        return result

    def get_all_stock_metrics(self, days=20):
        """获取所有股票的技术指标"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT DISTINCT code FROM stock_history''')
        codes = [r[0] for r in c.fetchall()]
        
        results = []
        for code in codes:
            metrics = self.get_stock_metrics(code, days)
            if not metrics.get('error'):
                results.append(metrics)
        
        conn.close()
        return results

    def cleanup_old_data(self, years=3):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        cutoff = f"date('now', '-{years} years')"
        tables_cols = [
            ("stock_history", "trade_date"),
            ("stock_limit_up", "limit_date"),
            ("stock_news", "publish_date"),
            ("stock_fund_flow", "update_date"),
            ("stock_finance", "report_date"),
            ("stock_trend", "update_date"),
            ("stock_alert", "create_time"),
            ("stock_technical", "created_at"),
        ]
        deleted = {}
        for table, col in tables_cols:
            try:
                c.execute(f"DELETE FROM {table} WHERE date({col}) < {cutoff}")
                deleted[table] = c.rowcount
            except Exception:
                deleted[table] = -1
        conn.commit()
        conn.close()
        return deleted

if __name__ == "__main__":
    DBManager("../data/stock_data.db")
    print("OK")