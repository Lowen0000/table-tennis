import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. 行動端與專業情蒐版面配置
st.set_page_config(page_title="Lin Yun-Ju 戰術情蒐系統", layout="centered")

# 專業情蒐暗色調與手機端優化 UI
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.5rem; padding-right: 0.5rem; }
    h1 { font-size: 1.5rem !important; text-align: center; color: #0f172a; font-weight: 800; margin-bottom: 0.5rem; }
    h2 { font-size: 1.2rem !important; color: #1e3a8a; margin-top: 0.8rem; border-left: 4px solid #3b82f6; padding-left: 8px; }
    .kpi-container { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
    .kpi-card { background: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .kpi-title { font-size: 0.75rem; color: #64748b; font-weight: 600; }
    .kpi-value { font-size: 1.3rem; font-weight: 700; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_scout_data():
    df = pd.read_csv('Lin_data260426.csv')
    # 嚴格修正 Simi Scout 的千倍空間座標
    if df['x'].max() > 1000:
        df['x'] = df['x'] / 1000
        df['y'] = df['y'] / 1000
        
    # 情蒐特徵工程：按回合與擊球順序排序
    df = df.sort_values(by=['rally_id', 'order']).reset_index(drop=True)
    df['tempo_sec'] = df.groupby('rally_id')['time_sec'].diff()
    return df

df = load_scout_data()
# 鎖定核心情蒐對象
lin_df = df[df['player'] == 'Lin_Yun_Ju'].copy()

st.title("🛡️ 林昀儒國家隊級戰術情蒐面板")

# --- 頂級情蒐動態過濾器（優化：預設全選，支援一鍵自定義） ---
with st.expander("⚙️ 戰局動態篩選器（預設已載入完整大數據）", expanded=True):
    all_opps = sorted(list(lin_df['opponent'].unique()))
    selected_opps = st.multiselect("對手 (Opponent)", all_opps, default=all_opps)
    scout_df = lin_df[lin_df['opponent'].isin(selected_opps)]
    
    all_matches = sorted(list(scout_df['match'].unique()))
    selected_matches = st.multiselect("賽事樣本 (Match)", all_matches, default=all_matches)
    scout_df = scout_df[scout_df['match'].isin(selected_matches)]
    
    all_games = sorted(list(scout_df['games'].unique()))
    selected_games = st.multiselect("特定局數 (Games)", all_games, default=all_games)
    scout_df = scout_df[scout_df['games'].isin(selected_games)]

# --- 情蒐核心量化指標 ---
total_rallies = scout_df['rally_id'].nunique()
won_df = scout_df[scout_df['results'] == 'won']
lost_df = scout_df[scout_df['results'] == 'lost']
scout_win_rate = (won_df['rally_id'].nunique() / total_rallies * 100) if total_rallies > 0 else 0

# 側擰專項核心指標
side_df = scout_df[scout_df['skill'] == 'side-spin drive']
side_total = len(side_df)
side_won = len(side_df[side_df['results'] == 'won'])
side_efficiency = (side_won / side_total * 100) if side_total > 0 else 0

st.markdown(f"""
    <div class='kpi-container'>
        <div class='kpi-card'><div class='kpi-title'>樣本總回合 (Rallies)</div><div class='kpi-value' style='color:#1e3a8a;'>{total_rallies}</div></div>
        <div class='kpi-card'><div class='kpi-title'>當前勝率 (Win Rate)</div><div class='kpi-value' style='color:#16a34a;'>{scout_win_rate:.1f}%</div></div>
        <div class='kpi-card'><div class='kpi-title'>側擰實戰使用 (Usage)</div><div class='kpi-value' style='color:#2563eb;'>{side_total} 次</div></div>
        <div class='kpi-card'><div class='kpi-title'>側擰得分率 (Expectation)</div><div class='kpi-value' style='color:#ea580c;'>{side_efficiency:.1f}%</div></div>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- 情蒐分頁（依照運動統計學高階指標分類） ---
tab1, tab2, tab3 = st.tabs(["📊 戰術組合鏈", "⚡ 節奏臨界值", "🎯 空間控制力"])

# ================= TAB 1: 戰術組合鏈分析 (Tactical Chain) =================
with tab1:
    st.subheader("💡 核心得分手段與板數衔接")
    
    if not won_df.empty:
        tactical_combinations = won_df.groupby(['stroke', 'style', 'skill']).size().reset_index(name='致勝次數')
        # 篩選前三板（發球搶攻與接發球體系）與主力相持板數
        tactical_combinations = tactical_combinations[tactical_combinations['stroke'].isin([2, 3, 5])].sort_values(by='致勝次數', ascending=False)
        
        # 優化：去除不必要的 Y 軸重複標籤，簡化圖面
        fig_chain = px.bar(
            tactical_combinations, x='致勝次數', y='skill', color='style',
            facet_col='stroke',
            orientation='h',
            color_discrete_map={'backhand': '#2563eb', 'forehand': '#dc2626'},
            labels={'skill': '', '致勝次數': '得分貢獻 (次)', 'style': '持拍', 'stroke': '第幾板'}
        )
        
        # 統計美學修飾：精簡重疊文字
        fig_chain.for_each_annotation(lambda a: a.update(text=f"第 {a.text.split('=')[-1]} 板"))
        fig_chain.update_layout(
            height=280, 
            margin=dict(l=10, r=10, t=30, b=10), 
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
            yaxis=dict(autorange="reversed")
        )
        fig_chain.update_yaxes(matches=None, showticklabels=True) # 確保手機橫向看時每欄都有獨立名字
        st.plotly_chart(fig_chain, use_container_width=True)
        
        with st.expander("🔬 國家隊級戰術鏈報告（展開/收起）"):
            st.markdown("""
            **📋 戰術銜接與制敵機理：**
            * **第二板接發球（第 2 板）**：小林的致勝關鍵高度密集於反手 `side-spin drive` (側擰)。在統計學上，這展現出極強的**「主動破發」**能力。他利用高質量的摩擦直接破壞對手的發球優勢，將回球轉化為得分，或為第四板創造機會。
            * **第三板發球搶攻（第 3 板）**：此時得分手段向正手 `drive` (拉/衝) 與反手 `drive` 分流。這說明小林的發球體系是以「控短逼長」為主，迫使對手回擊出半出台球後，由小林進行第一板強攻。
            * **多板數相持（第 5 板）**：若戰局進入多板數，正手弧圈球（Forehand Drive）的得分權重大幅上升，屬於經典的「反手控節奏、正手進攻終結」體系。
            """)
    else:
        st.info("樣本數不足，無法生成戰術鏈。")

# ================= TAB 2: 節奏臨界值分析 (Tempo Threshold) =================
with tab2:
    st.subheader("⏱️ 擊球相差時間與風險回歸")
    
    valid_tempo = scout_df[scout_df['tempo_sec'].notna() & (scout_df['tempo_sec'] > 0) & (scout_df['tempo_sec'] < 1.5)]
    
    if not valid_tempo.empty:
        # 優化：美化盒鬚圖，去除重複的中文字，精簡圖例
        fig_tempo = px.box(
            valid_tempo, x='results', y='tempo_sec', color='style',
            points="all", 
            color_discrete_map={'backhand': '#2563eb', 'forehand': '#dc2626'},
            labels={'tempo_sec': '球速與節奏時間 (秒)', 'results': '回合結果', 'style': '持拍'},
        )
        # 精簡圖表 X 軸呈現
        fig_tempo.update_xaxes(ticktext=['相持 (continue)', '失誤 (lost)', '得分 (won)'], tickvals=['continue', 'lost', 'won'])
        fig_tempo.update_layout(
            height=320, 
            margin=dict(l=10, r=10, t=20, b=10), 
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_tempo, use_container_width=True)
        
        q1_tempo = valid_tempo[valid_tempo['results'] == 'won']['tempo_sec'].quantile(0.25)
        median_tempo = valid_tempo[valid_tempo['results'] == 'won']['tempo_sec'].median()
        
        with st.expander("🔬 國家隊級節奏臨界值報告（展開/收起）"):
            st.markdown(f"""
            **⏱️ 節奏流速與戰術窗口 (Tempo Analysis)：**
            * **黃金進攻窗口（中位數）**：小林得分回合的擊球間隔中位數為 **{median_tempo:.2f} 秒**。
            * **極速極限（下四分位數 Q1）**：當兩球間隔被壓縮至 **{q1_tempo:.2f} 秒** 以下時，屬於近台的超高速相持。
            * **統計學防守臨界點**：
                * 當綠色（Won）點高度集中在 0.40 - 0.55 秒時，說明小林在**快節奏、高對抗**中具備極佳的肌肉記憶與回擊質量。
                * 如果紅色（Lost）的點在 0.65 秒以上增加，這在情蒐上是個**重要預警**：意味著當對手故意放慢節奏、退到中遠台拉大弧圈球時，小林的借力突擊優勢會被削弱，失誤風險隨之上升。
            """)
    else:
        st.info("缺少回合連續時間數據。")

# ================= TAB 3: 空間控制力分析 (Spatial Control) =================
with tab3:
    st.subheader("🎯 側擰 (Side-spin Drive) 精準邊際落點")
    
    x_min, x_max = 100, 252
    y_min, y_max = 100, 374
    y_net = 237
    x_mid = 176
    
    if not side_df.empty:
        # 優化：完全拿掉背景網格、X與Y數值標籤，讓球桌呈現達到純淨情蒐級視覺
        fig_spatial = px.scatter(
            side_df, x="x", y="y", color="results", symbol="results",
            hover_data=["games", "stroke", "opponent", "match"],
            color_discrete_map={'won': '#16a34a', 'lost': '#dc2626', 'continue': '#2563eb'},
            symbol_map={'won': 'circle', 'lost': 'x', 'continue': 'diamond'},
            range_x=[x_min - 5, x_max + 5], range_y=[y_min - 5, y_max + 5],
            labels={'results': '球路結果'}
        )
        
        # 標準乒乓球檯幾何重現
        fig_spatial.add_shape(type="rect", x0=x_min, y0=y_min, x1=x_max, y1=y_max,
                              line=dict(color="#475569", width=2), fillcolor="#1e3a8a", opacity=0.15)
        fig_spatial.add_shape(type="line", x0=x_min, y0=y_net, x1=x_max, y1=y_net,
                              line=dict(color="#f59e0b", width=3, dash="dash")) # 球網
        fig_spatial.add_shape(type="line", x0=x_mid, y0=y_min, x1=x_mid, y1=y_max,
                              line=dict(color="#cbd5e1", width=1, dash="dot")) # 中線
        
        # 徹底去除不必要的繁雜文字與網格軸線
        fig_spatial.update_layout(
            width=340, height=440,
            margin=dict(l=5, r=5, t=10, b=5),
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )
        # 優化圖例顯示文字，不重複
        new_labels = {'won': '得分 (won)', 'lost': '失誤 (lost)', 'continue': '相持 (continue)'}
        fig_spatial.for_each_trace(lambda t: t.update(name=new_labels.get(t.name, t.name)))
        
        st.plotly_chart(fig_spatial, use_container_width=False)
        
        with st.expander("🔬 國家隊級空間落點報告（展開/收起）"):
            st.markdown("""
            **📐 空間幾何與落點控制力分析：**
            * **線路壓迫（落點縱深）**：觀察綠色點（🟢）在球檯底線的密集度。若大量落點逼近底線，代表小林的側擰具備極強的**「頂人」效果**，能有效壓制對方反手，使其無法退台發力。
            * **下網風險分析（球網臨界）**：黃色虛線為球網。若紅色點（🔴）高度密佈在球網前後，說明小林在處理該對手的發球時，對轉向或旋轉強度的判斷出現誤差，摩擦不夠或擊球時間過晚。
            * **角度調動（橫向落區）**：落在球檯兩側邊線的點，表明小林在接發球時主動拉開角度，對正手或反手位大位進行突襲，具備極高的撕開防線效果。
            """)
    else:
        st.info("💡 當前篩選條件下，無 Side-spin Drive (側擰) 數據。")

# --- 最底層數據矩陣 ---
st.markdown("---")
with st.expander("📊 原始大數據矩陣明細（可供導出與二次複盤）"):
    st.dataframe(scout_df[['match', 'games', 'stroke', 'player', 'style', 'skill', 'results', 'opponent', 'tempo_sec']], use_container_width=True)