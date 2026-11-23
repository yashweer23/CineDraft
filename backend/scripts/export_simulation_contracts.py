"""Export the immutable Phase 8 result schema without changing historical schemas."""
import json
from pathlib import Path
from app.simulation.schemas import SimulationResult
if __name__=='__main__':
    path=Path(__file__).resolve().parents[2]/'contracts'/'result.phase8.schema.json'
    path.write_text(json.dumps(SimulationResult.model_json_schema(),indent=2)+'\n')
    print('Exported contracts/result.phase8.schema.json')
