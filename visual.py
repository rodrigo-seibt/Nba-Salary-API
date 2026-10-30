# ============================================================
# visual.py
# Elementos visuais do dashboard: quadra de fundo, logo da NBA,
# logos dos times e CSS.
#
# Logos: o app procura primeiro um arquivo local em assets/
# (assets/nba_logo.svg|png e assets/times/BOS.svg|png ...) e, se não
# achar, tenta baixar do CDN da NBA. Se nada funcionar, o logo é
# omitido e o resto do dashboard continua normal.
# ============================================================

import base64
import html
import time
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st
from nba_api.stats.static import teams as nba_teams

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

NBA_LOGO_URL = "https://cdn.nba.com/logos/leagues/logo-nba.svg"
TIME_LOGO_URL = "https://cdn.nba.com/logos/nba/{team_id}/global/L/logo.svg"

# Siglas do Basketball-Reference (usadas no dataset) -> siglas da NBA
SIGLAS_NBA = {"BRK": "BKN", "CHO": "CHA", "PHO": "PHX"}

AZUL = "#1D428A"

# O SVG do logo da NBA no CDN tem margens transparentes grandes (o desenho ocupa ~40% da imagem).
# Este fator amplia o desenho para ele aparecer maior. Só vale para o logo baixado do CDN;
# um logo próprio em assets/ é exibido sem ampliação.
ESCALA_LOGO_NBA = 2.0
VERMELHO = "#C8102E"

_MIME = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".webp": "image/webp"}
_FALHAS: dict = {}          # url -> instante da última falha (evita travar a tela)
_ESPERA_APOS_FALHA = 600    # segundos


# ============================================================
# Imagens (local primeiro, CDN depois)
# ============================================================
def _data_uri(conteudo: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(conteudo).decode()}"


