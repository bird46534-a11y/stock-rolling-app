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
    df = yf.download(stock_id, period="2y", interval="1d", progress=False)
    if df.empty or len(df) < 20:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="2y", interval="1d", progress=False)
    
    if df.empty: return None

    df = df[df['Volume'] > 0].copy()
    latest_data = df.iloc[-1]
    data_date = df.index[-1].strftime('%Y-%m-%d')
    curr_p = float(latest_data['Close'])
    
    # 成交量拆解
    total_volume_shares = int(latest_data['Volume'])
    main_volume_lots = total_volume_shares // 1000
    odd_volume_shares = total_volume_shares % 1000
    avg_vol_5_lots = round(float(df['Volume'].iloc[-6:-1].mean()) / 1000)
    vol_ratio = main_volume_lots / avg_vol_5_lots if avg_vol_5_lots > 0 else 1
    
    ma_series = df['Close'].rolling(window=20).mean()
    ma20 = float(ma_series.iloc[-1])
    ma20_prev = float(ma_series.iloc[-6])
    is_ma_up = ma20 > ma20_prev
    
    # 診斷理由與多空邏輯
    reasons = []
    if curr_p >= ma20:
        if is_ma_up:
            trend_status, trend_color = "🌕 強勢多頭", "green"
            reasons.append("✅ **趨勢翻多**：股價站在上彎的月線之上。")
            if vol_ratio >= 1.2:
                reasons.append(f"🔥 **帶量突破**：成交張數 ({main_volume_lots}) 具備攻擊動能。")
            elif vol_ratio < 0.8:
                reasons.append(f"⚠️ **量縮過線**：雖然過線但動能不足，慎防震盪。")
        else:
            trend_status, trend_color = "☁️ 弱勢反彈 (防假突破)", "blue"
            reasons.append("⚠️ **假突破警戒**：股價雖過線，但月線仍下彎，不建議進場。")
    else:
        trend_status, trend_color = ("⛅ 多頭回檔", "orange") if is_ma_up else ("🌑 趨勢偏弱", "red")
        reasons.append("❌ **非多頭格局**：目前不符合建倉條件。")

    win_rate, total_ret, profit_amt, max_loss = backtest_strategy(df.iloc[-252:], total_capital)
    shares = int((total_capital * 0.4) // curr_p)
    
    return {
        "id": stock_no, "date": data_date, "price": adjust_tick(curr_p), "ma20": adjust_tick(ma20),
        "trend_status": trend_status, "trend_color": trend_color, "reasons": reasons,
        "main_vol": main_volume_lots, "odd_vol": odd_volume_shares, "avg_vol_5": avg_vol_5_lots,
        "lots": shares // 1000, "odds": shares % 1000,
        "stop_loss": adjust_tick(curr_p * 0.93),
        "add_1": adjust_tick(curr_p * 1.07), "tp_1": adjust_tick(curr_p * 1.15),
        "win_rate": win_rate, "total_ret": total_ret, "profit_amt": profit_amt, "max_loss": max_loss,
        "capital": total_capital
    }

# --- 介面呈現 ---
st.title("📈 國泰滾動決策中心")

st.sidebar.header("⚙️ 參數設定")
user_capital = st.sidebar.number_input("總投入本金 (台幣)", min_value=10000, value=100000, step=10000)

target = st.text_input("📍 請輸入股票代號 (如: 3481)", "")

if target:
    res = analyze_stock(target, user_capital)
    if res:
        st.divider()
        st.subheader(f"🔍 {res['id']} 診斷報告 (日期: {res['date']})")
        st.markdown(f"### 狀態：:{res['trend_color']}[{res['trend_status']}]")
        
        v1, v2, v3 = st.columns(3)
        v1.metric("當前股價", f"{res['price']:.2f}")
        v2.metric("一般成交量", f"{res['main_vol']:,} 張")
        v3.metric("5日均張", f"{res['avg_vol_5']:,} 張")
        st.caption(f"ℹ️ 包含額外零股/盤後量：{res['odd_vol']:,} 股")

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
            st.code(f"買進建議：{res['lots']}張 + {res['odds']}股\n止損參考：{res['stop_loss']:.2f}", language="text")
            plan_df = pd.DataFrame({
                "動作": ["🛑 止損", "📍 建倉", "➕ 加倉", "💰 停利"],
                "價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"]
            })
            st.table(plan_df)
        else:
            st.warning(f"❌ 當前非強勢多頭，暫不執行計畫。")

        # --- 底部：補回金字塔策略準則 ---
        st.subheader("📖 金字塔滾動策略準則")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 1️⃣ 資金分配 (4:3:3)")
            st.write(f"- **第一筆 (40%)底倉**：股價站穩月線進場。")
            st.write(f"- **第二筆 (30%)加碼**：獲利達 **+7%** 時執行。")
            st.write(f"- **第三筆 (30%)剩餘**：獲利持續擴大或帶量突破新高。")
        with col_b:
            st.markdown("#### 2️⃣ 出場紀律")
            st.write(f"- **硬性止損**：買入成本 **-7%** 絕對出場。")
            st.write(f"- **趨勢出場**：收盤跌破月線 (**{res['ma20']:.2f}**)。")
            st.write(f"- **移動停利**：獲利達 **+15%** 以上分批落袋。")

        st.info(f"""
        **⚠️ 投資風險溫馨提醒：**
        1. **回測數據說明**：上方「歷史勝率」與「累積報酬」係根據**過去一年 (252個交易日)** 歷史模擬。過去績效不代表未來表現。
        2. **假突破風險**：即便指標翻多，仍須嚴格設定止損以應對假突破陷阱。
        3. **執行力**：策略核心在於「砍斷虧損，讓利潤奔跑」。
        """)
    else:
        st.error("查無資料。")
