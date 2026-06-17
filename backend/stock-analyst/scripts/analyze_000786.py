#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 专门分析北新建材 000786

import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import akshare as ak
import baostock as bs
from llm_client import LLMClient
from db_manager import DBManager

# 配置
DB_PATH = "../data/stock_data.db"
STOCK_CODE = "000786"
STOCK_NAME = "北新建材"

def get_realtime_data(code, name):
    """获取实时行情"""
    try:
        # 尝试使用akshare获取实时数据
        df = ak.stock_zh_a_spot_em()
        stock = df[df['代码'] == code]
        if not stock.empty:
            row = stock.iloc[0]
            return {
                'code': code,
                'name': name,
                'price': float(row.get('最新价', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'volume': int(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'turnover': float(row.get('换手率', 0)),
                'pe': float(row.get('市盈率-动态', 0)) if row.get('市盈率-动态') != '-' else 0,
                'pb': float(row.get('市净率', 0)) if row.get('市净率') != '-' else 0,
            }
    except Exception as e:
        print(f"获取实时行情失败: {e}")
    return None

def get_fund_flow(code):
    """获取资金流向"""
    try:
        df = ak.stock_individual_fund_flow(stock=code, market="sz")
        if not df.empty:
            latest = df.iloc[0]
            return {
                'code': code,
                'main_inflow': float(latest.get('主力净流入', 0) or 0) * 10000,  # 转为元
            }
    except Exception as e:
        print(f"获取资金流向失败: {e}")
    return {'code': code, 'main_inflow': 0}

def get_history_kline(code, days=60):
    """获取历史K线数据"""
    try:
        bs_code = f"sz.{code}"
        lg = bs.login()
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        rs = bs.query_history_k_data_plus(bs_code,
            'date,code,open,high,low,close,volume,amount,turnover',
            start_date=start_date, end_date=datetime.now().strftime('%Y-%m-%d'),
            frequency='d', adjustflag='2')
        
        data = []
        while rs.error_code == '0' and rs.next():
            row = rs.get_row_data()
            if row[0]:
                data.append({
                    'trade_date': row[0],
                    'open': float(row[2]) if row[2] else 0,
                    'high': float(row[3]) if row[3] else 0,
                    'low': float(row[4]) if row[4] else 0,
                    'close': float(row[5]) if row[5] else 0,
                    'volume': float(row[6]) if row[6] else 0,
                    'amount': float(row[7]) if row[7] else 0,
                    'turnover': float(row[8]) if row[8] else 0,
                })
        bs.logout()
        return data
    except Exception as e:
        print(f"获取K线数据失败: {e}")
        return []

def get_limit_up_days(code, days=20):
    """计算20日内涨停次数"""
    history = get_history_kline(code, days=days)
    if not history:
        return 0
    
    limit_up_count = 0
    for i in range(1, len(history)):
        prev_close = history[i-1]['close']
        curr_close = history[i]['close']
        if prev_close > 0:
            change_pct = (curr_close - prev_close) / prev_close * 100
            if change_pct >= 9.9:  # 近似涨停
                limit_up_count += 1
    return limit_up_count

def calculate_ma(history, days=5):
    """计算移动平均线"""
    if len(history) < days:
        return 0
    recent = history[-days:]
    return sum([d['close'] for d in recent]) / days

def analyze_kline_pattern(history):
    """分析K线形态（红肥绿瘦）"""
    if len(history) < 5:
        return "数据不足"
    
    red_days = 0  # 上涨阳线
    green_days = 0  # 下跌阴线
    red_sum = 0
    green_sum = 0
    
    for d in history[-5:]:
        change = d['close'] - d['open']
        if change > 0:
            red_days += 1
            red_sum += change
        elif change < 0:
            green_days += 1
            green_sum += abs(change)
    
    if red_days > green_days and red_sum > green_sum:
        return "红肥绿瘦（强势）"
    elif green_days > red_days and green_sum > red_sum:
        return "绿肥红瘦（弱势）"
    else:
        return "多空平衡"

def get_financial_data(code):
    """获取财务数据"""
    try:
        bs_code = f"sz.{code}"
        lg = bs.login()
        
        # 获取2024年年报数据
        rs = bs.query_profit_data(code=bs_code, year='2024')
        profit_data = {}
        while rs.error_code == '0' and rs.next():
            row = rs.get_row_data()
            if row and len(row) > 8:
                profit_data = {
                    'year': '2024',
                    'net_profit': row[6],  # 净利润
                    'revenue': row[8],  # 主营业务收入
                }
        
        bs.logout()
        return profit_data
    except Exception as e:
        print(f"获取财务数据失败: {e}")
        return {}

def main():
    print(f"\n{'='*60}")
    print(f"深度分析 {STOCK_NAME} ({STOCK_CODE})")
    print(f"{'='*60}\n")
    
    # 初始化数据
    realtime = None
    current_price = 0
    change_pct = 0
    volume = 0
    amount = 0
    turnover = 0
    pe = 0
    pb = 0
    
    # 1. 获取实时行情
    print("[1/5] 获取实时行情...")
    try:
        realtime = get_realtime_data(STOCK_CODE, STOCK_NAME)
        if realtime:
            current_price = realtime.get('price', 0)
            change_pct = realtime.get('change_pct', 0)
            volume = realtime.get('volume', 0)
            amount = realtime.get('amount', 0)
            turnover = realtime.get('turnover', 0)
            pe = realtime.get('pe', 0)
            pb = realtime.get('pb', 0)
            print(f"  当前价: ¥{current_price:.2f}")
            print(f"  涨跌幅: {change_pct:+.2f}%")
            print(f"  成交量: {volume/10000:.2f}万手")
            print(f"  成交额: {amount/100000000:.2f}亿")
            print(f"  换手率: {turnover:.2f}%")
            print(f"  市盈率: {pe:.2f}")
            print(f"  市净率: {pb:.2f}")
        else:
            print("  实时行情获取失败")
    except Exception as e:
        print(f"  实时行情获取异常: {e}")
    
    # 如果没有获取到实时数据，使用历史K线最后一天的价格
    if current_price == 0:
        print("  尝试使用历史K线数据...")
    
    # 2. 获取资金流向
    print("\n[2/5] 获取资金流向...")
    fund_flow = get_fund_flow(STOCK_CODE)
    main_inflow = fund_flow.get('main_inflow', 0)
    print(f"  主力净流入: ¥{main_inflow/100000000:.2f}亿")
    
    # 3. 获取历史K线
    print("\n[3/5] 获取历史K线...")
    history = get_history_kline(STOCK_CODE, days=60)
    print(f"  获取到 {len(history)} 条K线数据")
    
    ma5 = 0
    ma10 = 0
    ma20 = 0
    pattern = "数据不足"
    
    if history:
        # 计算技术指标
        ma5 = calculate_ma(history, 5)
        ma10 = calculate_ma(history, 10)
        ma20 = calculate_ma(history, 20)
        
        # 如果实时价格没有获取到，使用K线最后一天的价格
        if current_price == 0:
            current_price = history[-1]['close']
        
        print(f"  当前价: ¥{current_price:.2f}")
        print(f"  5日均线: ¥{ma5:.2f}")
        print(f"  10日均线: ¥{ma10:.2f}")
        print(f"  20日均线: ¥{ma20:.2f}")
        
        # 判断均线位置
        if current_price > ma5:
            print(f"  股价在5日线上方: ✅")
        else:
            print(f"  股价在5日线下方: ❌")
        
        # K线形态
        pattern = analyze_kline_pattern(history)
        print(f"  K线形态: {pattern}")
    
    # 4. 计算涨停次数
    print("\n[4/5] 计算涨停次数...")
    limit_up_count = get_limit_up_days(STOCK_CODE, days=20)
    print(f"  20日内涨停次数: {limit_up_count}次")
    
    # 5. 获取财务数据
    print("\n[5/5] 获取财务数据...")
    finance = get_financial_data(STOCK_CODE)
    if finance:
        print(f"  2024年营收: {finance.get('revenue', 'N/A')}")
        print(f"  2024年净利润: {finance.get('net_profit', 'N/A')}")
    
    # 构建分析数据
    analysis_data = {
        'code': STOCK_CODE,
        'name': STOCK_NAME,
        'realtime': realtime or {},
        'fund_flow': fund_flow,
        'history': history[-20:] if history else [],
        'limit_up_count': limit_up_count,
        'finance': finance,
        'ma5': round(ma5, 2) if ma5 else 0,
        'ma10': round(ma10, 2) if ma10 else 0,
        'ma20': round(ma20, 2) if ma20 else 0,
        'current_price': round(current_price, 2) if current_price else 0,
        'kline_pattern': pattern if pattern else "数据不足",
    }
    
    # 调用LLM进行深度分析
    print("\n" + "="*60)
    print("调用LLM进行深度分析...")
    print("="*60)
    
    llm = LLMClient()
    
    # 提取最近20日K线数据用于分析
    recent_klines = []
    if history:
        for h in history[-20:]:
            recent_klines.append({
                'date': h['trade_date'],
                'open': round(h['open'], 2),
                'high': round(h['high'], 2),
                'low': round(h['low'], 2),
                'close': round(h['close'], 2),
                'volume': int(h['volume']),
            })
    
    prompt = f"""你是一个专业的A股股票分析师。请根据以下北新建材（000786）的详细数据，遵循严格的交易原则进行深度分析。

## 交易原则（必须严格遵守）
1. 只选20日内出现过涨停的股票
2. 强势股看"红肥绿瘦"
3. 股价在五日线上就稳稳持有
4. 不冲高不卖，不跳水不买，趋势不明朗不交易
5. 趋势优先，买绿不买红，卖红不卖绿
6. 学会空仓：五日线拐头向下或股价在均线下方时必须空仓

## 股票数据

### 基本信息
- 股票代码: 000786
- 股票名称: 北新建材
- 当前价格: ¥{analysis_data['current_price']:.2f}

### 实时行情
- 涨跌幅: {change_pct:+.2f}%
- 成交量: {volume/10000:.2f}万手
- 成交额: {amount/100000000:.2f}亿
- 换手率: {turnover:.2f}%
- 市盈率: {pe:.2f}
- 市净率: {pb:.2f}

### 资金流向
- 主力净流入: ¥{main_inflow/100000000:.2f}亿

### 技术指标
- 5日均线: ¥{analysis_data['ma5']:.2f}
- 10日均线: ¥{analysis_data['ma10']:.2f}
- 20日均线: ¥{analysis_data['ma20']:.2f}
- 股价在5日线上: {'是' if analysis_data['current_price'] > analysis_data['ma5'] else '否'}
- K线形态: {analysis_data['kline_pattern']}

### 涨停记录
- 20日内涨停次数: {limit_up_count}次

### 最近20日K线数据
{json.dumps(recent_klines, ensure_ascii=False, indent=2)}

### 财务数据
{json.dumps(finance, ensure_ascii=False, indent=2)}

## 用户问题
用户当前有不少北新建材的仓位，想知道是否可以全部卖出。

## 分析要求
请深度分析并给出以下建议：

1. **当前持仓状态评估**
   - 分析当前股价位置和趋势
   - 判断是否符合持有条件

2. **具体操作建议**
   - 清仓/减仓/持有？
   - 如果减仓，建议减多少？

3. **买入点、止损点、目标价**
   - 如果还有仓位，应该在哪里卖出
   - 止损位设在哪里
   - 短期/中期目标价

4. **风险提示**
   - 当前面临哪些风险
   - 需要注意什么

请严格按照交易原则进行分析，给出明确的可执行建议。"""

    system_prompt = """你是一个专业的A股短线交易分析师，擅长技术分析和资金流向分析。严格按照交易原则选股和分析持仓，特别擅长回答"现在能否卖出"这类问题。分析时要结合量价关系、资金流向、均线系统进行综合判断。给出明确、可执行的建议，避免模棱两可的表述。"""
    
    result, error = llm.chat(prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=4000)
    
    if error:
        print(f"LLM分析失败: {error}")
        return
    
    print("\n" + "="*60)
    print("LLM深度分析报告")
    print("="*60)
    print(result)
    
    # 保存报告
    output_dir = "/Users/ws/Desktop/Project/A-share-Project/Resource/股票分析报告"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"北新建材_000786_深度分析_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    filepath = os.path.join(output_dir, filename)
    
    report = f"""# 北新建材（000786）深度分析报告

**分析日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**LLM模型**: qwen3.5-35b-a3b

---

## 原始数据

### 基本信息
- 股票代码: 000786
- 股票名称: 北新建材
- 当前价格: ¥{analysis_data['current_price']:.2f}

### 实时行情
- 涨跌幅: {change_pct:+.2f}%
- 成交量: {volume/10000:.2f}万手
- 成交额: {amount/100000000:.2f}亿
- 换手率: {turnover:.2f}%
- 市盈率: {pe:.2f}
- 市净率: {pb:.2f}

### 资金流向
- 主力净流入: ¥{main_inflow/100000000:.2f}亿

### 技术指标
- 5日均线: ¥{analysis_data['ma5']:.2f}
- 10日均线: ¥{analysis_data['ma10']:.2f}
- 20日均线: ¥{analysis_data['ma20']:.2f}
- 股价在5日线上: {'是' if analysis_data['current_price'] > analysis_data['ma5'] else '否'}
- K线形态: {analysis_data['kline_pattern']}

### 涨停记录
- 20日内涨停次数: {limit_up_count}次

### 财务数据
{json.dumps(finance, ensure_ascii=False, indent=2)}

---

## LLM深度分析

{result}

---

*本报告由AI自动分析生成，仅供参考，不构成投资建议*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ 报告已保存: {filepath}")

if __name__ == "__main__":
    main()