def _achar_local(nome_base: str):
    for ext in _MIME:
        caminho = ASSETS_DIR / f"{nome_base}{ext}"
        if caminho.exists():
            return caminho
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def _baixar(url: str):
    """Só guarda em cache quando dá certo (exceções não são cacheadas)."""
    resp = requests.get(url, timeout=4, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    mime = resp.headers.get("Content-Type", "").split(";")[0].strip()
    if not mime.startswith("image/"):
        mime = _MIME.get(Path(url).suffix.lower(), "image/png")
    return resp.content, mime


def imagem_uri(nome_base: str, url: str | None):
    """Data URI da imagem: arquivo em assets/ -> CDN -> None."""
    local = _achar_local(nome_base)
    if local:
        return _data_uri(local.read_bytes(), _MIME[local.suffix.lower()])

    if url and time.time() - _FALHAS.get(url, 0) > _ESPERA_APOS_FALHA:
        try:
            conteudo, mime = _baixar(url)
            return _data_uri(conteudo, mime)
        except Exception:
            _FALHAS[url] = time.time()
    return None


@st.cache_data
def _ids_times():
    return {t["abbreviation"]: t["id"] for t in nba_teams.get_teams()}


def logo_time_uri(sigla: str):
    sigla_nba = SIGLAS_NBA.get(sigla, sigla)
    team_id = _ids_times().get(sigla_nba)
    if team_id is None:
        return None
    return imagem_uri(f"times/{sigla_nba}", TIME_LOGO_URL.format(team_id=team_id))


# ============================================================
# Quadra de fundo (SVG desenhado aqui, sem imagem externa)
# ============================================================
def quadra_svg() -> str:
    linha = "#F5F0E6"
    meia_quadra = f"""
      <rect x="0" y="170" width="190" height="160" fill="{AZUL}" fill-opacity="0.85"/>
      <rect x="0" y="170" width="190" height="160" fill="none" stroke="{linha}" stroke-width="4"/>
      <path d="M190,190 A60,60 0 0 1 190,310" fill="none" stroke="{linha}" stroke-width="4"/>
      <path d="M190,190 A60,60 0 0 0 190,310" fill="none" stroke="{linha}" stroke-width="4" stroke-dasharray="10 10"/>
      <path d="M52.5,210 A40,40 0 0 1 52.5,290" fill="none" stroke="{linha}" stroke-width="4"/>
      <path d="M0,30 H142 A237.5,237.5 0 0 1 142,470 H0" fill="none" stroke="{linha}" stroke-width="4"/>
      <line x1="40" y1="220" x2="40" y2="280" stroke="{linha}" stroke-width="6"/>
      <circle cx="52.5" cy="250" r="7.5" fill="none" stroke="{VERMELHO}" stroke-width="4"/>
    """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 940 500" preserveAspectRatio="xMidYMid slice">
  <defs>
    <linearGradient id="madeira" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#D9A868"/><stop offset="0.5" stop-color="#CF9A58"/><stop offset="1" stop-color="#D9A868"/>
    </linearGradient>
    <pattern id="tabuas" width="940" height="20" patternUnits="userSpaceOnUse">
      <rect width="940" height="20" fill="url(#madeira)"/>
      <rect y="19" width="940" height="1" fill="#000" fill-opacity="0.10"/>
    </pattern>
  </defs>
  <rect width="940" height="500" fill="url(#tabuas)"/>
  <line x1="470" y1="0" x2="470" y2="500" stroke="{linha}" stroke-width="4"/>
  <circle cx="470" cy="250" r="60" fill="none" stroke="{linha}" stroke-width="4"/>
  <circle cx="470" cy="250" r="20" fill="{AZUL}" fill-opacity="0.85" stroke="{linha}" stroke-width="4"/>
  <g>{meia_quadra}</g>
  <g transform="translate(940,0) scale(-1,1)">{meia_quadra}</g>
  <rect x="3" y="3" width="934" height="494" fill="none" stroke="{linha}" stroke-width="6"/>
</svg>"""


@st.cache_data
def _quadra_uri() -> str:
    return _data_uri(quadra_svg().encode(), "image/svg+xml")


# ============================================================
# Paletas (claro / escuro)
# ============================================================
def _paleta(escuro: bool) -> dict:
    if escuro:
        return dict(
            texto="#E8ECF4", suave="#9AA6BA", card="rgba(18, 23, 34, 0.93)", card_solido="#171D2B", logo_fundo="#FFFFFF",
            borda="#2C3547", campo="#222A3A", sidebar="#0F1420",
            veu="rgba(6, 10, 20, 0.62)", metrica="#1B2230", hover="#2A3345",
            grade="#2C3547",
        )
    return dict(
        texto="#1B1B1B", suave="#5B6472", card="rgba(255, 255, 255, 0.94)", card_solido="#FFFFFF", logo_fundo="transparent",
        borda="#E3E8F0", campo="#FFFFFF", sidebar="#F7F8FA",
        veu="rgba(255, 255, 255, 0.0)", metrica="#FFFFFF", hover="#EEF2F8",
        grade="#E3E8F0",
    )


# ============================================================
# CSS
# ============================================================
def css(escuro: bool = False) -> str:
    p = _paleta(escuro)
    return f"""
<style>
/* ---------- Fundo: quadra no painel principal ---------- */
.stApp {{
    background-image: linear-gradient({p['veu']}, {p['veu']}), url("{_quadra_uri()}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    color: {p['texto']};
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stHeader"] *, [data-testid="stToolbar"] * {{ color: {p['texto']} !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{
    padding-top: 3.2rem; max-width: 1400px;
}}

/* ---------- Sidebar (sólida: a quadra aparece só no painel principal) ---------- */
[data-testid="stSidebar"] {{
    background: {p['sidebar']};
    border-right: 4px solid {VERMELHO};
}}
[data-testid="stSidebar"] img {{ border-radius: 12px; }}
[data-testid="stSidebar"] hr {{ border-color: {p['borda']}; }}

/* ---------- Cartões sobre a quadra ---------- */
.painel, [class*="st-key-card_"] {{
    background: {p['card']};
    border: 1px solid {p['borda']};
    border-radius: 16px;
    padding: 16px 22px;
    margin-bottom: 14px;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.28);
}}

/* ---------- Textos ---------- */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp label, .stApp li,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] * {{
    color: {p['texto']};
}}
[data-testid="stCaptionContainer"] * {{ color: {p['suave']} !important; }}

