"""Synthetic identity collision: no API, database or upstream request required."""
import json
from app.drafting.assignment import Talent,minimum_assignment,legal_candidates
from app.domain import Slot

def example():
    pool=[Talent('synthetic-multi-role','writer',100000),Talent('synthetic-multi-role','composer',100000),
          Talent('synthetic-writer-only','writer',400000),Talent('synthetic-composer-only','composer',900000)]
    slots=[Slot.WRITER,Slot.COMPOSER];result=minimum_assignment(pool,slots)
    return {'synthetic':True,'naive_separate_minima_usd':200000,'exact_distinct_people_assignment':result,
            'available_usd':600000,'writer_offers':[{'person_id':r['talent'].person_id,'fee_usd':r['talent'].fee_usd,
            'selectable':r['selectable'],'blocked_reason':r['blocked_reason'],'remaining_cost_usd':r['completion_cost_usd']}
            for r in legal_candidates(pool,Slot.WRITER,[Slot.COMPOSER],set(),600000)]}
if __name__=='__main__':print(json.dumps(example(),indent=2))
