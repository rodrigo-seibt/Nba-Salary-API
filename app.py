# ============================================================
# app.py
# Dashboard interativo NBA Salary Predictor (Streamlit)
#
# Para rodar (no terminal, na pasta do projeto):
#   streamlit run app.py
#
# A API FastAPI deve estar rodando em paralelo:
#   uvicorn main:app --reload
# ============================================================

import os
import unicodedata
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from nba_api.stats.static import players as nba_players

import visual  # quadra de fundo, logos e CSS (visual.py)

# ============================================================
# Configuração da página
# ============================================================
st.set_page_config(page_title="NBA Salary Predictor", page_icon="🏀", layout="wide")

# Modo escuro: começa pelo parâmetro da URL (?tema=escuro) e é controlado pelo botão da sidebar
if "escuro" not in st.session_state:
    st.session_state["escuro"] = st.query_params.get("tema") == "escuro"
escuro = st.session_state["escuro"]
st.markdown(visual.css(escuro), unsafe_allow_html=True)


def salvar_tema():
    """Guarda o tema na URL para sobreviver ao recarregar a página."""
    st.query_params["tema"] = "escuro" if st.session_state["escuro"] else "claro"

# ============================================================
# Constantes (podem ser sobrescritas por variáveis de ambiente)
# ============================================================
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = os.getenv("NBA_CSV", str(BASE_DIR / "data" / "nba_dashboard.csv"))  # gerado por preparar_dados.py
FOTO_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

# AJUSTE: nomes das colunas no seu CSV
COL_NOME = "Player Name"
COL_SALARIO = "Salary"
COL_POSICAO = "Position"
COL_TIME = "Team"
COL_ID = "PLAYER_ID"  # criada pelo preparar_dados.py

POSICOES = ["PG", "SG", "SF", "PF", "C"]
TIERS = {
    1: "Tier 1 — Menor mercado",
    2: "Tier 2 — Mercado médio",
    3: "Tier 3 — Grande mercado",
}


