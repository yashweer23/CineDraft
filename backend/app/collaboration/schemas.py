from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.domain import Role

class Output(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class GraphVersion(Output):
    graph_id: str
    dataset_id: str
    graph_hash: str
    algorithm_version: str
    created_at: datetime
    source: str
    report: dict
    playable: Literal[False] = False

class VersionPage(Output):
    items: list[GraphVersion]
    next_offset: int | None

class Node(Output):
    person_id: UUID
    name: str
    role: Role
    source: Literal["tmdb", "fixture"]
    source_key: str
    film_count: Annotated[int, Field(gt=0)]

class NodePage(Output):
    graph_id: str
    items: list[Node]
    next_offset: int | None

class Edge(Output):
    edge_id: str | None
    a: Node
    b: Node
    shared_movie_count: Annotated[int, Field(ge=0)]
    bonus: Annotated[int, Field(ge=0, le=12)]
    capped: bool

class EdgePage(Output):
    graph_id: str
    items: list[Edge]
    next_offset: int | None

class PairResult(Output):
    graph_id: str
    dataset_id: str
    edge: Edge
    message: str

class SharedFilm(Output):
    movie_id: UUID
    title: str
    year: int | None
    source: Literal["tmdb", "fixture"]
    source_key: str
    source_url: str | None
    poster_url: str | None
    jobs_a: list[str]
    jobs_b: list[str]

class EvidencePage(Output):
    graph_id: str
    dataset_id: str
    edge: Edge
    items: list[SharedFilm]
    next_offset: int | None

class GraphReport(Output):
    version: GraphVersion
    parameters: dict
    dataset_manifest_hash: str
    input_rows_hash: str
    output_rows_hash: str
