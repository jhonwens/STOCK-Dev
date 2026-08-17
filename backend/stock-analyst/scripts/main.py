#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 股票分析主入口 - 定时任务调度

import os
import sys
import yaml
import time
from datetime import datetime

# 添加scripts目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_crawler import StockCrawler
from finance_fetcher import FinanceFetcher
from news_fetcher import NewsFetcher
from trend_analyzer import TrendAnalyzer
from alert_engine import AlertEngine
from db_manager import DBManager
from stock_picker import StockPicker
from llm_client import LLMClient


class StockAnalyst:
    def __init__(self):
        # 获取脚本目录
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_dir = os.path.join(self.base_dir, '..')

        # 加载配置
        self.config = self._load_config()
        self.stock_list = self._load_stock_list()
        self.stock_names = {s['code']: s['name'] for s in self.stock_list.get('stocks', [])}

        # 数据库路径优先级：
        # 1. STOCK_DB_PATH 环境变量（打包模式下由 Rust 设置，指向可写应用数据目录）
        # 2. config.yaml 中的 database.path
        # 3. 默认 <base_dir>/../data/stock_data.db
        db_path = (
            os.environ.get("STOCK_DB_PATH")
            or self.config.get('database', {}).get('path', '')
            or os.path.join(self.base_dir, '..', 'data', 'stock_data.db')
        )
        # 转为绝对路径
        db_path = os.path.abspath(db_path)
        self.db = DBManager(db_path)
        self.crawler = StockCrawler()
        self.finance_fetcher = FinanceFetcher()
        self.news_fetcher = NewsFetcher()
        self.trend_analyzer = TrendAnalyzer(db_path)
        self.alert_engine = AlertEngine(self.config.get('alert', {}).get('rules', {}))
        self.llm = LLMClient()
    
    def _load_config(self):
        """加载配置文件"""
        config_path = os.path.join(self.base_dir, 'config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {
                'database': {'path': '../data/stock_data.db'},
                'alert': {'enabled': True, 'rules': {
                    'change_pct_threshold': 5,
                    'fund_flow_threshold': 10000000,
                    'revenue_growth_threshold': 30,
                    'profit_growth_threshold': 50
                }}
            }
    
    def _load_stock_list(self):
        """加载股票列表
        优先级：
          1. STOCK_LIST_PATH 环境变量（打包模式下由 Rust 设置，指向用户可写目录）
          2. 默认: resource/stock_list.yaml（开发模式 / bundle 资源）
        """
        list_path = os.environ.get("STOCK_LIST_PATH") or os.path.join(self.config_dir, 'resource', 'stock_list.yaml')
        try:
            with open(list_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"加载股票列表失败 ({list_path}): {e}")
            return {'stocks': []}
    
    def run(self, skip_llm=False, skip_history=False, quick=False):
        """执行分析"""
        print(f"\n{'='*50}")
        print(f"股票分析助手 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
        
        # 检查股票列表
        if not self.stock_list.get('stocks'):
            print("警告: 股票列表为空，请在 stock_list.yaml 中添加股票")
            stock_codes = ['600519']
        else:
            stock_codes = [s.get('code') for s in self.stock_list.get('stocks', [])]
        
        print(f"待分析股票: {stock_codes}")
        print(f"共 {len(stock_codes)} 只")
        print("-" * 50)
        
        # Step 1: 爬取实时行情
        print("\n[1/5] 爬取实时行情...")
        realtime_data = self.crawler.batch_crawl_realtime(stock_codes)
        self.db.insert_realtime(realtime_data)
        print(f"  完成: {len(realtime_data)} 条")
        
        # Step 2: 爬取资金流向
        if quick:
            print("\n[2/6] 爬取资金流向... 已跳过（quick 模式）")
            fund_flow_data = []
        else:
            print("\n[2/6] 爬取资金流向...")
            fund_flow_data = self.crawler.batch_crawl_fund_flow(stock_codes)
            self.db.insert_fund_flow(fund_flow_data)
            print(f"  完成: {len(fund_flow_data)} 条")
        
        # Step 3: 爬取财务指标
        print(f"\n[3/6] 爬取财务指标...")
        finance_data = self.finance_fetcher.batch_fetch(stock_codes)
        self.db.insert_finance(finance_data)
        for i, data in enumerate(realtime_data):
            if i < len(finance_data) and finance_data[i].get('code') == data.get('code'):
                data['pe'] = finance_data[i].get('pe', 0)
                data['pb'] = finance_data[i].get('pb', 0)
        self.db.insert_realtime(realtime_data)
        print(f"  完成: {len(finance_data)} 条")
        
        # Step 4: 爬取资讯公告
        if quick:
            print("\n[4/6] 爬取资讯公告... 已跳过（quick 模式）")
            news_data = []
        else:
            print("\n[4/6] 爬取资讯公告...")
            news_data = self.news_fetcher.batch_fetch(stock_codes)
            self.db.insert_news(news_data)
            print(f"  完成: {len(news_data)} 条")
        
        # Step 5: 趋势分析 (获取历史K线，最近6个月约130天)
        if skip_history:
            print("\n[5/6] 获取历史K线... 已跳过（quick 模式）")
        else:
            print("\n[5/6] 获取历史K线...")
            import baostock as bs
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d')
            lg = bs.login()
            for code in stock_codes:  # 获取所有股票历史数据
                bs_code = f"sh.{code}" if code.startswith('6') else f"sz.{code}"
                rs = bs.query_history_k_data_plus(bs_code, 'date,code,open,high,low,close,volume',
                    start_date=start_date, end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency='d', adjustflag='2')
                while rs.error_code == '0' and rs.next():
                    row = rs.get_row_data()
                    if row[0]:
                        self.db.insert_history([{
                            'code': code,
                            'trade_date': row[0],
                            'open': float(row[2]) if row[2] else 0,
                            'high': float(row[3]) if row[3] else 0,
                            'low': float(row[4]) if row[4] else 0,
                            'close': float(row[5]) if row[5] else 0,
                            'volume': float(row[6]) if row[6] else 0,
                        }])
            bs.logout()
            print(f"  完成")

        # Step 5b: 技术指标计算
        print("\n[5b/6] 技术指标计算...")
        try:
            from technical_indicators import calculate_all_indicators
            tech_count = 0
            for code in stock_codes:
                klines = self.db.query_history(code, limit=120)
                if klines and len(klines) >= 30:
                    indicators = calculate_all_indicators(klines)
                    self.db.insert_technical(code, str(indicators))
                    tech_count += 1
            print(f"  完成: {tech_count} 只股票")
        except ImportError:
            print("  ⚠️ technical_indicators 模块未就绪，跳过")
        
        # Step 6: 涨停扫描
        print("\n[6/6] 涨停扫描...")
        from limit_up_finder import LimitUpFinder
        limit_up_finder = LimitUpFinder(self.db.db_path)
        limit_up_finder.scan_all_stocks(days=20)
        print(f"  完成")
        trend_data = self.trend_analyzer.batch_analyze(stock_codes)
        self.db.insert_trend(trend_data)
        print(f"  完成: {len(trend_data)} 条")
        
        # 执行预警检测
        print("\n" + "=" * 50)
        print("预警检测...")
        print("-" * 50)
        
        alerts = self.alert_engine.check_all(
            realtime_data=realtime_data,
            fund_flow_data=fund_flow_data,
            trend_data=trend_data,
            news_data=news_data
        )
        
        if alerts:
            self.db.insert_alert(alerts)
            print(f"发现 {len(alerts)} 条预警:")
            for i, alert in enumerate(alerts, 1):
                print(f"  {i}. [{alert['alert_type']}] {alert['alert_msg']}")
        else:
            print("未发现预警")
        
        # LLM深度分析
        if not skip_llm:
            print("\n" + "=" * 50)
            print("LLM深度分析...")
            print("-" * 50)

            llm_result = self._llm_deep_analysis(stock_codes, realtime_data, fund_flow_data, finance_data, news_data, trend_data)
            if llm_result:
                print(llm_result)
        
        print("\n" + "=" * 50)
        print(f"分析完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        return alerts
    
    def _llm_deep_analysis(self, stock_codes, realtime_data, fund_flow_data, finance_data, news_data, trend_data):
        """调用LLM进行深度分析"""
        import json
        
        # 构建股票数据摘要
        stock_summary = []
        for code in stock_codes:
            name = self.stock_names.get(code, code)
            
            # 实时行情
            rt = next((r for r in realtime_data if r.get('code') == code), {})
            
            # 资金流向
            ff = next((f for f in fund_flow_data if f.get('code') == code), {})
            
            # 财务数据
            fin = next((f for f in finance_data if f.get('code') == code), {})
            
            # 趋势数据
            td = next((t for t in trend_data if t.get('code') == code), {})
            
            stock_info = {
                'code': code,
                'name': name,
                'price': rt.get('price', 0),
                'change_pct': rt.get('change_pct', 0),
                'volume': rt.get('volume', 0),
                'main_inflow': ff.get('main_inflow', 0),
                'limit_up_count': td.get('limit_up_count', 0),
                'ma5': td.get('ma5', 0),
                'pe': fin.get('pe', 0),
                'score': td.get('score', 0)
            }
            stock_summary.append(stock_info)
        
        prompt = f"""你是一个专业的A股股票分析师。请根据以下股票数据，遵循严格的交易原则进行选股和深度分析。

## 交易原则（必须严格遵守）
1. 只选20日内出现过涨停的股票
2. 强势股看"红肥绿瘦"
3. 股价在五日线上就稳稳持有
4. 不冲高不卖，不跳水不买，趋势不明朗不交易
5. 趋势优先，买绿不买红，卖红不卖绿
6. 学会空仓：五日线拐头向下或股价在均线下方时必须空仓

## 当前股票池数据
{json.dumps(stock_summary, ensure_ascii=False, indent=2)}

## 分析要求
1. 严格按交易原则筛选股票
2. 对每只股票给出买入/持有/卖出/观望建议
3. 给出具体的仓位建议和止损点
4. 分析资金流向和技术面趋势
5. 识别风险点和机会点
6. 只推荐符合原则的股票，拒绝垃圾股

请输出结构化的分析报告，包括：
- 符合买入条件的股票及理由
- 不符合条件但需关注的股票
- 风险预警
- 具体交易建议（仓位、买入点、止损点）
"""
        
        system_prompt = """你是一个专业的A股短线交易分析师，擅长技术分析和资金流向分析。严格按照交易原则选股，不推荐弱势股和阴跌股。分析时要结合量价关系、资金流向、均线系统进行综合判断。"""
        
        result, error = self.llm.chat(prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=4000)
        
        if error:
            print(f"LLM分析失败: {error}")
            return None
        
        return result

    def _fix_industries(self):
        """将 stock_list.yaml 中行业为「其他」的股票，通过 baostock 查询真实行业并更新"""
        import os, yaml
        list_path = os.path.join(self.config_dir, 'resource', 'stock_list.yaml')
        if not os.path.exists(list_path):
            return
        with open(list_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        stocks = data.get('stocks', [])
        to_fix = [s for s in stocks if not s.get('industry') or s.get('industry') in ('其他', '其他/其他', '')]
        if not to_fix:
            return
        import baostock as bs
        bs.login()
        changed = 0
        for s in to_fix:
            code = s['code']
            bs_code = f"sh.{code}" if code.startswith('6') else f"sz.{code}"
            try:
                rs = bs.query_stock_industry(bs_code)
                while rs.next():
                    row = rs.get_row_data()
                    official = row[3]
                    # 关键词 → 简化行业映射
                    kw_map = [
                        # 新能源/电气
                        ('电气机械', 'AI/新能源'), ('汽车', '新能源车'), ('锂', '新能源车'),
                        ('电池', '新能源车'), ('光伏', '光伏'), ('电力', '光伏'),
                        ('电气设备', 'AI/新能源'),
                        # 消费
                        ('酒', '消费/白酒'), ('食品', '消费'), ('饮料', '消费'),
                        ('调味品', '消费'), ('化妆品', '消费'), ('农副食品', '消费'),
                        ('烟草', '消费'), ('纺织', '消费'), ('服装', '消费/服装'),
                        ('皮革', '消费'), ('木材', '消费'), ('家具', '消费'),
                        ('造纸', '消费'), ('印刷', '消费'), ('文教', '消费'),
                        ('文体', '消费'), ('娱乐', '消费'), ('餐饮', '消费'),
                        ('零售', '消费'), ('住宿', '消费'),
                        # 金融
                        ('货币金融', '银行'), ('银行', '银行'), ('保险', '保险'),
                        ('证券', '证券'), ('资本市场', '证券'), ('金融', '银行'),
                        # 房地产
                        ('房地产', '房地产'),
                        # 医药
                        ('医药', '医药'), ('医疗', '医药'), ('制药', '医药'),
                        ('生物', '医药/生物制药'), ('卫生', '医药'),
                        # AI/软件
                        ('计算机', 'AI/软件'), ('软件', 'AI/软件'), ('信息技术', 'AI/软件'),
                        ('互联网', 'AI/软件'), ('云计算', 'AI/软件'),
                        ('大数据', 'AI/软件'), ('人工智能', 'AI/软件'),
                        # 芯片/电子
                        ('电子', '芯片'), ('半导体', '芯片'), ('集成电路', '芯片'),
                        ('通信', '芯片/通信'), ('电子设备', '芯片'),
                        ('仪器仪表', '芯片'), ('元器件', '芯片'),
                        # 化工
                        ('化工', '化工'), ('化学', '化工'), ('石化', '化工'),
                        ('石油', '化工'), ('橡胶', '化工'), ('塑料', '化工'),
                        ('化纤', '化工'), ('涂料', '化工'),
                        # 有色/金属
                        ('有色', '有色'), ('金属', '有色'), ('钢铁', '制造'),
                        ('非金属矿物', '制造/建材'), ('有色金属', '有色'),
                        # 制造
                        ('家电', '制造/家电'), ('机械', '制造'), ('设备', '制造'),
                        ('通用设备', '制造'), ('专用设备', '制造'),
                        ('运输设备', '制造'), ('仪器仪表制造', '制造'),
                        # 军工
                        ('军工', '军工'), ('航空', '军工'), ('航天', '军工'),
                        ('船舶', '军工'), ('兵器', '军工'),
                        # 基建/建材
                        ('建材', '制造/建材'), ('建筑', '基建'), ('基建', '基建'),
                        ('土木工程', '基建'), ('装饰', '基建'),
                        # 交通/航运
                        ('交通运输', '航运'), ('铁路', '基建'), ('公路', '基建'),
                        ('水上运输', '航运'), ('航空运输', '航运'), ('物流', '航运'),
                        # 农牧
                        ('农业', '制造/农牧'), ('牧', '制造/农牧'), ('渔业', '消费'),
                        ('林业', '制造/农牧'),
                        # PCB
                        ('印刷电路', 'PCB'), ('PCB', 'PCB'),
                        # 环保/新能源
                        ('环保', '新能源'), ('公共设施', '光伏/电力'),
                        ('生态', '新能源'), ('环境', '新能源'),
                        # 综合
                        ('综合', '其他'), ('多元', '其他'),
                    ]
                    matched = '其他'
                    for kw, cat in kw_map:
                        if kw in official:
                            matched = cat
                            break
                    s['industry'] = matched
                    changed += 1
                    break
            except:
                pass
        bs.logout()
        if changed:
            with open(list_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"[_fix_industries] 已修正 {changed} 只股票的行业分类")
        else:
            print("[_fix_industries] 无需修改")

    def run_pipeline(self, mode="quick"):
        """Run analysis pipeline for Tauri sidecar integration"""
        import json
        try:
            if mode == "quick":
                self.run(skip_llm=True, skip_history=True, quick=True)
            else:
                self.run()
            from scoring_engine import run_scoring
            stock_codes = [s.get('code') for s in self.stock_list.get('stocks', [])]
            run_scoring(self.db.db_path, stock_codes)
            self._fix_industries()
            self.db.cleanup_old_data(years=3)
            return {"status": "success", "message": f"Pipeline {mode} completed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


def get_stock_name(code, stock_names):
    """获取股票名称"""
    return stock_names.get(code, code)


def get_financial_data(stock_code):
    """从baostock获取财务数据（营收和净利润）"""
    try:
        import baostock as bs
        
        lg = bs.login()
        if lg.error_code != '0':
            return None
        
        # 转换为baostock格式
        bs_code = f"sh.{stock_code}" if stock_code.startswith('6') else f"sz.{stock_code}"
        
        def get_year_data(bs_code, year):
            """获取单年数据"""
            profit_2025, revenue_2025 = None, None
            rs_profit = bs.query_profit_data(code=bs_code, year=year)
            while rs_profit.error_code == '0' and rs_profit.next():
                row = rs_profit.get_row_data()
                if row and len(row) > 8:
                    # netProfit (索引6) = 净利润
                    # MBRevenue (索引8) = 主营业务收入
                    profit_2025 = row[6]
                    revenue_2025 = row[8]
            return profit_2025, revenue_2025
        
        # 2025年数据
        profit_2025, revenue_2025 = get_year_data(bs_code, '2025')
        
        # 2024年数据
        profit_2024, revenue_2024 = get_year_data(bs_code, '2024')
        
        # 2023年数据
        profit_2023, revenue_2023 = get_year_data(bs_code, '2023')
        
        bs.logout()
        
        return {
            'revenue': {'2023': revenue_2023, '2024': revenue_2024, '2025': revenue_2025},
            'profit': {'2023': profit_2023, '2024': profit_2024, '2025': profit_2025}
        }
    except Exception as e:
        print(f"获取{stock_code}财务数据失败: {e}")
        return None


def calculate_growth_rate(finance_data):
    """计算增长率"""
    if not finance_data or not finance_data.get('revenue'):
        return None
    
    revenue = finance_data.get('revenue', {})
    profit = finance_data.get('profit', {})
    
    # 营收数据
    rev_2025 = revenue.get('2025', '')
    rev_2024 = revenue.get('2024', '')
    rev_2023 = revenue.get('2023', '')
    
    # 解析数值（可能带单位如"亿"、"万"）
    def parse_value(val):
        if not val or val == 'N/A':
            return 0
        val_str = str(val).replace(',', '').strip()
        try:
            if '亿' in val_str:
                return float(val_str.replace('亿', '')) * 100000000
            elif '万' in val_str:
                return float(val_str.replace('万', '')) * 10000
            else:
                return float(val_str)
        except:
            return 0
    
    rev_2025_val = parse_value(rev_2025)
    rev_2024_val = parse_value(rev_2024)
    rev_2023_val = parse_value(rev_2023)
    
    # 计算2024年增长率
    rev_growth_2024 = 0
    if rev_2023_val > 0:
        rev_growth_2024 = ((rev_2024_val - rev_2023_val) / rev_2023_val) * 100
    
    # 计算2025年增长率
    rev_growth_2025 = 0
    if rev_2024_val > 0:
        rev_growth_2025 = ((rev_2025_val - rev_2024_val) / rev_2024_val) * 100
    
    # 利润数据
    profit_2025 = profit.get('2025', '')
    profit_2024 = profit.get('2024', '')
    profit_2023 = profit.get('2023', '')
    profit_2025_val = parse_value(profit_2025)
    profit_2024_val = parse_value(profit_2024)
    profit_2023_val = parse_value(profit_2023)
    
    # 2024年利润增长
    profit_growth_2024 = 0
    if profit_2023_val > 0:
        profit_growth_2024 = ((profit_2024_val - profit_2023_val) / profit_2023_val) * 100
    
    # 2025年利润增长
    profit_growth_2025 = 0
    if profit_2024_val > 0:
        profit_growth_2025 = ((profit_2025_val - profit_2024_val) / profit_2024_val) * 100
    
    # 格式化显示值（从元转换为亿元）
    def format_for_display(val):
        if not val:
            return 'N/A'
        val_float = parse_value(val)
        if abs(val_float) == 0:
            return 'N/A'
        # 转换为亿元
        val_yi = val_float / 100000000
        if abs(val_yi) >= 1:
            return f"{val_yi:.2f}亿"
        else:
            # 小于1亿元显示为万元
            val_wan = val_float / 10000
            return f"{val_wan:.2f}万"
    
    return {
        'rev_2024_growth': round(rev_growth_2024, 2),
        'rev_2025_growth': round(rev_growth_2025, 2),
        'profit_2024_growth': round(profit_growth_2024, 2),
        'profit_2025_growth': round(profit_growth_2025, 2),
        'revenue_2023': format_for_display(rev_2023),
        'revenue_2024': format_for_display(rev_2024),
        'revenue_2025': format_for_display(rev_2025),
        'profit_2023': format_for_display(profit_2023),
        'profit_2024': format_for_display(profit_2024),
        'profit_2025': format_for_display(profit_2025)
    }


def get_trading_points(stock, code, name):
    """计算买卖点和仓位建议"""
    price = stock.get('price', 0)
    ma5 = stock.get('ma5', 0)
    ma10 = stock.get('ma10', 0)
    main_inflow = stock.get('main_inflow', 0)
    score = stock.get('score', 0)
    limit_up_count = stock.get('limit_up_count', 0)
    volume_ratio = stock.get('volume_ratio', 1)
    
    # 买入点：回调到5日均线附近或支撑位
    buy_point = round(ma5 * 0.98, 2) if ma5 else round(price * 0.95, 2)
    
    # 止损点：跌破10日均线
    stop_loss = round(ma10 * 0.95, 2) if ma10 else round(price * 0.92, 2)
    
    # 短期目标：上涨15%
    short_target = round(price * 1.15, 2)
    
    # 中长期目标：上涨30-50%
    medium_target = round(price * 1.30, 2)
    long_target = round(price * 1.50, 2)
    
    # 仓位建议
    if score >= 100 and main_inflow > 50000000:
        position = "20%"
        position_reason = f"资金持续净流入({main_inflow/10000:.0f}万)，技术面强势，业绩确定性强"
    elif score >= 90 and main_inflow > 30000000:
        position = "15%"
        position_reason = f"主力资金净流入{main_inflow/10000:.0f}万，20日内{limit_up_count}次涨停，趋势向好"
    elif score >= 80 and main_inflow > 10000000:
        position = "10%"
        position_reason = f"均线多头排列，成交量放量{volume_ratio:.1f}倍，有一定的上涨动能"
    elif score >= 70:
        position = "5-8%"
        position_reason = f"符合基本选股条件，但资金流入较少，建议轻仓试水"
    else:
        position = "3-5%"
        position_reason = "评分较低，建议谨慎，轻仓参与"
    
    # 核心逻辑
    if main_inflow > 50000000:
        core_reason = f"主力资金大幅净流入{main_inflow/10000:.0f}万抢筹，看好中长期趋势"
    elif limit_up_count > 0:
        core_reason = f"近期{limit_up_count}次涨停，市场关注度高，资金持续炒作"
    elif volume_ratio > 1.5:
        core_reason = f"成交量放大{volume_ratio:.1f}倍，资金活跃度提升"
    else:
        core_reason = "技术面企稳，均线多头，可中长线布局"
    
    return {
        'buy_point': buy_point,
        'stop_loss': stop_loss,
        'short_target': short_target,
        'medium_target': medium_target,
        'long_target': long_target,
        'position': position,
        'position_reason': position_reason,
        'core_reason': core_reason
    }


def get_stars(score):
    """根据评分返回星级"""
    if score >= 100:
        return "⭐⭐⭐⭐⭐"
    elif score >= 90:
        return "⭐⭐⭐⭐"
    elif score >= 80:
        return "⭐⭐⭐"
    else:
        return "⭐⭐"


def generate_stock_analysis(stock, stock_names):
    """生成单只股票的分析（按模板格式）"""
    code = stock.get('code', '')
    name = get_stock_name(code, stock_names)
    trading = get_trading_points(stock, code, name)
    score = stock.get('score', 0)
    stars = get_stars(score)
    price = stock.get('price', 0)
    main_inflow = stock.get('main_inflow', 0)
    limit_up_count = stock.get('limit_up_count', 0)
    
    # 获取财务数据
    finance_data = get_financial_data(code)
    growth = calculate_growth_rate(finance_data) if finance_data else None
    
    # 判断是否亏损
    is_loss = False
    if growth:
        profit_2024 = growth.get('profit_2024', '')
        if '亿' in str(profit_2024):
            try:
                profit_val = float(str(profit_2024).replace('亿', '').replace('-', ''))
                if profit_val < 0:
                    is_loss = True
            except:
                pass
    
    # 生成分析报告
    analysis = f"""
## 一、{name} ({code}) {stars}

### 1. 核心指标

| 指标 | 数值 |
|------|------|
| 当前价 | ¥{price:.2f} |
| 20日涨停 | {'✅ ' if limit_up_count > 0 else '❌'}{limit_up_count}次 |
| 主力资金 | ¥{main_inflow/100000000:.2f}亿 |
| 评分 | {score}分 |

### 2. 买卖点建议

| 类型 | 价格 | 理由 |
|------|------|------|
| **买入点** | ¥{trading['buy_point']:.0f}-{trading['buy_point']+2:.0f} | 现价可入，股价在5日均线上方 |
| **止损点** | ¥{trading['stop_loss']:.0f} | 跌破10日线必须止损 |
| **短期卖出** | ¥{trading['short_target']:.0f} | +{((trading['short_target']-price)/price*100):.0f}%，5-10个交易日 |
| **中长期卖出** | ¥{trading['medium_target']:.0f}-{trading['long_target']:.0f} | +{((trading['medium_target']-price)/price*100):.0f}-{((trading['long_target']-price)/price*100):.0f}%，1-3个月 |
| **建议仓位** | **{trading['position']}** | {trading['position_reason'].split('，')[0]} |

### 3. 仓位分析

**给予{trading['position']}仓位的理由**：
{get_position_reasons(stock, trading, is_loss)}

"""
    
    # 财务数据
    if growth:
        analysis += f"""
### 4. 三年财务数据

| 年份 | 营收 | 净利润 | 同比 |
|------|------|--------|------|
| 2025年 | {growth.get('revenue_2025', 'N/A')} | {growth.get('profit_2025', 'N/A')} | {growth.get('profit_2025_growth', 0):+.1f}% |
| 2024年 | {growth.get('revenue_2024', 'N/A')} | {growth.get('profit_2024', 'N/A')} | {growth.get('profit_2024_growth', 0):+.1f}% |
| 2023年 | {growth.get('revenue_2023', 'N/A')} | {growth.get('profit_2023', 'N/A')} | - |
"""
        
        if is_loss:
            profit_2025_str = growth.get('profit_2025', 'N/A')
            profit_2024_str = growth.get('profit_2024', 'N/A')
            profit_2025_val = parse_value(profit_2025_str)
            profit_2024_val = parse_value(profit_2024_str)
            loss_trend = "亏损扩大" if profit_2025_val < profit_2024_val else "亏损收窄"
            
            analysis += f"""
### 5. 亏损情况分析

**2025年净利润**: {profit_2025_str}，{loss_trend}

- 建议关注公司是否处于产能爬坡期
- 关注研发投入是否持续增加
- 关注毛利率变化趋势
- 关注现金流情况

**未来展望**：
- 产能释放后有望实现盈亏平衡
- 需要持续跟踪公司经营战略调整
"""
        else:
            rev_2025 = growth.get('revenue_2025', 'N/A')
            rev_2024 = growth.get('revenue_2024', 'N/A')
            profit_2025 = growth.get('profit_2025', 'N/A')
            profit_2024 = growth.get('profit_2024', 'N/A')
            rev_growth_2025 = growth.get('rev_2025_growth', 0)
            rev_growth_2024 = growth.get('rev_2024_growth', 0)
            profit_growth_2025 = growth.get('profit_2025_growth', 0)
            profit_growth_2024 = growth.get('profit_2024_growth', 0)
            
            # 动态生成经营分析
            if rev_growth_2025 > 20:
                trend = "快速增长"
            elif rev_growth_2025 > 0:
                trend = "稳健增长"
            elif rev_growth_2025 > -10:
                trend = "小幅下降"
            else:
                trend = "明显下滑"
            
            analysis += f"""
### 5. 2025年经营情况分析

**营收表现**：{rev_2025}，同比{rev_growth_2025:+.1f}%，整体{trend}

**利润表现**：{profit_2025}，同比{profit_growth_2025:+.1f}%

### 6. 2024年经营情况回顾

**营收**：{rev_2024}，同比{rev_growth_2024:+.1f}%
**利润**：{profit_2024}，同比{profit_growth_2024:+.1f}%

### 7. 经营趋势总结

根据2023-2025年财务数据，公司近三年营收复合增长率约为{calculate_cagr({'2023': growth.get('revenue_2023', ''), '2024': growth.get('revenue_2024', ''), '2025': growth.get('revenue_2025', '')})}%，利润复合增长率约为{calculate_cagr({'2023': growth.get('profit_2023', ''), '2024': growth.get('profit_2024', ''), '2025': growth.get('profit_2025', '')})}%。

- 若营收和利润持续增长，表明公司具有良好的成长性
- 若增速放缓，需关注行业景气度变化
- 若出现下滑，需分析是周期性因素还是结构性变化

（更多深度分析建议参考公司最新财报和行业研报）
"""
    else:
        analysis += """
### 4. 三年财务数据

*注: 财务数据获取失败，请参考公司定期报告*
"""
    
    # 添加政策匹配与发展预期（数据驱动）
    policy_analysis = get_policy_analysis(code, name, growth)
    analysis += f"""
### 8. 政策匹配与行业发展预期

{policy_analysis}
"""

    analysis += "\n---\n"
    
    return analysis


def calculate_cagr(values_dict):
    """计算复合增长率"""
    vals = []
    for y in ['2023', '2024', '2025']:
        v = values_dict.get(y, '')
        if v:
            try:
                val = float(str(v).replace('亿', '').replace(',', ''))
                vals.append(val)
            except:
                pass
    if len(vals) >= 2 and vals[0] > 0:
        cagr = ((vals[-1] / vals[0]) ** (1/(len(vals)-1)) - 1) * 100
        return f"{cagr:.1f}"
    return "N/A"


def get_policy_analysis(code, name, growth):
    """动态获取政策匹配与发展预期"""
    rev_growth_2025 = growth.get('rev_2025_growth', 0) if growth else 0
    
    # 判断行业
    if code.startswith('68') or code.startswith('300'):
        industry = "半导体"
    elif '002475' in code or '002241' in code:
        industry = "消费电子"
    elif '600519' in code or '000858' in code:
        industry = "白酒"
    elif '600438' in code or '601012' in code:
        industry = "光伏"
    elif '300750' in code or '002594' in code:
        industry = "新能源车"
    elif '000651' in code or '000333' in code:
        industry = "家电"
    elif '600276' in code or '300003' in code:
        industry = "医药"
    elif any(x in code for x in ['601398', '601939', '600036', '601166']):
        industry = "银行"
    else:
        industry = "综合"
    
    # 动态获取2026年政策预期
    try:
        import subprocess
        result = subprocess.run(
            ['python3', '-c', f'''
import json
try:
    from_websearch = True
    import sys
    sys.path.insert(0, "/Users/ws/.config/opencode/skills/stock-analyst/scripts")
    from main import websearch
    results = websearch(f"{industry}行业 2026年政策 支持 发展预期")
    print(results[:500] if results else "")
except:
    print("")
'''],
            capture_output=True, text=True, timeout=10
        )
        policy_info = result.stdout.strip() if result.stdout.strip() else ""
    except:
        policy_info = ""
    
    # 根据营收增长趋势生成预期
    if rev_growth_2025 > 15:
        outlook = "行业景气度较高，2026年有望继续保持增长态势"
    elif rev_growth_2025 > 0:
        outlook = "行业平稳发展，2026年预期保持稳健增长"
    elif rev_growth_2025 > -10:
        outlook = "行业短期承压，2026年有望逐步企稳复苏"
    else:
        outlook = "行业面临挑战，需关注转型升级进展"
    
    return f"""**行业定位**：{industry}行业

**发展预期**：{outlook}

**政策环境**：国家稳增长政策持续发力，{industry}行业受益于相关产业政策支持。建议关注公司是否具备核心竞争力和行业地位。

（更多政策信息请参考最新行业研报）"""
    
    
def get_position_reasons(stock, trading, is_loss):
    """生成仓位分析理由"""
    main_inflow = stock.get('main_inflow', 0)
    limit_up_count = stock.get('limit_up_count', 0)
    volume_ratio = stock.get('volume_ratio', 1)
    score = stock.get('score', 0)
    position = trading['position']
    
    reasons = []
    
    if main_inflow > 50000000:
        reasons.append(f"✅ 主力资金大幅净流入{main_inflow/100000000:.2f}亿，机构抢筹明显")
    elif main_inflow > 10000000:
        reasons.append(f"✅ 主力资金持续净流入{main_inflow/100000000:.2f}亿")
    
    if limit_up_count > 0:
        reasons.append(f"✅ 近期{limit_up_count}次涨停，市场关注度高")
    
    if is_loss:
        reasons.append("⚠️ 持续亏损，短期内难以盈利")
        reasons.append("✅ 营收增长，产能扩张中，国产替代空间大")
    else:
        reasons.append("✅ 基本面稳健，业绩确定性强")
    
    if volume_ratio > 1.5:
        reasons.append(f"✅ 成交量放大{volume_ratio:.1f}倍，资金活跃")
    
    if score >= 100:
        reasons.append("✅ 技术面强势，均线多头排列")
    
    # 根据仓位添加理由
    if position == "20%":
        reasons.append("✅ 资金持续流入，基本面稳健")
    elif position == "15-20%":
        reasons.append("✅ 资金抢入，国产替代加速")
    elif position == "10-15%":
        reasons.append("✅ 涨停强势，但需控制风险")
    elif "5%" in position:
        reasons.append("⚠️ 轻仓长线，等待拐点")
    
    # 生成理由列表
    reason_lines = []
    for i, r in enumerate(reasons, 1):
        reason_lines.append(f"{i}. {r}")
    
    return "\n".join(reason_lines)


def run_analysis():
    """执行日常分析"""
    analyst = StockAnalyst()
    analyst.run()


def run_deep_analysis(top_n=10):
    """执行深度分析并生成报告（LLM驱动）"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    db_path = config.get('database', {}).get('path', '')
    output_dir = config.get('output_dir', '/Users/ws/Desktop/Project/A-share-Project/Resource/买入推送')
    
    # 加载股票名称映射
    config_dir = os.path.join(base_dir, '..')
    list_path = os.path.join(config_dir, 'resource', 'stock_list.yaml')
    with open(list_path, 'r', encoding='utf-8') as f:
        stock_list_data = yaml.safe_load(f)
    stock_names = {s['code']: s['name'] for s in stock_list_data.get('stocks', [])}
    
    # 获取符合原则的股票
    picker = StockPicker(db_path)
    stocks = picker.recommend_stocks(top_n=top_n)
    
    # 调用LLM进行深度分析
    llm = LLMClient()
    
    # 构建股票完整数据
    stock_full_data = []
    for s in stocks:
        code = s.get('code', '')
        name = stock_names.get(code, code)
        
        # 从数据库获取更详细数据
        db = DBManager(db_path)
        history = db.get_history(code, days=20) or []
        finance = db.get_finance(code) or {}
        news = db.get_news(code, limit=5) or []
        
        stock_info = {
            'code': code,
            'name': name,
            'price': s.get('price', 0),
            'change_pct': s.get('change_pct', 0),
            'volume': s.get('volume', 0),
            'main_inflow': s.get('main_inflow', 0),
            'limit_up_count': s.get('limit_up_count', 0),
            'ma5': s.get('ma5', 0),
            'ma10': s.get('ma10', 0),
            'pe': s.get('pe', 0),
            'score': s.get('score', 0),
            'history': history,
            'finance': finance,
            'news': news[:3]
        }
        stock_full_data.append(stock_info)
    
    import json
    prompt = f"""你是一个专业的A股股票分析师。请根据以下股票数据，遵循严格的交易原则进行深度分析并生成买入报告。

## 交易原则（必须严格遵守）
1. 只选20日内出现过涨停的股票
2. 强势股看"红肥绿瘦"
3. 股价在五日线上就稳稳持有
4. 不冲高不卖，不跳水不买，趋势不明朗不交易
5. 趋势优先，买绿不买红，卖红不卖绿
6. 学会空仓：五日线拐头向下或股价在均线下方时必须空仓

## 股票数据
{json.dumps(stock_full_data, ensure_ascii=False, indent=2)}

## 输出要求
请生成一份专业的买入分析报告，包含：
1. 每只股票的买入/持有/卖出/观望建议及理由
2. 具体仓位建议（不超过20%单只）
3. 买入点、止损点、目标价
4. 资金流向和技术面分析
5. 风险提示
6. 最终汇总：符合条件的股票列表及总仓位建议

格式要求：Markdown格式，清晰易读。"""
    
    system_prompt = """你是一个专业的A股短线交易分析师，擅长技术分析和资金流向分析。严格按照交易原则选股，不推荐弱势股和阴跌股。分析时要结合量价关系、资金流向、均线系统进行综合判断。输出专业的分析报告。"""
    
    result, error = llm.chat(prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=6000)
    
    if error:
        print(f"LLM分析失败: {error}")
        return stocks
    
    report = f"""# 📈 股票深度分析报告（LLM智能分析）

**生成日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析股票数**: {len(stocks)} 只
**LLM模型**: qwen3.5-35b-a3b

---

{result}

---

*本报告由AI自动分析生成，仅供参考*
"""
    
    os.makedirs(output_dir, exist_ok=True)
    filename = f"股票深度分析报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ LLM深度分析报告已生成:")
    print(f"📁 {filepath}")
    
    # 同时打印到控制台
    print("\n" + "="*60)
    print("LLM分析结果:")
    print("="*60)
    print(result)
    
    return stocks


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
股票分析助手 - 使用说明

用法:
    python3 main.py              # 执行日常分析
    python3 main.py --pick       # 选股筛选（自动生成深度报告）
    python3 main.py --pick --top=10  # 推荐前10只
    python3 main.py --analyze   # 生成深度分析报告

功能:
    - 爬取实时行情和资金流向
    - 获取财务指标
    - 获取资讯公告
    - 趋势分析
    - 预警检测
    - 选股推送（按交易原则）
    - 深度分析报告（买卖点+仓位+财务）

选股原则:
    1. 只选20日内出现过涨停的股票
    2. 强势股看"红肥绿瘦"
    3. 股价在五日线上就稳稳持有
    4. 创200天新高主升浪
    5. 放量上涨持有，放量滞涨卖出

配置文件:
    - scripts/config.yaml
    - resource/stock_list.yaml

数据库:
    - ../data/stock_data.db

输出目录:
    - /Users/ws/Desktop/Project/A-share-Project/Resource/买入推送/
        """)
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == '--pick':
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--top', type=int, default=10, help='推荐数量')
        args = parser.parse_args(sys.argv[2:])
        
        run_deep_analysis(top_n=args.top)
        return
    
    if len(sys.argv) > 1 and sys.argv[1] == '--analyze':
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--top', type=int, default=10, help='分析股票数量')
        args = parser.parse_args(sys.argv[2:])
        
        run_deep_analysis(top_n=args.top)
        return
    
    run_analysis()


if __name__ == "__main__":
    # Detect sidecar mode (--mode) vs legacy CLI
    if "--mode" in sys.argv:
        try:
            mode_idx = sys.argv.index("--mode")
            sidecar_mode = sys.argv[mode_idx + 1] if mode_idx + 1 < len(sys.argv) else "quick"
            sidecar_scope = "portfolio"
            try:
                scope_idx = sys.argv.index("--scope")
                sidecar_scope = sys.argv[scope_idx + 1] if scope_idx + 1 < len(sys.argv) else "portfolio"
            except ValueError:
                pass
        except (ValueError, IndexError):
            sidecar_mode = "quick"
            sidecar_scope = "portfolio"

        import json
        analyst = StockAnalyst()
        if sidecar_mode == "llm":
            stock_codes = [s.get('code') for s in analyst.stock_list.get('stocks', [])]
            realtime_data = analyst.crawler.batch_crawl_realtime(stock_codes)
            fund_flow_data = analyst.crawler.batch_crawl_fund_flow(stock_codes)
            finance_data = analyst.finance_fetcher.batch_fetch(stock_codes)
            news_data = analyst.news_fetcher.batch_fetch(stock_codes)
            trend_data = analyst.trend_analyzer.batch_analyze(stock_codes)
            result = analyst._llm_deep_analysis(stock_codes, realtime_data, fund_flow_data, finance_data, news_data, trend_data)
            print(json.dumps({"report": str(result)}, ensure_ascii=False))
        else:
            result = analyst.run_pipeline(mode=sidecar_mode)
            print(json.dumps(result, ensure_ascii=False))
    else:
        main()