from datetime import datetime,time,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import hashlib
POLICY={'version':'daily-1.0','attempt_limit':1,'seed_policy':'shared-secret-committed-until-close','submission':'automatic-first-successful-release-before-close','ranking':['studio_score_desc','profit_usd_desc','submitted_at_asc','draft_id_asc'],'results':'private-reports-and-public-ranks-hidden-until-close','practice_eligible':False}

def window(day,zone):
    try:tz=ZoneInfo(zone)
    except ZoneInfoNotFoundError:raise ValueError('Unknown IANA timezone.') from None
    return datetime.combine(day,time(),tz).astimezone(timezone.utc),datetime.combine(day+timedelta(days=1),time(),tz).astimezone(timezone.utc)

def phase(opens,closes,now):return 'scheduled' if now<opens else 'closed' if now>=closes else 'open'
def commitment(seed):return hashlib.sha256(seed.encode('ascii')).hexdigest()