/* ---------- Métricas ---------- */
[data-testid="stMetric"] {{
    background: {p['metrica']};
    border: 1px solid {p['borda']};
    border-left: 5px solid {AZUL};
    border-radius: 12px;
    padding: 10px 14px;
}}
[data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] * {{ color: {p['texto']} !important; }}

/* ---------- Campos (Streamlit atual: React Aria; seletores BaseWeb mantidos p/ versões antigas) ---------- */
[data-testid="stNumberInputContainer"], [data-testid="stSelectbox"] [role="group"],
[data-baseweb="input"], [data-baseweb="input"] > div, [data-baseweb="base-input"], [data-baseweb="select"] > div {{
    background-color: {p['campo']} !important;
    border-color: {p['borda']} !important;
}}
input {{ color: {p['texto']} !important; -webkit-text-fill-color: {p['texto']} !important; }}
[data-testid="stSelectbox"] button, [data-baseweb="select"] svg {{ color: {p['texto']} !important; fill: {p['texto']} !important; }}
[data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"],
[data-testid="stNumberInput"] button {{ background-color: {p['campo']} !important; color: {p['texto']} !important; }}
[data-testid="stNumberInput"] button svg {{ fill: {p['texto']} !important; }}
.react-aria-Popover, [role="listbox"], [role="option"], [data-baseweb="popover"] *, [data-baseweb="menu"] {{
    background-color: {p['campo']} !important; color: {p['texto']} !important;
}}
[role="option"]:hover, [role="option"][data-focused], [role="option"][aria-selected="true"] {{
    background-color: {p['hover']} !important;
}}
[data-testid="stForm"] {{ border-color: {p['borda']} !important; background: transparent; }}

/* ---------- Botões primários ---------- */
[data-testid^="stBaseButton-primary"], [data-testid^="stBaseButton-primary"] * {{ color: #FFFFFF !important; }}

/* ---------- Alertas (st.success / info / warning / error) ---------- */
[data-testid="stAlertContainer"] {{
    background-color: {p['card_solido']} !important;
    border: 1px solid {p['borda']}; border-left-width: 6px;
}}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {{ border-left-color: #21C354; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {{ border-left-color: #1C83E1; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {{ border-left-color: #FACA2B; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{ border-left-color: #FF4B4B; }}

/* ---------- Métricas do cartão de estatísticas: sem corte com "…" ---------- */
.st-key-card_stats [data-testid="stMetric"] {{ padding: 10px 12px; }}
.st-key-card_stats [data-testid="stMetricValue"], .st-key-card_stats [data-testid="stMetricValue"] * {{
    font-size: 1.8rem !important; overflow: visible !important; text-overflow: clip !important; white-space: nowrap !important;
}}

/* ---------- Cabeçalho da página ---------- */
.topo {{ display: flex; align-items: center; gap: 22px; border-left: 8px solid {VERMELHO}; }}
.topo-logo-box {{
    display: flex; align-items: center; flex-shrink: 0; padding: 10px 18px; border-radius: 14px;
    background: linear-gradient(135deg, #0B1D45, {AZUL}); border-bottom: 6px solid {VERMELHO};
}}
.topo-logo {{ height: 78px; }}
.topo-logo-box.recorte {{ width: 160px; height: 96px; padding: 0; overflow: hidden; justify-content: center; box-sizing: border-box; }}
.topo-logo-box.recorte .topo-logo {{ transform: scale({ESCALA_LOGO_NBA}); }}
.selo-nba {{
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    height: 80px; width: 80px; border-radius: 14px; background: {AZUL};
    color: #fff; font-weight: 900; font-size: 1.6rem; letter-spacing: 1px;
    border-bottom: 8px solid {VERMELHO};
}}
.topo-titulo {{ font-size: 2.3rem; font-weight: 800; color: {AZUL if not escuro else '#7FA6F0'}; line-height: 1.12; }}
.topo-sub {{ color: {p['suave']}; font-size: 1rem; margin-top: 2px; }}

/* ---------- Jogador ---------- */
.jogador-nome {{ font-size: 2rem; font-weight: 800; color: {AZUL if not escuro else '#7FA6F0'}; line-height: 1.1; }}
.jogador-info {{ color: {p['suave']}; font-size: 0.95rem; margin-top: 4px; }}

/* ---------- Logo do time na sidebar ---------- */
.side-logos {{ display: flex; justify-content: center; align-items: center; gap: 12px; margin: 6px 0 18px 0; }}
.side-logos img {{ height: 165px; max-width: 100%; min-width: 0; flex: 0 1 auto; object-fit: contain; box-sizing: border-box; padding: 8px; background: {p['logo_fundo']}; border-radius: 18px !important; }}
.selo-time {{
    display: flex; align-items: center; justify-content: center; height: 100px; min-width: 100px;
    padding: 0 14px; border-radius: 50%; background: {AZUL}; color: #fff;
    font-weight: 900; font-size: 1.5rem; border-bottom: 6px solid {VERMELHO};
}}
</style>
"""


# ============================================================
# Blocos HTML
# ============================================================
def cabecalho(titulo: str, subtitulo: str) -> str:
    """Logo da NBA (no lugar da bola) + título."""
    uri = imagem_uri("nba_logo", NBA_LOGO_URL)
    recorte = "" if _achar_local("nba_logo") else " recorte"   # logo do CDN: amplia e recorta as margens
    logo = (f'<div class="topo-logo-box{recorte}"><img class="topo-logo" src="{uri}" alt="NBA"></div>'
            if uri else '<div class="selo-nba">NBA</div>')
    return (
        f'<div class="painel topo">{logo}<div>'
        f'<div class="topo-titulo">{html.escape(titulo)}</div>'
        f'<div class="topo-sub">{html.escape(subtitulo)}</div>'
        "</div></div>"
    )


def logo_time_html(time: str) -> str:
    """Logo(s) grande(s) do(s) time(s) do jogador, para o topo da sidebar."""
    siglas = [s.strip() for s in str(time).split("/") if s.strip() and s.strip() != "—"]
    itens = ""
    for sigla in siglas:
        uri = logo_time_uri(sigla)
        if uri:
            itens += f'<img src="{uri}" alt="{html.escape(sigla)}" title="{html.escape(sigla)}">'
        else:
            itens += f'<div class="selo-time">{html.escape(sigla)}</div>'
    return f'<div class="side-logos">{itens}</div>' if itens else ""


def jogador_html(nome: str, posicao: str, time: str) -> str:
    return (
        '<div class="painel">'
        f'<div class="jogador-nome">{html.escape(nome)}</div>'
        f'<div class="jogador-info">Posição: {html.escape(posicao)} • Time: {html.escape(str(time))}</div>'
        "</div>"
    )


# ============================================================
# Gráfico real vs previsto (cores fixas por tema)
# ============================================================
def grafico_comparativo(real: float, previsto: float, escuro: bool = False):
    p = _paleta(escuro)
    dados = pd.DataFrame({"Tipo": ["Real", "Previsto"], "Salário": [real, previsto]})
    base = alt.Chart(dados).encode(
        x=alt.X("Tipo:N", sort=None, axis=alt.Axis(labelAngle=0, title=None, labelFontSize=14)),
        y=alt.Y("Salário:Q", axis=alt.Axis(format="$~s", title=None)),
    )
    barras = base.mark_bar(size=90, cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
        color=alt.Color("Tipo:N", legend=None,
                        scale=alt.Scale(domain=["Real", "Previsto"], range=[AZUL, VERMELHO]))
    )
    rotulos = base.mark_text(dy=-10, fontSize=15, fontWeight="bold", color=p["texto"]).encode(
        text=alt.Text("Salário:Q", format="$.3~s")
    )
    grafico = (
        (barras + rotulos)
        .properties(height=320, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=p["texto"], domainColor=p["grade"], gridColor=p["grade"], tickColor=p["grade"])
    )
    st.altair_chart(grafico, use_container_width=True, theme=None)
