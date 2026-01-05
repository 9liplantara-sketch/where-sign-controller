import streamlit as st
import requests
import os
from datetime import datetime
from typing import Optional

# ページ設定
st.set_page_config(
    page_title="Where is Nagi?",
    page_icon="📍",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Adafruit IO設定
AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")
FEED_NAME = "where"
API_BASE_URL = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{FEED_NAME}/data"

# セッション状態の初期化
if "last_value" not in st.session_state:
    st.session_state.last_value = None
if "last_sent_time" not in st.session_state:
    st.session_state.last_sent_time = None

def send_to_adafruit_io(value: str) -> tuple[bool, Optional[str]]:
    """
    Adafruit IOのFeedに値を送信する
    
    Args:
        value: 送信する値（"LAB", "CAMPUS", "HOME", "ELSE"）
    
    Returns:
        (成功フラグ, エラーメッセージ)
    """
    if not AIO_USERNAME or not AIO_KEY:
        return False, "環境変数 AIO_USERNAME または AIO_KEY が設定されていません"
    
    headers = {
        "X-AIO-Key": AIO_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "value": value
    }
    
    try:
        response = requests.post(API_BASE_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return True, None
    except requests.exceptions.RequestException as e:
        error_msg = f"通信エラー: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" (ステータスコード: {e.response.status_code})"
        return False, error_msg

# UI表示
st.title("📍 Where is Nagi?")
st.markdown("---")

# 現在の状態表示
col1, col2 = st.columns(2)
with col1:
    if st.session_state.last_value:
        st.metric("現在地", st.session_state.last_value)
    else:
        st.metric("現在地", "-")
with col2:
    if st.session_state.last_sent_time:
        st.metric("最終送信時刻", st.session_state.last_sent_time.strftime("%H:%M:%S"))
    else:
        st.metric("最終送信時刻", "-")

st.markdown("---")
st.markdown("### 場所を選択してください")

# ボタン配置（2列×2行のグリッド）
col1, col2 = st.columns(2)

with col1:
    if st.button("🏢 研究室\n(LAB)", use_container_width=True, key="lab", type="primary"):
        success, error = send_to_adafruit_io("LAB")
        if success:
            st.session_state.last_value = "LAB"
            st.session_state.last_sent_time = datetime.now()
            st.success("「研究室」を送信しました！")
            st.rerun()
        else:
            st.error(error)

with col2:
    if st.button("🏫 大学構内\n(CAMPUS)", use_container_width=True, key="campus", type="primary"):
        success, error = send_to_adafruit_io("CAMPUS")
        if success:
            st.session_state.last_value = "CAMPUS"
            st.session_state.last_sent_time = datetime.now()
            st.success("「大学構内」を送信しました！")
            st.rerun()
        else:
            st.error(error)

col3, col4 = st.columns(2)

with col3:
    if st.button("🏠 自宅\n(HOME)", use_container_width=True, key="home", type="primary"):
        success, error = send_to_adafruit_io("HOME")
        if success:
            st.session_state.last_value = "HOME"
            st.session_state.last_sent_time = datetime.now()
            st.success("「自宅」を送信しました！")
            st.rerun()
        else:
            st.error(error)

with col4:
    if st.button("📍 その他\n(ELSE)", use_container_width=True, key="else", type="primary"):
        success, error = send_to_adafruit_io("ELSE")
        if success:
            st.session_state.last_value = "ELSE"
            st.session_state.last_sent_time = datetime.now()
            st.success("「その他」を送信しました！")
            st.rerun()
        else:
            st.error(error)

# フッター
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.9em;'>"
    "Adafruit IO 経由で M5Stack ATOM Lite に送信"
    "</div>",
    unsafe_allow_html=True
)

