"""Export the current API and Phase 10 schemas without rewriting historical contracts."""
import json
from pathlib import Path
from app.main import create_app
from app.config import Settings
from app.accounts.schemas import Registration
from app.challenges.schemas import ChallengeView,Leaderboard

def main():
    app=create_app(Settings(db_name='contract_export',db_user='contract_export',db_password='unused-local-export'))
    root=Path(__file__).resolve().parents[2]/'contracts'
    try:
        (root/'openapi.current.json').write_text(json.dumps(app.openapi(),indent=2)+'\n')
        for name,model in [('account-registration.phase10.schema.json',Registration),('challenge.phase10.schema.json',ChallengeView),('leaderboard.phase10.schema.json',Leaderboard)]:
            (root/name).write_text(json.dumps(model.model_json_schema(),indent=2)+'\n')
    finally:app.state.database.close()
if __name__=='__main__':main()
