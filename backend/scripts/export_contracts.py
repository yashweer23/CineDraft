"""Generate proposed OpenAPI and JSON Schema, without mounting future routes."""
import json
from pathlib import Path
from typing import Annotated
from uuid import UUID
from fastapi import Depends, FastAPI, Path as ApiPath, Query
from fastapi.security import HTTPBearer
from pydantic.json_schema import models_json_schema
from app import contracts as c
from app.domain import Role

ROOT = Path(__file__).resolve().parents[2]

def proposed_spec():
    app = FastAPI(title="CineDraft proposed game API — NOT IMPLEMENTED", version="0.3.0-contract",
        description="Phase 3 design artifact only. None of these routes is mounted by app.main. Authentication, draft engine and result generation are future work.")
    bearer = HTTPBearer(description="Future verified user or guest capability; never a draft UUID alone")
    errors = {code: {"model": c.ContractError} for code in [401, 404, 409, 422, 503]}
    def register(path, methods, endpoint, response, *, private=False, status=200):
        app.add_api_route("/api/v1" + path, endpoint, methods=methods, response_model=response,
            status_code=status, responses=errors, dependencies=[Depends(bearer)] if private else [],
            openapi_extra={"x-implementation-status": "planned", "x-phase": 7 if "/drafts" in path else 4})

    def genres():
        raise NotImplementedError
    register("/catalog/genres", ["GET"], genres, list[c.GenreView])

    def candidates(dataset_id: c.VersionId, feature_id: c.VersionId, pricing_id: c.VersionId,
                   role: Role, genre_id: c.GenreId, limit: Annotated[int, Query(ge=1, le=50)] = 20,
                   cursor: Annotated[str | None, Query(max_length=512)] = None):
        raise NotImplementedError
    register("/catalog/candidates", ["GET"], candidates, c.CatalogPage)

    def person(person_id: UUID, dataset_id: c.VersionId, feature_id: c.VersionId,
               pricing_id: c.VersionId, role: Role, genre_id: c.GenreId):
        raise NotImplementedError
    register("/catalog/people/{person_id}", ["GET"], person, c.CandidateCard)

    def create(body: c.CreateDraftRequest):
        raise NotImplementedError
    register("/drafts", ["POST"], create, c.DraftView, private=True, status=201)

    def read(draft_id: UUID):
        raise NotImplementedError
    register("/drafts/{draft_id}", ["GET"], read, c.DraftView, private=True)

    for route, request, status in [
        ("picks", c.PickRequest, 200), ("rerolls", c.RerollRequest, 200),
        ("recast/preview", c.RecastPreviewRequest, 200),
        ("recast/cancel", c.RecastCancelRequest, 200),
        ("recast/confirm", c.RecastConfirmRequest, 200),
        ("finalize", c.MutationRequest, 200), ("release", c.MutationRequest, 202),
        ("retry-simulation", c.MutationRequest, 202), ("abandon", c.MutationRequest, 200),
    ]:
        def endpoint(draft_id: UUID, body):
            raise NotImplementedError
        endpoint.__name__ = route.replace("/", "_").replace("-", "_")
        endpoint.__annotations__["body"] = request
        register("/drafts/{draft_id}/" + route, ["POST"], endpoint, c.DraftView, private=True, status=status)

    def result(draft_id: UUID):
        raise NotImplementedError
    register("/drafts/{draft_id}/result", ["GET"], result, c.ResultView, private=True)
    spec = app.openapi()
    # The runtime uses the shared envelope; replace FastAPI's stock validation shape.
    for path in spec["paths"].values():
        for op in path.values():
            if isinstance(op, dict) and "responses" in op:
                op["responses"]["422"] = {"description": "Contract validation failed", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ContractError"}}}}
    return spec

def main():
    out = ROOT / "contracts"
    out.mkdir(exist_ok=True)
    (out / "openapi.proposed.json").write_text(json.dumps(proposed_spec(), indent=2) + "\n")
    models = [(value, "validation") for value in vars(c).values() if isinstance(value, type) and issubclass(value, c.Contract) and value is not c.Contract]
    _, schema = models_json_schema(models, title="CineDraft Phase 3 wire schemas")
    (out / "schemas.json").write_text(json.dumps(schema, indent=2) + "\n")
    print("Exported contracts/openapi.proposed.json and contracts/schemas.json")

if __name__ == "__main__":
    main()
