"""Export Phase 12 only; historical schemas remain intact."""
import json
from pathlib import Path
from app.config import Settings
from app.main import create_app
from app.analytics.schemas import Stream,ReplayRequest

def main():
    root=Path(__file__).resolve().parents[2]/'contracts';app=create_app(Settings(db_name='contract_export',db_user='contract_export',db_password='unused-local-export'))
    try:
        for filename,value in [('openapi.current.json',app.openapi()),('gameplay-events.phase12.schema.json',Stream.model_json_schema()),('practice-replay.phase12.schema.json',ReplayRequest.model_json_schema())]:
            (root/filename).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    finally:app.state.database.close()
if __name__=='__main__':main()
