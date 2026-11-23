from app.domain import Slot, TIERS
from app.repository import canonical_hash

RULES_ID='rules:classic-1.0'
SCORING_ID='scoring:baseline-1.0'
PRNG_VERSION='sha256-order-1.0'
SIMULATION_VERSION='simulation-1.0'
RULES={"schema_version":"classic-1.0","currency":"USD","reserve_percent":35,
       "tiers":TIERS,"slot_order":[s.value for s in Slot],"offer_size":3,"rerolls":2,"recasts":1,
       "prng_version":PRNG_VERSION,"assignment":"exact-slot-mask-dp-1.0",
       "normal_offer_priority":"legal choices first", "reroll_priority":"maximum fresh identities with at least one legal choice",
       "recast":"cached per slot until confirmed; no rerolls"}
# Frozen baseline specification; execution of these formulas belongs to Phase 8.
# Decimal coefficients are strings so the stored contract has exact values.
SCORING={
    "schema_version":"baseline-1.0","implementation_phase":8,"simulation_version":SIMULATION_VERSION,
    "slot_weights":["1.5","1.3","1.1","0.7","0.7","1.4","1.1","0.9"],
    "studio_weights":{"genre":"0.30","talent":"0.30","chemistry":"0.25","efficiency":"0.15"},
    "chemistry":{"neutral":60,"range":40,"edges":12,"edge_cap":12,"formula":"60 + 40 * sum(edge_bonus) / 144"},
    "efficiency":{"formula":"clamp((0.5*G + 0.5*T)*(1 - 0.30*talent_spend/talent_budget), 0, 100)"},
    "cast_appeal":"mean of four actor popularity_percentile values; missing uses 50",
    "critics":{"formula":"clamp(0.50*T + 0.35*G + 0.15*H + noise, 0, 100)","stream":"critics","uniform_noise":["-5","5"]},
    "audience":{"formula":"clamp(0.30*T + 0.30*G + 0.20*H + 0.20*P_cast + noise, 0, 100)","stream":"audience","uniform_noise":["-5","5"]},
    "gross_multiplier":{"formula":"clamp(0.50 + 0.018*audience + 0.010*critics + 0.008*P_cast + noise, 0.2, 5.0)","stream":"revenue","uniform_noise":["-0.6","0.6"]},
    "finance":{"production":"reserve + talent_spend","marketing_fraction":"0.20","receipts_fraction":"0.50",
               "profit":"receipts - production - marketing","return_percent":"100*profit/(production + marketing)"},
    "weekly":{"retention":"clamp(0.40 + 0.004*audience, 0.40, 0.80)","weights":["1","r","r^2","r^3"],
              "rounding":"normalize weights; floor weeks 1-3 to integer USD; week 4 receives residual"},
    "rounding":"integer-usd-half-up","review_precision":"unrounded values feed downstream formulas",
    "reference":"docs/phase-01/scoring-design.md"
}
RELATIONSHIPS=[('director',s) for s in ('lead','co_lead','supporting_1','supporting_2','writer','cinematographer','composer')]+[
    ('writer','lead'),('writer','co_lead'),('lead','co_lead'),('lead','supporting_1'),('co_lead','supporting_2')]


def ordered(rows, seed, stream):
    return sorted(rows,key=lambda r:(canonical_hash([PRNG_VERSION,seed,stream,r['talent'].person_id]),r['talent'].person_id))


def choose_offer(rows, seed, stream, previous=None):
    ranked=ordered(rows,seed,stream)
    if previous is None:
        return sorted(ranked,key=lambda r:not r['selectable'])[:3]
    selected=sorted(ranked,key=lambda r:(r['talent'].person_id in previous,not r['selectable']))[:3]
    if selected and not any(r['selectable'] for r in selected):
        legal=next((r for r in ranked if r['selectable']),None)
        if legal:selected[-1]=legal
    return selected
