import html
import hashlib
from io import BytesIO
import os
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

from .ai import AIHealth, AIService, AIUnavailable, LoginRequired
from .auth import Auth
from .catalog import MANUAL, TASKS, subjects, topics
from .models import AIMode, AIRequest, Conversation, Feature, FEATURE_LABELS, LOCAL_TZ, MODE_LABELS, history_group, now_iso
from .storage import ImageQuotaExceeded, Store

ROOT = Path(__file__).resolve().parent.parent
TOOLS_NAV = "tools"
IMAGE_MAX_BYTES = 10 * 1024 * 1024
IMAGE_MAX_PIXELS = 20_000_000
DEFAULT_IMAGE_DAILY_LIMIT = 3
ICONS = {Feature.STUDY: ":material/school:", Feature.WELLBEING: ":material/spa:", Feature.CAREER: ":material/explore:"}
DESCRIPTIONS = {
    Feature.STUDY: "Hiểu cách làm, luyện đúng trọng tâm và chuẩn bị cho mục tiêu tiếp theo.",
    Feature.WELLBEING: "Một khoảng dừng để nhìn lại cảm xúc và tìm một bước nhỏ phù hợp với bạn.",
    Feature.CAREER: "Hiểu bản thân hơn, khám phá lựa chọn và thử những bước đi thực tế.",
}
EDUCATIONAL_TOOLS = {
    "Bảng biến thiên & đồ thị": {
        "url": "https://congcutoanhoc.com/congcu/ve_bbt_dothi.html",
        "description": "Vẽ bảng biến thiên và đồ thị hàm số.",
        "embed": True,
    },
    "GeoGebra Classic": {
        "url": "https://www.geogebra.org/classic",
        "description": "Khám phá hình học, đại số và đồ thị tương tác.",
        "embed": True,
    },
    "Symbolab": {
        "url": "https://vi.symbolab.com/",
        "description": "Tra cứu công cụ giải toán và lời giải từng bước.",
        "embed": False,
    },
    "PhET": {
        "url": "https://phet.colorado.edu/vi/",
        "description": "Học khoa học qua các mô phỏng tương tác miễn phí.",
        "embed": False,
    },
}

