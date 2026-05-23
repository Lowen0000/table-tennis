import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import requests

# --- 0. 網頁基本設定 (手機版面優化) ---
st.set_page_config(
    page_title="🏓 瑊寶積分賽管理系統",
    page_icon="🏓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("🏓 瑊寶積分賽管理系統")

# --- 1. 設定區：已完美對接你「最新」的試算表 ID 與 GAS 網址 ---
YOUR_SHEET_ID = "1uGJnG7ISxrTP-GCdwZO8cyrGd9PlXSE_jhuYTZVB8S4"
YOUR_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxCZpTqzu9o6Yv33toVio1OpyQROWBm8uL4PX95ibB5bWx-HE0-BrfTSvJmGPHKoozV/exec"

BASE_URL = f"https://docs.google.com/spreadsheets/d/{YOUR_SHEET_ID}/gviz/tq?tqx=out:csv&sheet="

# --- 2. 免外掛試算表讀取核心 ---
@st.cache_data(ttl=1)
def load_data():
    try:
        df_players = pd.read_csv(BASE_URL + urllib.parse.quote("Players"))
        df_matches = pd.read_csv(BASE_URL + urllib.parse.quote("Matches"))
        if not df_players.empty and "Points" in df_players.columns:
            df_players['Points'] = pd.to_numeric(df_players['Points'])
        return df_players, df_matches
    except Exception as e:
        st.error(f"無法讀取 Google Sheet，請確認試算表共用權限（需開啟『知道連結的任何人都可以檢視/編輯』）。錯誤: {e}")
        return pd.DataFrame(columns=["Name", "Points"]), pd.DataFrame(columns=["Date", "Winner", "Loser", "Score", "Type", "Change"])

df_p, df_m = load_data()

# --- 3. TAIN/USATT 積分計算邏輯 ---
def calc_exchange(w_pts, l_pts):
    diff = abs(w_pts - l_pts)
    is_upset = w_pts < l_pts
    if diff <= 12: val = (8, 8)
    elif diff <= 37: val = (7, 10)
    elif diff <= 62: val = (6, 13)
    elif diff <= 87: val = (5, 16)
    elif diff <= 112: val = (4, 20)
    elif diff <= 137: val = (3, 25)
    elif diff <= 162: val = (2, 30)
    elif diff <= 187: val = (2, 35)
    elif diff <= 212: val = (1, 40)
    elif diff <= 237: val = (1, 45)
    else: val = (0, 50)
    return val[1] if is_upset else val[0]

# --- 4. UI 分頁設計 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 排名", "📝 登記", "📜 紀錄", "⚙️ 選手", "ℹ️ 規則"])

# ----- Tab 1: 積分排名 -----
with tab1:
    st.subheader("🏆 目前實力排行榜")
    if not df_p.empty and "Name" in df_p.columns:
        col1, col2 = st.columns(2)
        col1.metric("選手總數", f"{len(df_p)} 人")
        col2.metric("最高積分", f"{int(df_p['Points'].max())} 分")
        df_ranking = df_p.sort_values(by="Points", ascending=False).reset_index(drop=True)
        df_ranking.index = df_ranking.index + 1
        df_ranking.index.name = "名次"
        st.dataframe(df_ranking, use_container_width=True)
    else:
        st.info("目前尚無選手資料，請至選手管理新增。")

# ----- Tab 2: 登記比賽 -----
with tab2:
    st.subheader("📝 輸入比賽結果")
    if not df_p.empty and "Name" in df_p.columns:
        player_list = sorted(df_p['Name'].tolist())
        winner = st.selectbox("🏆 勝方選手", options=player_list, key="win")
        loser = st.selectbox("💀 負方選手", options=player_list, key="lose")
        match_type = st.radio("賽制選擇", ["5戰3勝", "3戰2勝"], horizontal=True)
        
        st.write("**詳細比分 (局數)**")
        col_w, col_l = st.columns(2)
        default_w = 3 if match_type == "5戰3勝" else 2
        w_score = col_w.number_input("勝方局數", min_value=default_w, max_value=default_w, value=default_w)
        l_score = col_l.number_input("負方局數", min_value=0, max_value=default_w-1, value=0)
        
        if winner == loser:
            st.error("❌ 錯誤：勝負方不能為同一人")
        else:
            w_pts = df_p.loc[df_p['Name'] == winner, 'Points'].values[0]
            l_pts = df_p.loc[df_p['Name'] == loser, 'Points'].values[0]
            change = calc_exchange(w_pts, l_pts)
            
            st.info(f"💡 **積分異動預覽**：\n\n**{winner}**: {w_pts} ➔ **{w_pts + change}** (+{change})\n\n**{loser}**: {l_pts} ➔ **{max(0, l_pts - change)}** (-{change})")
            
            if st.button("🚀 提交結果並同步雲端", type="primary", use_container_width=True):
                with st.spinner("正在將戰報同步至 Google 雲端..."):
                    payload = {
                        "action": "record_match",
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "winner": winner,
                        "loser": loser,
                        "score": f"{w_score}:{l_score}",
                        "type": match_type,
                        "change": int(change),
                        "winner_new_pt": int(w_pts + change),
                        "loser_new_pt": int(max(0, l_pts - change))
                    }
                    res = requests.post(YOUR_WEB_APP_URL, json=payload)
                    if res.status_code == 200:
                        st.success("🎉 比賽紀錄已成功永久寫入雲端！")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("寫入失敗，請確認 GAS 網址與權限。")
    else:
        st.warning("請先到選手管理頁面建立名單。")

# ----- Tab 3: 比賽紀錄 (防呆刪除功能) -----
with tab3:
    st.subheader("📜 歷史戰績列表")
    if not df_m.empty and "Winner" in df_m.columns and len(df_m) > 0:
        df_m_clean = df_m.dropna(subset=["Winner"])
        df_m_display = df_m_clean.iloc[::-1].reset_index(drop=True)
        st.dataframe(df_m_display, use_container_width=True)
        
        st.write("---")
        st.subheader("🗑️ 登記錯誤？撤銷比賽紀錄")
        
        match_options = [
            f"[{row['Date']}] {row['Winner']} 勝 {row['Loser']} ({row['Score']}) - 變動:{row['Change']}分"
            for _, row in df_m_display.iterrows()
        ]
        selected_match_str = st.selectbox("選擇欲刪除的比賽場次（會自動幫選手扣回/加回分數）", options=match_options)
        
        if st.button("🚨 確認刪除此紀錄並復原分數", type="secondary", use_container_width=True):
            with st.spinner("正在由雲端撤銷紀錄..."):
                idx = match_options.index(selected_match_str)
                target_match = df_m_display.iloc[idx]
                orig_idx = len(df_m_clean) - 1 - idx  # 計算在原始試算表中的實際行號
                
                w_name = target_match['Winner']
                l_name = target_match['Loser']
                change_val = int(target_match['Change'])
                
                w_curr = df_p.loc[df_p['Name'] == w_name, 'Points'].values[0] if w_name in df_p['Name'].tolist() else 1000
                l_curr = df_p.loc[df_p['Name'] == l_name, 'Points'].values[0] if l_name in df_p['Name'].tolist() else 1000
                
                payload = {
                    "action": "delete_match",
                    "orig_row_idx": int(orig_idx + 2), 
                    "winner": w_name,
                    "loser": l_name,
                    "winner_orig_pt": int(w_curr - change_val),
                    "loser_orig_pt": int(l_curr + change_val)
                }
                res = requests.post(YOUR_WEB_APP_URL, json=payload)
                if res.status_code == 200:
                    st.success("🗑️ 該場紀錄已成功抹除，選手積分已安全回復！")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("刪除失敗。")
    else:
        st.info("目前尚無任何比賽紀錄。")

# ----- Tab 4: 選手管理 (具備新增與刪除功能) -----
with tab4:
    st.subheader("⚙️ 選手名單與管理")
    if not df_p.empty and "Name" in df_p.columns:
        st.dataframe(df_p.sort_values(by="Name").reset_index(drop=True), use_container_width=True)
    
    st.write("---")
    col_add, col_del = st.columns(2)
    
    with col_add:
        st.markdown("### ➕ 新增選手")
        new_name = st.text_input("選手姓名", placeholder="請輸入姓名", key="add_n")
        new_pts = st.number_input("初始積分", min_value=0, max_value=3000, value=1000, step=50)
        if st.button("確認加入", use_container_width=True):
            if new_name.strip() == "": st.error("姓名不能為空")
            elif not df_p.empty and "Name" in df_p.columns and new_name in df_p['Name'].tolist(): st.error("該選手姓名已存在")
            else:
                with st.spinner("正在寫入雲端..."):
                    payload = {"action": "add_player", "name": new_name, "points": int(new_pts)}
                    res = requests.post(YOUR_WEB_APP_URL, json=payload)
                    if res.status_code == 200:
                        st.success(f"成功新增：{new_name}")
                        st.cache_data.clear()
                        st.rerun()
    
    with col_del:
        st.markdown("### 🗑️ 刪除選手")
        if not df_p.empty and "Name" in df_p.columns:
            del_name = st.selectbox("選擇要刪除的選手", options=sorted(df_p['Name'].tolist()), key="del_n")
            st.warning(f"⚠️ 警告：刪除『{del_name}』將直接自名單除名。")
            if st.button("🔥 確定刪除選手", use_container_width=True):
                with st.spinner("正在自雲端移除..."):
                    payload = {"action": "delete_player", "name": del_name}
                    res = requests.post(YOUR_WEB_APP_URL, json=payload)
                    if res.status_code == 200:
                        st.success(f"已成功刪除選手：{del_name}")
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("目前無選手可供刪除。")

# ----- Tab 5: 規則說明 -----
with tab5:
    st.subheader("ℹ️ TAIN 積分計算規則說明")
    rule_data = {
        "對戰選手積分差距": ["0 ~ 12", "13 ~ 37", "38 ~ 62", "63 ~ 87", "88 ~ 112", "113 ~ 137", "138 ~ 162", "163 ~ 187", "188 ~ 212", "213 ~ 237", "238以上"],
        "高積分者勝 (勝方加/負方扣)": [8, 7, 6, 5, 4, 3, 2, 2, 1, 1, 0],
        "低積分者勝 (勝方加/負方扣)": [8, 10, 13, 16, 20, 25, 30, 35, 40, 45, 50]
    }
    st.table(pd.DataFrame(rule_data))