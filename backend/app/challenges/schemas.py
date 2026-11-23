from datetime import datetime
from uuid import UUID
from app.contracts import Contract,GenreId,Tier,Hash

class Begin(Contract):
    request_id:UUID

class ChallengeView(Contract):
    challenge_id:str
    opens_at:datetime
    closes_at:datetime
    timezone:str
    status:str
    genre_id:GenreId
    tier:Tier
    catalog_id:str
    config_hash:Hash
    seed_commitment:Hash
    configuration:dict
    results_hidden:bool
    synthetic:bool

class ChallengePage(Contract):
    items:list[ChallengeView]
    next_offset:int|None

class RankingRow(Contract):
    rank:int
    username:str
    studio_score:int
    profit_usd:int
    submitted_at:datetime
    output_hash:Hash

class Leaderboard(Contract):
    challenge:ChallengeView
    items:list[RankingRow]
    next_offset:int|None
    message:str

class Mine(Contract):
    draft_id:UUID|None
class Context(Contract):
    challenge:ChallengeView|None
    submitted:bool
class Audit(Contract):
    challenge:ChallengeView
    seed:Hash
    seed_commitment:Hash
    commitment_algorithm:str
