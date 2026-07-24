"""Where is TARA? — 4色円盤サイン表示ビュー（読み取り専用）"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import requests
import streamlit as st
import streamlit.components.v1 as components

# ── ページ設定 ──────────────────────────────────────────────
st.set_page_config(
    page_title="Where is TARA?",
    page_icon="📍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Adafruit IO（where フィードが正本）──────────────────────
def _aio_cred(name: str) -> Optional[str]:
    """環境変数 → Streamlit secrets の順で読む。"""
    v = os.getenv(name)
    if v:
        return v.strip()
    try:
        return str(st.secrets[name]).strip()  # type: ignore[index]
    except Exception:
        return None


AIO_USERNAME = _aio_cred("AIO_USERNAME")
AIO_KEY = _aio_cred("AIO_KEY")
FEED_NAME = "where"
POLL_SECONDS = 300  # 自動同期間隔（5分）
TZ_TOKYO = ZoneInfo("Asia/Tokyo")
HISTORY_LIMIT = 8


def _api_base() -> Optional[str]:
    if not AIO_USERNAME:
        return None
    return f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{FEED_NAME}/data"

# 色配置（実物サイン写真と一致・対角分割）:
#   上=緑 CAMPUS / 右=青 LAB / 下=黒 ELSE / 左=赤 HOME
# フックは常に上固定。円盤を回転させて、選択中の色が上に来る。
STATUSES = {
    # 実物写真: 上緑 / 右青 / 下黒 / 左赤（対角の分割線）
    "CAMPUS": {
        "label": "通勤・構内",
        "short": "構内",
        "color": "#3dba3d",
        "rotation": 0,  # 緑がフック直下
    },
    "LAB": {
        "label": "研究室",
        "short": "研究室",
        "color": "#3a7de0",
        "rotation": -90,  # 青を上へ
    },
    "ELSE": {
        "label": "その他",
        "short": "その他",
        "color": "#141414",
        "rotation": -180,  # 黒を上へ
    },
    "HOME": {
        "label": "自宅",
        "short": "自宅",
        "color": "#e22222",
        "rotation": 90,  # 赤を上へ（時計回り）
    },
}

ORDER = ["CAMPUS", "LAB", "ELSE", "HOME"]

# セッション状態
if "last_value" not in st.session_state:
    st.session_state.last_value = None
if "last_sent_time" not in st.session_state:
    st.session_state.last_sent_time = None
if "feed_error" not in st.session_state:
    st.session_state.feed_error = None
if "history" not in st.session_state:
    st.session_state.history = []
if "synced_at" not in st.session_state:
    st.session_state.synced_at = None
if "auto_sync" not in st.session_state:
    st.session_state.auto_sync = True


def _parse_feed_item(item: dict) -> tuple[Optional[str], Optional[datetime]]:
    value = str(item.get("value", "")).strip().upper()
    if value not in STATUSES:
        # 未知の値は ELSE 扱い（表示はできるが警告用にそのまま返す場合もある）
        pass
    created = item.get("created_at")
    dt = None
    if created:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(TZ_TOKYO)
    return value, dt



def fetch_feed(limit: int = 1) -> tuple[list[dict], Optional[str]]:
    """Adafruit IO where フィードからデータ取得。

    戻り値: (items, error)
    各 item: {"value": str, "at": datetime|None, "raw": str}
    """
    base = _api_base()
    if not base or not AIO_KEY:
        return [], "AIO_USERNAME / AIO_KEY が未設定です（環境変数または .streamlit/secrets.toml）"

    headers = {"X-AIO-Key": AIO_KEY}
    try:
        response = requests.get(f"{base}?limit={limit}", headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return [], "予期しないレスポンス形式です"
        items: list[dict] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            value, dt = _parse_feed_item(row)
            items.append({"value": value, "at": dt, "raw": value})
        return items, None
    except requests.exceptions.RequestException as e:
        return [], f"取得エラー: {e}"


def fetch_latest_from_feed() -> tuple[Optional[str], Optional[datetime], Optional[str]]:
    """互換ラッパ: 最新1件。"""
    items, err = fetch_feed(limit=1)
    if err:
        return None, None, err
    if not items:
        return None, None, "フィードにデータがありません"
    return items[0]["value"], items[0]["at"], None


def sync_from_adafruit() -> None:
    """where フィードを正本として session_state を更新。"""
    items, err = fetch_feed(limit=HISTORY_LIMIT)
    st.session_state.feed_error = err
    st.session_state.history = items
    st.session_state.synced_at = datetime.now(TZ_TOKYO)
    if items:
        latest = items[0]
        val = latest["value"]
        if val in STATUSES:
            st.session_state.last_value = val
            st.session_state.last_sent_time = latest["at"]
        else:
            st.session_state.feed_error = (
                err or f"未知の値「{val}」（HOME/CAMPUS/LAB/ELSE 以外）"
            )



def format_jst(dt: Optional[datetime]) -> str:
    """最終更新などの表示用。常に日本時間。"""
    if dt is None or not hasattr(dt, "strftime"):
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_TOKYO)
    else:
        dt = dt.astimezone(TZ_TOKYO)
    return dt.strftime("%m/%d %H:%M")


def dial_svg_html(active: Optional[str]) -> str:
    """実物サイン写真に寄せた、セルシェード風の光沢4色円盤。"""
    rotation = STATUSES.get(active or "CAMPUS", STATUSES["CAMPUS"])["rotation"]
    label = STATUSES.get(active or "", {}).get("label", "未選択")
    if not active:
        label = "未選択"
        rotation = 0

    # 対角分割の角座標（半径112、中心140,158）
    # NW=(60.8,78.8) NE=(219.2,78.8) SE=(219.2,237.2) SW=(60.8,237.2)
    return f"""
