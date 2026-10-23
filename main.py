# ============================================================
# main.py
# Ponto de entrada da aplicação FastAPI
# Gerencia o ciclo de vida e inclui os roteadores
# ============================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers.predict import router
from services import model_service


# ============================================================
# Lifespan — Ciclo de vida da aplicação
# O modelo é carregado UMA ÚNICA VEZ na inicialização
# e mantido na memória RAM durante toda a execução
# É PROIBIDO carregar o modelo dentro dos endpoints
# pois geraria gargalo de I/O a cada requisição
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação:
    - Startup: carrega o modelo na memória RAM
    - Shutdown: libera os recursos
    """
    # --------------------------------------------------------
    # STARTUP — executado ao iniciar a aplicação
    # --------------------------------------------------------
    print("🚀 Iniciando NBA Salary Predictor API...")
    model_service.carregar_modelo()
    print("✅ API pronta para receber requisições!")

    yield  # API fica disponível aqui

    # --------------------------------------------------------
    # SHUTDOWN — executado ao encerrar a aplicação
    # --------------------------------------------------------
    print("🔴 Encerrando NBA Salary Predictor API...")


# ============================================================
# Instância da aplicação FastAPI
# ============================================================
app = FastAPI(
    title="NBA Salary Predictor API",
    description="""
    API para predição de salários de jogadores da NBA
    com base em suas estatísticas de desempenho.

    ## Modelo
    - **Rede Neural** (Keras/TensorFlow)
    - **Versão:** v2
    - **Dataset:** NBA Players Stats and Salaries 2022-23
    - **R²:** 0.7219

    ## Endpoints
    - **GET /v1/health** — verificação de saúde da API
    - **POST /v1/predict** — predição de salário
    """,
    version="2.0.0",
    lifespan=lifespan
)


# ============================================================
# Inclusão dos roteadores
# ============================================================
app.include_router(router)


# ============================================================
# Rota raiz — redirecionamento para documentação
# ============================================================
@app.get("/", tags=["Root"])
async def root():
    """
    Rota raiz — informações básicas da API
    """
    return {
        "api"      : "NBA Salary Predictor",
        "versao"   : "2.0.0",
        "modelo"   : "Rede Neural (Keras) v2",
        "docs"     : "/docs",
        "health"   : "/v1/health",
        "predict"  : "/v1/predict"
    }