CSS = """
<style>
:root {
 --em-violet:#6d5dfc; --em-blue:#3b82f6; --em-cyan:#22c7c9;
 --em-orange:#ff9f43; --em-pink:#ff6b9a; --em-ink:#17213a;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] { min-height:100%; height:auto; }
[data-testid="stAppViewContainer"] > .main { min-height:100vh; height:auto; overflow-y:auto; overflow-x:hidden; }
.block-container { max-width:1280px; min-height:100vh; height:auto; padding:1rem 1.5rem 2.2rem; display:flex; flex-direction:column; overflow:visible; }
.block-container > [data-testid="stVerticalBlock"] { flex:1 1 auto; min-height:0; display:flex; flex-direction:column; gap:.75rem; }
h1 { font-size:clamp(1.55rem, 2.4vw, 2.2rem) !important; font-weight:800 !important; letter-spacing:-.045em; line-height:1.08 !important; }
h2 { font-size:1.32rem !important; letter-spacing:-.025em; }
h3 { font-size:1.05rem !important; letter-spacing:-.015em; }
p, li { line-height:1.5; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { border-right:1px solid color-mix(in srgb, currentColor 9%, transparent); }
[data-testid="stSidebar"] .block-container { min-height:100vh; padding:1rem .9rem 2rem; overflow-y:auto; }
[data-testid="stSidebar"] .block-container > [data-testid="stVerticalBlock"] { min-height:100%; display:flex; flex-direction:column; gap:.5rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap:.2rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:.45rem .65rem; border-radius:12px; transition:.2s ease; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:color-mix(in srgb, var(--em-violet) 8%, transparent); transform:translateX(2px); }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { color:var(--em-violet); font-weight:750; background:color-mix(in srgb, var(--em-violet) 12%, transparent); }
[data-testid="stSidebar"] [data-testid="stButton"] button { text-align:left; justify-content:flex-start; }
[data-testid="stSidebar"] [data-testid="stButton"] button p { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.brand { display:flex; align-items:center; gap:.68rem; margin:.05rem 0 .75rem; }
.brand-logo { width:45px; height:45px; flex:none; filter:drop-shadow(0 7px 13px rgba(80,76,200,.22)); }
.brand-name { font-size:1.28rem; letter-spacing:-.045em; font-weight:850; line-height:1; }
.brand-name span { background:linear-gradient(115deg,var(--em-violet),var(--em-blue),var(--em-cyan)); -webkit-background-clip:text; color:transparent; }
.brand-sub { font-size:.62rem; opacity:.58; letter-spacing:.13em; text-transform:uppercase; margin-top:.22rem; }
.eyebrow { font-size:.68rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:var(--em-violet); margin-bottom:.28rem; }
.lead { max-width:680px; opacity:.72; font-size:.92rem; line-height:1.45; margin:.2rem 0 .55rem; }
.tag { display:inline-flex; align-items:center; font-size:.72rem; font-weight:650; border:1px solid color-mix(in srgb, var(--em-violet) 21%, transparent); background:color-mix(in srgb, var(--em-violet) 7%, transparent); border-radius:999px; padding:4px 10px; margin:0 .3rem .3rem 0; }
.step-label { font-size:.68rem; letter-spacing:.1em; font-weight:800; opacity:.58; margin-bottom:.45rem; }
.muted { opacity:.65; font-size:.84rem; }
.page-heading { display:flex; justify-content:space-between; align-items:center; gap:1.25rem; min-height:64px; padding:.15rem .2rem; }
.page-heading > div:first-child { flex:1 1 auto; min-width:0; }
.page-heading .mascot-wrap { flex:0 0 auto; }
.page-heading h1 { margin:0; }
.page-heading .lead { margin:.2rem 0 0; }
.hero { position:relative; overflow:hidden; min-height:128px; padding:1.2rem 1.45rem; border-radius:22px; color:white; background:linear-gradient(120deg,#5848e8 0%,#6d5dfc 42%,#2d9de7 100%); box-shadow:0 16px 38px rgba(72,79,190,.20); }
.hero:before,.hero:after { content:""; position:absolute; border-radius:50%; background:rgba(255,255,255,.12); }
.hero:before { width:190px; height:190px; right:-38px; top:-92px; }
.hero:after { width:110px; height:110px; right:120px; bottom:-78px; }
.hero .mascot-wrap { position:absolute; right:1.45rem; top:50%; transform:translateY(-50%); z-index:2; }
.hero .mascot-wrap:after { background:rgba(25,31,91,.22); }
.hero h1 { margin:.12rem 0 .35rem; max-width:650px; }
.hero p { margin:0; max-width:calc(100% - 125px); opacity:.88; }
.today-pill { display:inline-flex; padding:.3rem .65rem; border-radius:999px; background:rgba(255,255,255,.16); font-size:.7rem; font-weight:750; letter-spacing:.04em; }
.feature-card { min-height:190px; height:100%; border-radius:20px; padding:1rem 1.05rem; border:1px solid color-mix(in srgb, currentColor 9%, transparent); background:color-mix(in srgb, var(--card-color) 7%, transparent); box-shadow:0 8px 24px rgba(35,42,75,.07); transition:transform .2s ease, box-shadow .2s ease; display:flex; flex-direction:column; justify-content:space-between; }
.feature-card:hover { transform:translateY(-3px); box-shadow:0 14px 30px rgba(35,42,75,.12); }
.feature-icon { width:42px; height:42px; display:grid; place-items:center; border-radius:13px; color:white; background:var(--card-color); box-shadow:0 8px 18px color-mix(in srgb, var(--card-color) 28%, transparent); font-size:1.25rem; margin-bottom:.65rem; }
.feature-card h3 { margin:0 0 .32rem; }
.feature-card p { opacity:.72; font-size:.83rem; margin:0; }
.mini-banner { display:flex; align-items:center; gap:.75rem; padding:.65rem .85rem; border:1px solid color-mix(in srgb, var(--em-orange) 22%, transparent); background:color-mix(in srgb, var(--em-orange) 8%, transparent); border-radius:15px; }
.mini-banner strong { color:color-mix(in srgb, var(--em-orange) 78%, currentColor); }
.mascot { width:92px; height:92px; flex:none; filter:drop-shadow(0 10px 16px rgba(50,50,120,.16)); animation:pet-float 3.2s ease-in-out infinite; transform-origin:50% 90%; }
.mascot .pet-eye { transform-origin:center; animation:pet-blink 4.6s infinite; }
.mascot .pet-wing-left { transform-origin:30% 55%; animation:pet-wave 2.8s ease-in-out infinite; }
.mascot-wrap { position:relative; display:flex; align-items:center; justify-content:center; }
.mascot-wrap:after { content:""; position:absolute; width:62px; height:10px; border-radius:50%; background:rgba(54,58,110,.13); bottom:0; animation:pet-shadow 3.2s ease-in-out infinite; }
@keyframes pet-float { 0%,100%{transform:translateY(0) rotate(-1deg)} 50%{transform:translateY(-7px) rotate(1deg)} }
@keyframes pet-shadow { 0%,100%{transform:scale(1);opacity:.65} 50%{transform:scale(.82);opacity:.35} }
@keyframes pet-blink { 0%,43%,47%,100%{transform:scaleY(1)} 45%{transform:scaleY(.08)} }
@keyframes pet-wave { 0%,100%{transform:rotate(0)} 50%{transform:rotate(-9deg)} }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:18px; border-color:color-mix(in srgb, currentColor 10%, transparent); }
[data-testid="stChatMessage"] { border-radius:16px; padding:.85rem 1rem; margin-bottom:.45rem; border:1px solid color-mix(in srgb, currentColor 6%, transparent); }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background:linear-gradient(120deg,color-mix(in srgb,var(--em-violet) 9%,transparent),color-mix(in srgb,var(--em-blue) 7%,transparent)); }
[data-testid="stButton"] button { min-height:2.5rem; font-weight:700; border-radius:12px; transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
[data-testid="stButton"] button:hover { transform:translateY(-1px); border-color:var(--em-violet); box-shadow:0 8px 18px rgba(91,79,210,.13); }
[data-testid="stButton"] button[kind="primary"] { border:0; color:white; background:linear-gradient(110deg,var(--em-violet),var(--em-blue)); box-shadow:0 8px 18px rgba(79,89,210,.22); }
[data-testid="stPopover"] button { min-height:2.3rem; border-radius:12px; }
[data-testid="stSidebar"] [data-testid="stPopover"] button { min-width:0; width:100%; padding:.15rem; }
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input { border-radius:12px; }
[data-testid="stExpander"] { border-radius:16px; border-color:color-mix(in srgb, currentColor 12%, transparent); }
.st-key-overview-cards { flex:1 1 auto; min-height:0; }
.st-key-sr-title { position:absolute !important; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
.st-key-overview-cards > div, .st-key-overview-cards [data-testid="stHorizontalBlock"] { height:100%; }
.st-key-overview-footer { flex:0 0 auto; margin-top:.45rem; }
.st-key-feature-toolbar { flex:0 0 auto; padding:.55rem .7rem; border-radius:16px; border:1px solid color-mix(in srgb,currentColor 9%,transparent); background:color-mix(in srgb,var(--em-violet) 4%,transparent); }
.st-key-conversation { flex:1 1 auto; min-height:140px; max-height:calc(100vh - 290px); overflow-y:auto; overscroll-behavior:contain; scroll-behavior:smooth; scroll-padding-block:1rem; padding:.25rem .5rem .5rem .25rem; scrollbar-width:thin; scrollbar-color:color-mix(in srgb,var(--primary-color,var(--em-violet)) 45%,transparent) transparent; }
.st-key-conversation > div, .st-key-conversation [data-testid="stVerticalBlock"] { min-height:0; }
.st-key-conversation [data-testid="stChatMessageContent"] { min-width:0; overflow-wrap:anywhere; }
.st-key-conversation [data-testid="stMarkdownContainer"] p { line-height:1.75; margin:0 0 .85rem; }
.st-key-conversation [data-testid="stMarkdownContainer"] li { line-height:1.7; margin:.2rem 0; }
.st-key-conversation [data-testid="stMarkdownContainer"] pre { max-width:100%; overflow-x:auto; }
.st-key-conversation [data-testid="stMarkdownContainer"] table { display:block; max-width:100%; overflow-x:auto; }
.st-key-conversation [data-testid="stMarkdownContainer"] img { max-width:100%; height:auto; }
.tool-embed { width:100%; min-height:460px; border:1px solid color-mix(in srgb,currentColor 14%,transparent); border-radius:16px; overflow:hidden; }
.image-preview img { max-height:360px; object-fit:contain; }
.st-key-conversation-empty { flex:0 0 auto; }
.st-key-study-empty [data-testid="stVerticalBlockBorderWrapper"] { padding:.8rem 1.1rem; border-radius:16px; background:color-mix(in srgb, var(--em-violet) 4%, transparent); }
.st-key-composer { flex:0 0 auto; min-height:0; padding:.65rem .85rem .55rem; border:1px solid color-mix(in srgb,currentColor 18%,transparent) !important; border-radius:17px !important; background:color-mix(in srgb,currentColor 5%,transparent); color:inherit; box-shadow:0 -4px 20px color-mix(in srgb,currentColor 6%,transparent); margin-top:.25rem; margin-bottom:.55rem; }
.st-key-composer [data-testid="stTextArea"] textarea { min-height:44px !important; height:clamp(44px,8vh,88px) !important; max-height:88px !important; overflow-y:auto !important; padding-top:.65rem; resize:none; border:0; color:inherit; background:color-mix(in srgb,currentColor 4%,transparent); }
.st-key-composer [data-testid="stButton"] button { border-radius:999px; min-height:2.4rem; }
.st-key-wellbeing-wizard { position:relative; flex:0 0 auto; min-height:195px; border:1px solid color-mix(in srgb,var(--em-pink) 20%,transparent); background:linear-gradient(120deg,color-mix(in srgb,var(--em-pink) 7%,transparent),color-mix(in srgb,var(--em-violet) 6%,transparent)); border-radius:20px; padding:1.15rem 1.4rem 1.15rem 200px; overflow:hidden; }
.st-key-wizard-state-keeper { display:none !important; }
.context-pet { width:145px; text-align:center; color:var(--text-color,inherit); }
.context-pet svg { width:132px; height:132px; overflow:visible; filter:drop-shadow(0 10px 16px color-mix(in srgb,var(--text-color,#17213a) 15%,transparent)); animation:pet-float 3.2s ease-in-out infinite; }
.context-pet .pet-eye { transform-origin:center; animation:pet-blink 4.6s infinite; }
.context-pet .pet-accessory { transform-origin:center; animation:pet-wave 2.7s ease-in-out infinite; }
.context-pet-label { margin-top:.25rem; font-size:.74rem; font-weight:800; opacity:.75; line-height:1.25; }
.st-key-wellbeing-wizard .context-pet { position:absolute; left:20px; top:20px; width:145px; margin:0; }
.contextual-card { display:flex; align-items:center; gap:1.75rem; padding:1.2rem 1.6rem; border-radius:20px; border:1px solid color-mix(in srgb,currentColor 14%,transparent); background:linear-gradient(120deg,color-mix(in srgb,var(--em-violet) 8%,transparent),color-mix(in srgb,currentColor 4%,transparent)); box-shadow:0 4px 18px color-mix(in srgb,currentColor 4%,transparent); margin-bottom:.45rem; }
.contextual-pet-wrap { flex:0 0 145px; display:flex; justify-content:center; align-items:center; }
.contextual-pet-wrap .context-pet { position:relative !important; left:auto !important; top:auto !important; width:145px; }
.contextual-text-wrap { flex:1 1 auto; min-width:0; }
.contextual-title { font-size:1.12rem; font-weight:800; letter-spacing:-.02em; margin-bottom:.35rem; color:inherit; line-height:1.35; }
.contextual-desc { font-size:.88rem; opacity:.78; margin:0; line-height:1.5; }
.thinking-bubble { display:flex; align-items:center; gap:.7rem; padding:.72rem .9rem; border-radius:15px; border:1px solid color-mix(in srgb,currentColor 14%,transparent); background:color-mix(in srgb,currentColor 5%,transparent); }
.thinking-mini { width:38px; height:38px; animation:pet-float 2s ease-in-out infinite; }
.thinking-dots { display:inline-flex; gap:.24rem; margin-left:.25rem; }
.thinking-dots i { width:6px; height:6px; border-radius:50%; background:var(--primary-color,var(--em-violet)); animation:thinking-dot 1.15s infinite ease-in-out; }
.thinking-dots i:nth-child(2) { animation-delay:.16s; }.thinking-dots i:nth-child(3) { animation-delay:.32s; }
@keyframes thinking-dot { 0%,70%,100%{transform:translateY(0);opacity:.35} 35%{transform:translateY(-5px);opacity:1} }
.wizard-progress { display:flex; gap:.35rem; margin:.2rem 0 .7rem; }
.wizard-progress span { height:5px; flex:1; border-radius:999px; background:color-mix(in srgb,currentColor 10%,transparent); }
.wizard-progress span.done { background:linear-gradient(90deg,var(--em-pink),var(--em-violet)); }
.wizard-question { font-size:1.05rem; font-weight:800; margin:.2rem 0 .15rem; }
.wizard-copy { opacity:.66; font-size:.8rem; margin-bottom:.45rem; }
.st-key-mobile-orient-notice { display:none !important; }
@media(max-width: 850px) {
 .block-container { padding:.85rem 1rem 2.2rem; }
 .hero { min-height:112px; padding:1rem; }
 .hero p { font-size:.82rem; max-width:76%; }
 .feature-card { min-height:174px; padding:.8rem; }
 .feature-card p { font-size:.78rem; }
 .mascot { width:74px; height:74px; }
 .st-key-wellbeing-wizard { padding-left:165px; }
 .st-key-wellbeing-wizard .context-pet { left:14px; top:16px; width:120px; }
 .st-key-wellbeing-wizard .context-pet svg { width:110px; height:110px; }
}
@media(max-width: 768px) and (orientation: portrait) {
 .st-key-mobile-orient-notice {
  display:block !important;
  margin:.25rem 0 .75rem;
  padding:.8rem .95rem .7rem;
  border-radius:16px;
  border:1px solid color-mix(in srgb, var(--em-violet) 28%, transparent);
  background:linear-gradient(130deg, color-mix(in srgb, var(--em-violet) 10%, transparent), color-mix(in srgb, var(--em-blue) 8%, transparent));
  box-shadow:0 4px 18px rgba(109, 93, 252, 0.10);
 }
 .orient-badge { display:inline-flex; align-items:center; gap:4px; font-size:.72rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; color:var(--em-violet); margin-bottom:.2rem; }
 .orient-text-body strong { font-size:.92rem; font-weight:750; display:block; line-height:1.3; margin-bottom:.2rem; }
 .orient-text-body p { font-size:.8rem; opacity:.78; margin:0 0 .55rem; line-height:1.4; }
 .st-key-mobile-orient-notice [data-testid="stHorizontalBlock"] { gap:.5rem; }
 .st-key-mobile-orient-notice [data-testid="stButton"] button { min-height:2.15rem; font-size:.82rem; padding:.2rem .4rem; }
}
@media(max-width: 700px) {
 .block-container { padding:.75rem .75rem 2rem; }
 .page-heading { min-height:50px; }
 .page-heading .lead { display:none; }
 .hero { min-height:105px; }
 .hero p { display:none; }
 .st-key-overview-cards { overflow-y:auto; }
 .st-key-overview-cards [data-testid="stHorizontalBlock"] { flex-direction:column !important; height:auto; gap:.55rem; }
 .st-key-overview-cards [data-testid="stColumn"] { flex:1 1 auto !important; width:100% !important; min-width:0 !important; }
 .feature-card { min-height:112px; }
 .feature-card p { display:none; }
 .st-key-composer { margin-bottom:.85rem; }
 .st-key-composer [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; align-items:center; gap:.35rem; }
 .st-key-composer [data-testid="stColumn"]:first-child { flex:1 1 auto !important; width:auto !important; min-width:0 !important; }
 .st-key-composer [data-testid="stColumn"]:last-child { flex:0 0 58px !important; width:58px !important; min-width:58px !important; }
 .st-key-composer [data-testid="stCaptionContainer"] { display:none; }
 .st-key-feature-toolbar [data-testid="stHorizontalBlock"] { flex-wrap:wrap; gap:.25rem; }
 .st-key-conversation { min-height:120px; max-height:48vh; }
 .tool-embed { min-height:360px; }
 .st-key-wellbeing-wizard { padding:.9rem 1rem .9rem 96px !important; min-height:0; }
 .st-key-wellbeing-wizard .context-pet { position:absolute !important; left:10px !important; top:14px !important; width:72px !important; float:none !important; margin:0 !important; }
 .st-key-wellbeing-wizard .context-pet svg { width:68px !important; height:68px !important; }
 .st-key-wellbeing-wizard .context-pet-label { display:none !important; }
 .contextual-card { gap:1.1rem; padding:.9rem 1.1rem; align-items:center; }
 .contextual-pet-wrap { flex:0 0 76px; }
 .contextual-pet-wrap .context-pet { width:76px; }
 .contextual-pet-wrap .context-pet svg { width:70px; height:70px; }
 .contextual-pet-wrap .context-pet-label { display:none; }
 .contextual-title { font-size:.96rem; margin-bottom:.2rem; }
 .contextual-desc { font-size:.82rem; }
 [data-testid="stDialog"] [role="dialog"] { max-width:calc(100vw - 1rem); }
}
@media(max-height:700px) {
 .block-container { padding-top:.6rem; padding-bottom:1.8rem; gap:.4rem; }
 .page-heading { min-height:44px; }
 .page-heading .lead { display:none; }
 .page-heading .mascot-wrap { display:none; }
 .st-key-feature-toolbar { padding:.35rem .5rem; }
 .st-key-composer { padding:.4rem .55rem .32rem; margin-bottom:.6rem; }
 .st-key-composer [data-testid="stTextArea"] textarea { height:44px !important; max-height:66px !important; }
}
@media(prefers-reduced-motion: reduce) { .mascot,.mascot .pet-eye,.mascot .pet-wing-left,.mascot-wrap:after,.context-pet svg,.context-pet .pet-eye,.context-pet .pet-accessory,.thinking-mini,.thinking-dots i { animation:none !important; } }
</style>
"""


