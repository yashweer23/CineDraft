"""Publish compatible server-selected versions after exact tier feasibility checks."""
import re
from collections import Counter
from sqlalchemy import select,text,func
from sqlalchemy.orm import Session
from app import models as m
from app.domain import Slot,TIERS
from app.repository import canonical_hash
from app.talent.api import versions_query
from app.talent.calculation import price_profile
from app.collaboration.calculation import ALGORITHM_VERSION
from app.drafting.assignment import Talent,validate_pool,minimum_assignment
from app.drafting.rules import RULES,SCORING,RULES_ID,SCORING_ID
from app.drafting.errors import DraftProblem

CATALOG_VERSION='draft-catalog-1.0'
MAX_PROFILES=5000


def pool_for(s,pricing_id):
    count=s.scalar(select(func.count()).select_from(m.RolePrice).where(m.RolePrice.pricing_id==pricing_id))
    if count>MAX_PROFILES:raise ValueError(f'This local drafting build supports at most {MAX_PROFILES} role profiles per catalog.')
    pool=[Talent(str(row.person_id),row.role,row.fee_usd) for row in s.scalars(select(m.RolePrice).where(m.RolePrice.pricing_id==pricing_id))]
    validate_pool(pool)
    return pool


def bundle(s,pricing_id,graph_id):
    row=s.execute(versions_query().where(m.PricingVersion.id==pricing_id)).one_or_none()
    graph=s.get(m.GraphVersion,graph_id)
    if row is None or graph is None or not graph.sealed or graph.algorithm_version!=ALGORITHM_VERSION:
        raise ValueError('Choose published computed Phase 5 prices and a supported Phase 6 graph.')
    pricing,feature,ds=row
    if graph.dataset_id!=ds.id:raise ValueError('Prices and graph must use the same sealed dataset.')
    for version in (pricing,feature,ds,graph):
        if canonical_hash(version.configuration)!=version.content_hash:raise ValueError('Version manifest integrity check failed.')
    if (feature.configuration['dataset_manifest_hash']!=ds.content_hash or
        graph.configuration['dataset_manifest_hash']!=ds.content_hash or
        pricing.configuration['feature_manifest_hash']!=feature.content_hash):
        raise ValueError('Version dependencies do not match.')
    pool=pool_for(s,pricing_id)
    nodes={(str(pid),role) for pid,role in s.execute(select(m.GraphNode.person_id,m.GraphNode.role).where(m.GraphNode.graph_id==graph_id))}
    for f,p in s.execute(select(m.RoleFeature,m.RolePrice).join(m.RolePrice,
            (m.RolePrice.feature_id==m.RoleFeature.feature_id)&(m.RolePrice.person_id==m.RoleFeature.person_id)&(m.RolePrice.role==m.RoleFeature.role))
            .where(m.RolePrice.pricing_id==pricing_id)):
        if (str(p.person_id),p.role) not in nodes or price_profile(p.role,f.attributes)['fee_usd']!=p.fee_usd:
            raise ValueError('A priced role lacks graph evidence or its fee does not match the pinned formula.')
    return pricing,feature,ds,graph,pool


def ensure_version(s,model,key,config):
    old=s.get(model,key);digest=canonical_hash(config)
    if old is not None:
        if not old.sealed or old.content_hash!=digest or old.configuration!=config:raise ValueError('Reserved rules/scoring version differs from the supported configuration.')
        return
    row=model(id=key,configuration=config,content_hash=digest)
    s.add(row);s.flush();row.sealed=True;s.flush()


