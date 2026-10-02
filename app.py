import json
import os
import time
import urllib.parse
from PIL import Image
import requests
import streamlit as st
from google import genai
from google.genai import types

# -------------------------------------------------------------------
# ページ基本設定
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Scent Finder | 香りの正体を特定するAI",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -------------------------------------------------------------------
# APIキー・アフィリエイトID設定 (st.secrets から読み込み)
# -------------------------------------------------------------------
GEMINI_API_KEY = st.secrets.get(
    "GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", "")
)
RAKUTEN_APP_ID = st.secrets.get("RAKUTEN_APP_ID", "")
RAKUTEN_AFFILIATE_ID = st.secrets.get("RAKUTEN_AFFILIATE_ID", "")
YAHOO_APP_ID = st.secrets.get("YAHOO_APP_ID", "")
YAHOO_SID = st.secrets.get("YAHOO_SID", "")  # バリューコマース SID (任意)
YAHOO_PID = st.secrets.get("YAHOO_PID", "")  # バリューコマース PID (任意)


# -------------------------------------------------------------------
# ECモール API 連携関数（キャッシュ処理つき）
# -------------------------------------------------------------------
@st.cache_data(ttl=86400)
def get_rakuten_product(keyword: str):
    """楽天WEB APIから最上位商品のダイレクトアフィリエイトURLを取得"""
    if not RAKUTEN_APP_ID or not RAKUTEN_AFFILIATE_ID:
        encoded = urllib.parse.quote(keyword)
        target = f"https://search.rakuten.co.jp/search/mall/{encoded}/"
        return f"https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_AFFILIATE_ID}/?pc={urllib.parse.quote(target)}"

    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "keyword": keyword,
        "hits": 1,
        "sort": "standard",
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if "Items" in data and len(data["Items"]) > 0:
            return data["Items"][0]["Item"]["affiliateUrl"]
    except Exception:
        pass

    encoded = urllib.parse.quote(keyword)
    return f"https://search.rakuten.co.jp/search/mall/{encoded}/"


