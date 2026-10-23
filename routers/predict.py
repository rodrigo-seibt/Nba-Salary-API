# ============================================================
# routers/predict.py
# Definição dos endpoints da API usando APIRouter
# Desacopla as rotas do ponto de entrada (main.py)
# ============================================================

from fastapi import APIRouter, HTTPException
from schemas.player import PlayerInput, PlayerOutput, HealthOutput
from services import model_service

# --------------------------------------------------------
# APIRouter agrupa os endpoints de negócio
# prefix="/v1" — versionamento da API
# tags — agrupamento na documentação Swagger
# --------------------------------------------------------
router = APIRouter(prefix="/v1", tags=["NBA Salary Predictor"])


@router.get(
    "/health",
    response_model=HealthOutput,
    summary="Verificação de saúde da API",
    description="Retorna o status do serviço e se o modelo está na memória RAM"
)
async def health_check():
    """
    Endpoint de monitoramento — GET /v1/health

    Verifica se:
    - O serviço está ativo
    - O modelo está carregado na memória RAM

    Retorna HTTP 200 OK se tudo estiver funcionando.
    Retorna HTTP 503 Service Unavailable se o modelo
    não estiver carregado.
    """
    carregado = model_service.modelo_carregado()

    if not carregado:
        raise HTTPException(
            status_code=503,
            detail="Modelo não está carregado na memória RAM"
        )

    return HealthOutput(
        status="online",
        modelo_carregado=carregado,
        versao="v2"
    )


@router.post(
    "/predict",
    response_model=PlayerOutput,
    summary="Predição de salário de jogador NBA",
    description="Recebe as estatísticas de um jogador e retorna o salário previsto"
)
async def predict(dados: PlayerInput):
    """
    Endpoint de inferência — POST /v1/predict

    Recebe as estatísticas de um jogador validadas
    pelo Pydantic e retorna o salário anual previsto
    pela Rede Neural.

    Retorna HTTP 200 OK com o salário previsto.
    Retorna HTTP 422 Unprocessable Entity se os dados
    enviados forem inválidos.
    Retorna HTTP 500 Internal Server Error se ocorrer
    erro durante a inferência.
    """
    try:
        resultado = model_service.prever_salario(dados)
        return PlayerOutput(**resultado)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro durante a inferência: {str(e)}"
        )