<style>
  .sign-wrap {{
    font-family: "Hiragino Sans", "Noto Sans JP", system-ui, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.7rem;
    padding: 0.25rem 0 0.1rem;
  }}
  .sign-stage {{
    position: relative;
    width: min(340px, 92vw);
    aspect-ratio: 340 / 340;
  }}
  .sign-svg {{
    width: 100%;
    height: 100%;
    display: block;
  }}
  .sign-rotor {{
    transform-box: fill-box;
    transform-origin: center;
    transition: transform 0.6s cubic-bezier(.45,.05,.2,1);
  }}
  .sign-label {{
    font-size: 1.2rem;
    font-weight: 700;
    color: #f5f5f4;
    letter-spacing: 0.06em;
    margin-top: -0.15rem;
  }}
  .sign-hint {{
    font-size: 0.7rem;
    color: #a8a29e;
    text-align: center;
    line-height: 1.45;
    max-width: 22em;
  }}
  html, body {{
    margin: 0;
    background: #1f1f1f;
  }}
  .sign-wrap {{
    background: #1f1f1f;
  }}
</style>
<div class="sign-wrap">
  <div class="sign-stage">
    <svg class="sign-svg" viewBox="-40 -20 340 340" xmlns="http://www.w3.org/2000/svg" aria-label="4色円盤サイン">
      <defs>
        <!-- 壁のざらつき -->
        <filter id="wallNoise" x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" result="n"/>
          <feColorMatrix type="matrix" values="0 0 0 0 0.55  0 0 0 0 0.52  0 0 0 0 0.48  0 0 0 0.18 0" in="n"/>
        </filter>
        <!-- 柔らかい投影 -->
        <filter id="softShadow" x="-30%" y="-20%" width="160%" height="160%">
          <feDropShadow dx="4" dy="6" stdDeviation="4.5" flood-color="#000" flood-opacity="0.45"/>
        </filter>
        <filter id="hookShadow" x="-40%" y="-20%" width="180%" height="180%">
          <feDropShadow dx="1.5" dy="2" stdDeviation="1.2" flood-color="#000" flood-opacity="0.45"/>
        </filter>

        <!-- ほぼフラットなセルシェード色（縁だけわずかに落とす） -->
        <radialGradient id="gGreen" cx="50%" cy="28%" r="80%">
          <stop offset="0%" stop-color="#55c455"/>
          <stop offset="70%" stop-color="#3dba3d"/>
          <stop offset="100%" stop-color="#2f9a2f"/>
        </radialGradient>
        <radialGradient id="gBlue" cx="72%" cy="50%" r="80%">
          <stop offset="0%" stop-color="#5b94ee"/>
          <stop offset="65%" stop-color="#3a7de0"/>
          <stop offset="100%" stop-color="#2a5fbc"/>
        </radialGradient>
        <radialGradient id="gBlack" cx="50%" cy="72%" r="80%">
          <stop offset="0%" stop-color="#2a2a2a"/>
          <stop offset="55%" stop-color="#141414"/>
          <stop offset="100%" stop-color="#050505"/>
        </radialGradient>
        <radialGradient id="gRed" cx="28%" cy="50%" r="80%">
          <stop offset="0%" stop-color="#ff3d3d"/>
          <stop offset="65%" stop-color="#e22222"/>
          <stop offset="100%" stop-color="#b01010"/>
        </radialGradient>

        <!-- 縁の三日月ハイライト（凸面の縁光） -->
        <radialGradient id="rimSpec" cx="38%" cy="22%" r="78%">
          <stop offset="0%" stop-color="#fff" stop-opacity="0.42"/>
          <stop offset="22%" stop-color="#fff" stop-opacity="0.14"/>
          <stop offset="45%" stop-color="#fff" stop-opacity="0"/>
          <stop offset="100%" stop-color="#000" stop-opacity="0.06"/>
        </radialGradient>

        <!-- 赤道付近の波ハイライト（実物の特徴） -->
        <linearGradient id="waveFill" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#fff" stop-opacity="0"/>
          <stop offset="12%" stop-color="#fff" stop-opacity="0.08"/>
          <stop offset="28%" stop-color="#fff" stop-opacity="0.62"/>
          <stop offset="40%" stop-color="#fff" stop-opacity="0.22"/>
          <stop offset="55%" stop-color="#fff" stop-opacity="0.55"/>
          <stop offset="72%" stop-color="#fff" stop-opacity="0.18"/>
          <stop offset="88%" stop-color="#fff" stop-opacity="0.48"/>
          <stop offset="100%" stop-color="#fff" stop-opacity="0"/>
        </linearGradient>
        <linearGradient id="waveSoft" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#fff" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="#fff" stop-opacity="0.05"/>
        </linearGradient>

        <radialGradient id="rivet" cx="32%" cy="28%" r="72%">
          <stop offset="0%" stop-color="#f0d2a8"/>
          <stop offset="45%" stop-color="#d4a06a"/>
          <stop offset="100%" stop-color="#8a5528"/>
        </radialGradient>
        <linearGradient id="hookMetal" x1="0%" y1="0%" x2="80%" y2="100%">
          <stop offset="0%" stop-color="#6a6a6a"/>
          <stop offset="35%" stop-color="#2e2e2e"/>
          <stop offset="100%" stop-color="#0c0c0c"/>
        </linearGradient>
        <linearGradient id="rodMetal" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#4a4a4a"/>
          <stop offset="50%" stop-color="#222"/>
          <stop offset="100%" stop-color="#111"/>
        </linearGradient>

        <clipPath id="diskClip">
          <circle cx="140" cy="158" r="112"/>
        </clipPath>
      </defs>

      <!-- 背景は親ページのダークグレーに合わせ、SVG内は透明寄り -->
      <rect x="0" y="0" width="280" height="310" fill="transparent"/>

      <!-- 取り付けロッド（左下から長く伸ばす） -->
      <g opacity="0.95">
        <rect x="-36" y="218" width="128" height="12" rx="4"
              transform="rotate(-32 20 224)" fill="url(#rodMetal)" stroke="#000" stroke-width="1.1"/>
        <rect x="-32" y="220" width="118" height="3.2" rx="1"
              transform="rotate(-32 20 224)" fill="#fff" opacity="0.1"/>
        <rect x="-34" y="226" width="122" height="2" rx="1"
              transform="rotate(-32 20 224)" fill="#000" opacity="0.35"/>
      </g>

      <!-- 矢印パイプ（背面）：サイン裏側から真上へ（奥行きUの裏側） -->
      <g opacity="0.95">
        <path d="M140,125 L140,8"
              fill="none" stroke="#000" stroke-width="14"
              stroke-linecap="butt"/>
        <path d="M140,125 L140,8"
              fill="none" stroke="#141414" stroke-width="11"
              stroke-linecap="butt"/>
      </g>

      <!-- 回転する円盤 -->
      <g class="sign-rotor" filter="url(#softShadow)" style="transform-origin:140px 158px;transform:rotate({rotation}deg)">
        <!-- 4扇（対角分割）: 上緑・右青・下黒・左赤 -->
        <path d="M140,158 L60.8,78.8 A112,112 0 0,1 219.2,78.8 Z" fill="url(#gGreen)"/>
        <path d="M140,158 L219.2,78.8 A112,112 0 0,1 219.2,237.2 Z" fill="url(#gBlue)"/>
        <path d="M140,158 L219.2,237.2 A112,112 0 0,1 60.8,237.2 Z" fill="url(#gBlack)"/>
        <path d="M140,158 L60.8,237.2 A112,112 0 0,1 60.8,78.8 Z" fill="url(#gRed)"/>

        <!-- 分割線（対角・実物の細い黒線） -->
        <line x1="60.8" y1="78.8" x2="219.2" y2="237.2" stroke="#0a0a0a" stroke-width="2.4" stroke-linecap="round"/>
        <line x1="219.2" y1="78.8" x2="60.8" y2="237.2" stroke="#0a0a0a" stroke-width="2.4" stroke-linecap="round"/>

        <!-- 外縁の太いアウトライン -->
        <circle cx="140" cy="158" r="112" fill="none" stroke="#0a0a0a" stroke-width="3.2"/>

        <!-- 光沢レイヤ：右上だけに絞る（円盤と一緒に回転） -->
        <g clip-path="url(#diskClip)">
          <!-- 右上の縁スペキュラのみ -->
          <ellipse cx="198" cy="108" rx="62" ry="48"
                   fill="#fff" opacity="0.22"/>
          <ellipse cx="210" cy="98" rx="34" ry="22"
                   fill="#fff" opacity="0.28"/>
          <!-- 右上外周の細いリム光 -->
          <path d="M168,58 A112,112 0 0,1 240,148"
                fill="none" stroke="#fff" stroke-width="3.2" opacity="0.32"
                stroke-linecap="round"/>
          <path d="M178,62 A100,100 0 0,1 232,140"
                fill="none" stroke="#fff" stroke-width="1.4" opacity="0.18"
                stroke-linecap="round"/>
          <!-- 右上だけの短い波ハイライト -->
          <path d="M168,112
                   C182,102 196,108 210,100
                   C222,94 232,98 238,108
                   L234,118
                   C224,108 214,114 202,118
                   C190,122 178,116 168,120 Z"
                fill="#fff" opacity="0.38"/>
        </g>

        <!-- 中央リベット（銅ドーム） -->
        <circle cx="140" cy="158" r="15.5" fill="#5a3a18"/>
        <circle cx="140" cy="158" r="14" fill="url(#rivet)"/>
        <ellipse cx="135" cy="152" rx="5.5" ry="3.8" fill="#fff" opacity="0.4"/>
        <circle cx="140" cy="158" r="5.5" fill="#7a4a22" opacity="0.55"/>
        <circle cx="140" cy="158" r="2.2" fill="#4a2a10" opacity="0.5"/>
      </g>

      <!-- 矢印（前面）：奥行きで表へ折り返し → 表側パイプはまっすぐ下降 -->
      <g filter="url(#hookShadow)">
        <!-- 頂点の奥行きU（正面では短い半円。左右には大きく曲がらない） -->
        <path d="M140,8
                 C128,-6 152,-6 140,8"
              fill="none" stroke="#000" stroke-width="14"
              stroke-linecap="round"/>
        <path d="M140,8
                 C128,-6 152,-6 140,8"
              fill="none" stroke="url(#hookMetal)" stroke-width="11"
              stroke-linecap="round"/>

        <!-- 表側パイプ：中心線上をまっすぐ下へ（均一太さ） -->
        <path d="M140,8 L140,70"
              fill="none" stroke="#000" stroke-width="14"
              stroke-linecap="butt"/>
        <path d="M140,8 L140,70"
              fill="none" stroke="url(#hookMetal)" stroke-width="11"
              stroke-linecap="butt"/>
        <!-- ハイライト（まっすぐ） -->
        <path d="M140,12 L140,64"
              fill="none" stroke="#c4c4c4" stroke-width="2.2"
              stroke-linecap="round" opacity="0.4"/>

        <!-- 手前の下向き矢印 -->
        <path d="M122,66 L140,104 L158,66 Z"
              fill="#151515" stroke="#000" stroke-width="1.2"
              stroke-linejoin="round"/>
        <path d="M130,68 L140,90 L150,68 Z"
              fill="#3a3a3a" opacity="0.5"/>
      </g>

    </svg>
  </div>
  <div class="sign-label">{label}</div>
  <p class="sign-hint">手前の矢印が指す色が現在の状態です。</p>
