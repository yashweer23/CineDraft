"""Export the implemented API, distinct from proposed game contracts."""
import json
from pathlib import Path
from app.config import Settings
from app.main import create_app

if __name__ == "__main__":
    config=Settings(_env_file=None,db_name="contract_export",db_user="contract_export",db_password="not-used")
    app=create_app(config)
    try:
        output=Path(__file__).resolve().parents[2]/"contracts"/"openapi.current.json"
        output.write_text(json.dumps(app.openapi(),indent=2)+"\n")
        print("Exported contracts/openapi.current.json")
    finally:
        app.state.database.close()