@st.cache_data(ttl=86400)
def get_yahoo_product(keyword: str):
    """Yahoo!ショッピング APIから最上位商品のURL（アフィリエイト変換対応）を取得"""
    encoded = urllib.parse.quote(keyword)
    fallback_url = f"https://shopping.yahoo.co.jp/search?p={encoded}"

    if not YAHOO_APP_ID:
        return fallback_url

    url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
    params = {
        "appid": YAHOO_APP_ID,
        "query": keyword,
        "results": 1,
        "sort": "-score",
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if "hits" in data and len(data["hits"]) > 0:
            item_url = data["hits"][0]["url"]
            if YAHOO_SID and YAHOO_PID:
                vc_encoded = urllib.parse.quote(item_url)
                return f"https://ck.jp.ap.valuecommerce.com/servlet/referral?sid={YAHOO_SID}&pid={YAHOO_PID}&vc_url={vc_encoded}"
            return item_url
    except Exception:
        pass

    return fallback_url


# --- スマホ最適化 & ラグジュアリー・ウォームグレージュ CSS ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Noto+Serif+JP:wght@400;600&family=Noto+Sans+JP:wght@400;500;700&display=swap');

    .stApp {
        background-color: #f5f2eb !important;
        color: #1f2421 !important;
    }
    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', sans-serif;
        color: #1f2421;
    }

    .hero-container {
        text-align: center;
        padding: 1.5rem 1.0rem 1.2rem 1.0rem;
        background: linear-gradient(145deg, #ffffff 0%, #ebe5d8 100%);
        border-radius: 16px;
        border: 1px solid #dcd5c5;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.2rem;
    }
    .hero-subhead {
        font-family: 'Cinzel', serif;
        font-size: 0.75rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: #9c7a3c;
        margin-bottom: 0.3rem;
        font-weight: 700;
    }
    .hero-title {
        font-family: 'Cinzel', 'Noto Serif JP', serif;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        color: #1a1e1c;
        margin: 0;
    }
    .hero-desc {
        font-size: 0.85rem;
        color: #555c56;
        margin-top: 0.5rem;
        line-height: 1.5;
        font-weight: 400;
    }

    .tag-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: 0.6rem 0 1.0rem 0;
    }
    .scent-tag {
        background: #ffffff;
        border: 1px solid #d5cbba;
        color: #4a453e;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    .input-card-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #1a1e1c;
        letter-spacing: 0.02em;
        margin-bottom: 0.3rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #e4ddcf;
        padding: 4px;
        border-radius: 12px;
        border: 1px solid #d5ccbd;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 0.82rem;
        font-weight: 500;
        color: #555c56;
        background-color: transparent;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        color: #1a1e1c !important;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    div.stButton > button:first-child {
        background: linear-gradient(135deg, #2b2b2b 0%, #171717 100%);
        color: #fbf9f5 !important;
        border: 1px solid #1a1a1a;
        border-radius: 12px;
        font-weight: 600;
        letter-spacing: 0.04em;
        padding: 0.85rem 1.2rem;
        font-size: 0.95rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
        transition: all 0.2s ease;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background: #000000;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
        color: #ffffff !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        border: 1px solid #ded6c8 !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03) !important;
        padding: 1rem !important;
    }

    .category-badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        font-size: 0.7rem;
        font-weight: 600;
        border-radius: 9999px;
        letter-spacing: 0.03em;
        margin-bottom: 0.2rem;
    }
    .badge-perfume { background-color: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; }
    .badge-softener { background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
    .badge-hair { background-color: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }

    .rank-tag {
        font-family: 'Cinzel', serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: #9c7a3c;
        margin-right: 0.3rem;
    }

    .reason-box {
        background-color: #f8f6f0;
        border-left: 3.5px solid #9c7a3c;
        padding: 0.6rem 0.8rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.82rem;
        color: #2b302c;
        margin: 0.5rem 0;
        line-height: 1.5;
    }
    .notes-box {
        font-size: 0.78rem;
        color: #3b423d;
        background: #ebe6dc;
        padding: 0.3rem 0.6rem;
        border-radius: 6px;
        display: inline-block;
        font-weight: 500;
    }

    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #1a1e1c !important;
        border: 1px solid #cfc6b5 !important;
        border-radius: 10px !important;
    }

    .disclaimer-box {
        font-size: 0.73rem;
        color: #777e79;
        text-align: center;
        margin-top: 2.5rem;
        padding: 1.0rem;
        border-top: 1px dashed #d5ccbd;
        line-height: 1.6;
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- Scent Interactions Class (無料版・最適化ロジック) ---
class ScentInteractions:

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        # 制限（429）発生時に自動フォールバックできるようモデルを複数準備
        self.candidate_models = [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
        ]
        self.system_instruction = """
        あなたは世界中の香水、柔軟剤、シャンプー、ヘアオイルに精通したトップパフューマー兼リサーチャーです。
        ユーザーからのテキストの印象や添付画像（香水瓶や製品パッケージなど）から、該当する可能性が極めて高い実在の商品を3〜5つ特定してください。
        日本国内で入手・認知されている人気ブランドや海外有名メゾン（SHIRO, Diptyque, Margiela, Le Labo, Aesop, Byredo, 各種人気柔軟剤・ヘアケア等）を重視してください。
        
        必ず以下のJSON配列フォーマットのみで出力してください:
        [
          {
            "name": "商品名",
            "brand": "ブランド名/メーカー名",
            "category": "香水 または 柔軟剤 または シャンプー/ヘアケア",
            "scent_family": "サボン系 / ウッディ系 / フローラル系 など",
            "match_rate": 90,
            "reason": "なぜこの商品だと考えられるのかの具体的な調香的理由や特徴",
            "notes": "主要ノート（例: 洋梨、リリー、ホワイトムスク）",
            "approx_price": "約3,000円"
          }
        ]
        """

    def analyze_interaction(
        self, prompt_text: str, image_data: Image.Image = None
    ) -> list:
        contents = [f"以下の条件から商品を特定してください:\n\n{prompt_text}"]
        if image_data:
            contents.append(image_data)

        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            response_mime_type="application/json",
            temperature=0.3,
        )

        last_exception = None

        for model in self.candidate_models:
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=model, contents=contents, config=config
                    )
                    return json.loads(response.text)
                except Exception as e:
                    last_exception = e
                    err_str = str(e)

                    # 429（日上限20回超過）時はリトライせず次のモデル候補へ速やかに切替
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        break

                    # 503（サーバー混雑）時は指数バックオフ（2秒、4秒）で待機して再試行
                    if "503" in err_str and attempt < max_retries - 1:
                        time.sleep(2 ** (attempt + 1))
                        continue
                    break

        raise last_exception


