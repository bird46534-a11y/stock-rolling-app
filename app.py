import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# --- 網頁配置 ---
st.set_page_config(page_title="金字塔滾動策略系統", layout="centered")

# --- 硬編碼 Fugle API Token ---
FUGLE_TOKEN = "YjhjNGU4MDgtNGU1Zi00ZDc3LWE0ODItMTczMTVkMzAwNzAwIDk3YzQwZWYxLWQ4NWItNDg5NS1iODFjLWU0YjYzNTIwOTdlYw=="

# --- 核心邏輯：跳動單位修正 ---
def adjust_tick(price):
    if price < 10: return round(price, 2)
    elif price < 50: return round(price * 20) / 20
    elif price < 100: return round(price * 10) / 10
    elif price < 500: return round(price * 2) / 2
    elif price < 1000: return round(price)
    else: return round(price / 5) * 5

# --- 富果 API 名稱抓取 ---
@st.cache_data(ttl=86400)
def get_stock_name(stock_no):
    try:
        url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/tickers/{stock_no}"
        headers = {"X-Fugle-Resusage-Token": FUGLE_TOKEN}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get('name')
    except:
        pass
    return stock_no

# --- 回測引擎 ---
def backtest_strategy(df, capital):
    df = df.copy()
    close_prices = df['Close'].squeeze()
    ma20_series = close_prices.rolling(window=20).mean()
    in_position, buy_price, trades = False, 0, []
    for i in range(20, len(df)):
        curr_p = float(close_prices.iloc[i])
        ma20 = float(ma20_series.iloc[i])
        if pd.isna(ma20): continue
        if not in_position:
            if curr_p > ma20:
                in_position, buy_price = True, curr_p
        else:
            if curr_p < ma20 or curr_p < buy_price * 0.93:
                trades.append((curr_p - buy_price) / buy_price)
                in_position = False
    if not trades: return 0, 0, 0, 0
    win_rate = len([t for t in trades if t > 0]) / len(trades)
    total_ret = (np.prod([1 + t for t in trades]) - 1)
    return win_rate, total_ret, capital * total_ret, min(trades)

