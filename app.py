import streamlit as st
import yfinance as yf
import pandas as pd

# --- 網頁配置 ---
st.set_page_config(page_title="國泰滾動助手", layout="centered")
st.title("📈 個人交易決策系統")
st.caption("策略：10萬金字塔滾動法 | 手續費：國泰 2.8 折優化")

# --- 核心邏輯 ---
def analyze_stock(stock_no):
    stock_id = f"{stock_no}.TW"
    # 抓取資料 (優先嘗試上市，不行再嘗試上櫃)
    df = yf.download(stock_id, period="60d", interval="1d", progress=False)
    if df.empty:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="60d", interval="1d", progress=False)
    
    if df.empty: return None

    # 計算技術指標
    df['MA20'] = df['Close'].rolling(window=20).mean()
    curr_p = float(df['Close'].iloc[-1])
    ma20 = float(df['MA20'].iloc[-1])
    
    # 計算國泰下單股數 (本金 40% 為第一階段)
    target_amount = 40000 
    total_shares = int(target_amount // curr_p)
    full_lots = total_shares // 1000
    odd_shares = total_shares % 1000
    
    return {
        "name": stock_no,
        "price": curr_p,
        "ma20": ma20,
        "lots": full_lots,
        "odds": odd_shares,
        "stop_loss": curr_p * 0.93
    }

# --- 介面呈現 ---
target = st.text_input("📍 請輸入股票代號", placeholder="例如: 3481")

if target:
    res = analyze_stock(target)
    if res:
        st.divider()
        
        # 第一層：股價與趨勢
        col1, col2 = st.columns(2)
        col1.metric("當前股價", f"{res['price']:.2f}")
        col2.metric("月線 (MA20)", f"{res['ma20']:.2f}", 
                    delta=f"{res['price']-res['ma20']:.2f}", delta_color="normal")

        # 第二層：下單決策 (最醒目的部分)
        if res['price'] > res['ma20']:
            st.success("🟢 趨勢偏多：符合『底倉』進場條件")
            
            # 用大字體顯示下單指令
            st.markdown(f"""
            ### 🛒 國泰 App 下單指令：
            - **整股買進**：<span style='color: #1ed760; font-size: 24px; font-weight: bold;'>{res['lots']}</span> 張
            - **零股買進**：<span style='color: #1ed760; font-size: 24px; font-weight: bold;'>{res['odds']}</span> 股
            """, unsafe_allow_html=True)
            
            # 止損提醒
            st.error(f"⚠️ 智慧單止損建議設在：**{res['stop_loss']:.2f}** 元")
        else:
            st.warning("🔴 趨勢偏弱：股價低於月線，目前不建議進場。")
            
        st.divider()
    else:
        st.error("查無此代號，請確認輸入是否正確。")

st.info("💡 提示：本工具計算已自動避開台股單筆零股 999 股上限。")
