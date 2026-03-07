import streamlit as st
import yfinance as yf
import pandas as pd

# --- 網頁配置 ---
st.set_page_config(page_title="國泰滾動決策中心", layout="centered")

# 自定義 CSS 讓介面更美觀
st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #1ed760; }
    .price-box { padding: 20px; border-radius: 10px; border: 1px solid #444; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 台股滾動交易決策看板")
st.caption("策略：10萬金字塔滾動法 | 視覺化戰術地圖")

# --- 核心邏輯 ---
def analyze_stock(stock_no):
    stock_id = f"{stock_no}.TW"
    df = yf.download(stock_id, period="60d", interval="1d", progress=False)
    if df.empty:
        stock_id = f"{stock_no}.TWO"
        df = yf.download(stock_id, period="60d", interval="1d", progress=False)
    
    if df.empty: return None

    curr_p = float(df['Close'].iloc[-1])
    ma20 = float(df['Close'].rolling(window=20).mean().iloc[-1])
    
    # 國泰下單股數 (本金 40,000 為底倉)
    shares = int(40000 // curr_p)
    
    return {
        "price": curr_p,
        "ma20": ma20,
        "lots": shares // 1000,
        "odds": shares % 1000
    }

# --- 介面呈現 ---
target = st.text_input("📍 請輸入股票代號", placeholder="例如: 3481")

if target:
    res = analyze_stock(target)
    if res:
        st.divider()
        
        # 頂部核心數據
        col1, col2 = st.columns(2)
        with col1:
            st.metric("當前股價", f"{res['price']:.2f}")
        with col2:
            diff = res['price'] - res['ma20']
            st.metric("月線 (MA20)", f"{res['ma20']:.2f}", delta=f"{diff:.2f}")

        if res['price'] > res['ma20']:
            st.success(f"✅ 趨勢偏多：建議買入 {res['lots']} 張 + {res['odds']} 股")
            
            # --- 視覺化加倉地圖 ---
            st.subheader("🚀 進場與加倉地圖")
            p = res['price']
            
            st.write(f"1. **底倉已就位** ({p:.2f})")
            st.progress(0.33)
            
            st.write(f"2. **預計加倉點 (+7%)**：🎯 **{p * 1.07:.2f}**")
            st.progress(0.0)
            
            st.write(f"3. **目標停利點 (+15%)**：💰 **{p * 1.15:.2f}**")
            
            # --- 分批出場計畫表 ---
            st.subheader("🛡️ 國泰智慧單設定參考")
            
            # 建立帶有顏色標記的表格數據
            plan_data = {
                "目標": ["⚠️ 初始止損", "⚖️ 成本保衛", "💎 分批停利", "🚪 終極清倉"],
                "觸發價格": [f"{p*0.93:.2f}", f"{p:.2f}", f"{p*1.10:.2f}", f"{res['ma20']:.2f}"],
                "動作": ["全數清倉", "減倉一半", "獲利入袋", "全數清倉"]
            }
            st.table(pd.DataFrame(plan_data))
            
            st.info("💡 提示：進度條代表目前的獲利進程，當股價上漲時，上方進度會自動填滿。")
        else:
            st.warning("目前股價低於月線，暫不建議進場。")
            st.write(f"💡 需等股價回升至 **{res['ma20']:.2f}** 以上再考慮。")
            
        st.divider()
    else:
        st.error("查無資料，請確認代號是否正確。")
