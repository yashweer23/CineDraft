"""Export Phase 7 persisted-input contract; historical Phase 3 schemas stay intact."""
import json
from pathlib import Path
from app.drafting.schemas import FrozenDraft
if __name__=='__main__':
    output=Path(__file__).resolve().parents[2]/'contracts'/'snapshot.phase7.schema.json'
    output.write_text(json.dumps(FrozenDraft.model_json_schema(),indent=2)+'\n')
    print('Exported contracts/snapshot.phase7.schema.json')