BRAND_LOGO = """
<svg class="brand-logo" viewBox="0 0 64 64" role="img" aria-label="Logo EduMind AI">
  <defs><linearGradient id="brandGradient" x1="8" y1="7" x2="56" y2="58" gradientUnits="userSpaceOnUse"><stop stop-color="#7c64ff"/><stop offset=".58" stop-color="#3b82f6"/><stop offset="1" stop-color="#22c7c9"/></linearGradient></defs>
  <path fill="url(#brandGradient)" d="M32 4 57 18v28L32 60 7 46V18z"/>
  <path fill="white" opacity=".96" d="M18 22.5c0-2 1.8-3.4 3.7-2.8L32 23.1l10.3-3.4c1.9-.6 3.7.8 3.7 2.8v19.7c0 1.4-1.4 2.4-2.7 1.9L32 40.4l-11.3 3.7c-1.3.5-2.7-.5-2.7-1.9V22.5Z"/>
  <path fill="#6654e8" d="M29.7 27.4 22 24.9v13.8l7.7-2.5V27.4Zm4.6 0v8.8l7.7 2.5V24.9l-7.7 2.5Z"/>
  <circle cx="32" cy="15" r="3.2" fill="#ffd166"/>
</svg>
"""


MASCOT = """
<div class="mascot-wrap" aria-label="Mascot cú mèo Mindi đang vẫy cánh">
<svg class="mascot" viewBox="0 0 120 120" role="img">
  <defs><linearGradient id="petBody" x1="25" y1="20" x2="94" y2="99"><stop stop-color="#806cff"/><stop offset="1" stop-color="#4f8df7"/></linearGradient></defs>
  <path class="pet-wing-left" fill="#5c54d8" d="M33 60C14 64 12 82 22 90c8 6 20-2 25-12L33 60Z"/>
  <path fill="#4c45bd" d="M87 61c19 5 20 22 10 29-8 6-19-2-24-12l14-17Z"/>
  <path fill="url(#petBody)" d="M30 43 25 22l18 12c10-7 25-7 35 0l18-12-6 22c7 8 11 19 10 31-1 24-17 35-40 35S21 99 20 75c-1-12 3-24 10-32Z"/>
  <ellipse cx="60" cy="75" rx="29" ry="28" fill="#eef4ff" opacity=".96"/>
  <circle cx="44" cy="54" r="15" fill="white"/><circle cx="76" cy="54" r="15" fill="white"/>
  <g class="pet-eye"><circle cx="46" cy="55" r="6" fill="#243052"/><circle cx="74" cy="55" r="6" fill="#243052"/><circle cx="48" cy="52" r="2" fill="white"/><circle cx="76" cy="52" r="2" fill="white"/></g>
  <path fill="#ffb84c" d="m60 61 8 7-8 6-8-6 8-7Z"/>
  <path fill="none" stroke="#6d5dfc" stroke-width="4" stroke-linecap="round" d="M47 83c8 6 18 6 26 0"/>
  <path fill="#ffcd67" d="M43 105h13l-6 6-7-6Zm21 0h13l-7 6-6-6Z"/>
</svg></div>
"""


def contextual_mindi(expression="calm", accessory="heart", label="Mindi ở đây cùng bạn"):
    eyes = {
        "happy": '<path class="pet-eye" d="M39 54q7-8 14 0M68 54q7-8 14 0" fill="none" stroke="#243052" stroke-width="4" stroke-linecap="round"/>',
        "tired": '<path class="pet-eye" d="M39 55h14M68 55h14" fill="none" stroke="#243052" stroke-width="4" stroke-linecap="round"/>',
        "sad": '<g class="pet-eye"><circle cx="46" cy="56" r="5" fill="#243052"/><circle cx="75" cy="56" r="5" fill="#243052"/><path d="M39 47l13-3M69 44l13 3" stroke="#243052" stroke-width="3" stroke-linecap="round"/></g>',
        "anxious": '<g class="pet-eye"><ellipse cx="46" cy="55" rx="6" ry="8" fill="#243052"/><ellipse cx="75" cy="55" rx="6" ry="8" fill="#243052"/><circle cx="48" cy="52" r="2" fill="white"/><circle cx="77" cy="52" r="2" fill="white"/></g>',
        "curious": '<g class="pet-eye"><circle cx="46" cy="55" r="6" fill="#243052"/><circle cx="75" cy="53" r="7" fill="#243052"/><circle cx="48" cy="52" r="2" fill="white"/><circle cx="77" cy="50" r="2" fill="white"/></g>',
        "calm": '<g class="pet-eye"><circle cx="46" cy="55" r="6" fill="#243052"/><circle cx="75" cy="55" r="6" fill="#243052"/><circle cx="48" cy="52" r="2" fill="white"/><circle cx="77" cy="52" r="2" fill="white"/></g>',
    }.get(expression, "")
    mouth = '<path d="M50 83q10 8 20 0" fill="none" stroke="#6d5dfc" stroke-width="4" stroke-linecap="round"/>'
    if expression == "sad":
        mouth = '<path d="M51 88q9-7 18 0" fill="none" stroke="#6d5dfc" stroke-width="4" stroke-linecap="round"/><path d="M82 63q5 8 0 13-5-5 0-13" fill="#5bb7ff"/>'
    elif expression == "anxious":
        mouth = '<ellipse cx="60" cy="86" rx="7" ry="5" fill="#6d5dfc"/>'
    accessory_svg = {
        "heart": '<g class="pet-accessory"><path d="M91 31c5-8 17-3 13 6-2 5-8 9-13 13-5-4-11-8-13-13-4-9 8-14 13-6Z" fill="#ff6b9a"/></g>',
        "search": '<g class="pet-accessory"><circle cx="92" cy="35" r="11" fill="none" stroke="#ffb84c" stroke-width="5"/><path d="m100 43 10 10" stroke="#ffb84c" stroke-width="6" stroke-linecap="round"/></g>',
        "compare": '<g class="pet-accessory"><rect x="82" y="21" width="16" height="23" rx="4" fill="#ff9f43"/><rect x="98" y="28" width="16" height="23" rx="4" fill="#22c7c9"/></g>',
        "compass": '<g class="pet-accessory"><circle cx="96" cy="36" r="15" fill="#fff" stroke="#22aeb3" stroke-width="4"/><path d="m101 29-4 10-10 4 4-10 10-4Z" fill="#ff6b9a"/></g>',
    }.get(accessory, "")
    return f'''<div class="context-pet"><svg viewBox="0 0 120 120" role="img" aria-label="{html.escape(label)}">
      <path fill="#554bc7" d="M31 61C14 66 13 83 23 90c8 5 18-2 24-12L31 61Zm58 0c17 5 18 22 8 29-8 5-18-2-24-12l16-17Z"/>
      <path fill="#6d5dfc" d="M30 43 25 22l18 12c10-7 25-7 35 0l18-12-6 22c7 8 11 19 10 31-1 24-17 35-40 35S21 99 20 75c-1-12 3-24 10-32Z"/>
      <ellipse cx="60" cy="75" rx="29" ry="28" fill="#eef4ff"/><circle cx="44" cy="54" r="15" fill="white"/><circle cx="76" cy="54" r="15" fill="white"/>
      {eyes}<path fill="#ffb84c" d="m60 62 8 7-8 6-8-6 8-7Z"/>{mouth}{accessory_svg}
      <path fill="#ffcd67" d="M43 105h13l-6 6-7-6Zm21 0h13l-7 6-6-6Z"/>
    </svg><div class="context-pet-label">{html.escape(label)}</div></div>'''


def wellbeing_expression(mood):
    return {
        "Khá ổn": "happy", "Mệt mỏi": "tired", "Lo lắng": "anxious",
        "Buồn": "sad", "Bối rối": "curious", "Khó gọi tên": "calm",
    }.get(mood, "calm")


def career_pet(stage):
    if stage and stage.startswith("2"):
        return contextual_mindi("curious", "compare", "Mindi cùng bạn so sánh")
    if stage and stage.startswith("3"):
        return contextual_mindi("happy", "compass", "Mindi cùng bạn lập kế hoạch")
    return contextual_mindi("curious", "search", "Mindi cùng bạn khám phá")


def initialize():
    defaults = {
        "user": None,
        "chats": {},
        "current": None,
        "nav": "overview",
        "mode": AIMode.FAST.value,
        "failure": None,
        "drafts": {},
        "pending_request": None,
        "ai_health": None,
        "ai_health_at": 0.0,
        "image_picker_revisions": {},
        "image_previews": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if "_next_nav" in st.session_state:
        st.session_state.nav = st.session_state.pop("_next_nav")


def image_daily_limit():
    raw_limit = setting("EDUMIND_IMAGE_DAILY_LIMIT", str(DEFAULT_IMAGE_DAILY_LIMIT))
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError) as exc:
        raise ValueError("EDUMIND_IMAGE_DAILY_LIMIT phải là số nguyên dương.") from exc
    if limit < 1 or limit > 100:
        raise ValueError("EDUMIND_IMAGE_DAILY_LIMIT cần nằm trong khoảng 1–100.")
    return limit


def normalize_image_upload(upload):
    data = upload.getvalue()
    if not data:
        raise ValueError("Ảnh trống hoặc không đọc được.")
    if len(data) > IMAGE_MAX_BYTES:
        raise ValueError("Ảnh vượt quá giới hạn 10 MB. Hãy chọn ảnh nhỏ hơn.")
    try:
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            if image_format not in {"JPEG", "PNG"}:
                raise ValueError("Chỉ hỗ trợ ảnh JPG, JPEG hoặc PNG.")
            if image.width * image.height > IMAGE_MAX_PIXELS:
                raise ValueError("Ảnh có độ phân giải quá lớn. Hãy giảm kích thước rồi thử lại.")
            image.load()
            normalized = BytesIO()
            image.save(normalized, format=image_format, optimize=True)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Không đọc được ảnh. Hãy chọn tệp JPG hoặc PNG hợp lệ.") from exc
    normalized_bytes = normalized.getvalue()
    if len(normalized_bytes) > IMAGE_MAX_BYTES:
        raise ValueError("Ảnh sau khi xử lý vượt quá giới hạn 10 MB.")
    mime_type = "image/jpeg" if image_format == "JPEG" else "image/png"
    return normalized_bytes, mime_type


