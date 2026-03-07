import streamlit as st
import yfinance as yf
import pandas as pd

# --- 網頁配置 ---
st.set_page_config(page_title="國泰滾動決策中心", layout="centered")

# 自定義 CSS 讓介面更具專業感
st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #1ed760; }
    .report-box { background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px dashed #555; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 台股滾動交易決策看板")
st.caption("策略：10萬金字塔滾動法 | 手續費：國泰 2.8 折優化")

# --- 核心邏輯函數 ---
def analyze_stock(stock_no):
    stock_id = f"{stock_no}.TW"
    # 抓取資料 (優先嘗試上市 TW，不行再嘗試上櫃 TWO)
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
    
    # 國泰下單股數計算 (本金 40,000 為底倉)
    target_amount = 40000 
    total_shares = int(target_amount // curr_p)
    full_lots = total_shares // 1000
    odd_shares = total_shares % 1000
    
    # 計算策略價格
    stop_loss = curr_p * 0.93
    add_1 = curr_p * 1.07
    tp_1 = curr_p * 1.15
    
    return {
        "id": stock_no,
        "price": curr_p,
        "ma5": ma5,
        "ma20": ma20,
        "lots": full_lots,
        "odds": odd_shares,
        "stop_loss": stop_loss,
        "add_1": add_1,
        "tp_1": tp_1
    }

# --- 介面呈現 ---
target = st.text_input("📍 請輸入股票代號（輸入後按 Enter）", placeholder="例如: 3481")

if target:
    res = analyze_stock(target)
    if res:
        st.divider()
        
        # 1. 頂部數據儀表板
        col1, col2, col3 = st.columns(3)
        col1.metric("當前股價", f"{res['price']:.2f}")
        col2.metric("5日線 (MA5)", f"{res['ma5']:.2f}")
        col3.metric("月線 (MA20)", f"{res['ma20']:.2f}", delta=f"{res['price']-res['ma20']:.2f}")

        if res['price'] > res['ma20']:
            st.success(f"✅ {res['id']} 趨勢偏多：符合 10 萬本金滾動建倉條件！")
            
            # 2. 視覺化加倉進度
            st.subheader("🚀 交易進程視覺化")
            st.write(f"當前水位：已達底倉進場點 ({res['price']:.2f})")
            st.progress(0.35)
            st.caption(f"下一加倉目標點：{res['add_1']:.2f} (+7%)")
            
            # 3. 客製化文字策略 (帶入代號與價格)
            st.subheader("📝 客製化作戰計畫書")
            
            report_text = f"""
【{res['id']} 10萬金字塔滾動策略報告】

一、 初始建倉指令：
   - 狀態：股價 {res['price']:.2f} 站上月線，今日執行建倉。
   - 動作：國泰 App 買入【 {res['lots']} 張 + {res['odds']} 股 】。

二、 防守與加倉：
   - 止損位：跌破 {res['stop_loss']:.2f} 元 (-7%) 全數出清。
   - 加倉位：股價漲至 {res['add_1']:.2f} 元 (+7%) 時，再投入 3 萬本金。

三、 出場計畫：
   - 停利點：目標價 {res['tp_1']:.2f} 元 (+15%)。
   - 趨勢轉變：若股價收盤跌破月線 ({res['ma20']:.2f} 元)，則不論盈虧清倉。

※ 註：此計畫專為 10 萬本金設計，手續費已依國泰 2.8 折優化。
            """
            st.code(report_text, language="text")
            st.info("💡 提示：點擊右上角圖標可一鍵複製計畫至備忘錄。")

            # 4. 視覺化表格總結
            st.subheader("📊 關鍵價位速查表")
            plan_df = pd.DataFrame({
                "動作": ["🛑 止損清倉", "📍 當前建倉", "➕ 加倉點", "💰 目標停利"],
                "觸發價格": [f"{res['stop_loss']:.2f}", f"{res['price']:.2f}", f"{res['add_1']:.2f}", f"{res['tp_1']:.2f}"],
                "說明": ["虧損 7% 離場", "投入 40% 本金", "獲利 7% 擴大戰果", "獲利 15% 分批入袋"]
            })
            st.table(plan_df)
            
        else:
            st.warning(f"❌ {res['id']} 目前股價低於月線，不建議進場。")
            st.info(f"建議觀察位：需站回 {res['ma20']:.2f} 元以上再行評估。")
            
        st.divider()
    else:
        st.error("查無此股票資料，請檢查代號是否正確。")

# --- 底部策略準則 (錦囊妙計) ---
with st.expander("📖 查看 10 萬本金滾動策略核心準則"):
    st.markdown("""
    - **進場**：月線之上才動手，底倉 40%。
    - **加碼**：只在賺錢時加碼，分兩次 30%、30% 投入。
    - **止損**：-7% 絕對執行，不攤平。
    - **停利**：跌破月線或達目標價分批退場。
    """)