def prepare(engine,pricing_id,graph_id,label,*,dry_run=False,activate=False):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,70}',label):raise ValueError('Use a 1–71 character lowercase version label.')
    catalog_id='draft-catalog:'+label
    with Session(engine) as s,s.begin():
        if not dry_run and not s.scalar(text('SELECT pg_try_advisory_xact_lock(41007,1)')):raise ValueError('Another drafting catalog preparation is active.')
        pricing,feature,ds,graph,pool=bundle(s,pricing_id,graph_id)
        witness=minimum_assignment(pool,list(Slot))
        tiers=[]
        for tier,total in TIERS.items():
            budget=total-total*35//100;enabled=witness is not None and witness['cost_usd']<=budget
            tiers.append(dict(tier=tier,total_budget_usd=total,talent_budget_usd=budget,enabled=enabled,
                minimum_cost_usd=witness['cost_usd'] if witness else None,
                reason=None if enabled else 'No complete distinct-person assignment.' if witness is None else 'The cheapest complete roster exceeds this talent budget.'))
        config={'schema_version':CATALOG_VERSION,'source':ds.provenance.get('source'),'dataset_hash':ds.content_hash,
            'feature_hash':feature.content_hash,'pricing_hash':pricing.content_hash,'graph_hash':graph.content_hash,
            'rules_hash':canonical_hash(RULES),'scoring_hash':canonical_hash(SCORING),'tiers':tiers,
            'minimum_assignment':witness,'profiles':len(pool),'role_counts':dict(sorted(Counter(r.role for r in pool).items()))}
        result={'catalog_id':catalog_id,'dataset_id':ds.id,'pricing_id':pricing_id,'graph_id':graph_id,
                'catalog_hash':canonical_hash(config),'tiers':tiers,'minimum_assignment':witness,'created':False,'activated':False,'dry_run':dry_run}
        old=s.get(m.DraftCatalog,catalog_id)
        if old is not None and not (old.sealed and old.configuration==config and old.content_hash==result['catalog_hash'] and
            old.pricing_id==pricing_id and old.graph_id==graph_id):raise ValueError('Catalog label belongs to different/incomplete output. Choose a new label.')
        if dry_run:return result
        if not any(t['enabled'] for t in tiers):raise ValueError('No budget tier can complete a draft. Review catalog coverage or publish a revised pricing version.')
        ensure_version(s,m.RulesVersion,RULES_ID,RULES);ensure_version(s,m.ScoringVersion,SCORING_ID,SCORING)
        if old is None:
            old=m.DraftCatalog(id=catalog_id,dataset_id=ds.id,feature_id=feature.id,pricing_id=pricing_id,graph_id=graph_id,
                rules_id=RULES_ID,scoring_id=SCORING_ID,configuration=config,content_hash=result['catalog_hash'])
            s.add(old);s.flush();old.sealed=True;s.flush();result['created']=True
        if activate:
            current=s.scalar(select(m.CatalogActivation.catalog_id).order_by(m.CatalogActivation.id.desc()).limit(1))
            if current!=catalog_id:s.add(m.CatalogActivation(catalog_id=catalog_id));result['activated']=True
        return result


def checked_catalog(s,key=None):
    if key is None:key=s.scalar(select(m.CatalogActivation.catalog_id).order_by(m.CatalogActivation.id.desc()).limit(1))
    row=s.get(m.DraftCatalog,key) if key else None
    if row is None or not row.sealed or row.configuration.get('schema_version')!=CATALOG_VERSION:
        raise DraftProblem(503,'catalog_unavailable','Prepare and activate a compatible drafting catalog from the Phase 7 README.')
    if canonical_hash(row.configuration)!=row.content_hash or row.configuration['rules_hash']!=canonical_hash(RULES) or row.configuration['scoring_hash']!=canonical_hash(SCORING):
        raise DraftProblem(503,'unsupported_catalog','Catalog integrity or rules version does not match this engine.')
    return row


def availability(engine):
    with Session(engine) as s:
        c=checked_catalog(s)
        return dict(catalog_id=c.id,dataset_id=c.dataset_id,pricing_id=c.pricing_id,graph_id=c.graph_id,
            synthetic=c.configuration['source']=='fixture',tiers=c.configuration['tiers'],rules=RULES,simulation_available=True)