</div>
"""



# ── カスタム CSS（Streamlit 全体） ───────────────────────────
st.markdown(
    """
<style>
  .stApp {
    background: #1f1f1f; /* 約12%グレー */
  }
  .stApp, .stApp p, .stApp span, .stCaption, [data-testid="stCaptionContainer"] {
    color: #e7e5e4 !important;
  }
  h1 { color: #f5f5f4 !important; }
  div[data-testid="stMetricLabel"] { color: #a8a29e !important; }
  div[data-testid="stMetricValue"] { color: #fafaf9 !important; }
  hr { border-color: #3f3f46 !important; }
  .block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 520px; }
  h1 { font-size: 1.45rem !important; letter-spacing: 0.04em; }
  div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
  /* 色付きボタン */
  .status-btn-row { margin-top: 0.35rem; }
  div.stButton > button {
    border-radius: 12px !important;
    font-weight: 650 !important;
    border: 2px solid rgba(0,0,0,.2) !important;
    min-height: 3.1rem;
  }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Where is TARA?")
st.caption("表示専用 · Adafruit IO の状態を確認するビューです（操作はできません）")

# ── フィード同期（正本 = Adafruit IO）──────────────────────
auth_ok = bool(AIO_USERNAME and AIO_KEY)
if not auth_ok:
    st.error(
        "Adafruit IO の認証情報がありません。"
        "`.streamlit/secrets.toml` に AIO_USERNAME / AIO_KEY を設定してください。"
    )
else:
    sync_col1, sync_col2 = st.columns([2, 1])
    with sync_col1:
        st.session_state.auto_sync = st.toggle(
            "自動更新（5分ごと）",
            value=st.session_state.auto_sync,
            help="表示の更新のみです。実機への送信は行いません",
        )
    with sync_col2:
        if st.button("今すぐ更新", use_container_width=True, key="btn_sync_now"):
            sync_from_adafruit()
            st.rerun()

    if st.session_state.synced_at is None:
        sync_from_adafruit()

    if st.session_state.auto_sync:
        try:
            @st.fragment(run_every=POLL_SECONDS)
            def _auto_sync_fragment() -> None:
                prev = st.session_state.last_value
                sync_from_adafruit()
                if st.session_state.last_value != prev:
                    st.rerun()

            _auto_sync_fragment()
        except Exception:
            pass  # 古い Streamlit では手動更新のみ

active = st.session_state.last_value

# 円盤表示
components.html(dial_svg_html(active), height=440, scrolling=False)

# 状態
m1, m2 = st.columns(2)
with m1:
    st.metric("現在地", STATUSES[active]["label"] if active in STATUSES else "—")
with m2:
    st.metric("最終更新", format_jst(st.session_state.last_sent_time))

if st.session_state.feed_error:
    st.warning(f"フィード: {st.session_state.feed_error}")

# 色の意味（丸＋ラベルのみ）
st.markdown(
    """
<div style="margin:0.75rem 0 1rem;padding:0.85rem 1rem;border:1px solid #3f3f46;
            border-radius:12px;background:#282828;">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.55rem 1.25rem;font-size:0.95rem;color:#f5f5f4;">
    <div style="display:flex;align-items:center;gap:0.55rem;">
      <span style="width:14px;height:14px;border-radius:50%;background:#3dba3d;display:inline-block;flex-shrink:0;"></span>
      <span>通勤・構内</span>
    </div>
    <div style="display:flex;align-items:center;gap:0.55rem;">
      <span style="width:14px;height:14px;border-radius:50%;background:#3a7de0;display:inline-block;flex-shrink:0;"></span>
      <span>研究室</span>
    </div>
    <div style="display:flex;align-items:center;gap:0.55rem;">
      <span style="width:14px;height:14px;border-radius:50%;background:#141414;border:1px solid #555;display:inline-block;flex-shrink:0;"></span>
      <span>その他</span>
    </div>
    <div style="display:flex;align-items:center;gap:0.55rem;">
      <span style="width:14px;height:14px;border-radius:50%;background:#e22222;display:inline-block;flex-shrink:0;"></span>
      <span>自宅</span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# 表示専用（実機への操作・送信 UI は置かない）

st.markdown(
    "<div style='text-align:center;color:#78716c;font-size:0.8em;margin-top:1rem;'>"
    "表示専用ビュー · 実機の操作はできません"
    "</div>",
    unsafe_allow_html=True,
)
