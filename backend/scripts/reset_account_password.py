"""Local database operator recovery. Passwords are prompted, never command-line arguments."""
import argparse,getpass,json
from app.config import Settings
from app.database import Database
from app.accounts.service import reset_password
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--username',required=True);a=p.parse_args()
    first=getpass.getpass('New password (15–128 characters): ')
    if first!=getpass.getpass('Repeat new password: '):raise SystemExit('Passwords do not match.')
    db=Database(Settings())
    try:print(json.dumps(reset_password(db.engine,a.username,first)))
    finally:db.close()
