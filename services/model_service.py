# ============================================================
# services/model_service.py
# Camada de serviço — carregamento e inferência do modelo
# Desacopla a lógica de negócio do protocolo HTTP
# ============================================================

import numpy as np
import joblib
from tensorflow import keras
from schemas.player import PlayerInput

# ============================================================
# Variáveis globais para armazenar o modelo em memória RAM
# Carregadas UMA ÚNICA VEZ na inicialização da aplicação
# via lifespan — proibido recarregar a cada requisição
# ============================================================
modelo = None
pipeline_scaler = None
label_encoder = None


def carregar_modelo():
    """
    Carrega o modelo Keras, o pipeline de pré-processamento
    e o LabelEncoder na memória RAM.
    Chamada apenas uma vez no lifespan da aplicação.
    """
    global modelo, pipeline_scaler, label_encoder

    modelo = keras.models.load_model("models/modelo_rn_v2.keras")
    pipeline_scaler = joblib.load("models/pipeline_scaler.pkl")
    label_encoder = joblib.load("models/label_encoder.pkl")

    print("✅ Modelo Rede Neural v2 carregado na memória RAM")
    print("✅ Pipeline de pré-processamento carregado")
    print("✅ LabelEncoder carregado")


def modelo_carregado() -> bool:
    """
    Verifica se o modelo está carregado na memória RAM.
    Utilizado pelo endpoint /health.
    """
    return modelo is not None


def preprocessar_entrada(dados: PlayerInput) -> np.ndarray:
    """
    Converte os dados de entrada do esquema Pydantic
    para um array NumPy pronto para inferência.

    Etapas:
    1. Aplica Label Encoding na posição
    2. Organiza as features na ordem correta
    3. Trata valores NaN
    4. Aplica o pipeline de escalonamento
    """

    # Ordem das features — deve ser idêntica ao treino
    ordem_features = [
        "Position", "Age", "GP", "GS", "3P", "TRB",
        "AST", "STL", "BLK", "PF", "PTS", "PER",
        "TS%", "3PAr", "FTr", "ORB%", "TRB%", "STL%",
        "BLK%", "TOV%", "USG%", "WS", "tier_time", "eficiencia"
    ]

    # Aplicando Label Encoding na posição
    posicao_encoded = label_encoder.transform([dados.Position])[0]

    # Montando o dicionário com os valores na ordem correta
    valores = {
        "Position"  : posicao_encoded,
        "Age"       : dados.Age,
        "GP"        : dados.GP,
        "GS"        : dados.GS,
        "3P"        : dados.field_3P,
        "TRB"       : dados.TRB,
        "AST"       : dados.AST,
        "STL"       : dados.STL,
        "BLK"       : dados.BLK,
        "PF"        : dados.PF,
        "PTS"       : dados.PTS,
        "PER"       : dados.PER,
        "TS%"       : dados.TS_pct,
        "3PAr"      : dados.field_3PAr,
        "FTr"       : dados.FTr,
        "ORB%"      : dados.ORB_pct,
        "TRB%"      : dados.TRB_pct,
        "STL%"      : dados.STL_pct,
        "BLK%"      : dados.BLK_pct,
        "TOV%"      : dados.TOV_pct,
        "USG%"      : dados.USG_pct,
        "WS"        : dados.WS,
        "tier_time" : dados.tier_time,
        "eficiencia": dados.eficiencia
    }

    # Convertendo para array na ordem correta
    array = np.array([[valores[f] for f in ordem_features]])

    # --------------------------------------------------------
    # Tratando NaN antes de escalonar
    # Evita incompatibilidade do SimpleImputer entre versões
    # do Scikit-learn — substituímos NaN por 0.0 diretamente
    # --------------------------------------------------------
    array = np.nan_to_num(array, nan=0.0)

    # Aplicando apenas o StandardScaler do pipeline
    array_scaled = pipeline_scaler["scaler"].transform(array)

    return array_scaled


def prever_salario(dados: PlayerInput) -> dict:
    """
    Realiza a inferência do modelo para prever o salário.

    Parâmetros:
        dados: PlayerInput — dados validados pelo Pydantic

    Retorna:
        dict com salário previsto, formatado, modelo e versão
    """
    # Pré-processamento
    array_scaled = preprocessar_entrada(dados)

    # Inferência
    predicao = modelo.predict(array_scaled, verbose=0)
    salario = float(predicao[0][0])

    # Garantir que o salário não seja negativo
    salario = max(0, salario)

    return {
        "salario_previsto" : round(salario, 2),
        "salario_formatado": f"US$ {salario:,.2f}",
        "modelo"           : "Rede Neural (Keras)",
        "versao"           : "v2"
    }