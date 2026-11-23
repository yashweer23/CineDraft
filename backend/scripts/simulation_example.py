"""Run an explicitly synthetic release without a database or upstream requests."""
import json
from app.simulation.example import synthetic_snapshot
from app.simulation.engine import simulate
from app.simulation.schemas import SimulationResult
from app.repository import canonical_hash

def example():
    frozen=synthetic_snapshot();inputs=frozen.model_dump(mode='json');digest=canonical_hash(inputs)
    value=SimulationResult.model_validate(simulate(frozen,digest)).model_dump(mode='json')
    return dict(synthetic=True,note='Invented arithmetic exercise. No catalog was imported or published.',
                input_hash=digest,output_hash=canonical_hash(value),result=value)
if __name__=='__main__':print(json.dumps(example(),indent=2,allow_nan=False))
