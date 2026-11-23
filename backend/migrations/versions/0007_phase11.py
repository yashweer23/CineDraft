"""Immutable hypothetical analyses and independent request receipts."""
from alembic import op
revision='0007_phase11'
down_revision='0006_phase10'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("\nCREATE TABLE whatif_analyses (\n\tid UUID NOT NULL, \n\tdraft_id UUID NOT NULL, \n\tsource_input_hash VARCHAR(64) NOT NULL, \n\tsource_output_hash VARCHAR(64) NOT NULL, \n\tversion VARCHAR(40) NOT NULL, \n\tslot VARCHAR(32) NOT NULL, \n\tperson_id UUID NOT NULL, \n\tinput_hash VARCHAR(64) NOT NULL, \n\tinputs JSONB NOT NULL, \n\toutput_hash VARCHAR(64) NOT NULL, \n\toutputs JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tCONSTRAINT pk_whatif_analyses PRIMARY KEY (id), \n\tCONSTRAINT fk_whatif_analyses_draft_id_draft_snapshots FOREIGN KEY(draft_id, source_input_hash) REFERENCES draft_snapshots (draft_id, input_hash), \n\tCONSTRAINT uq_whatif_variant UNIQUE (draft_id, version, slot, person_id), \n\tCONSTRAINT uq_whatif_identity UNIQUE (id, draft_id), \n\tCONSTRAINT ck_whatif_analyses_slot CHECK (slot IN ('director', 'lead', 'co_lead', 'supporting_1', 'supporting_2', 'writer', 'cinematographer', 'composer')), \n\tCONSTRAINT ck_whatif_analyses_hashes CHECK (input_hash ~ '^[0-9a-f]{64}$' AND output_hash ~ '^[0-9a-f]{64}$' AND source_output_hash ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT fk_whatif_analyses_draft_id_results FOREIGN KEY(draft_id) REFERENCES results (draft_id), \n\tCONSTRAINT fk_whatif_analyses_person_id_people FOREIGN KEY(person_id) REFERENCES people (id)\n)\n\n")
    op.execute('CREATE INDEX ix_whatif_history ON whatif_analyses (draft_id, created_at, id)')
    op.execute("\nCREATE TABLE whatif_receipts (\n\tdraft_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tanalysis_id UUID NOT NULL, \n\tbody_hash VARCHAR(64) NOT NULL, \n\trequest_body JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tCONSTRAINT pk_whatif_receipts PRIMARY KEY (draft_id, request_id), \n\tCONSTRAINT fk_whatif_receipts_analysis_id_whatif_analyses FOREIGN KEY(analysis_id, draft_id) REFERENCES whatif_analyses (id, draft_id), \n\tCONSTRAINT ck_whatif_receipts_hash CHECK (body_hash ~ '^[0-9a-f]{64}$')\n)\n\n")
    for table in ('whatif_analyses','whatif_receipts'):
        op.execute(f'CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION cd_append_only()')
    op.execute("""
CREATE FUNCTION cd_whatif_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r results%ROWTYPE; a whatif_analyses%ROWTYPE;
BEGIN
 IF EXISTS (SELECT 1 FROM challenge_attempts ca JOIN daily_challenges dc ON dc.id=ca.challenge_id WHERE ca.draft_id=NEW.draft_id AND clock_timestamp()<dc.closes_at) THEN
  RAISE EXCEPTION 'hypothetical lab is embargoed until challenge closes' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS (SELECT 1 FROM drafts WHERE id=NEW.draft_id AND status='results_available') THEN
  RAISE EXCEPTION 'hypothetical lab requires a released film' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME='whatif_analyses' THEN
  SELECT * INTO r FROM results WHERE draft_id=NEW.draft_id;
  IF r.draft_id IS NULL OR r.input_hash IS DISTINCT FROM NEW.source_input_hash OR r.output_hash IS DISTINCT FROM NEW.source_output_hash
  OR r.outputs->>'schema_version' IS DISTINCT FROM 'phase8-v1'
  OR NEW.inputs->>'schema_version' IS DISTINCT FROM 'phase11-inputs-v1'
  OR NEW.outputs->>'schema_version' IS DISTINCT FROM 'phase11-result-v1'
  OR NEW.outputs->>'hypothetical' IS DISTINCT FROM 'true'
  OR NEW.inputs->>'draft_id' IS DISTINCT FROM NEW.draft_id::text
  OR NEW.outputs->>'draft_id' IS DISTINCT FROM NEW.draft_id::text
  OR NEW.inputs->>'slot' IS DISTINCT FROM NEW.slot OR NEW.inputs->>'person_id' IS DISTINCT FROM NEW.person_id::text THEN
   RAISE EXCEPTION 'hypothetical report requires matching source and identity' USING ERRCODE='23514';
  END IF;
 ELSE
  SELECT * INTO a FROM whatif_analyses WHERE id=NEW.analysis_id AND draft_id=NEW.draft_id;
  IF a.id IS NULL OR NEW.request_body->>'request_id' IS DISTINCT FROM NEW.request_id::text
  OR NEW.request_body->>'slot' IS DISTINCT FROM a.slot OR NEW.request_body->>'person_id' IS DISTINCT FROM a.person_id::text THEN
   RAISE EXCEPTION 'hypothetical receipt must match its report and request' USING ERRCODE='23514';
  END IF;
 END IF;
 NEW.created_at=clock_timestamp();
 RETURN NEW;
END $$
""")
    for table in ('whatif_analyses','whatif_receipts'):
        op.execute(f'CREATE TRIGGER source_guard BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION cd_whatif_guard()')

def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM whatif_analyses) OR EXISTS (SELECT 1 FROM whatif_receipts) THEN
 RAISE EXCEPTION 'retain hypothetical analysis history; use a deliberate backup restore instead' USING ERRCODE='23514'; END IF; END $$""")
    op.drop_table('whatif_receipts');op.drop_table('whatif_analyses');op.execute('DROP FUNCTION cd_whatif_guard()')
