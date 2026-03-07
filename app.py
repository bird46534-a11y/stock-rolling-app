import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 網頁配置 ---
st.set_page_config(page_title="金字塔滾動策略系統", layout="centered")

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

# --- 強度更高的中文名稱抓取 ---
@st.cache_data(ttl=86400)
def get_stock_name(stock_id):
    try:
        ticker = yf.Ticker(stock_id)
        # 嘗試從 info 中提取，Yahoo 對台股通常在 longName 或 shortName 提供中文
        info = ticker.info
        name = info.get('longName') or info.get('shortName') or info.get('symbol')
        
        # 過濾：如果抓到的是純英文且包含 ".TW"，則只顯示代號
        if not name or name == stock_id:
            return stock_id.split('.')[0]
        return name
    except:
        return stock_id.split('.')[0]

def analyze_stock(stock_no, total_capital):
    stock_id = f"{stock_no}.TW"
    # 下載數據，強制不使用 progress bar 減少干擾
    df = yf.download(stock_id, period="2y", interval="1d", progress=False)
    if df.empty or len(df) < 20:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="2y", interval="1d", progress=False)
    
    if df.empty: return None

    # 執行名稱抓取
    stock_name = get_stock_name(stock_id)
    
    df = df[df['Volume'] > 0].copy()
    latest_data = df.iloc[-1]
    data_date = df.index[-1].strftime('%Y-%m-%d')
    curr_p = float(latest_data['Close'])
    
    # 成交量拆解
    total_volume_shares = int(latest_data['Volume'])
    main_volume_lots = total_volume_shares // 1000
    odd_volume_shares = total_volume_shares % 1000
    avg_vol_5_lots = round(float(df['Volume'].iloc[-6:-1].mean()) / 1000)
    
    ma_series = df['Close'].rolling(window=20).mean()
    ma20 = float(ma_series.iloc[-1])
    ma20_prev = float(ma_series.iloc[-6])
    is_ma_up = ma20 > ma20_prev
    
    # 診斷與假突破邏輯
    reasons = []
    if curr_p >= ma20:
        if is_ma_up:
            trend_status, trend_color = "🌕 強勢多頭", "green"
            reasons.append("✅ **趨勢翻多**：股價站在上彎的月線之上。")
        else:
            trend_status, trend_color = "☁️ 弱勢反彈 (防假突破)", "blue"
            reasons.append("⚠️ **假突破警戒**：月線仍下彎，目前過線極可能是假突破。")
    else:
        trend_status, trend_color = ("⛅ 多頭回檔", "orange") if is_ma_up else ("🌑 趨勢偏弱", "red")
        reasons.append("❌ **目前不符合建倉條件**。")

    win_rate, total_ret, profit_amt, max_loss = backtest_strategy(df.iloc[-252:], total_capital)
    shares = int((total_capital * 0.4) // curr_p)
    
    return {
        "id": stock_no, "name": stock_name, "date": data_date, "price": adjust_tick(curr_p), "ma20": adjust_tick(ma20),
        "trend_status": trend_status, "trend_color": trend_color, "reasons": reasons,
        "main_vol": main_volume_lots, "odd_vol": odd_volume_shares, "avg_vol_5": avg_vol_5_lots,
        "lots": shares // 1000, "odds": shares % 1000,
        "stop_loss": adjust_tick(curr_p * 0.93),
        "add_1": adjust_tick(curr_p * 1.07), "tp_1": adjust_tick(curr_p * 1.15),
        "win_rate": win_rate, "total_ret": total_ret, "profit_amt": profit_amt, "max_loss": max_loss,
        "capital": total_capital
    }

# --- 介面呈現 ---
st.title("🏆 金字塔滾動策略系統")

st.sidebar.header("⚙️ 參數設定")
user_capital = st.sidebar.number_input("總投入本金 (台幣)", min_value=10000, value=100000, step=10000)

target = st.text_input("📍 請輸入股票代號 (如: 2330, 3481)", "")

if target:
    res = analyze_stock(target, user_capital)
    if res:
        st.divider()
        # 標題優化：顯眼的中文字樣
        st.header(f"📌 {res['name']} ({res['id']})")
        st.markdown(f"### 當前狀態：:{res['trend_color']}[{res['trend_status']}]")
        
        v1, v2, v3 = st.columns(3)
        v1.metric("當前股價", f"{res['price']:.2f}")
        v2.metric("一般成交量", f"{res['main_vol']:,} 張")
        v3.metric("5日均張", f"{res['avg_vol_5']:,} 張")
        st.caption(f"ℹ️ 包含額外零股/盤後量：{res['odd_vol']:,} 股 | 數據日期: {res['date']}")

        st.write("---")
        st.subheader("💡 盤勢診斷細節")
        for r in res['reasons']: st.write(r)

        st.write("---")
        st.caption(f"📊 過去一年回測績效 (本金: {res['capital']:,.0f})")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("歷史勝率", f"{res['win_rate']*100:.1f}%")
        c2.metric("累積報酬", f"{res['total_ret']*100:.1f}%")
        c3.metric("獲利金額", f"{int(res['profit_amt']):,}")
        c4.metric("最大單賠", f"{res['max_loss']*100:.1f}%")
        
        st.divider()
        
        if res['trend_status'] == "🌕 強勢多頭":
            st.success("✅ 符合建倉條件")
            st.code(f"【作戰計畫】\n建議買進：{res['lots']}張 + {res['odds']}股\n止損參考：{res['stop_loss']:.2f}", language="text")
            plan_df = pd.DataFrame({
                "動作": ["🛑 止損", "📍 建倉", "➕ 加倉", "💰 停利"],
                "價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"]
            })
            st.table(plan_df)
        else:
            st.warning(f"❌ 目前非強勢多頭，不建議執行金字塔建倉。")

        # --- 底部：金字塔策略準則 ---
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
        **⚠️ 投資風險溫馨提醒：**
        1. **回測數據說明**：歷史績效係根據過去一年數據模擬，不代表未來表現。
        2. **假突破風險**：即便指標翻多，仍須嚴格設定止損以應對假突破陷阱。
        3. **執行力**：策略核心在於「砍斷虧損，讓利潤奔跑」。
        """)
    else:
        st.error("查無資料。")
