from datetime import date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ───────────── Auth ─────────────

class CadastroIn(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=72)  # bcrypt só usa 72 bytes
    papel: Literal["medico", "paciente"]
    especialidade: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _especialidade_do_medico(self):
        if self.papel == "medico":
            esp = (self.especialidade or "").strip()
            if not esp:
                raise ValueError("Informe a especialidade do médico.")
            self.especialidade = esp
        else:
            self.especialidade = None
        return self


class LoginIn(BaseModel):
    email: str
    senha: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    papel: str
    especialidade: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ───────────── Médicos ─────────────

class MedicoOut(BaseModel):
    id: int
    nome: str
    especialidade: str | None = None
    horarios_livres: int = 0  # horários livres de hoje em diante


# ───────────── Agenda ─────────────

class SlotOut(BaseModel):
    id: int
    inicio: datetime
    fim: datetime
    livre: bool
    minha: bool = False  # consulta marcada pelo usuário logado (paciente)
    paciente_nome: str | None = None  # só aparece para o médico dono da agenda


class ConsultaOut(BaseModel):
    id: int
    inicio: datetime
    fim: datetime
    medico_nome: str
    especialidade: str | None = None
    paciente_nome: str
    passada: bool


class Faixa(BaseModel):
    inicio: time
    fim: time

    @model_validator(mode="after")
    def _fim_depois_do_inicio(self):
        if self.fim <= self.inicio:
            raise ValueError("Em cada faixa, o fim deve ser depois do início.")
        return self


class GerarSlotsIn(BaseModel):
    data_inicio: date
    data_fim: date
    dias_semana: list[int] = Field(min_length=1)  # 0 = segunda ... 6 = domingo
    faixas: list[Faixa] = Field(min_length=1, max_length=6)
    duracao_min: int = Field(ge=5, le=240)

    @field_validator("dias_semana")
    @classmethod
    def _dias_validos(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("Dia da semana inválido.")
        return sorted(set(v))

    @model_validator(mode="after")
    def _periodo(self):
        if self.data_fim < self.data_inicio:
            raise ValueError("A data final deve ser igual ou depois da inicial.")
        if self.data_fim - self.data_inicio > timedelta(days=366):
            raise ValueError("O período máximo é de 1 ano.")
        return self


class GerarSlotsOut(BaseModel):
    criados: int
    ignorados: int  # já existiam, se sobrepunham ou estavam no passado
