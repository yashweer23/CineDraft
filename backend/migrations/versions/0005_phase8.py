"""Immutable simulation attempts and Phase 8 result consistency guards."""
from alembic import op
revision='0005_phase8'
down_revision='0004_phase7'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("\nCREATE TABLE simulation_attempts (\n\tid UUID NOT NULL, \n\tdraft_id UUID NOT NULL, \n\tinput_hash VARCHAR(64) NOT NULL, \n\tattempt_number INTEGER NOT NULL, \n\tcommand VARCHAR(24) NOT NULL, \n\trequest_id UUID NOT NULL, \n\trevision INTEGER NOT NULL, \n\tsimulation_version VARCHAR(100) NOT NULL, \n\tengine_manifest_hash VARCHAR(64) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\terror_code VARCHAR(80), \n\toutput_hash VARCHAR(64), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_simulation_attempts PRIMARY KEY (id), \n\tCONSTRAINT fk_simulation_attempts_draft_id_draft_snapshots FOREIGN KEY(draft_id, input_hash) REFERENCES draft_snapshots (draft_id, input_hash), \n\tCONSTRAINT uq_simulation_attempt_number UNIQUE (draft_id, attempt_number), \n\tCONSTRAINT uq_simulation_attempt_request UNIQUE (draft_id, command, request_id), \n\tCONSTRAINT uq_simulation_attempt_revision UNIQUE (draft_id, revision), \n\tCONSTRAINT ck_simulation_attempts_command CHECK (command IN ('release', 'retry_simulation')), \n\tCONSTRAINT ck_simulation_attempts_status CHECK (status IN ('succeeded', 'failed')), \n\tCONSTRAINT ck_simulation_attempts_counters CHECK (attempt_number > 0 AND revision > 0), \n\tCONSTRAINT ck_simulation_attempts_manifest_hash CHECK (engine_manifest_hash ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT ck_simulation_attempts_outcome CHECK ((status='succeeded' AND error_code IS NULL AND output_hash IS NOT NULL AND output_hash ~ '^[0-9a-f]{64}$') OR (status='failed' AND error_code IS NOT NULL AND error_code='engine_error' AND output_hash IS NULL))\n)\n\n")

    op.execute("CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON simulation_attempts FOR EACH ROW EXECUTE FUNCTION cd_append_only()")
    op.execute("""
CREATE FUNCTION cd_phase8_result_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d drafts%ROWTYPE;
BEGIN
 SELECT * INTO d FROM drafts WHERE id=NEW.draft_id FOR UPDATE;
 IF d.id IS NULL OR d.status <> 'simulation_running' OR d.simulation_version <> NEW.simulation_version
 OR NEW.outputs->>'draft_id' IS DISTINCT FROM NEW.draft_id::text
 OR NEW.outputs->>'input_hash' IS DISTINCT FROM NEW.input_hash
 OR NEW.outputs->>'simulation_id' IS DISTINCT FROM NEW.simulation_id::text
 OR NEW.outputs->>'simulation_version' IS DISTINCT FROM NEW.simulation_version THEN
  RAISE EXCEPTION 'Phase 8 result must match its running draft and frozen inputs' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER phase8_result_guard BEFORE INSERT ON results FOR EACH ROW WHEN (NEW.outputs->>'schema_version'='phase8-v1') EXECUTE FUNCTION cd_phase8_result_guard()")
    op.execute("""
CREATE FUNCTION cd_simulation_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d drafts%ROWTYPE; previous_count integer;
BEGIN
 SELECT * INTO d FROM drafts WHERE id=NEW.draft_id FOR UPDATE;
 SELECT count(*) INTO previous_count FROM simulation_attempts WHERE draft_id=NEW.draft_id;
 IF d.id IS NULL OR d.revision<>NEW.revision OR d.simulation_version<>NEW.simulation_version
 OR NEW.attempt_number<>previous_count+1 THEN
  RAISE EXCEPTION 'simulation attempt must match the serialized draft revision and sequence' USING ERRCODE='23514';
 END IF;
 IF NEW.status='succeeded' THEN
  IF d.status<>'results_available' OR NOT EXISTS
    (SELECT 1 FROM results WHERE draft_id=NEW.draft_id AND input_hash=NEW.input_hash AND output_hash=NEW.output_hash AND simulation_version=NEW.simulation_version) THEN
   RAISE EXCEPTION 'successful attempt requires its immutable result' USING ERRCODE='23514';
  END IF;
 ELSE
  IF d.status<>'simulation_failed' OR EXISTS (SELECT 1 FROM results WHERE draft_id=NEW.draft_id) THEN
   RAISE EXCEPTION 'failed attempt cannot have a result' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER outcome_guard BEFORE INSERT ON simulation_attempts FOR EACH ROW EXECUTE FUNCTION cd_simulation_attempt_guard()")


def downgrade():
    op.execute("""DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM simulation_attempts) OR EXISTS (SELECT 1 FROM results WHERE outputs->>'schema_version'='phase8-v1') THEN
  RAISE EXCEPTION 'Phase 8 release history exists; retain attempts and result guards' USING ERRCODE='23514';
 END IF;
END $$""")
    op.drop_table('simulation_attempts')
    op.execute('DROP TRIGGER phase8_result_guard ON results')
    op.execute('DROP FUNCTION cd_simulation_attempt_guard()')
    op.execute('DROP FUNCTION cd_phase8_result_guard()')
