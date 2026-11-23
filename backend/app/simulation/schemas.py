from datetime import datetime
from decimal import Decimal,localcontext,ROUND_HALF_UP
from typing import Annotated,Literal
from uuid import UUID
from pydantic import Field,model_validator
from app import contracts as c
from app.drafting.schemas import LiveDraft,DraftVersions
from app.simulation.engine import PRECISION

DecimalText=Annotated[str,Field(pattern=r'^-?[0-9]+(?:\.[0-9]+)?$',max_length=300)]

class ScoreComponent(c.Contract):
    name:Literal['genre','talent','chemistry','efficiency']
    value:DecimalText
    weight:DecimalText
    contribution:DecimalText

class SimulationResult(c.ResultView):
    schema_version:Literal['phase8-v1']='phase8-v1'
    versions:DraftVersions
    studio_score_unrounded:DecimalText
    score_components:Annotated[list[ScoreComponent],Field(min_length=4,max_length=4)]
    cast_appeal:DecimalText
    critics_unrounded:DecimalText
    audience_unrounded:DecimalText
    gross_multiplier:DecimalText
    total_cost_usd:c.Money
    unused_talent_budget_usd:c.Money
    return_on_total_cost_percent:DecimalText
    weekly_retention:DecimalText
    reproducibility:dict

    @model_validator(mode='after')
    def phase8_accounting(self):
        with localcontext() as ctx:
            ctx.prec=PRECISION;ctx.rounding=ROUND_HALF_UP
            if self.total_cost_usd!=self.production_cost_usd+self.marketing_usd or self.total_cost_usd<=0:
                raise ValueError('Total cost must include production and marketing')
            if [c.name for c in self.score_components]!=['genre','talent','chemistry','efficiency']:
                raise ValueError('Expected four ordered score components')
            if any(not 0<=Decimal(c.value)<=100 or not 0<=Decimal(c.weight)<=1 or Decimal(c.contribution)!=Decimal(c.value)*Decimal(c.weight) for c in self.score_components):
                raise ValueError('Invalid weighted score contribution')
            if sum(Decimal(c.weight) for c in self.score_components)!=1:raise ValueError('Score weights must sum to one')
            raw=sum(Decimal(c.contribution) for c in self.score_components)
            if raw!=Decimal(self.studio_score_unrounded) or int(raw.quantize(Decimal(1)))!=self.studio_score:
                raise ValueError('Studio score must reconcile with unrounded contributions')
            if Decimal(self.return_on_total_cost_percent)!=Decimal(100)*self.profit_usd/self.total_cost_usd:
                raise ValueError('Return must include marketing cost')
        if self.simulation_version!=self.versions.simulation_version:raise ValueError('Simulation version must match frozen versions')
        return self

class SavedResult(c.Contract):
    output_hash:c.Hash
    result:SimulationResult

class AttemptView(c.Contract):
    attempt_id:UUID
    attempt_number:Annotated[int,Field(ge=1)]
    command:Literal['release','retry_simulation']
    request_id:UUID
    revision:c.Revision
    status:Literal['succeeded','failed']
    error_code:Literal['engine_error']|None
    message:str
    created_at:datetime

class SimulationStatus(c.Contract):
    draft_id:UUID
    status:c.DraftStatus
    latest_attempt:AttemptView|None
    result_available:bool

class ReleaseReceipt(c.Contract):
    draft:LiveDraft
    attempt:AttemptView
