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
    df['MA20'] = df['Close'].rolling(window=20).mean()
    in_position = False
    buy_price = 0
    trades = []
    
    for i in range(20, len(df)):
        curr_p = df['Close'].iloc[i]
        ma20 = df['MA20'].iloc[i]
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

    recent_df = df.iloc[-60:]
    curr_p = float(recent_df['Close'].iloc[-1])
    ma20 = float(recent_df['Close'].rolling(window=20).mean().iloc[-1])
    ma5 = float(recent_df['Close'].rolling(window=5).mean().iloc[-1])
    
    # --- 成交量分析 ---
    curr_vol = float(df['Volume'].iloc[-1])
    avg_vol_5 = float(df['Volume'].iloc[-6:-1].mean()) # 過去 5 天平均量
    vol_ratio = curr_vol / avg_vol_5 if avg_vol_5 > 0 else 1
    
    win_rate, total_ret, max_loss = backtest_strategy(df.iloc[-252:])
    anchor_amount = total_capital * 0.4
    shares = int(anchor_amount // curr_p)
    
    # --- 原因分析邏輯 (加入量能) ---
    reasons = []
    if curr_p >= ma20:
        reasons.append("✅ **趨勢翻多**：股價目前站穩 20 日月線之上。")
        if vol_ratio > 1.2:
            reasons.append(f"✅ **帶量突破**：今日成交量為均量的 {vol_ratio:.1f} 倍，攻擊力道顯著。")
        elif vol_ratio < 0.8:
            reasons.append(f"⚠️ **量縮過線**：雖然過線但量能不足（僅均量 {vol_ratio:.1f} 倍），須防假突破。")
        else:
            reasons.append("✅ **量能穩定**：成交量維持水平，走勢尚稱穩健。")
    else:
        reasons.append("❌ **趨勢偏弱**：股價低於月線，不建議進場。")
    
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
st.sidebar.divider()
st.sidebar.write(f"💰 **資金分配規劃：**")
st.sidebar.write(f"- 底倉 (40%): {user_capital*0.4:,.0f} 元")
st.sidebar.write(f"- 加倉一 (30%): {user_capital*0.3:,.0f} 元")
st.sidebar.write(f"- 加倉二 (30%): {user_capital*0.3:,.0f} 元")

target = st.text_input("📍 請輸入股票代號 (例如: 3481)", "")

if target:
    res = analyze_stock(target, user_capital)
    if res:
        st.divider()
        st.subheader(f"📊 {res['id']} 策略分析與回測")
        
        # 增加成交量指標顯示
        m1, m2, m3 = st.columns(3)
        m1.metric("當前股價", f"{res['price']:.2f}")
        m2.metric("今日成交量", f"{int(res['vol']):,}")
        m3.metric("量能倍數", f"{res['vol_ratio']:.2f}x")

        # 回測數據
        c1, c2, c3 = st.columns(3)
        c1.metric("歷史勝率", f"{res['win_rate']*100:.1f}%")
        c2.metric("累積報酬率", f"{res['total_ret']*100:.1f}%")
        c3.metric("最大單筆虧損", f"{res['max_loss']*100:.1f}%")
        
        st.divider()
        st.subheader("💡 盤勢診斷原因 (含價量關係)")
        for r in res['reasons']:
            st.write(r)

        if res['price'] >= res['ma20']:
            st.success(f"✅ 符合建倉條件 (建議：{'量增建倉更有力' if res['vol_ratio'] > 1 else '量縮謹慎試單'})")
            
            st.subheader("📝 客製化作戰計畫書")
            report = f"""
【{res['id']} 滾動計畫建議】
1. 初始建倉價格：{res['price']:.2f} 元。
2. 下單指令：買進【 {res['lots']} 張 + {res['odds']} 股 】。
3. 防守設定：跌破 {res['stop_loss']:.2f} 元 (-7%) 全數清倉。
4. 加倉計畫：漲至 {res['add_1']:.2f} 元 (+7%) 時，再投入 {res['capital']*0.3:,.0f} 元。
5. 停利計畫：目標價 {res['tp_1']:.2f} 元 (+15%) 分批獲利。
            """
            st.code(report, language="text")

            plan_df = pd.DataFrame({
                "動作": ["🛑 止損", "📍 建倉", "➕ 加倉", "💰 停利"],
                "價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"]
            })
            st.table(plan_df)

        # 底部策略準則與提示
        st.divider()
        st.subheader("📖 10 萬本金滾動策略準則")
        st.markdown(f"- **底倉 (40%)**：站上月線且**成交量放大**為佳。")
        st.markdown(f"- **加碼 (30%+30%)**：獲利 7% 且趨勢持續時執行。")
        st.info(f"""
        **💡 溫馨提示：**
        1. **價量配合**：股價漲、成交量增才是健康的攻擊訊號。
        2. **跳動修正**：價格已依台股跳動級距修正（如：{res['price']:.2f}）。
        3. **紀律執行**：計畫書產出後，請直接依數值設定智慧單。
        """)
    else:
        st.error("查無資料。")
