import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date

st.set_page_config(page_title="10萬本金滾動助手", layout="centered")
st.title("📈 台股金字塔滾動交易系統")
st.write("針對國泰證券 2.8 折手續費優化")

CAPITAL = 100000
FEE_DISCOUNT = 0.28
TAX_RATE = 0.003

def analyze_stock(stock_no):
    stock_id = f"{stock_no}.TW"
    df = yf.download(stock_id, period="1y", interval="1d", progress=False)
    if df.empty:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="1y", interval="1d", progress=False)
    if df.empty: return None
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    curr_p = float(df['Close'].iloc[-1])
    ma20 = float(df['MA20'].iloc[-1])
    ma5 = float(df['MA5'].iloc[-1])
    total_shares = int(40000 // curr_p)
    return {"stock_id": stock_id, "price": curr_p, "ma20": ma20, "ma5": ma5, "lots": total_shares // 1000, "odds": total_shares % 1000, "stop_loss": curr_p * 0.93}

target = st.text_input("輸入台股代號 (例: 3481)", "")
if st.button("開始分析"):
    if target:
        res = analyze_stock(target)
        if res:
            st.subheader(f"📊 分析結果：{res['stock_id']}")
            col1, col2 = st.columns(2)
            col1.metric("當前股價", f"{res['price']:.2f}")
            col2.metric("月線 (MA20)", f"{res['ma20']:.2f}")
            if res['price'] > res['ma20']:
                st.success("✅ 趨勢偏多：符合建倉條件")
                st.info(f"💡 **國泰 App 操作指令**：\n\n買入 **{res['lots']} 張** + **{res['odds']} 股**\n\n智慧單止損設：**{res['stop_loss']:.2f}**")
            else:
                st.warning("❌ 趨勢偏弱：目前股價在月線下，建議觀望。")
        else: st.error("找不到該股票資料。")
st.divider()
st.caption("註：本網頁僅供策略模擬參考，投資請謹慎評估風險。")
