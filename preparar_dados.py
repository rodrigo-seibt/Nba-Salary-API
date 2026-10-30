# ============================================================
# preparar_dados.py
# Gera o CSV usado pelo dashboard (data/nba_dashboard.csv)
#
# Parte do CSV ORIGINAL (o mesmo usado no notebook da Rede Neural)
# e reproduz as mesmas etapas do notebook:
#   - Position: primeira posição (PG-SG -> PG)
#   - tier_time: tier do time pelo salário médio (p33 / p66)
#   - eficiencia: PTS + AST + TRB + STL + BLK
# Acrescenta:
#   - PLAYER_ID (nba_api, offline) para a foto
#   - conjunto: "treino" ou "teste" (mesmo split 80/20, random_state=42)
#
# Para rodar (na pasta do projeto):
#   python preparar_dados.py
# ============================================================

import os
import unicodedata

import numpy as np
import pandas as pd
from nba_api.stats.static import players
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE_DIR, "data", "nba_2022-23_all_stats_with_salary.csv")
SAIDA = os.path.join(BASE_DIR, "data", "nba_dashboard.csv")

# IDs corrigidos à mão (nome no dataset diferente do nome na nba_api)
OVERRIDES = {"Jeenathan Williams": 1631466}  # listado como "Nate Williams"

# Features numéricas enviadas ao modelo (Position é tratada à parte)
FEATURES = [
    "Age", "GP", "GS", "3P", "TRB", "AST", "STL", "BLK", "PF", "PTS", "PER",
    "TS%", "3PAr", "FTr", "ORB%", "TRB%", "STL%", "BLK%", "TOV%", "USG%", "WS",
]

SUFIXOS = {"jr", "sr", "ii", "iii", "iv"}


def normalizar(texto: str) -> str:
    """Remove acentos, pontuação e sufixos (Jr., III) para casar nomes."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = t.lower().replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(p for p in t.split() if p not in SUFIXOS)


raw = pd.read_csv(RAW).drop(columns=["Unnamed: 0"], errors="ignore")

# ------------------------------------------------------------
# 1) Position: primeira posição informada
# ------------------------------------------------------------
raw["Position"] = raw["Position"].str.split("-").str[0].str.strip()

# ------------------------------------------------------------
# 2) NaN: mediana, como o SimpleImputer do pipeline de treino
# ------------------------------------------------------------
for f in FEATURES:
    raw[f] = raw[f].fillna(raw[f].median())

# ------------------------------------------------------------
# 3) eficiencia e tier_time (mesma lógica do notebook)
# ------------------------------------------------------------
raw["eficiencia"] = raw[["PTS", "AST", "TRB", "STL", "BLK"]].sum(axis=1)

time_principal = raw["Team"].str.split("/").str[0]          # LAL/LAC -> LAL
salario_por_time = raw.groupby(time_principal)["Salary"].mean()
p33, p66 = salario_por_time.quantile(0.33), salario_por_time.quantile(0.66)


def classificar_tier(time):
    media = salario_por_time[time]
    return 3 if media >= p66 else (2 if media >= p33 else 1)


raw["tier_time"] = time_principal.map(classificar_tier)

# ------------------------------------------------------------
# 4) Conjunto treino/teste (mesmo split do notebook: 80/20, seed 42)
#    Os índices dependem de o CSV estar na mesma ordem do notebook.
# ------------------------------------------------------------
idx_treino, idx_teste = train_test_split(np.arange(len(raw)), test_size=0.2, random_state=42)
raw["conjunto"] = "treino"
raw.loc[idx_teste, "conjunto"] = "teste"

# ------------------------------------------------------------
# 5) IDs dos jogadores (lista embutida da nba_api, sem rede)
# ------------------------------------------------------------
ids = pd.DataFrame(players.get_players())
ids["_chave"] = ids["full_name"].map(normalizar)
ids = ids.sort_values("is_active", ascending=False).drop_duplicates("_chave")

raw["_chave"] = raw["Player Name"].map(normalizar)
raw = raw.merge(ids[["_chave", "id"]], on="_chave", how="left")
raw = raw.rename(columns={"id": "PLAYER_ID"}).drop(columns="_chave")

for nome, pid in OVERRIDES.items():
    raw.loc[raw["Player Name"] == nome, "PLAYER_ID"] = pid

sem_id = raw[raw["PLAYER_ID"].isna()]["Player Name"].tolist()
raw["PLAYER_ID"] = raw["PLAYER_ID"].astype("Int64")

os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
raw.to_csv(SAIDA, index=False)

print(f"✅ {len(raw)} jogadores salvos em {SAIDA}")
print(f"✅ {len(raw) - len(sem_id)}/{len(raw)} com PLAYER_ID")
print(f"✅ treino: {(raw['conjunto'] == 'treino').sum()} | teste: {(raw['conjunto'] == 'teste').sum()}")
if sem_id:
    print("⚠️ Sem ID (adicione em OVERRIDES):", sem_id)
