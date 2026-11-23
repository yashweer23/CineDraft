"""Phase 7 capabilities, drafting catalog, active offers and nullable graph pins.
Historical drafts/snapshots are not rewritten.
"""
from alembic import op
import sqlalchemy as sa
revision = "0004_phase7"
down_revision = "0003_phase6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('drafts', sa.Column('graph_id', sa.String(100), nullable=True))
    op.create_foreign_key('fk_drafts_graph_dataset','drafts','graph_versions',['graph_id','dataset_id'],['id','dataset_id'])
    op.create_unique_constraint('uq_offers_id_draft','offers',['id','draft_id'])
    op.execute("\nCREATE TABLE guest_sessions (\n\tid UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tCONSTRAINT pk_guest_sessions PRIMARY KEY (id), \n\tCONSTRAINT ck_guest_sessions_hash CHECK (token_hash ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT uq_guest_sessions_token_hash UNIQUE (token_hash)\n)\n\n")
    op.execute("\nCREATE TABLE draft_catalogs (\n\tdataset_id VARCHAR(100) NOT NULL, \n\tfeature_id VARCHAR(100) NOT NULL, \n\tpricing_id VARCHAR(100) NOT NULL, \n\tgraph_id VARCHAR(100) NOT NULL, \n\trules_id VARCHAR(100) NOT NULL, \n\tscoring_id VARCHAR(100) NOT NULL, \n\tid VARCHAR(100) NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tcontent_hash VARCHAR(64) NOT NULL, \n\tsealed BOOLEAN DEFAULT 'false' NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_draft_catalogs PRIMARY KEY (id), \n\tCONSTRAINT fk_draft_catalogs_feature_id_feature_versions FOREIGN KEY(feature_id, dataset_id) REFERENCES feature_versions (id, dataset_id), \n\tCONSTRAINT fk_draft_catalogs_pricing_id_pricing_versions FOREIGN KEY(pricing_id, feature_id) REFERENCES pricing_versions (id, feature_id), \n\tCONSTRAINT fk_draft_catalogs_graph_id_graph_versions FOREIGN KEY(graph_id, dataset_id) REFERENCES graph_versions (id, dataset_id), \n\tCONSTRAINT ck_draft_catalogs_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT fk_draft_catalogs_dataset_id_dataset_versions FOREIGN KEY(dataset_id) REFERENCES dataset_versions (id), \n\tCONSTRAINT fk_draft_catalogs_rules_id_rules_versions FOREIGN KEY(rules_id) REFERENCES rules_versions (id), \n\tCONSTRAINT fk_draft_catalogs_scoring_id_scoring_versions FOREIGN KEY(scoring_id) REFERENCES scoring_versions (id)\n)\n\n")
    op.execute('\nCREATE TABLE catalog_activations (\n\tid SERIAL NOT NULL, \n\tcatalog_id VARCHAR(100) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_catalog_activations PRIMARY KEY (id), \n\tCONSTRAINT fk_catalog_activations_catalog_id_draft_catalogs FOREIGN KEY(catalog_id) REFERENCES draft_catalogs (id)\n)\n\n')
    op.execute("\nCREATE TABLE draft_runtime (\n\tdraft_id UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\tcatalog_id VARCHAR(100) NOT NULL, \n\tcreation_request_id UUID NOT NULL, \n\tcreation_body_hash VARCHAR(64) NOT NULL, \n\tcreation_response JSONB NOT NULL, \n\tcurrent_offer_id UUID, \n\trecast_cache JSONB NOT NULL, \n\tCONSTRAINT pk_draft_runtime PRIMARY KEY (draft_id), \n\tCONSTRAINT uq_draft_creation_request UNIQUE (session_id, creation_request_id), \n\tCONSTRAINT fk_runtime_current_offer FOREIGN KEY(current_offer_id, draft_id) REFERENCES offers (id, draft_id), \n\tCONSTRAINT ck_draft_runtime_hash CHECK (creation_body_hash ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT fk_draft_runtime_draft_id_drafts FOREIGN KEY(draft_id) REFERENCES drafts (id), \n\tCONSTRAINT fk_draft_runtime_session_id_guest_sessions FOREIGN KEY(session_id) REFERENCES guest_sessions (id), \n\tCONSTRAINT fk_draft_runtime_catalog_id_draft_catalogs FOREIGN KEY(catalog_id) REFERENCES draft_catalogs (id)\n)\n\n")
    op.execute("""
CREATE FUNCTION cd_phase7_graph_pin() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM graph_versions WHERE id=NEW.graph_id AND dataset_id=NEW.dataset_id AND sealed) THEN
  RAISE EXCEPTION 'new graph pin must use a compatible sealed graph' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER graph_pin BEFORE INSERT ON drafts FOR EACH ROW WHEN (NEW.graph_id IS NOT NULL) EXECUTE FUNCTION cd_phase7_graph_pin()")
    op.execute("CREATE TRIGGER seal_guard BEFORE INSERT OR UPDATE OR DELETE ON draft_catalogs FOR EACH ROW EXECUTE FUNCTION cd_seal_guard()")
    for table, column in [('dataset_versions','dataset_id'),('feature_versions','feature_id'),('pricing_versions','pricing_id'),('graph_versions','graph_id'),('rules_versions','rules_id'),('scoring_versions','scoring_id')]:
        op.execute(f"CREATE TRIGGER source_{column} BEFORE INSERT ON draft_catalogs FOR EACH ROW EXECUTE FUNCTION cd_sealed_dependency('{table}','{column}')")
    op.execute("CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON catalog_activations FOR EACH ROW EXECUTE FUNCTION cd_append_only()")
    op.execute("CREATE TRIGGER sealed_dependency BEFORE INSERT ON catalog_activations FOR EACH ROW EXECUTE FUNCTION cd_sealed_dependency('draft_catalogs','catalog_id')")
    op.execute("""
CREATE FUNCTION cd_session_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'retain guest session history' USING ERRCODE='23514'; END IF;
 IF OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL OR (to_jsonb(NEW)-'revoked_at') IS DISTINCT FROM (to_jsonb(OLD)-'revoked_at') THEN
  RAISE EXCEPTION 'only session revocation is permitted' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER session_guard BEFORE UPDATE OR DELETE ON guest_sessions FOR EACH ROW EXECUTE FUNCTION cd_session_guard()")
    op.execute("""
CREATE FUNCTION cd_runtime_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d drafts%ROWTYPE; c draft_catalogs%ROWTYPE; owner_hash text;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'retain draft creation history' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (to_jsonb(NEW)-ARRAY['current_offer_id','recast_cache']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['current_offer_id','recast_cache']) THEN
   RAISE EXCEPTION 'draft ownership and creation receipt are frozen' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
 END IF;
 SELECT * INTO d FROM drafts WHERE id=NEW.draft_id;
 SELECT * INTO c FROM draft_catalogs WHERE id=NEW.catalog_id AND sealed;
 SELECT token_hash INTO owner_hash FROM guest_sessions WHERE id=NEW.session_id AND revoked_at IS NULL AND expires_at>now();
 IF owner_hash IS NULL OR owner_hash IS DISTINCT FROM d.owner_key_hash OR c.id IS NULL
 OR (d.dataset_id,d.feature_id,d.pricing_id,d.graph_id,d.rules_id,d.scoring_id) IS DISTINCT FROM
    (c.dataset_id,c.feature_id,c.pricing_id,c.graph_id,c.rules_id,c.scoring_id) THEN
  RAISE EXCEPTION 'draft runtime requires matching owner and sealed catalog pins' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER runtime_guard BEFORE INSERT OR UPDATE OR DELETE ON draft_runtime FOR EACH ROW EXECUTE FUNCTION cd_runtime_guard()")


def downgrade():
    op.execute("""DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM drafts WHERE graph_id IS NOT NULL) THEN
  RAISE EXCEPTION 'Phase 7 drafts exist; retain their ownership and graph pins instead of downgrading' USING ERRCODE='23514';
 END IF;
END $$""")
    for table in ('draft_runtime','catalog_activations','draft_catalogs','guest_sessions'):
        op.drop_table(table)
    op.execute('DROP TRIGGER graph_pin ON drafts')
    op.execute('DROP FUNCTION cd_runtime_guard()')
    op.execute('DROP FUNCTION cd_session_guard()')
    op.execute('DROP FUNCTION cd_phase7_graph_pin()')
    op.drop_constraint('fk_drafts_graph_dataset','drafts',type_='foreignkey')
    op.drop_constraint('uq_offers_id_draft','offers',type_='unique')
    op.drop_column('drafts','graph_id')