def analyze_stock(stock_no, total_capital):
    stock_id = f"{stock_no}.TW"
    ticker = yf.Ticker(stock_id)
    df = ticker.history(period="2y")
    if df.empty or len(df) < 20:
        stock_id = f"{stock_no}.TWO"
        ticker = yf.Ticker(stock_id)
        df = ticker.history(period="2y")
    
    if df.empty: return None

    # --- 基本面與籌碼面數據 ---
    try:
        yoy = ticker.info.get('revenueGrowth', 0) * 100
        inst_pct = ticker.info.get('heldPercentInstitutions', 0) * 100
    except:
        yoy, inst_pct = 0, 0

    stock_name = get_stock_name(stock_no)
    latest_data = df.iloc[-1]
    curr_p = float(latest_data['Close'])
    
    # 技術指標
    ma_series = df['Close'].rolling(window=20).mean()
    ma20 = float(ma_series.iloc[-1])
    is_ma_up = ma20 > float(ma_series.iloc[-6])
    
    # 診斷理由
    reasons = []
    if curr_p >= ma20:
        status, color = ("🌕 強勢多頭", "green") if is_ma_up else ("☁️ 弱勢反彈 (防假突破)", "blue")
        if is_ma_up: reasons.append("✅ **趨勢翻多**：股價站上月線且趨勢向上。")
        else: reasons.append("⚠️ **假突破警告**：月線仍下彎，小心騙線觀望。")
    else:
        status, color = ("⛅ 多頭回檔", "orange") if is_ma_up else ("🌑 趨勢偏弱", "red")
        reasons.append("❌ **目前不符合進場條件**。")

    win_rate, total_ret, profit_amt, max_loss = backtest_strategy(df, total_capital)
    shares = int((total_capital * 0.4) // curr_p)
    
    return {
        "id": stock_no, "name": stock_name, "price": adjust_tick(curr_p), "ma20": adjust_tick(ma20),
        "status": status, "color": color, "reasons": reasons, "yoy": yoy, "inst": inst_pct,
        "main_vol": int(latest_data['Volume']) // 1000, "avg_vol_5": round(float(df['Volume'].iloc[-6:-1].mean()) / 1000),
        "lots": shares // 1000, "odds": shares % 1000,
        "stop_loss": adjust_tick(curr_p * 0.93), "add_1": adjust_tick(curr_p * 1.07), "tp_1": adjust_tick(curr_p * 1.15),
        "win_rate": win_rate, "total_ret": total_ret, "profit_amt": profit_amt, "max_loss": max_loss
    }

# --- 介面呈現 ---
st.title("🏆 金字塔滾動策略系統")

user_capital = st.sidebar.number_input("總投入本金 (台幣)", min_value=10000, value=100000)
target = st.text_input("📍 請輸入股票代號 (如: 2330, 3481)", "")

if target:
    res = analyze_stock(target, user_capital)
    if res:
        st.divider()
        st.header(f"📌 {res['name']} ({res['id']})")
        
        # 指標卡
        i1, i2, i3 = st.columns(3)
        i1.metric("營收年增率 (YoY)", f"{res['yoy']:.1f}%")
        i2.metric("法人持股 (估)", f"{res['inst']:.1f}%")
        i3.metric("當前股價", f"{res['price']:.2f}")

        st.markdown(f"### 狀態：:{res['color']}[{res['status']}]")
        
        v1, v2 = st.columns(2)
        v1.metric("今日成交張數", f"{res['main_vol']:,} 張")
        v2.metric("5 日均張", f"{res['avg_vol_5']:,} 張")

        st.write("---")
        st.subheader("💡 綜合診斷")
        for r in res['reasons']: st.write(r)

        st.write("---")
        st.caption(f"📊 過去一年回測績效")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("歷史勝率", f"{res['win_rate']*100:.1f}%")
        c2.metric("累積報酬", f"{res['total_ret']*100:.1f}%")
        c3.metric("獲利金額", f"{int(res['profit_amt']):,}")
        c4.metric("最大單賠", f"{res['max_loss']*100:.1f}%")
        
        st.divider()
        if res['status'] == "🌕 強勢多頭":
            st.success("✅ 符合建倉條件")
            st.code(f"買進建議：{res['lots']}張 + {res['odds']}股\n止損參考：{res['stop_loss']:.2f}", language="text")
            st.table(pd.DataFrame({
                "動作": ["🛑 止損 (-7%)", "📍 建倉 (40%)", "➕ 加倉 (+7%)", "💰 停利 (+15%)"],
                "價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"]
            }))
        else:
            st.warning("❌ 目前不符合進場條件。")

        # --- 補回：金字塔策略準則 (最重要區塊) ---
        st.write("---")
        st.subheader("📖 金字塔滾動策略準則")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 1️⃣ 資金分配 (4:3:3)")
            st.write(f"- **底倉 (40%)**：股價站穩月線進場。")
            st.write(f"- **加碼 (30%)**：獲利達 **+7%** 時執行。")
            st.write(f"- **剩餘 (30%)**：獲利擴大或突破新高。")
        with col_b:
            st.markdown("#### 2️⃣ 出場紀律")
            st.write(f"- **硬性止損**：成本 **-7%** 絕不留戀。")
            st.write(f"- **趨勢出場**：收盤跌破月線 (**{res['ma20']:.2f}**)。")
            st.write(f"- **移動停利**：獲利達 **+15%** 以上分批落袋。")

        st.info(f"""
        **⚠️ 投資風險提醒：**
        1. 營收 YoY > 0% 代表公司有基本面支撐。
        2. 法人持股比例越高，籌碼相對集中穩定。
        3. 策略核心：**「砍斷虧損，讓利潤奔跑」**。
        """)
    else:
        st.error("查無資料。")
