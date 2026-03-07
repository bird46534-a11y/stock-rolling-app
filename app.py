import streamlit as st
import yfinance as yf
import pandas as pd

# --- 網頁配置 ---
st.set_page_config(page_title="國泰滾動決策中心", layout="centered")
st.title("📈 台股滾動交易決策看板")
st.caption("策略：10萬金字塔滾動法 | 包含自動化盤勢解析")

# --- 核心邏輯 ---
def analyze_stock(stock_no):
    stock_id = f"{stock_no}.TW"
    # 抓取 60 天資料以計算均線
    df = yf.download(stock_id, period="60d", interval="1d", progress=False)
    if df.empty:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="60d", interval="1d", progress=False)
    
    if df.empty: return None

    # 技術指標計算
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    curr_p = float(df['Close'].iloc[-1])
    ma5 = float(df['MA5'].iloc[-1])
    ma20 = float(df['MA20'].iloc[-1])
    prev_p = float(df['Close'].iloc[-2])
    
    # --- 盤勢分析邏輯 ---
    analysis = []
    reason = []
    
    if curr_p > ma20:
        analysis.append("🟢 **目前處於多頭區域**：股價站穩月線之上，中期趨勢向上。")
        if curr_p > ma5:
            analysis.append("🔥 **短期走勢強勁**：股價連 MA5 短均線都沒跌破，動能充足。")
            reason.append("順勢交易：利用多頭慣性獲取波段利潤。")
        else:
            analysis.append("⚠️ **短期小回檔**：雖然在月線上，但目前跌破 MA5，建議等止跌再補。")
            reason.append("回測支撐：等待回踩月線不破的買點。")
    else:
        analysis.append("🔴 **空頭壓制中**：股價在月線下方，上方壓力沉重。")
        reason.append("觀望為宜：空頭格局下，抄底風險極高。")

    # 國泰下單股數計算
    target_amount = 40000 
    total_shares = int(target_amount // curr_p)
    full_lots = total_shares // 1000
    odd_shares = total_shares % 1000
    
    return {
        "price": curr_p,
        "ma20": ma20,
        "lots": full_lots,
        "odds": odd_shares,
        "stop_loss": curr_p * 0.93,
        "analysis": analysis,
        "reason": reason
    }

# --- 介面呈現 ---
target = st.text_input("📍 請輸入股票代號", "")

if target:
    res = analyze_stock(target)
    if res:
        st.divider()
        
        # 數據顯示
        c1, c2 = st.columns(2)
        c1.metric("當前股價", f"{res['price']:.2f}")
        c2.metric("月線 (MA20)", f"{res['ma20']:.2f}")

        # 盤勢分析區
        st.subheader("📝 盤勢分析")
        for item in res['analysis']:
            st.write(item)

        st.subheader("💡 建議買入理由")
        for item in res['reason']:
            st.info(item)

        # 決策區
        if res['price'] > res['ma20']:
            st.success(f"🛒 **國泰 App 操作指令**：買進 **{res['lots']}** 張 + **{res['odds']}** 股")
            st.error(f"🚩 智慧單止損位：**{res['stop_loss']:.2f}**")
        else:
            st.warning("目前不符合進場標準。")
            
        st.divider()
    else:
        st.error("查無此代號。")