# ============================================================
# Funções auxiliares
# ============================================================
def normalizar(texto: str) -> str:
    """Remove acentos e padroniza caixa (Jokić -> jokic) para casar nomes."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def para_numero(valor):
    """Converte '$40,000,000' ou 40000000 em float. Retorna None se não der."""
    try:
        return float(str(valor).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


@st.cache_data
def _ler_csv(caminho: str, modificado_em: float):
    # modificado_em faz parte da chave do cache: se o arquivo mudar, o cache é refeito
    return pd.read_csv(caminho)


def carregar_csv():
    """Dataset 2022-23 (estatísticas e salário real). None se não existir."""
    if not os.path.exists(CSV_PATH):
        return None  # não é cacheado: ao criar o arquivo, o app passa a enxergá-lo
    return _ler_csv(CSV_PATH, os.path.getmtime(CSV_PATH))


@st.cache_data
def carregar_ids():
    """
    IDs dos jogadores via lista embutida na nba_api.
    Não faz requisição de rede, então não sofre timeout do stats.nba.com.
    """
    return {normalizar(p["full_name"]): p["id"] for p in nba_players.get_players()}


@st.cache_data
def nomes_ativos():
    return sorted(p["full_name"] for p in nba_players.get_active_players())


@st.cache_data(ttl=10)
def verificar_api() -> bool:
    try:
        return requests.get(f"{API_URL}/v1/health", timeout=3).status_code == 200
    except requests.RequestException:
        return False


def prever_salario(dados: dict):
    """Retorna (resultado, erro). Um dos dois é sempre None."""
    try:
        resp = requests.post(f"{API_URL}/v1/predict", json=dados, timeout=30)
        resp.raise_for_status()
        return resp.json(), None
    except requests.HTTPError as e:
        return None, f"A API respondeu {e.response.status_code}: {e.response.text}"
    except requests.RequestException as e:
        return None, f"Falha de conexão com a API: {e}"


def pegar(linha, coluna, padrao):
    """Valor da coluna no CSV, ou o padrão se não existir / for nulo."""
    if linha is not None and coluna in linha.index and pd.notna(linha[coluna]):
        return linha[coluna]
    return padrao


# ============================================================
# Cabeçalho e verificação da API
# ============================================================
st.markdown(
    visual.cabecalho("NBA Salary Predictor Dashboard", "Previsão de salários com Rede Neural"),
    unsafe_allow_html=True,
)

if not verificar_api():
    st.error("❌ API FastAPI offline — rode: uvicorn main:app --reload")
    st.stop()
st.success("✅ API FastAPI online e modelo carregado!")

df = carregar_csv()
if df is None:
    st.warning(
        f"CSV não encontrado em '{CSV_PATH}'. Modo manual: sem estatísticas "
        "pré-preenchidas e sem comparativo com o salário real."
    )

# ============================================================
# Sidebar — foto e seleção do jogador
# ============================================================
with st.sidebar:
    slot_logo = st.container()  # preenchido depois que o jogador é escolhido

    nomes = sorted(df[COL_NOME].dropna().unique()) if df is not None else nomes_ativos()
    padrao = nomes.index("Stephen Curry") if "Stephen Curry" in nomes else 0
    nome = st.selectbox("Selecionar jogador", nomes, index=padrao)

    linha = None
    if df is not None:
        linha = df[df[COL_NOME] == nome].iloc[0]

    slot_logo.markdown(visual.logo_time_html(pegar(linha, COL_TIME, "—")), unsafe_allow_html=True)

    # 1º tenta o ID do CSV; se não houver, usa a lista embutida da nba_api
    player_id = para_numero(pegar(linha, COL_ID, None))
    if player_id is None:
        player_id = carregar_ids().get(normalizar(nome))

    if player_id:
        st.image(FOTO_URL.format(player_id=int(player_id)), caption=nome,
                 use_container_width=True)
    else:
        st.info("Foto não disponível")

    st.divider()
    st.toggle("🌙 Modo escuro", key="escuro", on_change=salvar_tema)


def campo(label, coluna, padrao, minimo, maximo, passo=None, formato=None):
    """
    number_input pré-preenchido com o valor do CSV.
    - converte o tipo (int/float) para bater com min/max (senão o Streamlit dá erro)
    - limita o valor ao intervalo permitido
    - key por jogador, para o campo atualizar ao trocar de jogador
    """
    bruto = pegar(linha, coluna, padrao)
    valor = int(bruto) if isinstance(padrao, int) else float(bruto)
    valor = max(minimo, min(maximo, valor))
    return st.number_input(
        label, min_value=minimo, max_value=maximo, value=valor,
        step=passo, format=formato, key=f"{coluna}_{nome}",
    )


# ============================================================
# Painel principal — nome, posição e estatísticas
# ============================================================
pos_csv = str(pegar(linha, COL_POSICAO, "PG")).split("-")[0].strip()
st.markdown(
    visual.jogador_html(nome, pos_csv, pegar(linha, COL_TIME, "—")),
    unsafe_allow_html=True,
)

with st.container(key="card_stats"):
    st.subheader("📊 Estatísticas reais (temporada 2022-23)")
    ESTATS = [  # (rótulo, coluna, formatação): todas com 1 casa decimal
        ("Pontos", "PTS", lambda v: f"{v:.1f}"),
        ("Rebotes", "TRB", lambda v: f"{v:.1f}"),
        ("Assistências", "AST", lambda v: f"{v:.1f}"),
        ("Minutos", "MP", lambda v: f"{v:.1f}"),
        ("PER", "PER", lambda v: f"{v:.1f}"),
        ("TS%", "TS%", lambda v: f"{v:.3f}"),   # proporção (0 a 1), como no dataset
        ("USG%", "USG%", lambda v: f"{v:.1f}%"),
        ("WS", "WS", lambda v: f"{v:.1f}"),
    ]
    for coluna_m, (rotulo, col, formatar) in zip(st.columns(len(ESTATS)), ESTATS):
        valor_bruto = pegar(linha, col, None)
        coluna_m.metric(rotulo, "—" if valor_bruto is None else formatar(valor_bruto))

with st.container(key="card_modelo"):
    st.markdown("##### Entradas do modelo")
    st.caption("Os valores iniciais são as estatísticas reais da temporada. Edite para simular cenários. "
               "TS%, 3PAr e FTr são proporções (0 a 1); as demais porcentagens estão em 0 a 100.")
    with st.form("form_jogador"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Perfil**")
            position = st.selectbox(
                "Posição", POSICOES,
                index=POSICOES.index(pos_csv) if pos_csv in POSICOES else 0,
                key=f"pos_{nome}",
            )
            age = campo("Idade", "Age", 25, 18, 45)
            gp = campo("Jogos (GP)", "GP", 60, 1, 85)
            gs = campo("Titularidades (GS)", "GS", 30, 0, 85)
            tier_padrao = int(pegar(linha, "tier_time", 2))
            tier_time = st.selectbox(
                "Tier do time", list(TIERS), format_func=TIERS.get,
                index=list(TIERS).index(tier_padrao) if tier_padrao in TIERS else 1,
                key=f"tier_{nome}",
            )

        with col2:
            st.markdown("**Estatísticas básicas**")
            pts = campo("Pontos (PTS)", "PTS", 15.0, 0.0, 40.0, 0.1)
            ast = campo("Assistências (AST)", "AST", 4.0, 0.0, 15.0, 0.1)
            trb = campo("Rebotes (TRB)", "TRB", 5.0, 0.0, 20.0, 0.1)
            stl = campo("Roubos (STL)", "STL", 1.0, 0.0, 5.0, 0.1)
            blk = campo("Bloqueios (BLK)", "BLK", 0.5, 0.0, 5.0, 0.1)
            pf = campo("Faltas (PF)", "PF", 2.0, 0.0, 6.0, 0.1)
            p3 = campo("Cestas 3pts (3P)", "3P", 1.5, 0.0, 7.0, 0.1)

        with col3:
            st.markdown("**Métricas avançadas**")
            per = campo("PER", "PER", 15.0, -25.0, 70.0, 0.1)
            ts_pct = campo("TS%", "TS%", 0.55, 0.0, 1.1, 0.01, "%.3f")
            p3ar = campo("3PAr", "3PAr", 0.35, 0.0, 1.0, 0.01)
            ftr = campo("FTr", "FTr", 0.25, 0.0, 2.0, 0.01)
            orb_pct = campo("ORB%", "ORB%", 3.0, 0.0, 30.0, 0.1)
            trb_pct = campo("TRB%", "TRB%", 10.0, 0.0, 30.0, 0.1)
            stl_pct = campo("STL%", "STL%", 1.5, 0.0, 25.0, 0.1)
            blk_pct = campo("BLK%", "BLK%", 1.0, 0.0, 45.0, 0.1)
            tov_pct = campo("TOV%", "TOV%", 12.0, 0.0, 100.0, 0.1)
            usg_pct = campo("USG%", "USG%", 20.0, 0.0, 55.0, 0.1)
            ws = campo("Win Shares (WS)", "WS", 3.0, -5.0, 20.0, 0.1)

        enviado = st.form_submit_button("🔮 Prever salário", type="primary", use_container_width=True)

# ============================================================
# Predição e comparativo real vs previsto
# ============================================================
if enviado:
    # Mesma fórmula usada no treino. Ideal: calcular isso dentro da API.
    eficiencia = pts + ast + trb + stl + blk

    dados = {
        "Position": position, "Age": age, "GP": gp, "GS": gs, "3P": p3,
        "TRB": trb, "AST": ast, "STL": stl, "BLK": blk, "PF": pf, "PTS": pts,
        "PER": per, "TS%": ts_pct, "3PAr": p3ar, "FTr": ftr, "ORB%": orb_pct,
        "TRB%": trb_pct, "STL%": stl_pct, "BLK%": blk_pct, "TOV%": tov_pct,
        "USG%": usg_pct, "WS": ws, "tier_time": tier_time, "eficiencia": eficiencia,
    }

    with st.spinner("Calculando previsão..."):
        resultado, erro = prever_salario(dados)

    if erro:
        st.error(erro)
        st.stop()

    with st.container(key="card_resultado"):
        st.subheader("💰 Salário previsto")

        real = para_numero(pegar(linha, COL_SALARIO, None))
        previsto = resultado.get("salario_previsto")  # AJUSTE: nome do campo numérico na API

        c1, c2, c3 = st.columns(3)
        c1.metric("Salário previsto", resultado["salario_formatado"])
        if real is not None:
            c2.metric("Salário real", f"US$ {real:,.0f}")
        if real is not None and previsto is not None:
            c3.metric("Diferença (previsto − real)", f"US$ {previsto - real:,.0f}")

            st.subheader("📊 Comparativo real vs previsto")
            visual.grafico_comparativo(real, previsto, escuro)
        elif real is not None:
            st.info("A API não retornou o salário previsto em formato numérico; "
                    "adicione esse campo na resposta para habilitar o gráfico comparativo.")

        conjunto = pegar(linha, "conjunto", None)
        if conjunto == "teste":
            st.info("Este jogador estava no **conjunto de teste**: o modelo não o viu no treino, "
                    "então o comparativo é uma avaliação fora da amostra.")
        elif conjunto == "treino":
            st.info("Este jogador estava no **conjunto de treino**: o modelo já viu o salário real dele, "
                    "então o comparativo tende a parecer melhor do que seria com jogadores novos.")

        st.caption(f"Modelo: {resultado['modelo']} • Versão: v{str(resultado['versao']).lstrip('vV')}")
