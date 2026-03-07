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
def backtest_strategy(df):
    df = df.copy()
    close_prices = df['Close'].squeeze()
    ma20_series = close_prices.rolling(window=20).mean()
    
    in_position = False
    buy_price = 0
    trades = []
    
    for i in range(20, len(df)):
        curr_p = float(close_prices.iloc[i])
        ma20 = float(ma20_series.iloc[i])
        if pd.isna(ma20): continue

        if not in_position:
            if curr_p > ma20:
                in_position = True
                buy_price = curr_p
        else:
            if curr_p < ma20 or curr_p < buy_price * 0.93:
                profit = (curr_p - buy_price) / buy_price
                trades.append(profit)
                in_position = False
    
    if not trades: return 0, 0, 0
    win_rate = len([t for t in trades if t > 0]) / len(trades)
    total_ret = (np.prod([1 + t for t in trades]) - 1)
    max_loss = min(trades) if trades else 0
    return win_rate, total_ret, max_loss

def analyze_stock(stock_no, total_capital):
    stock_id = f"{stock_no}.TW"
    df = yf.download(stock_id, period="18mo", interval="1d", progress=False)
    if df.empty:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="18mo", interval="1d", progress=False)
    
    if df.empty: return None

    curr_p = float(df['Close'].iloc[-1])
    ma20_all = df['Close'].rolling(window=20).mean()
    ma20 = float(ma20_all.iloc[-1])
    
    # 成交量分析
    curr_vol = float(df['Volume'].iloc[-1])
    avg_vol_5 = float(df['Volume'].iloc[-6:-1].mean())
    vol_ratio = curr_vol / avg_vol_5 if avg_vol_5 > 0 else 1
    
    # 強調：這裏是擷取近一年 (252個交易日) 做回測
    win_rate, total_ret, max_loss = backtest_strategy(df.iloc[-252:])
    
    shares = int((total_capital * 0.4) // curr_p)
    
    reasons = []
    if curr_p >= ma20:
        reasons.append("✅ **趨勢翻多**：股價目前站穩 20 日月線之上。")
        if vol_ratio > 1.2:
            reasons.append(f"✅ **帶量突破**：今日成交量為均量的 {vol_ratio:.1f} 倍，攻擊力強。")
        elif vol_ratio < 0.8:
            reasons.append(f"⚠️ **量縮過線**：動能稍弱（僅均量 {vol_ratio:.1f} 倍），須防假突破。")
    else:
        reasons.append("❌ **趨勢偏弱**：股價低於月線，不宜建倉。")
    
    return {
        "id": stock_no, "price": adjust_tick(curr_p), "ma20": adjust_tick(ma20),
        "vol": curr_vol, "vol_ratio": vol_ratio,
        "lots": shares // 1000, "odds": shares % 1000,
        "stop_loss": adjust_tick(curr_p * 0.93),
        "add_1": adjust_tick(curr_p * 1.07), "tp_1": adjust_tick(curr_p * 1.15),
        "win_rate": win_rate, "total_ret": total_ret, "max_loss": max_loss,
        "reasons": reasons, "capital": total_capital
    }

# --- 介面呈現 ---
st.title("📈 台股滾動交易決策看板")

st.sidebar.header("⚙️ 參數設定")
user_capital = st.sidebar.number_input("總投入本金 (台幣)", min_value=10000, max_value=10000000, value=100000, step=10000)

target = st.text_input("📍 請輸入股票代號 (例如: 3481)", "")

if target:
    res = analyze_stock(target, user_capital)
    if res:
        st.divider()
        st.subheader(f"📊 {res['id']} 策略分析報告 (近一年回測)")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("當前股價", f"{res['price']:.2f}")
        m2.metric("今日成交量", f"{int(res['vol']):,}")
        m3.metric("量能倍數", f"{res['vol_ratio']:.2f}x")

        c1, c2, c3 = st.columns(3)
        c1.metric("一年歷史勝率", f"{res['win_rate']*100:.1f}%")
        c2.metric("一年累積報酬", f"{res['total_ret']*100:.1f}%")
        c3.metric("單筆最大損", f"{res['max_loss']*100:.1f}%")
        
        st.divider()
        st.subheader("💡 盤勢診斷原因")
        for r in res['reasons']:
            st.write(r)

        if res['price'] >= res['ma20']:
            st.success(f"✅ 符合建倉條件 (本金：{res['capital']:,.0f})")
            report = f"""
【{res['id']} 滾動計畫建議】
1. 初始建倉價格：{res['price']:.2f} 元。
2. 下單指令：買進【 {res['lots']} 張 + {res['odds']} 股 】。
3. 防守位：跌破 {res['stop_loss']:.2f} 元 (-7%) 全數清倉。
4. 加倉點：漲至 {res['add_1']:.2f} 元 (+7%) 時再投入 30% 本金。
5. 停利點：目標價 {res['tp_1']:.2f} 元 (+15%)。
            """
            st.code(report, language="text")
            
            plan_df = pd.DataFrame({
                "動作": ["🛑 止損", "📍 建倉", "➕ 加倉", "💰 停利"],
                "價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"]
            })
            st.table(plan_df)

        # --- 補回：策略準則與提示 ---
        st.divider()
        st.subheader("📖 滾動策略準則")
        st.markdown(f"""
        - **金字塔建倉**：總本金 {res['capital']:,.0f} 元，分 4:3:3 比例投入。底倉佔 **{res['capital']*0.4:,.0f}** 元。
        - **止損紀律**：買入後跌破 -7% 絕對執行清倉，絕不補倉。
        - **趨勢出場**：當股價收盤跌破月線 ({res['ma20']:.2f}) 時，代表趨勢轉弱，應全數獲利了結或止損。
        """)

        st.info(f"""
        **💡 溫馨提示：**
        1. **回測資料說明**：上方顯示之勝率與報酬率是基於**過去一年 (約 252 個交易日)** 的歷史數據模擬而成，回測結果僅供參考。
        2. **跳動單位修正**：所有產出價格（如：{res['price']:.2f}）已自動修正至台股跳動單位，可直接於國泰 App 下單。
        3. **行情延遲**：數據約延遲 15 分鐘，實際成交請以證券商即時報價為準。
        4. **紀律第一**：金字塔策略核心為「砍斷虧損，讓利潤奔跑」。
        """)
    else:
        st.error("查無資料。")
