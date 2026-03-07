import streamlit as st
import yfinance as yf
import pandas as pd

# --- 網頁配置 ---
st.set_page_config(page_title="國泰滾動決策中心", layout="centered")
st.title("📈 台股滾動交易決策看板")
st.caption("策略：10萬金字塔滾動法 | 包含自動化盤勢解析與出場計畫")

# --- 核心邏輯 ---
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
    
    # 1. 買入計畫 (金字塔加倉)
    plan_buy = [
        {"階段": "底倉 (40%)", "觸發條件": "站上月線", "建議價格": f"{curr_p:.2f}"},
        {"階段": "第一次加倉", "觸發條件": "漲 7%", "建議價格": f"{curr_p * 1.07:.2f}"},
        {"階段": "第二次加倉", "觸發條件": "再漲 7%", "建議價格": f"{curr_p * 1.14:.2f}"},
    ]

    # 2. 出場計畫 (分批停利)
    plan_sell = [
        {"目標": "初始止損", "條件": "跌破成本 7%", "價格": f"{curr_p * 0.93:.2f}", "動作": "全數清倉"},
        {"目標": "第一波停利", "條件": "獲利回檔 5%", "價格": f"{curr_p * 1.10:.2f}", "動作": "減倉一半"},
        {"目標": "最終保命", "條件": "跌破月線", "價格": f"{ma20:.2f}", "動作": "全數清倉"},
    ]
    
    # 國泰下單股數
    target_amount = 40000 
    shares = int(target_amount // curr_p)
    
    return {
        "price": curr_p,
        "ma20": ma20,
        "lots": shares // 1000,
        "odds": shares % 1000,
        "buy_table": pd.DataFrame(plan_buy),
        "sell_table": pd.DataFrame(plan_sell)
    }

# --- 介面呈現 ---
target = st.text_input("📍 請輸入股票代號", "")

if target:
    res = analyze_stock(target)
    if res:
        st.divider()
        st.metric("當前股價", f"{res['price']:.2f}", delta=f"{res['price']-res['ma20']:.2f} (距月線)")

        if res['price'] > res['ma20']:
            st.success(f"🛒 **今日建議買入**：{res['lots']} 張 + {res['odds']} 股")
            
            # 顯示加倉計畫圖表
            st.subheader("🚀 進場與加倉地圖")
            st.table(res['buy_table'])

            # 顯示停利/停損計畫圖表
            st.subheader("🛡️ 出場與停利計畫")
            st.table(res['sell_table'])
            
            st.info("💡 建議：將上述價格設定在國泰 App 的『智慧單』，達到價格自動提醒。")
        else:
            st.warning("目前股價在月線下，暫不建議執行金字塔加倉策略。")
    else:
        st.error("查無資料。")