def navigate(feature, chat_id=None):
    st.session_state.current = chat_id
    st.session_state.failure = None
    st.session_state["_next_nav"] = feature.value if isinstance(feature, Feature) else feature
    st.rerun()


def user_id():
    user = st.session_state.user
    return user.id if user else None


def current_chat():
    return st.session_state.chats.get(st.session_state.current)


def composer_key(chat):
    revision = sum(m["role"] == "assistant" for m in chat.messages)
    return f"draft_{chat.id}_{revision}"


def ensure_chat(feature):
    chat = current_chat()
    if chat is not None and chat.feature == feature:
        return chat
    if not user_id():
        candidates = [item for item in st.session_state.chats.values() if item.owner is None and item.feature == feature]
        if candidates:
            chat = max(candidates, key=lambda item: item.updated_at or "")
            st.session_state.current = chat.id
            return chat
    chat = Conversation(feature=feature, owner=user_id(), save_enabled=bool(user_id()) and feature != Feature.WELLBEING)
    st.session_state.chats[chat.id] = chat
    st.session_state.current = chat.id
    return chat


def persist(store, chat):
    if user_id() and chat.save_enabled and chat.messages:
        store.save_chat(user_id(), chat)


def complete_login(store, user):
    guest_chats = [chat for chat in st.session_state.chats.values() if chat.owner is None]
    nav = st.session_state.nav
    requested_mode = st.session_state.mode
    chats = {chat.id: chat for chat in store.list_chats(user.id)}
    current_id = st.session_state.current if st.session_state.current in {chat.id for chat in guest_chats} else None
    saved_drafts = {}
    for guest in guest_chats:
        draft = st.session_state.drafts.get(guest.id, st.session_state.get(composer_key(guest), ""))
        if draft:
            saved_drafts[guest.id] = draft
        guest.owner = user.id
        guest.save_enabled = guest.feature != Feature.WELLBEING
        if guest.messages and guest.save_enabled:
            store.save_chat(user.id, guest)
        chats[guest.id] = guest
    pending_action = st.session_state.get("pending_action")
    pending_request = st.session_state.get("pending_request")
    st.session_state.clear()
    st.session_state.update(user=user, chats=chats, current=current_id, nav=nav, mode=requested_mode, failure=None, drafts=saved_drafts, pending_request=None)
    for guest in guest_chats:
        if guest.id in saved_drafts:
            st.session_state[composer_key(guest)] = saved_drafts[guest.id]
    if pending_action and pending_action.get("chat_id") in chats:
        st.session_state.pending_action = pending_action
    if pending_request and pending_request.get("chat_id") in chats:
        st.session_state.pending_request = pending_request


def submit_auth(store, kind):
    auth = Auth(store)
    try:
        if kind == "login":
            user = auth.authenticate(st.session_state.login_email, st.session_state.login_password)
            if not user:
                raise ValueError("Email hoặc mật khẩu chưa đúng.")
        elif kind == "register":
            if st.session_state.register_password != st.session_state.register_confirm:
                raise ValueError("Hai mật khẩu chưa khớp.")
            user = auth.register(st.session_state.register_email, st.session_state.register_password)
        else:
            user = auth.link_legacy_email(st.session_state.legacy_identity, st.session_state.legacy_password, st.session_state.legacy_email)
    except ValueError as exc:
        st.session_state.auth_error = str(exc)
    else:
        complete_login(store, user)


def close_dialog():
    st.session_state.pop("active_dialog", None)
    for key in ("login_password", "register_password", "register_confirm", "legacy_password", "auth_error", "rename_error", "auth_reason"):
        st.session_state.pop(key, None)


def clear_auth_error():
    st.session_state.pop("auth_error", None)


@st.dialog("Tài khoản EduMind", width="small", on_dismiss=close_dialog)
def auth_dialog(store):
    if not st.session_state.get("active_dialog"):
        st.rerun()
    st.caption(st.session_state.get("auth_reason", "Lưu hành trình học tập và mở chế độ Tư duy."))
    tab = st.radio("Thao tác", ["Đăng nhập", "Đăng ký", "Tài khoản cũ"], horizontal=True, label_visibility="collapsed", key="auth_tab", on_change=clear_auth_error)
    if tab == "Đăng nhập":
        with st.form("login_form"):
            st.text_input("Email", placeholder="ban@example.com", key="login_email", max_chars=254)
            st.text_input("Mật khẩu", type="password", key="login_password", max_chars=1024)
            st.form_submit_button("Đăng nhập", type="primary", use_container_width=True, on_click=submit_auth, args=(store, "login"))
        st.caption("Bản này chưa hỗ trợ khôi phục mật khẩu qua email.")
    elif tab == "Đăng ký":
        with st.form("register_form"):
            st.text_input("Email", placeholder="ban@example.com", key="register_email", max_chars=254)
            st.text_input("Mật khẩu", type="password", help="Ít nhất 8 ký tự. Nhấn biểu tượng con mắt để xem mật khẩu.", key="register_password", max_chars=1024)
            st.text_input("Nhập lại mật khẩu", type="password", key="register_confirm", max_chars=1024)
            st.caption("Email dùng để đăng nhập, hiện chưa được xác minh.")
            st.form_submit_button("Tạo tài khoản", type="primary", use_container_width=True, on_click=submit_auth, args=(store, "register"))
    else:
        st.info("Đã có tài khoản tên đăng nhập? Liên kết một email để giữ toàn bộ lịch sử cũ.")
        with st.form("legacy_form"):
            st.text_input("Tên tài khoản cũ", key="legacy_identity")
            st.text_input("Mật khẩu cũ", type="password", key="legacy_password", max_chars=1024)
            st.text_input("Email dùng từ bây giờ", key="legacy_email", max_chars=254)
            st.form_submit_button("Chuyển sang email", type="primary", use_container_width=True, on_click=submit_auth, args=(store, "legacy"))
    if st.session_state.get("auth_error"):
        st.error(st.session_state.auth_error)


def submit_rename(store, chat_id):
    chat = st.session_state.chats.get(chat_id)
    if not chat:
        close_dialog()
        return
    title = st.session_state[f"rename_title_{chat_id}"].strip()
    if not title:
        st.session_state.rename_error = "Tên cuộc trò chuyện không được để trống."
        return
    if chat.persisted:
        store.rename_chat(user_id(), chat.id, title)
    chat.title, chat.updated_at = title, now_iso()
    st.session_state.pop("rename_error", None)
    close_dialog()


@st.dialog("Đổi tên cuộc trò chuyện", on_dismiss=close_dialog)
def rename_dialog(store, chat_id):
    if not st.session_state.get("active_dialog"):
        st.rerun()
    chat = st.session_state.chats.get(chat_id)
    if not chat:
        return
    with st.form("rename_form"):
        st.text_input("Tên cuộc trò chuyện", value=chat.title, max_chars=120, key=f"rename_title_{chat_id}")
        st.form_submit_button("Lưu tên", type="primary", on_click=submit_rename, args=(store, chat_id))
    if st.session_state.get("rename_error"):
        st.error(st.session_state.rename_error)


def submit_delete(store, chat_id):
    chat = st.session_state.chats.get(chat_id)
    if chat:
        if chat.persisted:
            store.delete_chat(user_id(), chat.id)
        st.session_state.chats.pop(chat.id, None)
        if st.session_state.current == chat.id:
            st.session_state.current = None
        if st.session_state.failure and st.session_state.failure["chat_id"] == chat.id:
            st.session_state.failure = None
        st.session_state.drafts.pop(chat.id, None)
    close_dialog()


@st.dialog("Xóa cuộc trò chuyện?", on_dismiss=close_dialog)
def delete_dialog(store, chat_id):
    if not st.session_state.get("active_dialog"):
        st.rerun()
    chat = st.session_state.chats.get(chat_id)
    if not chat:
        return
    st.write(f'“{chat.title}” sẽ bị xóa. Bạn không thể khôi phục thao tác này.')
    st.button("Xóa cuộc trò chuyện", type="primary", key="confirm_delete", on_click=submit_delete, args=(store, chat_id))


def sorted_chats(search=""):
    result = [chat for chat in st.session_state.chats.values() if chat.messages]
    if search:
        query = search.casefold()
        result = [chat for chat in result if query in (chat.title + " " + " ".join(m["content"] for m in chat.messages)).casefold()]
    return sorted(result, key=lambda chat: chat.updated_at or "", reverse=True)


def on_nav_change():
    chat = current_chat()
    if chat and st.session_state.nav != chat.feature.value:
        st.session_state.current = None
    st.session_state.failure = None


def refresh_ai_health(service, force=False):
    now = time.monotonic()
    if force or st.session_state.ai_health is None or now - st.session_state.ai_health_at >= 60:
        st.session_state.ai_health = service.check_connection()
        st.session_state.ai_health_at = now
    return st.session_state.ai_health


