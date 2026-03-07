import streamlit as st
import yfinance as yf
import pandas as pd

# --- 網頁配置 ---
st.set_page_config(page_title="國泰滾動決策中心", layout="centered")

# --- 核心邏輯：計算符合台股跳動單位的價格 ---
def adjust_tick(price):
    if price < 10: return round(price, 2)
    elif price < 50: return round(price * 20) / 20
    elif price < 100: return round(price * 10) / 10
    elif price < 500: return round(price * 2) / 2
    elif price < 1000: return round(price)
    else: return round(price / 5) * 5

def analyze_stock(stock_no):
    stock_id = f"{stock_no}.TW"
    df = yf.download(stock_id, period="60d", interval="1d", progress=False)
    if df.empty:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="60d", interval="1d", progress=False)
    
    if df.empty: return None

    # 技術指標
    curr_p = float(df['Close'].iloc[-1])
    ma20 = float(df['Close'].rolling(window=20).mean().iloc[-1])
    
    # 價格與跳動單位修正
    final_p = adjust_tick(curr_p)
    ma20_tick = adjust_tick(ma20)
    stop_loss = adjust_tick(curr_p * 0.93)
    add_1 = adjust_tick(curr_p * 1.07)
    tp_1 = adjust_tick(curr_p * 1.15)
    
    # 國泰下單股數 (本金 40,000)
    shares = int(40000 // curr_p)
    
    return {
        "id": stock_no, "price": final_p, "ma20": ma20_tick,
        "lots": shares // 1000, "odds": shares % 1000,
        "stop_loss": stop_loss, "add_1": add_1, "tp_1": tp_1
    }

# --- 介面呈現 ---
st.title("📈 台股滾動交易決策看板")
st.caption("策略：10萬金字塔滾動法 | 價格已依台股 6 級距跳動單位修正")

target = st.text_input("📍 請輸入股票代號（例如: 2402 或 3481）", "")

if target:
    res = analyze_stock(target)
    if res:
        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("當前股價", f"{res['price']:.2f}")
        col2.metric("月線 (MA20)", f"{res['ma20']:.2f}")

        if res['price'] >= res['ma20']:
            st.success(f"✅ {res['id']} 趨勢偏多：符合建倉條件")
            
            # 文字計畫書
            report = f"""
【{res['id']} 滾動計畫書 - 價格已修正至正確跳動位】

1. 初始建倉：
   - 買入價格：{res['price']:.2f} 元。
   - 指令：【{res['lots']} 張 + {res['odds']} 股】。

2. 防守與加倉：
   - 止損設定：跌破 {res['stop_loss']:.2f} 元全數清倉。
   - 加倉點：漲至 {res['add_1']:.2f} 元再投入 3 萬。

3. 出場計畫：
   - 停利點：{res['tp_1']:.2f} 元。
   - 趨勢止損：收盤跌破月線 {res['ma20']:.2f} 元。
            """
            st.code(report, language="text")

            # 視覺化表格
            plan_df = pd.DataFrame({
                "動作": ["🛑 止損", "📍 建倉", "➕ 加倉", "💰 停利"],
                "價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"]
            })
            st.table(plan_df)
        else:
            st.warning(f"❌ 目前股價 {res['price']:.2f} 低於月線 {res['ma20']:.2f}，觀望。")
    else:
        st.error("查無此代號。")