# サイドバー
with st.sidebar:
    st.markdown(
        "<h3 style='color: #806024; font-family: Cinzel, serif;'>MAISON ENGINE</h3>",
        unsafe_allow_html=True,
    )
    if GEMINI_API_KEY:
        st.success("✨ AI特定エンジン稼働中")
    else:
        GEMINI_API_KEY = st.text_input("Gemini API Key を入力", type="password")
        st.markdown("[👉 APIキーを取得](https://aistudio.google.com/)")

    st.markdown("---")
    st.caption("ℹ **アフィリエイトに関する表記**")
    st.caption(
        "当サイトは楽天アフィリエイトおよびYahoo!ショッピング（バリューコマース）アフィリエイトプログラムの参加者です。"
    )

# ヒーローヘッダー
st.markdown(
    """
<div class="hero-container">
    <div class="hero-subhead">Maison de Fragrance Discovery</div>
    <h1 class="hero-title">Scent Finder</h1>
    <div class="hero-desc">
        記憶にある「あの人の良い匂い」の正体を特定。<br>
        香水・柔軟剤・サロンヘアケアからAIが瞬時に探索します。
    </div>
</div>
""",
    unsafe_allow_html=True,
)

IMAGE_MAP = {
    "香水": (
        "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=600&auto=format&fit=crop&q=80"
    ),
    "柔軟剤": (
        "https://images.unsplash.com/photo-1585751119414-ef2636f8aede?w=600&auto=format&fit=crop&q=80"
    ),
    "シャンプー": (
        "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=600&auto=format&fit=crop&q=80"
    ),
    "ヘアケア": (
        "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&auto=format&fit=crop&q=80"
    ),
}


def get_product_image(category):
    for key, url in IMAGE_MAP.items():
        if key in category:
            return url
    return IMAGE_MAP["香水"]


def get_badge_class(category):
    if "香水" in category:
        return "badge-perfume"
    elif "柔軟剤" in category:
        return "badge-softener"
    return "badge-hair"


# 共通エラーハンドリング関数
def handle_error(e):
    err_msg = str(e)
    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
        st.error(
            "⚠️ 本日の無料AI解析リクエスト上限に達しました。"
            "時間を置くか、明日再度お試しください。"
        )
    elif "503" in err_msg:
        st.error(
            "⏳ AIサーバーが一時的に非常に混み合っています。数秒おいてから再度ボタンを押してください。"
        )
    else:
        st.error(f"エラーが発生しました: {e}")


