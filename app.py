import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 網頁配置 ---
st.set_page_config(page_title="國泰滾動決策中心", layout="centered")

# --- 核心邏輯：跳動單位修正 ---
def adjust_tick(price):
    if price < 10: return round(price, 2)
    elif price < 50: return round(price * 20) / 20
    elif price < 100: return round(price * 10) / 10
    elif price < 500: return round(price * 2) / 2
    elif price < 1000: return round(price)
    else: return round(price / 5) * 5

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
    profit_amount = capital * total_ret
    max_loss = min(trades)
    return win_rate, total_ret, profit_amount, max_loss

def analyze_stock(stock_no, total_capital):
    stock_id = f"{stock_no}.TW"
    # 增加下載天數確保資料連續性
    df = yf.download(stock_id, period="2y", interval="1d", progress=False)
    if df.empty or len(df) < 20:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="2y", interval="1d", progress=False)
    
    if df.empty: return None

    # --- 數據清理：移除成交量為 0 的異常日 (如假日) ---
    df = df[df['Volume'] > 0]
    
    latest_data = df.iloc[-1]
    data_date = df.index[-1].strftime('%Y-%m-%d')
    curr_p = float(latest_data['Close'])
    ma_series = df['Close'].rolling(window=20).mean()
    ma20 = float(ma_series.iloc[-1])
    ma20_prev = float(ma_series.iloc[-6])
    
    # --- 多空判斷 ---
    is_ma_up = ma20 > ma20_prev
    if curr_p >= ma20 and is_ma_up:
        trend_status, trend_color, trend_advice = "🌕 強勢多頭", "green", "趨勢向上且站穩月線，建議執行建倉。"
    elif curr_p < ma20 and is_ma_up:
        trend_status, trend_color, trend_advice = "⛅ 多頭回檔", "orange", "趨勢仍向上但短線跌破，建議觀望止跌。"
    else:
        trend_status, trend_color, trend_advice = "🌑 趨勢偏弱", "red", "目前非多頭格局，絕對禁止買入。"

    # --- 成交量精確選取 ---
    curr_vol = float(latest_data['Volume'])
    avg_vol_5 = float(df['Volume'].iloc[-6:-1].mean()) # 取最近 5 個完整交易日
    vol_ratio = curr_vol / avg_vol_5 if avg_vol_5 > 0 else 1
    
    win_rate, total_ret, profit_amt, max_loss = backtest_strategy(df.iloc[-252:], total_capital)
    shares = int((total_capital * 0.4) // curr_p)
    
    return {
        "id": stock_no, "date": data_date, "price": adjust_tick(curr_p), "ma20": adjust_tick(ma20),
        "trend_status": trend_status, "trend_color": trend_color, "trend_advice": trend_advice,
        "vol": curr_vol, "avg_vol_5": avg_vol_5, "vol_ratio": vol_ratio,
        "lots": shares // 1000, "odds": shares % 1000,
        "stop_loss": adjust_tick(curr_p * 0.93),
        "add_1": adjust_tick(curr_p * 1.07), "tp_1": adjust_tick(curr_p * 1.15),
        "win_rate": win_rate, "total_ret": total_ret, "profit_amt": profit_amt, "max_loss": max_loss,
        "capital": total_capital
    }

# --- 介面呈現 ---
st.title("📈 台股滾動交易決策看板")

st.sidebar.header("⚙️ 參數設定")
user_capital = st.sidebar.number_input("總投入本金 (台幣)", min_value=10000, value=100000, step=10000)

target = st.text_input("📍 請輸入股票代號 (例如: 3481)", "")

if target:
    res = analyze_stock(target, user_capital)
    if res:
        st.divider()
        st.subheader(f"🔍 {res['id']} 趨勢診斷 (日期: {res['date']})")
        st.markdown(f"### 狀態：:{res['trend_color']}[{res['trend_status']}]")
        
        v1, v2, v3 = st.columns(3)
        v1.metric("當前股價", f"{res['price']:.2f}")
        # 成交量以「張」顯示更符合台股習慣 (1張 = 1000股)
        v2.metric("最新成交張數", f"{int(res['vol'] // 1000):,} 張")
        v3.metric("5日均張", f"{int(res['avg_vol_5'] // 1000):,} 張")

        st.write("---")
        st.caption(f"📊 過去一年策略模擬 (基於 {res['capital']:,.0f} 元本金)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("歷史勝率", f"{res['win_rate']*100:.1f}%")
        c2.metric("累積報酬", f"{res['total_ret']*100:.1f}%")
        c3.metric("獲利金額", f"{int(res['profit_amt']):,}")
        c4.metric("最大單賠", f"{res['max_loss']*100:.1f}%")
        
        st.divider()

        if "多頭" in res['trend_status']:
            st.success(f"✅ 符合建倉條件")
            st.code(f"【{res['id']} 作戰計畫】\n建議買進：{res['lots']}張 + {res['odds']}股\n設定止損：{res['stop_loss']:.2f}", language="text")
            
            plan_df = pd.DataFrame({
                "動作": ["🛑 止損", "📍 建倉", "➕ 加倉", "💰 停利"],
                "價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"]
            })
            st.table(plan_df)
        else:
            st.warning(f"❌ 趨勢尚未翻多，暫不執行滾動建倉。")

        # --- 底部：策略準則 ---
        st.divider()
        st.subheader("📖 金字塔滾動策略準則")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("### 1️⃣ 資金分配")
            st.write(f" - **底倉 (40%)**: {res['capital']*0.4:,.0f} 元")
            st.write(f" - **加碼 (30%+30%)**: 獲利後滾動")
        with col_s2:
            st.markdown("### 2️⃣ 出場紀律")
            st.write(f" - **止損**: 買入價 -7% 或 破月線")
            st.write(f" - **停利**: 達標分批退場")
        
        st.info(f"""
        **💡 溫馨提示：**
        1. **成交量單位**：系統已自動換算為「張數」，方便與國泰 App 對比。
        2. **數據日期**：目前顯示的是 {res['date']} 的結算數據。
        3. **回測範圍**：上方獲利金額為過去 252 個交易日（一年）之模擬。
        """)
    else:
        st.error("查無資料。")
