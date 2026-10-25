# ============================================================
# schemas/player.py
# Definição dos esquemas Pydantic para validação dos dados
# ============================================================

from pydantic import BaseModel, Field
from typing import Literal

class PlayerInput(BaseModel):
    """
    Esquema de entrada para predição de salário.
    Define e valida todos os dados necessários para
    prever o salário de um jogador da NBA.
    """

    # Perfil do jogador
    Position: Literal["PG", "SG", "SF", "PF", "C"] = Field(
        ...,
        description="Posição do jogador na quadra"
    )
    Age: int = Field(
        ..., ge=18, le=45,
        description="Idade do jogador em anos"
    )

    # Volume de jogo
    GP: int = Field(
        ..., ge=1, le=82,
        description="Jogos disputados na temporada"
    )
    GS: int = Field(
        ..., ge=0, le=82,
        description="Jogos como titular"
    )

    # Estatísticas ofensivas
    PTS: float = Field(
        ..., ge=0.0, le=40.0,
        description="Pontos por jogo"
    )
    AST: float = Field(
        ..., ge=0.0, le=15.0,
        description="Assistências por jogo"
    )
    TRB: float = Field(
        ..., ge=0.0, le=20.0,
        description="Rebotes totais por jogo"
    )
    STL: float = Field(
        ..., ge=0.0, le=5.0,
        description="Roubos de bola por jogo"
    )
    BLK: float = Field(
        ..., ge=0.0, le=5.0,
        description="Bloqueios por jogo"
    )
    PF: float = Field(
        ..., ge=0.0, le=6.0,
        description="Faltas pessoais por jogo"
    )

    # Arremessos
    field_3P: float = Field(
        ..., ge=0.0, le=7.0,
        alias="3P",
        description="Cestas de 3 pontos por jogo"
    )

    # Métricas avançadas
    PER: float = Field(
        ..., ge=-10.0, le=40.0,
        description="Player Efficiency Rating"
    )
    TS_pct: float = Field(
        ..., ge=0.0, le=1.0,
        alias="TS%",
        description="True Shooting Percentage"
    )
    field_3PAr: float = Field(
        ..., ge=0.0, le=1.0,
        alias="3PAr",
        description="3-Point Attempt Rate"
    )
    FTr: float = Field(
        ..., ge=0.0, le=2.0,
        description="Free Throw Rate"
    )
    ORB_pct: float = Field(
        ..., ge=0.0, le=30.0,
        alias="ORB%",
        description="Offensive Rebound Percentage"
    )
    TRB_pct: float = Field(
        ..., ge=0.0, le=30.0,
        alias="TRB%",
        description="Total Rebound Percentage"
    )
    STL_pct: float = Field(
        ..., ge=0.0, le=5.0,
        alias="STL%",
        description="Steal Percentage"
    )
    BLK_pct: float = Field(
        ..., ge=0.0, le=15.0,
        alias="BLK%",
        description="Block Percentage"
    )
    TOV_pct: float = Field(
        ..., ge=0.0, le=40.0,
        alias="TOV%",
        description="Turnover Percentage"
    )
    USG_pct: float = Field(
        ..., ge=0.0, le=50.0,
        alias="USG%",
        description="Usage Percentage"
    )
    WS: float = Field(
        ..., ge=-5.0, le=20.0,
        description="Win Shares"
    )
    tier_time: int = Field(
        ..., ge=1, le=3,
        description="Tier financeiro do time (1=menor, 3=maior)"
    )
    eficiencia: float = Field(
        ..., ge=0.0, le=60.0,
        description="Índice de eficiência (PTS+AST+TRB+STL+BLK)"
    )

    model_config = {"populate_by_name": True}


class PlayerOutput(BaseModel):
    """
    Esquema de saída da predição de salário.
    """
    salario_previsto: float = Field(
        ...,
        description="Salário anual previsto em dólares"
    )
    salario_formatado: str = Field(
        ...,
        description="Salário formatado para leitura humana"
    )
    modelo: str = Field(
        ...,
        description="Nome do modelo utilizado na predição"
    )
    versao: str = Field(
        ...,
        description="Versão do modelo utilizado"
    )


class HealthOutput(BaseModel):
    """
    Esquema de saída do endpoint de saúde.
    """
    status: str = Field(
        ...,
        description="Status do serviço"
    )
    modelo_carregado: bool = Field(
        ...,
        description="Se o modelo está na memória RAM"
    )
    versao: str = Field(
        ...,
        description="Versão do modelo em produção"
    )