# 結果レンダリング関数
def render_results(results):
    st.write("")
    st.markdown("### 🎯 特定されたアイテム候補")

    for rank, item in enumerate(results, start=1):
        query = f"{item['brand']} {item['name']}"

        rakuten_url = get_rakuten_product(query)
        yahoo_url = get_yahoo_product(query)

        img_src = get_product_image(item.get("category", ""))
        badge_cls = get_badge_class(item.get("category", ""))

        with st.container(border=True):
            st.markdown(
                f"""
            <div>
                <span class="category-badge {badge_cls}">{item.get('category', '商品')}</span>
                <h4 style="margin: 0.1rem 0 0.3rem 0; color: #1a1e1c; font-size: 1.1rem;"><span class="rank-tag">#{rank}</span>{item['name']}</h4>
                <p style="color: #4b524d; font-size: 0.85rem; margin-bottom: 0.4rem; font-weight: 500;">{item['brand']} ({item.get('approx_price', '価格不明')})</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            col_img, col_info = st.columns([1, 2])
            with col_img:
                st.image(img_src, use_container_width=True)
            with col_info:
                st.progress(
                    item.get("match_rate", 80) / 100,
                    text=f"一致度: {item.get('match_rate', 80)}%",
                )
                st.markdown(
                    f"""
                <div class="reason-box">
                    💡 <strong>特定理由:</strong> {item.get('reason', '')}
                </div>
                """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                f'<div class="notes-box">🌿 <strong>香りの構成:</strong>'
                f' {item.get("notes", "未設定")}</div>',
                unsafe_allow_html=True,
            )
            st.write("")

            btn1, btn2 = st.columns(2)
            with btn1:
                st.link_button(
                    "🛍️ 楽天市場で見る",
                    rakuten_url,
                    use_container_width=True,
                )
            with btn2:
                st.link_button(
                    "🔴 Yahoo!で見る",
                    yahoo_url,
                    use_container_width=True,
                )


# タブ制御
tab1, tab2, tab3 = st.tabs(
    ["✨ 記憶から探す", "📸 写真から探す", "📋 診断で探す"]
)

# --- タブ1: 自由入力 ---
with tab1:
    st.markdown(
        '<div class="input-card-title">香りの印象・シチュエーション</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    <div class="tag-container">
        <span class="scent-tag">#ホテルのシーツのような清潔感</span>
        <span class="scent-tag">#雨上がりのカフェとお茶</span>
        <span class="scent-tag">#美容室帰りのいい匂い</span>
        <span class="scent-tag">#甘すぎない大人バニラ</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    user_desc = st.text_area(
        label="香りの記憶",
        label_visibility="collapsed",
        placeholder=(
            "例:"
            " すれ違った人からした、石鹸っぽいけど奥に柑橘と紅茶のような爽やかさがある香り。柔軟剤かも？"
        ),
        height=100,
    )

    target_category = st.multiselect(
        "探索対象:",
        options=["香水", "柔軟剤", "シャンプー・ヘアケア"],
        default=["香水", "柔軟剤", "シャンプー・ヘアケア"],
    )

    if st.button("✨ この香りの正体を特定する", type="primary", key="btn_free"):
        if not GEMINI_API_KEY:
            st.error("APIキーを入力してください。")
        elif not user_desc.strip():
            st.warning("特徴を入力してください。")
        else:
            with st.spinner("AIがデータベースを探索中..."):
                try:
                    interaction = ScentInteractions(api_key=GEMINI_API_KEY)
                    prompt = (
                        f"【探すカテゴリ】: {', '.join(target_category)}\n【ユーザーの印象】:"
                        f" {user_desc}"
                    )
                    results = interaction.analyze_interaction(prompt)
                    render_results(results)
                except Exception as e:
                    handle_error(e)

# --- タブ2: 写真から特定 ---
with tab2:
    st.markdown(
        '<div class="input-card-title">ボトルやパッケージの写真を撮影/選択</div>',
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "写真をアップロードまたはカメラで撮影",
        type=["jpg", "jpeg", "png"],
    )
    photo_desc = st.text_input(
        "追加のメモ（任意）",
        placeholder="例: 友人宅で見かけた香水。ウッディ系でした",
    )

    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="解析対象の画像", use_container_width=True)

    if st.button("📸 写真から商品を特定する", type="primary", key="btn_photo"):
        if not GEMINI_API_KEY:
            st.error("APIキーを入力してください。")
        elif not uploaded_file:
            st.warning("画像を添付してください。")
        else:
            with st.spinner("AIが画像とパッケージから商品を解析中..."):
                try:
                    interaction = ScentInteractions(api_key=GEMINI_API_KEY)
                    img = Image.open(uploaded_file)
                    prompt = (
                        "画像に映っている香水・化粧品・柔軟剤などのアイテムを特定し、詳細を分析してください。"
                        f"メモ: {photo_desc}"
                    )
                    results = interaction.analyze_interaction(
                        prompt, image_data=img
                    )
                    render_results(results)
                except Exception as e:
                    handle_error(e)

# --- タブ3: 診断クイズ ---
with tab3:
    with st.form("quiz_form"):
        st.markdown(
            '<div class="input-card-title">Q1. 香りの第一印象</div>',
            unsafe_allow_html=True,
        )
        q1_family = st.selectbox(
            "大分類",
            [
                "サボン・石鹸・洗い立てのリネン系",
                "シトラス・柑橘・爽やかなハーブ系",
                "フローラル・華やかなお花・清楚系",
                "フルーティー・みずみずしい果実系",
                "ウッディ・森林・お香・サンダルウッド系",
                "グルマン・バニラ・甘いスイーツ系",
                "ムスク・アンバー・素肌のような色気系",
            ],
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="input-card-title" style="margin-top: 0.8rem;">Q2. 甘さの強さ</div>',
            unsafe_allow_html=True,
        )
        q2_sweetness = st.radio(
            "甘さ",
            [
                "甘さはない（すっきり）",
                "控えめな甘さ",
                "上品で程よい甘さ",
                "濃厚で甘い",
            ],
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="input-card-title" style="margin-top: 0.8rem;">Q3. 香り立ち・強さ</div>',
            unsafe_allow_html=True,
        )
        q3_intensity = st.radio(
            "広がり方",
            [
                "すれ違いざまにふわっと香る（柔軟剤・シャンプー寄り）",
                "近づくとふんわり香る（ライト香水・ヘアミスト）",
                "しっかり周囲に広がる（本格香水）",
            ],
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="input-card-title" style="margin-top: 0.8rem;">Q4. どこから香ったか</div>',
            unsafe_allow_html=True,
        )
        q4_source = st.selectbox(
            "出どころ",
            [
                "服や全体から（柔軟剤・ボディミスト）",
                "髪から（シャンプー・ヘアオイル）",
                "手首・首筋から（香水）",
                "わからない",
            ],
            label_visibility="collapsed",
        )

        submitted_quiz = st.form_submit_button(
            "🔍 診断結果を見る", use_container_width=True
        )

    if submitted_quiz:
        if not GEMINI_API_KEY:
            st.error("APIキーを入力してください。")
        else:
            with st.spinner("AIが条件を分析中..."):
                try:
                    interaction = ScentInteractions(api_key=GEMINI_API_KEY)
                    prompt = (
                        f"【Q1 系統】: {q1_family}\n【Q2 甘さ】:"
                        f" {q2_sweetness}\n【Q3 強さ】: {q3_intensity}\n【Q4"
                        f" 出どころ】: {q4_source}"
                    )
                    results = interaction.analyze_interaction(prompt)
                    render_results(results)
                except Exception as e:
                    handle_error(e)

# 免責事項表示
st.markdown(
    """
<div class="disclaimer-box">
    ※当サイト（Scent Finder）は、楽天アフィリエイトおよびYahoo!ショッピング（バリューコマース）等の広告プログラムに参加しています。<br>
    検索結果で提示されるリンクを経由して商品を購入された場合、サイト運営者に広告収入が発生する場合があります。
</div>
""",
    unsafe_allow_html=True,
)