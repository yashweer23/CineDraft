"""Export the current API and hypothetical schemas; historical contracts are preserved."""
import json
from pathlib import Path
from app.main import create_app
from app.config import Settings
from app.whatif.schemas import CompareRequest,Inputs,Saved,Candidates,History

def main():
    app=create_app(Settings(db_name='contract_export',db_user='contract_export',db_password='unused-local-export'))
    root=Path(__file__).resolve().parents[2]/'contracts'
    try:
        (root/'openapi.current.json').write_text(json.dumps(app.openapi(),indent=2)+'\n')
        for name,model in [('request',CompareRequest),('inputs',Inputs),('saved',Saved),('candidates',Candidates),('history',History)]:
            (root/f'whatif-{name}.phase11.schema.json').write_text(json.dumps(model.model_json_schema(),indent=2)+'\n')
    finally:app.state.database.close()
if __name__=='__main__':main()
