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
    df = yf.download(stock_id, period="18mo", interval="1d", progress=False)
    if df.empty:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="18mo", interval="1d", progress=False)
    
    if df.empty: return None

    latest_data = df.iloc[-1]
    data_date = df.index[-1].strftime('%Y-%m-%d')
    curr_p = float(latest_data['Close'])
    ma_series = df['Close'].rolling(window=20).mean()
    ma20 = float(ma_series.iloc[-1])
    ma20_prev = float(ma_series.iloc[-6])
    
    # --- 多空判斷 ---
    is_ma_up = ma20 > ma20_prev
    if curr_p >= ma20 and is_ma_up:
        trend_status, trend_color, trend_advice = "🌕 強勢多頭", "green", "趨勢向上且站穩月線，適合執行金字塔建倉。"
    elif curr_p < ma20 and is_ma_up:
        trend_status, trend_color, trend_advice = "⛅ 多頭回檔", "orange", "中期趨勢仍向上但短線跌破，建議觀望縮腳訊號。"
    elif curr_p >= ma20 and not is_ma_up:
        trend_status, trend_color, trend_advice = "☁️ 弱勢反彈", "blue", "股價雖過線但月線仍下彎，小心假突破。"
    else:
        trend_status, trend_color, trend_advice = "🌑 弱勢空頭", "red", "趨勢向下且股價低於月線，絕對禁止買入。"

    curr_vol = float(latest_data['Volume'])
    avg_vol_5 = float(df['Volume'].iloc[-6:-1].mean())
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

target = st.text_input("📍 請輸入股票代號 (例如: 2330)", "")

if target:
    res = analyze_stock(target, user_capital)
    if res:
        st.divider()
        st.subheader(f"🔍 {res['id']} 多空趨勢與一年回測")
        st.markdown(f"### 狀態：:{res['trend_color']}[{res['trend_status']}]")
        st.info(f"💡 **建議**：{res['trend_advice']}")
        
        v1, v2, v3 = st.columns(3)
        v1.metric("當前股價", f"{res['price']:.2f}")
        v2.metric("最新成交量", f"{int(res['vol']):,}")
        v3.metric("量能倍數", f"{res['vol_ratio']:.2f}x")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("歷史勝率", f"{res['win_rate']*100:.1f}%")
        c2.metric("累積報酬", f"{res['total_ret']*100:.1f}%")
        c3.metric("獲利金額", f"{int(res['profit_amt']):,}")
        c4.metric("最大單賠", f"{res['max_loss']*100:.1f}%")
        
        st.divider()

        if "多頭" in res['trend_status'] or "反彈" in res['trend_status']:
            st.success(f"✅ 符合建倉條件 (本金規模：{res['capital']:,.0f})")
            st.code(f"【{res['id']} 作戰計畫】\n建議買進：{res['lots']}張 + {res['odds']}股\n防守止損：{res['stop_loss']:.2f}", language="text")
            
            plan_df = pd.DataFrame({
                "動作": ["🛑 止損", "📍 建倉", "➕ 加倉", "💰 停利"],
                "價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"]
            })
            st.table(plan_df)
        else:
            st.warning(f"❌ 趨勢偏弱，暫不執行計畫。")

        # --- 底部：滾動策略準則 (補強內容) ---
        st.divider()
        st.subheader("📖 金字塔滾動策略準則")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("### 1️⃣ 資金分配 (4:3:3)")
            st.write(f" - **第一筆 (底倉 40%)**: 站穩月線進場。")
            st.write(f" - **第二筆 (加碼 30%)**: 獲利達 +7% 時加碼。")
            st.write(f" - **第三筆 (加碼 30%)**: 獲利續推或突破新高。")
        with col_s2:
            st.markdown("### 2️⃣ 出場紀律")
            st.write(f" - **硬性止損**: 買入價 -7% 絕對出場。")
            st.write(f" - **趨勢轉向**: 股價跌破月線 ({res['ma20']:.2f})。")
            st.write(f" - **分批停利**: 獲利達 +15% 以上逐步減碼。")
        
        st.markdown("---")
        st.markdown("### 3️⃣ 價量配合心法")
        st.markdown("- **帶量突破**: 股價過線且量能大於均量 1.2 倍為最佳買點。")
        st.markdown("- **量縮整理**: 股價回測月線不破且縮量，為多頭續強訊號。")

        st.info(f"""
        **💡 溫馨提示：**
        1. **一年回測說明**：歷史數據計算區間為過去 252 個交易日（統計至 {res['date']}）。
        2. **跳動單位**：所有價格（如止損價 {res['stop_loss']:.2f}）已修正至台股級距。
        3. **執行力**：策略核心在於「砍斷虧損，讓利潤奔跑」，計畫產出後請嚴格執行智慧單。
        """)
    else:
        st.error("查無資料。")