def sidebar(store, service):
    with st.sidebar:
        st.markdown(f'<div class="brand">{BRAND_LOGO}<div><div class="brand-name">EduMind <span>AI</span></div><div class="brand-sub">Học tập · Trưởng thành</div></div></div>', unsafe_allow_html=True)
        options = ["overview", *[f.value for f in Feature], TOOLS_NAV]
        labels = {"overview": "Tổng quan", TOOLS_NAV: "Công cụ học tập"}
        st.radio("Không gian của bạn", options, format_func=lambda v: labels[v] if v in labels else FEATURE_LABELS[Feature(v)], key="nav", on_change=on_nav_change, label_visibility="collapsed")
        if st.button("Cuộc trò chuyện mới", icon=":material/add:", use_container_width=True):
            if not user_id():
                st.session_state.auth_reason = "Đăng nhập để tạo thêm cuộc trò chuyện. Ba cuộc trò chuyện khách hiện tại vẫn được giữ nguyên."
                st.session_state.active_dialog = ("auth", None)
            else:
                feature = Feature(st.session_state.nav) if st.session_state.nav != "overview" else Feature.STUDY
                navigate(feature)
        st.divider()
        st.markdown("##### Cuộc trò chuyện")
        search = st.text_input("Tìm trong lịch sử", placeholder="Tìm cuộc trò chuyện…", key="history_search", label_visibility="collapsed")
        chats = sorted_chats(search)
        if not chats:
            st.caption("Chưa có kết quả phù hợp." if search else "Những cuộc trò chuyện của bạn sẽ xuất hiện ở đây.")
        with st.container(height="stretch", border=False):
            group = None
            for chat in chats:
                next_group = history_group(chat.updated_at)
                if next_group != group:
                    st.caption(next_group)
                    group = next_group
                title_col, menu_col = st.columns([.85, .15], gap="small")
                with title_col:
                    if st.button(chat.title, key=f"open_{chat.id}", type="primary" if st.session_state.current == chat.id else "tertiary", use_container_width=True, help=f"{FEATURE_LABELS[chat.feature]} · {'Đã lưu' if chat.persisted else 'Trong phiên'}"):
                        navigate(chat.feature, chat.id)
                with menu_col:
                    with st.popover("", icon=":material/more_horiz:", help="Tùy chọn cuộc trò chuyện"):
                        st.caption(FEATURE_LABELS[chat.feature])
                        if st.button("Đổi tên", key=f"rename_{chat.id}", icon=":material/edit:"):
                            st.session_state.active_dialog = ("rename", chat.id)
                        if st.button("Xóa", key=f"delete_{chat.id}", icon=":material/delete:"):
                            st.session_state.active_dialog = ("delete", chat.id)
        st.divider()
        if st.session_state.user:
            st.caption("Đang đăng nhập")
            st.write(st.session_state.user.email)
            if st.button("Đăng xuất", icon=":material/logout:", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            st.caption("Khách · Lịch sử chỉ giữ trong phiên này")
            if st.button("Đăng nhập / Đăng ký", icon=":material/person:", use_container_width=True):
                st.session_state.active_dialog = ("auth", None)
        health = st.session_state.ai_health
        st.markdown("##### Trạng thái AI")
        if health and health.ready:
            st.caption("🟢 AI đã kết nối")
        elif health:
            st.warning(health.message)
        if st.button("Kiểm tra lại kết nối", key="refresh_ai_health", icon=":material/refresh:", use_container_width=True):
            refresh_ai_health(service, force=True)
            st.rerun()
        st.caption("Đổi Sáng / Tối trong menu ⋮ → Settings → Theme.")


def overview(store):
    today = datetime.now(LOCAL_TZ)
    with st.container(key="sr-title"):
        st.title("Mỗi ngày, tiến thêm một bước.")
    st.markdown(
        f'<div class="hero"><span class="today-pill">HÔM NAY · {today.day:02d}/{today.month:02d}/{today.year}</span>'
        '<h1>Mỗi ngày, tiến thêm một bước.</h1>'
        '<p>Học thông minh hơn, lắng nghe chính mình và khám phá con đường phù hợp — tất cả trong một không gian.</p>'
        f'{MASCOT}</div>',
        unsafe_allow_html=True,
    )
    actions = {Feature.STUDY: "Bắt đầu học tập", Feature.WELLBEING: "Dành chút thời gian cho mình", Feature.CAREER: "Khám phá hướng đi"}
    colors = {Feature.STUDY: "#6d5dfc", Feature.WELLBEING: "#ff6b9a", Feature.CAREER: "#22aeb3"}
    symbols = {Feature.STUDY: "✦", Feature.WELLBEING: "♥", Feature.CAREER: "➜"}
    with st.container(key="overview-cards", height="stretch"):
        cols = st.columns(3, gap="medium", vertical_alignment="top")
        for col, feature in zip(cols, Feature):
            with col:
                st.markdown(
                    f'<div class="feature-card" style="--card-color:{colors[feature]}">'
                    f'<div class="feature-icon">{symbols[feature]}</div><h3>{FEATURE_LABELS[feature]}</h3>'
                    f'<p>{DESCRIPTIONS[feature]}</p></div>',
                    unsafe_allow_html=True,
                )
                if st.button(actions[feature], key=f"start_{feature.value}", use_container_width=True, icon=ICONS[feature]):
                    navigate(feature)
    with st.container(key="overview-footer"):
        left, right = st.columns([1.7, 1], gap="medium", vertical_alignment="center")
        with left:
            st.markdown('<div class="mini-banner"><span style="font-size:1.45rem">⚡</span><div><strong>Tiếp tục từ lần trước</strong><div class="muted">Mở nhanh cuộc trò chuyện gần nhất của bạn.</div></div></div>', unsafe_allow_html=True)
        recent = sorted_chats()[:3]
        if recent:
            with right:
                chat = recent[0]
                if st.button(chat.title, key=f"recent_{chat.id}", type="primary", use_container_width=True, icon=":material/history:"):
                    navigate(chat.feature, chat.id)
        else:
            with right:
                if not user_id() and st.button("Tạo tài khoản để lưu hành trình", key="overview_login", type="primary", use_container_width=True):
                    st.session_state.active_dialog = ("auth", None)
                elif user_id() and st.button("Bắt đầu cuộc trò chuyện mới", key="overview_new", type="primary", use_container_width=True, icon=":material/add:"):
                    navigate(Feature.STUDY)


def educational_tools_page():
    st.markdown(
        '<div class="page-heading"><div><div class="eyebrow">EDUMIND · TÀI NGUYÊN HỌC TẬP</div>'
        '<h1>Công cụ học tập</h1><p class="lead">Mở nhanh các công cụ Toán và Khoa học để học tập chủ động hơn.</p></div></div>',
        unsafe_allow_html=True,
    )
    name = st.selectbox("Chọn công cụ", list(EDUCATIONAL_TOOLS), key="educational_tool")
    tool = EDUCATIONAL_TOOLS[name]
    st.caption(tool["description"])
    st.link_button("Mở công cụ trong tab mới", tool["url"], use_container_width=True)
    if tool["embed"]:
        st.caption("Nếu công cụ không hiển thị trong khung, hãy mở bằng nút phía trên. EduMind không vượt giới hạn nhúng của website.")
        st.components.v1.iframe(tool["url"], height=650, scrolling=True)
    else:
        st.info("Website không cho phép nhúng nội dung vào EduMind; hãy mở công cụ trong tab mới.")


def header(feature):
    st.markdown(
        '<div class="page-heading"><div><div class="eyebrow">EDUMIND · KHÔNG GIAN CỦA BẠN</div>'
        f'<h1>{FEATURE_LABELS[feature]}</h1><p class="lead">{DESCRIPTIONS[feature]}</p></div>{MASCOT}</div>',
        unsafe_allow_html=True,
    )


def mode_control(store):
    st.radio("Chế độ AI", [mode.value for mode in AIMode], format_func=lambda v: MODE_LABELS[AIMode(v)], key="mode", horizontal=True, label_visibility="collapsed")
    if st.session_state.mode == AIMode.THINKING.value and not user_id():
        st.info("Đăng nhập để sử dụng Tư duy. Nội dung bạn đang soạn vẫn được giữ.")
        if st.button("Đăng nhập để dùng Tư duy", key="thinking_login"):
            st.session_state.active_dialog = ("auth", None)


def save_control(store, chat):
    if chat.feature == Feature.WELLBEING:
        key = f"mental_save_{chat.id}"
        if key not in st.session_state:
            st.session_state[key] = chat.save_enabled
        enabled = st.toggle("Lưu toàn bộ cuộc trò chuyện này vào tài khoản", key=key, disabled=not bool(user_id()), help="Bao gồm cả những tin nhắn đã có. Tắt sẽ dừng ghi tiếp; bản đã lưu vẫn còn cho đến khi bạn xóa.")
        changed = enabled != chat.save_enabled
        chat.save_enabled = enabled
        if changed and enabled:
            persist(store, chat)
            st.rerun()
        if chat.persisted and not enabled:
            st.caption("Đã dừng lưu tin nhắn mới. Bản lưu trước đó vẫn có trong lịch sử; bạn có thể xóa bằng menu của cuộc trò chuyện.")
        if not user_id():
            st.caption("Cần đăng nhập nếu bạn muốn chủ động lưu cuộc trò chuyện này.")
    elif user_id() and chat.owner is None:
        st.info("Đây là cuộc trò chuyện bạn bắt đầu khi dùng khách. Hiện vẫn chỉ giữ trong phiên.")
        if st.button("Lưu cuộc trò chuyện vào tài khoản", key=f"save_guest_{chat.id}", disabled=not chat.messages):
            chat.save_enabled = True
            persist(store, chat)
            st.rerun()
    else:
        st.caption("Tự động lưu vào tài khoản khi có tin nhắn." if user_id() else "Khách · Cuộc trò chuyện chỉ giữ trong phiên này.")


def select_value(label, values, key, default):
    if key not in st.session_state or st.session_state[key] not in values:
        st.session_state[key] = default if default in values else values[0]
    return st.selectbox(label, values, key=key)


def study_context(chat):
    meta = chat.metadata
    prefix = f"study_{chat.id}_"
    action = None
    if "study_setup_enabled" not in meta:
        legacy_fields = ("grade", "subject", "topic", "exercise", "task")
        meta["study_setup_enabled"] = any(field in meta for field in legacy_fields)
    setup_key = prefix + "setup_enabled"
    if setup_key not in st.session_state:
        st.session_state[setup_key] = bool(meta["study_setup_enabled"])
    enabled = st.toggle(
        "Dùng thiết lập nội dung học",
        key=setup_key,
        help="Tắt để chat tự do. Các lựa chọn cũ vẫn được giữ để bạn bật lại sau.",
    )
    meta["study_setup_enabled"] = enabled
    if not enabled:
        st.caption("Chat tự do đang bật · AI chỉ nhận nội dung bạn gửi trong khung chat.")
        return None
    with st.expander("Thiết lập nội dung học", expanded=not bool(chat.messages)):
        st.caption("Chọn gợi ý hoặc nhập nội dung của bạn. Danh mục không thay thế mục lục sách giáo khoa.")
        col1, col2 = st.columns(2)
        with col1:
            grade = select_value("Lớp", list(range(6, 13)), prefix + "grade", meta.get("grade", 9))
        if grade != meta.get("grade", grade):
            for suffix in ("subject", "topic", "exercise", "subject_custom", "topic_custom", "exercise_custom"):
                st.session_state.pop(prefix + suffix, None)
            for field in ("subject", "topic", "exercise", "subject_choice", "topic_choice", "exercise_choice"):
                meta.pop(field, None)
        with col2:
            subject_choice = select_value("Môn học", subjects(grade), prefix + "subject", meta.get("subject_choice", "Toán"))
        subject = subject_choice
        if subject_choice == MANUAL:
            subject = st.text_input("Nhập môn học", value=meta.get("subject", ""), key=prefix + "subject_custom", max_chars=100)
        if subject != meta.get("subject", subject):
            for suffix in ("topic", "exercise", "topic_custom", "exercise_custom"):
                st.session_state.pop(prefix + suffix, None)
            for field in ("topic", "exercise", "topic_choice", "exercise_choice"):
                meta.pop(field, None)
        catalog = topics(grade, subject)
        col1, col2 = st.columns(2)
        with col1:
            topic_choice = select_value("Chủ đề", [*catalog, MANUAL], prefix + "topic", meta.get("topic_choice", next(iter(catalog), MANUAL)))
            topic = st.text_input("Nhập chủ đề", value=meta.get("topic", ""), key=prefix + "topic_custom", max_chars=160) if topic_choice == MANUAL else topic_choice
        if topic != meta.get("topic", topic):
            for suffix in ("exercise", "exercise_custom"):
                st.session_state.pop(prefix + suffix, None)
            meta.pop("exercise_choice", None)
            meta.pop("exercise", None)
        with col2:
            exercise_choice = select_value("Dạng bài", [*catalog.get(topic, []), MANUAL], prefix + "exercise", meta.get("exercise_choice", MANUAL))
            exercise = st.text_input("Nhập dạng bài", value=meta.get("exercise", ""), key=prefix + "exercise_custom", max_chars=160) if exercise_choice == MANUAL else exercise_choice
        task = select_value("Bạn muốn được hỗ trợ thế nào?", TASKS, prefix + "task", meta.get("task", TASKS[1]))
        meta.update(grade=grade, subject=subject, topic=topic, exercise=exercise, subject_choice=subject_choice, topic_choice=topic_choice, exercise_choice=exercise_choice, task=task)
        if task == TASKS[3]:
            goal = st.text_input("Mục tiêu ôn tập", value=meta.get("goal", ""), key=prefix + "goal", placeholder="Ví dụ: ôn thi vào lớp 10, củng cố phần hình học", max_chars=300)
            a, b = st.columns(2)
            weeks = a.number_input("Thời hạn (tuần)", min_value=1, max_value=52, value=int(meta.get("weeks", 4)), key=prefix + "weeks")
            minutes = b.number_input("Thời gian học mỗi ngày (phút)", min_value=10, max_value=360, value=int(meta.get("minutes_per_day", 45)), step=5, key=prefix + "minutes")
            meta.update(goal=goal, weeks=weeks, minutes_per_day=minutes)
            if st.button("Tạo kế hoạch ôn tập", type="primary", disabled=not goal.strip(), key=prefix + "plan"):
                action = f"Hãy lập kế hoạch ôn tập cho mục tiêu: {goal}."
    tags = [f"Lớp {meta['grade']}", meta.get("subject"), meta.get("topic"), meta.get("exercise"), meta.get("task")]
    st.markdown("".join(f'<span class="tag">{html.escape(str(tag))}</span>' for tag in tags if tag), unsafe_allow_html=True)
    return action


STUDY_CONTEXT_FIELDS = {
    "grade", "subject", "topic", "exercise", "subject_choice", "topic_choice", "exercise_choice",
    "task", "goal", "weeks", "minutes_per_day",
}


def request_context(chat):
    context = dict(chat.metadata)
    if chat.feature == Feature.STUDY and not context.get("study_setup_enabled", False):
        for field in STUDY_CONTEXT_FIELDS:
            context.pop(field, None)
        context["study_setup_enabled"] = False
    return context


def wellbeing_context(chat):
    meta = chat.metadata
    supports = ["Được lắng nghe", "Gỡ rối suy nghĩ", "Tìm một bước nhỏ", "Chưa biết, cùng khám phá"]
    step_key = f"wellbeing_step_{chat.id}"
    if step_key not in st.session_state:
        st.session_state[step_key] = 4 if meta.get("checkin_complete") or chat.messages else 0
    step = st.session_state[step_key]
    if step >= 4:
        queued_action = st.session_state.pop(f"wellbeing_action_{chat.id}", None)
        with st.container(key="wizard-state-keeper"):
            saved_support = meta.get("support")
            st.radio("Cách hỗ trợ đã chọn", supports, index=supports.index(saved_support) if saved_support in supports else 0, key=f"wellbeing_support_{chat.id}", label_visibility="collapsed")
        with st.container(key="wellbeing-summary"):
            mood = meta.get("mood", "Chưa chia sẻ")
            support = meta.get("support", "Trò chuyện tự do")
            a, b = st.columns([4, 1], vertical_alignment="center")
            a.markdown(f'<span class="tag">Cảm xúc · {html.escape(str(mood))}</span><span class="tag">Mong muốn · {html.escape(str(support))}</span>', unsafe_allow_html=True)
            if b.button("Sửa check-in", key=f"edit_checkin_{chat.id}", icon=":material/edit:", use_container_width=True):
                st.session_state[step_key] = 0
                st.rerun()
        return queued_action

    questions = [
        ("Chào bạn, lúc này bạn đang cảm thấy thế nào?", "Chọn điều gần nhất với cảm xúc hiện tại. Không có câu trả lời đúng hay sai."),
        ("Điều gì đang khiến bạn bận tâm nhất?", "Bạn có thể kể ngắn gọn, hoặc để trống nếu chưa muốn nói."),
        ("Cảm giác này đang ảnh hưởng đến bạn ở mức nào?", "Chọn theo cảm nhận của bạn ngay lúc này."),
        ("Bạn mong EduMind hỗ trợ theo cách nào?", "Mình sẽ dựa vào lựa chọn này để bắt đầu cuộc trò chuyện phù hợp hơn."),
    ]
    with st.container(key="wellbeing-wizard"):
        active_mood = st.session_state.get(f"wellbeing_mood_{chat.id}", meta.get("mood"))
        st.markdown(contextual_mindi(wellbeing_expression(active_mood), "heart", "Mindi lắng nghe bạn"), unsafe_allow_html=True)
        st.markdown('<div class="step-label">CHECK-IN CÙNG MINDI · BƯỚC ' + str(step + 1) + '/4</div>', unsafe_allow_html=True)
        st.markdown('<div class="wizard-progress">' + "".join(f'<span class="{"done" if i <= step else ""}"></span>' for i in range(4)) + '</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="wizard-question">{questions[step][0]}</div><div class="wizard-copy">{questions[step][1]}</div>', unsafe_allow_html=True)

        if step == 0:
            moods = ["Khá ổn", "Mệt mỏi", "Lo lắng", "Buồn", "Bối rối", "Khó gọi tên"]
            mood_default = meta.get("mood") if meta.get("mood") in moods else None
            answer = st.radio("Cảm xúc hiện tại", moods, index=moods.index(mood_default) if mood_default else None, horizontal=True, key=f"wellbeing_mood_{chat.id}", label_visibility="collapsed")
            can_continue = bool(answer)
        elif step == 1:
            answer = st.text_area("Điều đang khiến bạn bận tâm", value=meta.get("situation", ""), placeholder="Ví dụ: chuyện học, gia đình, bạn bè, giấc ngủ…", height=76, max_chars=1200, key=f"wellbeing_situation_{chat.id}", label_visibility="collapsed")
            can_continue = True
        elif step == 2:
            levels = ["1 · Nhẹ", "2", "3 · Vừa", "4", "5 · Rất nhiều"]
            saved_level = meta.get("intensity")
            answer = st.radio("Mức độ ảnh hưởng", levels, index=levels.index(saved_level) if saved_level in levels else None, horizontal=True, key=f"wellbeing_intensity_{chat.id}", label_visibility="collapsed")
            can_continue = bool(answer)
        else:
            saved_support = meta.get("support")
            answer = st.radio("Cách hỗ trợ", supports, index=supports.index(saved_support) if saved_support in supports else None, horizontal=True, key=f"wellbeing_support_{chat.id}", label_visibility="collapsed")
            can_continue = bool(answer)

        back_col, next_col = st.columns([1, 3])
        if step > 0 and back_col.button("Quay lại", key=f"wellbeing_back_{chat.id}_{step}", icon=":material/arrow_back:", use_container_width=True):
            st.session_state[step_key] = step - 1
            st.rerun()
        label = "Bắt đầu trò chuyện" if step == 3 else "Tiếp tục"
        if next_col.button(label, key=f"wellbeing_next_{chat.id}_{step}", type="primary", icon=":material/arrow_forward:", use_container_width=True, disabled=not can_continue):
            fields = ["mood", "situation", "intensity", "support"]
            meta[fields[step]] = answer.strip() if isinstance(answer, str) else answer
            if step < 3:
                st.session_state[step_key] = step + 1
                st.rerun()
            meta["checkin_complete"] = True
            st.session_state[step_key] = 4
            situation = meta.get("situation", "").strip()
            detail = f" Điều mình đang bận tâm là: {situation}." if situation else " Mình chưa muốn kể chi tiết về nguyên nhân."
            st.session_state[f"wellbeing_action_{chat.id}"] = (
                f"Mình đang cảm thấy {meta['mood'].lower()}, mức ảnh hưởng {meta['intensity'].lower()}."
                f"{detail} Lúc này mình muốn {meta['support'].lower()}. Hãy bắt đầu bằng một câu hỏi ngắn để lắng nghe mình."
            )
            st.rerun()
    st.caption("Hỗ trợ tinh thần không thay thế chăm sóc chuyên môn. Nội dung bạn gửi được chuyển đến dịch vụ AI để tạo phản hồi.")
    return None


def career_context(chat):
    meta = chat.metadata
    prefix = f"career_{chat.id}_"
    with st.expander("Hồ sơ khám phá của bạn", expanded=not bool(chat.messages)):
        a, b = st.columns(2)
        saved_age = meta.get("age")
        age = a.number_input("Tuổi hiện tại *", min_value=10, max_value=25, value=int(saved_age) if saved_age else None, step=1, key=prefix + "age", placeholder="Chọn tuổi")
        grades = list(range(6, 13))
        saved_grade = meta.get("grade")
        grade = b.selectbox("Lớp hiện tại *", grades, index=grades.index(saved_grade) if saved_grade in grades else None, key=prefix + "grade", placeholder="Chọn lớp")
        a, b = st.columns(2)
        favorite = a.text_input("Môn bạn yêu thích", value=meta.get("favorite_subjects", ""), key=prefix + "favorite", placeholder="Ví dụ: Sinh học, Văn, Tin học", max_chars=250)
        interests = b.text_input("Điều bạn thích làm", value=meta.get("interests", ""), key=prefix + "interests", placeholder="Ví dụ: chăm sóc cây, viết, sửa đồ", max_chars=400)
        strengths = a.text_area("Thế mạnh bạn nhận thấy", value=meta.get("strengths", ""), key=prefix + "strengths", placeholder="Kể một việc bạn làm khá tốt hoặc được nhờ giúp.", max_chars=1000)
        conditions = b.text_area("Điều kiện cần cân nhắc", value=meta.get("conditions", ""), key=prefix + "conditions", placeholder="Thời gian, tài chính, mong muốn gia đình… (tùy chọn)", max_chars=1000)
        current_study_place = st.text_input("Bạn đang học ở đâu?", value=meta.get("current_study_place", ""), key=prefix + "current_study_place", placeholder="Tên trường, tỉnh/thành hoặc khu vực (tùy chọn)", max_chars=250)
        a, b = st.columns(2)
        preferred_study_place = a.text_input("Bạn muốn học tiếp ở đâu?", value=meta.get("preferred_study_place", ""), key=prefix + "preferred_study_place", placeholder="Trong tỉnh, thành phố khác, du học…", max_chars=250)
        preferred_work_place = b.text_input("Bạn muốn làm việc ở đâu?", value=meta.get("preferred_work_place", ""), key=prefix + "preferred_work_place", placeholder="Gần nhà, thành phố lớn, từ xa…", max_chars=250)
        preferred_work_environment = st.text_input("Môi trường làm việc mong muốn", value=meta.get("preferred_work_environment", ""), key=prefix + "preferred_work_environment", placeholder="Sáng tạo, ổn định, ngoài trời, làm với con người…", max_chars=300)
        goal = st.text_input("Mục tiêu hoặc nghề/ngành đang quan tâm", value=meta.get("goal", ""), key=prefix + "goal", placeholder="Có thể để trống nếu bạn đang khám phá.", max_chars=300)
        meta.update(
            age=int(age) if age is not None else None, grade=grade, favorite_subjects=favorite,
            interests=interests, strengths=strengths, conditions=conditions,
            current_study_place=current_study_place, preferred_study_place=preferred_study_place,
            preferred_work_place=preferred_work_place, preferred_work_environment=preferred_work_environment,
            goal=goal,
        )
    steps = ["1 · Khám phá bản thân", "2 · So sánh hướng đi", "3 · Kế hoạch & trải nghiệm"]
    stage = select_value("Bước tiếp theo", steps, prefix + "stage", meta.get("stage", steps[0]))
    meta["stage"] = stage
    ready = bool(meta.get("age") and meta.get("grade") and meta.get("interests", "").strip() and meta.get("strengths", "").strip())
    if stage == steps[0]:
        st.markdown("### Bắt đầu từ những điều gần gũi")
        st.write("Sở thích và thế mạnh là điểm xuất phát. Chúng có thể thay đổi khi bạn có thêm trải nghiệm.")
        if st.button("Khám phá 3 hướng phù hợp", type="primary", disabled=not ready, key=prefix + "explore"):
            meta["task"] = "Khám phá"
            return "Dựa vào hồ sơ của mình, hãy đề xuất 3 hướng học tập/nghề nghiệp để khám phá, kèm lý do, điều cần tìm hiểu và một trải nghiệm nhỏ cho mỗi hướng."
        if not ready:
            st.caption("Điền tuổi, lớp, sở thích và thế mạnh để nhận gợi ý. Các thông tin địa điểm là tùy chọn.")
    elif stage == steps[1]:
        choices = st.text_input("Các hướng bạn muốn so sánh", value=meta.get("choices", ""), key=prefix + "choices", placeholder="Ví dụ: thiết kế đồ họa, giáo dục, truyền thông", max_chars=400)
        meta["choices"] = choices
        if st.button("So sánh các lựa chọn", type="primary", disabled=not choices.strip(), key=prefix + "compare"):
            meta["task"] = "So sánh"
            return f"Hãy so sánh các hướng {choices} dựa trên hồ sơ của mình: hoạt động thường làm, lý do phù hợp, điều cần tìm hiểu và cách thử."
    else:
        role = st.text_input("Hướng muốn thử hoặc lên kế hoạch", value=meta.get("role", meta.get("goal", "")), key=prefix + "role", placeholder="Ví dụ: giáo viên, thiết kế, kỹ thuật, y tế…", max_chars=200)
        months = st.slider("Thời hạn kế hoạch (tháng)", 1, 60, int(meta.get("months", 6)), key=prefix + "months")
        meta.update(role=role, months=months)
        a, b = st.columns(2)
        if a.button("Xây kế hoạch", type="primary", disabled=not role.strip(), key=prefix + "roadmap", use_container_width=True):
            meta["task"] = "Lập kế hoạch"
            return f"Lập kế hoạch {months} tháng để mình tìm hiểu và chuẩn bị cho hướng {role}, phù hợp với lớp và điều kiện của mình."
        if b.button("Thử một tình huống", disabled=not role.strip(), key=prefix + "simulate", use_container_width=True):
            meta["task"] = "Trải nghiệm"
            return f"Cho mình thử một tình huống của hướng {role}, vừa sức học sinh. Đặt câu hỏi để mình trả lời trước khi góp ý."
    return None


def conversation_view(chat):
    for message in chat.messages:
        with st.chat_message(message["role"], avatar=":material/person:" if message["role"] == "user" else ":material/auto_awesome:"):
            context = message.get("context", {})
            if message["role"] == "user" and chat.feature == Feature.STUDY and context.get("grade"):
                st.caption(" · ".join(str(value) for value in [f"Lớp {context['grade']}", context.get("subject"), context.get("task")] if value))
            st.markdown(message["content"])
    if chat.feature == Feature.CAREER and any(m["role"] == "assistant" for m in chat.messages):
        text = "\n\n".join(("Bạn: " if m["role"] == "user" else "EduMind: ") + m["content"] for m in chat.messages)
        st.download_button("Tải nội dung & kế hoạch (.txt)", text, file_name="EduMind_dinh_huong.txt", mime="text/plain", icon=":material/download:", key=f"download_{chat.id}")


def queue_question(store, service, chat, text=None, retry=False):
    mode = AIMode(st.session_state.mode)
    if mode == AIMode.THINKING and not user_id():
        st.warning("Cần đăng nhập trước khi gửi bằng chế độ Tư duy.")
        return
    if not service.available:
        st.warning("AI chưa được cấu hình. Nội dung đang soạn vẫn được giữ.")
        return
    pending = st.session_state.get("pending_request")
    if pending and pending.get("chat_id") == chat.id:
        return
    if not retry:
        if chat.messages and chat.messages[-1]["role"] == "user":
            st.warning("Hãy thử trả lời lại câu hỏi gần nhất trước khi gửi thêm tin nhắn.")
            return
        if not text or not text.strip():
            return
        chat.add_question(text.strip())
        chat.messages[-1]["context"] = request_context(chat)
    elif not chat.messages or chat.messages[-1]["role"] != "user":
        return
    persist(store, chat)
    st.session_state.failure = None
    st.session_state.pending_request = {"chat_id": chat.id, "mode": mode.value}
    st.rerun()


def queue_image_question(store, service, chat, image_bytes, mime_type, daily_limit):
    if not user_id():
        st.warning("Đăng nhập để dùng chức năng giải bài bằng ảnh.")
        return
    if not service.available:
        st.warning("AI chưa được cấu hình. Ảnh chưa được gửi.")
        return
    pending = st.session_state.get("pending_request")
    if pending and pending.get("chat_id") == chat.id:
        return
    is_retry = bool(
        chat.messages
        and chat.messages[-1]["role"] == "user"
        and chat.messages[-1].get("kind") == "image"
    )
    if chat.messages and chat.messages[-1]["role"] == "user" and not is_retry:
        st.warning("Hãy nhận hoặc thử lại câu trả lời gần nhất trước khi gửi thêm nội dung.")
        return
    usage_date = datetime.now(LOCAL_TZ).date().isoformat()
    try:
        store.reserve_image_quota(user_id(), usage_date, daily_limit)
    except ImageQuotaExceeded as exc:
        st.error(str(exc))
        return
    if not is_retry:
        chat.add_question("Đã gửi ảnh bài tập")
        chat.messages[-1]["kind"] = "image"
        chat.messages[-1]["context"] = request_context(chat)
    persist(store, chat)
    st.session_state.failure = None
    st.session_state.pending_request = {
        "chat_id": chat.id,
        "mode": st.session_state.mode,
        "image_bytes": image_bytes,
        "image_mime_type": mime_type,
    }
    st.rerun()


def study_image_controls(store, service, chat):
    with st.expander("Giải bài tập qua ảnh", expanded=False):
        if not user_id():
            st.info("Đăng nhập để chụp/chọn ảnh. Hạn mức mặc định là 3 lượt mỗi ngày.")
            if st.button("Đăng nhập để giải bài bằng ảnh", key=f"image_login_{chat.id}", use_container_width=True):
                st.session_state.auth_reason = "Đăng nhập để dùng giải bài bằng ảnh với hạn mức 3 lượt mỗi ngày."
                st.session_state.active_dialog = ("auth", None)
            return
        try:
            daily_limit = image_daily_limit()
        except ValueError as exc:
            st.error(str(exc))
            return
        usage_date = datetime.now(LOCAL_TZ).date().isoformat()
        used, remaining = store.image_quota_status(user_id(), usage_date, daily_limit)
        st.caption(f"Hôm nay đã dùng {used}/{daily_limit} lượt · Còn {remaining} lượt.")
        st.caption("Mỗi lần gửi ảnh được tính một lượt, kể cả khi dịch vụ AI gặp lỗi. Ảnh không được lưu vào lịch sử.")
        if remaining <= 0:
            st.warning("Bạn đã dùng hết hạn mức hôm nay. Chức năng chọn/chụp ảnh sẽ mở lại vào ngày mai.")
            return

        revisions = st.session_state.image_picker_revisions
        revision = revisions.get(chat.id, 0)
        source = st.radio(
            "Nguồn ảnh",
            ["Chụp ảnh", "Chọn từ thư viện"],
            horizontal=True,
            key=f"image_source_{chat.id}",
            label_visibility="collapsed",
        )
        if source == "Chụp ảnh":
            uploaded = st.camera_input("Chụp bài tập", key=f"homework_camera_{chat.id}_{revision}")
        else:
            uploaded = st.file_uploader(
                "Chọn ảnh bài tập",
                type=["jpg", "jpeg", "png"],
                key=f"homework_upload_{chat.id}_{revision}",
                help="JPG/JPEG/PNG, tối đa 10 MB.",
            )

        image_bytes, mime_type = None, None
        if uploaded is not None:
            raw_bytes = uploaded.getvalue()
            fingerprint = hashlib.sha256(raw_bytes).digest()
            cached = st.session_state.image_previews.get(chat.id)
            if cached and cached[0] == fingerprint:
                image_bytes, mime_type = cached[1], cached[2]
            else:
                try:
                    image_bytes, mime_type = normalize_image_upload(uploaded)
                except ValueError as exc:
                    st.session_state.image_previews.pop(chat.id, None)
                    st.error(str(exc))
                else:
                    st.session_state.image_previews[chat.id] = (fingerprint, image_bytes, mime_type)
            if image_bytes:
                st.image(image_bytes, caption="Xem trước ảnh bài tập", use_container_width=True)

        clear_col, solve_col = st.columns([1, 2])
        if uploaded is not None and clear_col.button("Xóa / chọn ảnh khác", key=f"clear_image_{chat.id}", use_container_width=True):
            revisions[chat.id] = revision + 1
            st.session_state.image_previews.pop(chat.id, None)
            st.rerun()
        if solve_col.button(
            "Giải bài trong ảnh",
            key=f"solve_image_{chat.id}",
            type="primary",
            use_container_width=True,
            disabled=not image_bytes or not service.available,
        ):
            queue_image_question(store, service, chat, image_bytes, mime_type, daily_limit)


def waiting_indicator(chat):
    expression = wellbeing_expression(chat.metadata.get("mood")) if chat.feature == Feature.WELLBEING else "curious"
    eye = "M39 22q4-5 8 0M56 22q4-5 8 0" if expression == "happy" else "M40 22h7M57 22h7" if expression == "tired" else ""
    eyes = f'<path d="{eye}" fill="none" stroke="#243052" stroke-width="3" stroke-linecap="round"/>' if eye else '<circle cx="44" cy="22" r="4" fill="#243052"/><circle cx="60" cy="22" r="4" fill="#243052"/>'
    st.markdown(
        '<div class="thinking-bubble"><svg class="thinking-mini" viewBox="0 0 104 50" aria-hidden="true">'
        '<path fill="#6d5dfc" d="M30 12 24 2l13 7c8-5 22-5 30 0l13-7-6 11c5 5 7 11 6 18-1 13-12 18-28 18S25 44 24 31c-1-7 1-14 6-19Z"/>'
        f'<circle cx="42" cy="22" r="9" fill="white"/><circle cx="62" cy="22" r="9" fill="white"/>{eyes}'
        '<path fill="#ffb84c" d="m52 27 5 4-5 4-5-4 5-4Z"/></svg>'
        '<div><strong>AI đang suy nghĩ</strong><span class="thinking-dots"><i></i><i></i><i></i></span><div class="muted">Mindi đang chuẩn bị câu trả lời phù hợp.</div></div></div>',
        unsafe_allow_html=True,
    )


def process_pending_request(store, service, chat):
    pending = st.session_state.get("pending_request")
    if not pending or pending.get("chat_id") != chat.id:
        return
    if not chat.messages or chat.messages[-1]["role"] != "user":
        st.session_state.pending_request = None
        return
    mode = AIMode(pending.get("mode", AIMode.FAST.value))
    context = chat.messages[-1].get("context", request_context(chat))
    request = AIRequest(
        chat.feature,
        mode,
        chat.messages[-1]["content"],
        chat.messages[:-1],
        context,
        pending.get("image_bytes"),
        pending.get("image_mime_type"),
    )
    try:
        try:
            response = service.answer(request, user=st.session_state.user)
        except (AIUnavailable, LoginRequired) as exc:
            st.session_state.failure = {
                "chat_id": chat.id,
                "message": str(exc),
                "context": context,
                "kind": getattr(exc, "kind", None),
            }
        else:
            chat.messages.append({"role": "assistant", "content": response})
            chat.updated_at = now_iso()
            st.session_state.failure = None
            persist(store, chat)
            st.session_state.drafts.pop(chat.id, None)
            st.session_state.pop("pending_action", None)
    finally:
        if pending.get("image_bytes") is not None:
            pending.pop("image_bytes", None)
            pending.pop("image_mime_type", None)
            st.session_state.image_previews.pop(chat.id, None)
            revisions = st.session_state.image_picker_revisions
            revisions[chat.id] = revisions.get(chat.id, 0) + 1
    st.session_state.pending_request = None
    st.rerun()


def remember_draft(chat_id):
    chat = st.session_state.chats[chat_id]
    st.session_state.drafts[chat_id] = st.session_state.get(composer_key(chat), "")


def feature_page(store, service, feature):
    chat = ensure_chat(feature)
    header(feature)
    action = None
    pending = st.session_state.get("pending_request")
    is_pending = bool(pending and pending.get("chat_id") == chat.id)
    with st.container(key="feature-toolbar"):
        setup_col, mode_col, privacy_col = st.columns([1.35, 1.5, 1], vertical_alignment="center")
        with setup_col:
            if feature == Feature.WELLBEING:
                st.caption("🌿 Check-in riêng tư · Từng bước một")
            else:
                with st.popover("Thiết lập nội dung", icon=":material/tune:", use_container_width=True):
                    action = study_context(chat) if feature == Feature.STUDY else career_context(chat)
        with mode_col:
            mode_control(store)
        with privacy_col:
            with st.popover("Lưu & riêng tư", icon=":material/shield:", use_container_width=True):
                save_control(store, chat)
                if feature == Feature.WELLBEING and chat.messages:
                    if st.button("Xóa phiên đang mở", icon=":material/delete_sweep:", use_container_width=True, help="Nếu có bản đã lưu, thao tác xác nhận cũng xóa bản đó."):
                        st.session_state.active_dialog = ("delete", chat.id)
    if feature == Feature.WELLBEING:
        action = wellbeing_context(chat)
    with st.container(key="service_status"):
        if not service.available:
            st.info("AI chưa được cấu hình. Bạn vẫn có thể đăng nhập, thiết lập nội dung và xem lịch sử đã lưu.")
    if feature == Feature.STUDY:
        study_image_controls(store, service, chat)
    with st.container(key="conversation", height="stretch", border=False):
        conversation_view(chat)
        if is_pending:
            waiting_indicator(chat)
    failure = st.session_state.failure
    unanswered = bool(chat.messages and chat.messages[-1]["role"] == "user")
    with st.container(key="retry_panel"):
        if unanswered and not is_pending:
            is_image_question = chat.messages[-1].get("kind") == "image"
            fallback = (
                "Lượt giải ảnh đã được tính. Bạn có thể chọn lại ảnh và gửi lại nếu còn hạn mức."
                if is_image_question
                else "Câu hỏi gần nhất chưa có phản hồi. Bạn có thể thử lại."
            )
            st.warning(failure["message"] if failure and failure["chat_id"] == chat.id else fallback)
            if not is_image_question and st.button("Thử trả lời lại", key=f"retry_{chat.id}", disabled=not service.available):
                queue_question(store, service, chat, retry=True)
    with st.container(key="conversation_empty"):
        checkin_ready = feature != Feature.WELLBEING or chat.metadata.get("checkin_complete") or chat.messages
        if not chat.messages and checkin_ready:
            if feature in (Feature.WELLBEING, Feature.CAREER):
                if feature == Feature.WELLBEING:
                    pet_markup = contextual_mindi(wellbeing_expression(chat.metadata.get("mood")), "heart", "Mindi ở đây cùng bạn")
                    title = "Bạn có thể bắt đầu thật ngắn."
                    desc = "Mindi sẽ lắng nghe theo nhịp bạn thấy thoải mái."
                else:
                    pet_markup = career_pet(chat.metadata.get("stage"))
                    title = "Mỗi hướng đi bắt đầu từ một điều bạn tò mò."
                    desc = "Mở Thiết lập nội dung để hoàn thiện hồ sơ, hoặc đặt câu hỏi trực tiếp bên dưới."
                st.markdown(
                    f'<div class="contextual-card">'
                    f'<div class="contextual-pet-wrap">{pet_markup}</div>'
                    f'<div class="contextual-text-wrap">'
                    f'<div class="contextual-title">{html.escape(title)}</div>'
                    f'<div class="contextual-desc">{html.escape(desc)}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                with st.container(border=True, key="study-empty"):
                    st.markdown("**Bạn muốn bắt đầu từ đâu?**")
                    st.write("Gửi đề bài hoặc điều bạn chưa hiểu.")
    submitted, draft = False, ""
    if checkin_ready:
        draft_key = composer_key(chat)
        if draft_key not in st.session_state:
            st.session_state[draft_key] = st.session_state.drafts.get(chat.id, "")
        with st.container(border=True, key="composer"):
            message_col, send_col = st.columns([9, 1], vertical_alignment="center")
            with message_col:
                draft = st.text_area("Tin nhắn của bạn", key=draft_key, on_change=remember_draft, args=(chat.id,), placeholder="Nhắn cho EduMind…", height=68, max_chars=12000, label_visibility="collapsed", disabled=is_pending)
            with send_col:
                submitted = st.button("Gửi", key=f"send_{chat.id}", type="primary", icon=":material/arrow_upward:", use_container_width=True, disabled=not service.available or is_pending)
            st.caption(f"EduMind có thể mắc lỗi · Chế độ {MODE_LABELS[AIMode(st.session_state.mode)]}")
    if action:
        if service.available and not (st.session_state.mode == AIMode.THINKING.value and not user_id()):
            queue_question(store, service, chat, action)
        else:
            st.session_state["pending_action"] = {"chat_id": chat.id, "text": action}
            st.info("Yêu cầu đã được giữ. Đăng nhập hoặc chọn Nhanh, sau đó nhấn tiếp tục bên dưới.")
    pending = st.session_state.get("pending_action")
    if pending and pending["chat_id"] == chat.id:
        st.caption(pending["text"])
        if st.button("Tiếp tục yêu cầu đã chọn", disabled=not service.available):
            queue_question(store, service, chat, pending["text"])
    if submitted:
        if unanswered:
            st.warning("Hãy thử trả lời lại câu hỏi gần nhất trước khi gửi thêm tin nhắn.")
        else:
            queue_question(store, service, chat, draft)
    if is_pending:
        process_pending_request(store, service, chat)


def setting(name, default=None):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


def model_settings(list_name, single_name, default):
    configured = setting(list_name)
    models = [item.strip() for item in configured.split(",")] if configured else [setting(single_name, default)]
    # Keep the verified 2.5 model as the last-resort fallback.
    models.append("gemini-2.5-flash")
    return list(dict.fromkeys(model for model in models if model))


def mobile_orientation_banner():
    if st.session_state.get("mobile_rotate_dismissed"):
        return
    with st.container(key="mobile-orient-notice"):
        st.markdown(
            '<div class="orient-banner-inner">'
            '<div class="orient-badge">📱 ➔ 🔄 Gợi ý trải nghiệm</div>'
            '<div class="orient-text-body">'
            '<strong>Xoay ngang màn hình để học tập tốt hơn</strong>'
            '<p>EduMind AI hiển thị tối ưu và đầy đủ không gian nhất khi bạn xoay ngang màn hình điện thoại.</p>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2, gap="small")
        with col1:
            if st.button("Đồng ý", key="accept_rotate_screen", type="primary", use_container_width=True):
                st.session_state.mobile_rotate_dismissed = True
                st.toast("Hãy xoay ngang điện thoại để có trải nghiệm học tập tốt nhất! 🔄")
                st.rerun()
        with col2:
            if st.button("Từ chối", key="dismiss_rotate_screen", use_container_width=True):
                st.session_state.mobile_rotate_dismissed = True
                st.rerun()


def run():
    st.set_page_config(page_title="EduMind AI · Học tập & trưởng thành", page_icon="🎓", layout="wide", initial_sidebar_state="auto")
    load_dotenv(ROOT / ".env")
    store = Store(os.getenv("EDUMIND_DB_PATH", str(ROOT / "edumind_history.db")))
    store.migrate()
    initialize()
    st.markdown(CSS, unsafe_allow_html=True)
    keys = [setting("GEMINI_API_KEY"), *[setting(f"GEMINI_API_KEY_{i}") for i in range(1, 4)]]
    fast_models = model_settings("GEMINI_FAST_MODELS", "GEMINI_FAST_MODEL", "gemini-3.1-flash-lite")
    thinking_models = model_settings("GEMINI_THINKING_MODELS", "GEMINI_THINKING_MODEL", "gemini-3.6-flash")
    service = AIService(keys, fast_models=fast_models, thinking_models=thinking_models)
    refresh_ai_health(service)
    sidebar(store, service)
    mobile_orientation_banner()
    if st.session_state.nav == "overview":
        overview(store)
    elif st.session_state.nav == TOOLS_NAV:
        educational_tools_page()
    else:
        feature_page(store, service, Feature(st.session_state.nav))
    dialog = st.session_state.get("active_dialog")
    if dialog:
        kind, chat_id = dialog
        if kind == "auth":
            auth_dialog(store)
        elif kind == "rename":
            rename_dialog(store, chat_id)
        elif kind == "delete":
            delete_dialog(store, chat_id)
