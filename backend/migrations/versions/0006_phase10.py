"""Accounts, immutable guest claims and version-pinned daily competitions."""
from alembic import op
revision='0006_phase10'
down_revision='0005_phase8'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("\nCREATE TABLE accounts (\n\tid UUID NOT NULL, \n\tusername VARCHAR(32) NOT NULL, \n\tpassword_hash VARCHAR(256) NOT NULL, \n\tprimary_guest_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_accounts PRIMARY KEY (id), \n\tCONSTRAINT ck_accounts_username CHECK (username ~ '^[a-z0-9_]{3,32}$'), \n\tCONSTRAINT uq_accounts_username UNIQUE (username), \n\tCONSTRAINT uq_accounts_primary_guest_id UNIQUE (primary_guest_id), \n\tCONSTRAINT fk_accounts_primary_guest_id_guest_sessions FOREIGN KEY(primary_guest_id) REFERENCES guest_sessions (id)\n)\n\n")
    op.execute("\nCREATE TABLE account_sessions (\n\tid UUID NOT NULL, \n\taccount_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tCONSTRAINT pk_account_sessions PRIMARY KEY (id), \n\tCONSTRAINT ck_account_sessions_hash CHECK (token_hash ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT ck_account_sessions_expiry CHECK (expires_at > created_at), \n\tCONSTRAINT fk_account_sessions_account_id_accounts FOREIGN KEY(account_id) REFERENCES accounts (id), \n\tCONSTRAINT uq_account_sessions_token_hash UNIQUE (token_hash)\n)\n\n")
    op.execute('CREATE INDEX ix_account_sessions_account_id ON account_sessions (account_id)')
    op.execute('\nCREATE TABLE account_ownership (\n\tguest_session_id UUID NOT NULL, \n\taccount_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_account_ownership PRIMARY KEY (guest_session_id), \n\tCONSTRAINT fk_account_ownership_guest_session_id_guest_sessions FOREIGN KEY(guest_session_id) REFERENCES guest_sessions (id), \n\tCONSTRAINT fk_account_ownership_account_id_accounts FOREIGN KEY(account_id) REFERENCES accounts (id)\n)\n\n')
    op.execute('CREATE INDEX ix_account_ownership_account_id ON account_ownership (account_id)')
    op.execute('\nCREATE TABLE auth_throttles (\n\tbucket VARCHAR(80) NOT NULL, \n\tevents JSONB NOT NULL, \n\tCONSTRAINT pk_auth_throttles PRIMARY KEY (bucket)\n)\n\n')
    op.execute("\nCREATE TABLE daily_challenges (\n\tid VARCHAR(80) NOT NULL, \n\tcatalog_id VARCHAR(100) NOT NULL, \n\tgenre_id VARCHAR(40) NOT NULL, \n\ttier VARCHAR(16) NOT NULL, \n\topens_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcloses_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\ttimezone VARCHAR(80) NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tconfig_hash VARCHAR(64) NOT NULL, \n\tseed VARCHAR(64) NOT NULL, \n\tseed_commitment VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_daily_challenges PRIMARY KEY (id), \n\tCONSTRAINT ck_daily_challenges_window CHECK (closes_at > opens_at), \n\tCONSTRAINT ck_daily_challenges_tier CHECK (tier IN ('indie', 'studio', 'blockbuster')), \n\tCONSTRAINT ck_daily_challenges_hashes CHECK (config_hash ~ '^[0-9a-f]{64}$' AND seed ~ '^[0-9a-f]{64}$' AND seed_commitment ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT fk_daily_challenges_catalog_id_draft_catalogs FOREIGN KEY(catalog_id) REFERENCES draft_catalogs (id), \n\tCONSTRAINT fk_daily_challenges_genre_id_genres FOREIGN KEY(genre_id) REFERENCES genres (id)\n)\n\n")
    op.execute('CREATE INDEX ix_daily_challenges_opens_at ON daily_challenges (opens_at, id)')
    op.execute('\nCREATE TABLE challenge_attempts (\n\tdraft_id UUID NOT NULL, \n\tchallenge_id VARCHAR(80) NOT NULL, \n\taccount_id UUID NOT NULL, \n\trequest_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tCONSTRAINT pk_challenge_attempts PRIMARY KEY (draft_id), \n\tCONSTRAINT uq_challenge_account_attempt UNIQUE (challenge_id, account_id), \n\tCONSTRAINT uq_challenge_creation_request UNIQUE (account_id, request_id), \n\tCONSTRAINT uq_challenge_attempt_identity UNIQUE (draft_id, challenge_id, account_id), \n\tCONSTRAINT fk_challenge_attempts_draft_id_drafts FOREIGN KEY(draft_id) REFERENCES drafts (id), \n\tCONSTRAINT fk_challenge_attempts_challenge_id_daily_challenges FOREIGN KEY(challenge_id) REFERENCES daily_challenges (id), \n\tCONSTRAINT fk_challenge_attempts_account_id_accounts FOREIGN KEY(account_id) REFERENCES accounts (id)\n)\n\n')
    op.execute("\nCREATE TABLE challenge_submissions (\n\tdraft_id UUID NOT NULL, \n\tchallenge_id VARCHAR(80) NOT NULL, \n\taccount_id UUID NOT NULL, \n\toutput_hash VARCHAR(64) NOT NULL, \n\tstudio_score INTEGER NOT NULL, \n\tprofit_usd BIGINT NOT NULL, \n\tsubmitted_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tCONSTRAINT pk_challenge_submissions PRIMARY KEY (draft_id), \n\tCONSTRAINT fk_challenge_submissions_draft_id_challenge_attempts FOREIGN KEY(draft_id, challenge_id, account_id) REFERENCES challenge_attempts (draft_id, challenge_id, account_id), \n\tCONSTRAINT uq_challenge_submission UNIQUE (challenge_id, account_id), \n\tCONSTRAINT ck_challenge_submissions_score CHECK (studio_score BETWEEN 0 AND 100), \n\tCONSTRAINT ck_challenge_submissions_hash CHECK (output_hash ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT fk_challenge_submissions_draft_id_results FOREIGN KEY(draft_id) REFERENCES results (draft_id), \n\tCONSTRAINT fk_challenge_submissions_challenge_id_daily_challenges FOREIGN KEY(challenge_id) REFERENCES daily_challenges (id), \n\tCONSTRAINT fk_challenge_submissions_account_id_accounts FOREIGN KEY(account_id) REFERENCES accounts (id)\n)\n\n")
    op.execute('CREATE INDEX ix_challenge_ranking ON challenge_submissions (challenge_id, studio_score, profit_usd, submitted_at)')
    for table in ('account_ownership','daily_challenges','challenge_attempts','challenge_submissions'):
        op.execute(f'CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION cd_append_only()')
    op.execute("CREATE TRIGGER source_catalog BEFORE INSERT ON daily_challenges FOR EACH ROW EXECUTE FUNCTION cd_sealed_dependency('draft_catalogs','catalog_id')")
    op.execute("""
CREATE FUNCTION cd_account_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' OR (to_jsonb(NEW)-'password_hash') IS DISTINCT FROM (to_jsonb(OLD)-'password_hash') THEN
  RAISE EXCEPTION 'retain account identity and ownership' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER identity_guard BEFORE UPDATE OR DELETE ON accounts FOR EACH ROW EXECUTE FUNCTION cd_account_guard()')
    op.execute("""
CREATE FUNCTION cd_account_session_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'retain session history' USING ERRCODE='23514'; END IF;
 IF (to_jsonb(NEW)-'revoked_at') IS DISTINCT FROM (to_jsonb(OLD)-'revoked_at')
 OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at) THEN
  RAISE EXCEPTION 'account sessions can only be revoked once' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER identity_guard BEFORE UPDATE OR DELETE ON account_sessions FOR EACH ROW EXECUTE FUNCTION cd_account_session_guard()')
    op.execute("""
CREATE OR REPLACE FUNCTION cd_runtime_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
 SELECT token_hash INTO owner_hash FROM guest_sessions g WHERE g.id=NEW.session_id AND
  ((g.revoked_at IS NULL AND g.expires_at>clock_timestamp()) OR EXISTS (SELECT 1 FROM account_ownership WHERE guest_session_id=g.id));
 IF owner_hash IS NULL OR owner_hash IS DISTINCT FROM d.owner_key_hash OR c.id IS NULL
 OR (d.dataset_id,d.feature_id,d.pricing_id,d.graph_id,d.rules_id,d.scoring_id) IS DISTINCT FROM
    (c.dataset_id,c.feature_id,c.pricing_id,c.graph_id,c.rules_id,c.scoring_id) THEN
  RAISE EXCEPTION 'draft runtime requires matching owner and sealed catalog pins' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("""
CREATE FUNCTION cd_challenge_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c daily_challenges%ROWTYPE; d drafts%ROWTYPE; rt draft_runtime%ROWTYPE;
BEGIN
 SELECT * INTO c FROM daily_challenges WHERE id=NEW.challenge_id;
 SELECT * INTO d FROM drafts WHERE id=NEW.draft_id FOR UPDATE;
 SELECT * INTO rt FROM draft_runtime WHERE draft_id=NEW.draft_id;
 IF c.id IS NULL OR d.id IS NULL OR rt.draft_id IS NULL OR d.status<>'awaiting_pick' OR d.revision<>0
 OR rt.catalog_id<>c.catalog_id OR rt.creation_request_id<>NEW.request_id
 OR (d.genre_id,d.tier,d.seed) IS DISTINCT FROM (c.genre_id,c.tier,c.seed)
 OR NOT EXISTS (SELECT 1 FROM account_ownership WHERE guest_session_id=rt.session_id AND account_id=NEW.account_id)
 OR EXISTS (SELECT 1 FROM picks WHERE draft_id=d.id) THEN
  RAISE EXCEPTION 'official attempt requires a new owned draft with exact challenge pins' USING ERRCODE='23514';
 END IF;
 NEW.created_at=clock_timestamp();
 IF NEW.created_at<c.opens_at OR NEW.created_at>=c.closes_at THEN
  RAISE EXCEPTION 'challenge is outside its attempt window' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER attempt_guard BEFORE INSERT ON challenge_attempts FOR EACH ROW EXECUTE FUNCTION cd_challenge_attempt_guard()')
    op.execute("""
CREATE FUNCTION cd_challenge_submission_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c daily_challenges%ROWTYPE; r results%ROWTYPE;
BEGIN
 SELECT * INTO c FROM daily_challenges WHERE id=NEW.challenge_id;
 SELECT * INTO r FROM results WHERE draft_id=NEW.draft_id;
 NEW.submitted_at=clock_timestamp();
 IF c.id IS NULL OR r.draft_id IS NULL OR NEW.submitted_at<c.opens_at OR NEW.submitted_at>=c.closes_at
 OR NEW.output_hash IS DISTINCT FROM r.output_hash
 OR NEW.studio_score IS DISTINCT FROM (r.outputs->>'studio_score')::integer
 OR NEW.profit_usd IS DISTINCT FROM (r.outputs->>'profit_usd')::bigint
 OR r.outputs->>'schema_version' IS DISTINCT FROM 'phase8-v1'
 OR NOT EXISTS (SELECT 1 FROM drafts WHERE id=NEW.draft_id AND status='results_available') THEN
  RAISE EXCEPTION 'submission requires a matching official result within its deadline' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER submission_guard BEFORE INSERT ON challenge_submissions FOR EACH ROW EXECUTE FUNCTION cd_challenge_submission_guard()')
    op.execute("""
CREATE FUNCTION cd_challenge_action_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c daily_challenges%ROWTYPE;
BEGIN
 SELECT dc.* INTO c FROM daily_challenges dc JOIN challenge_attempts ca ON ca.challenge_id=dc.id WHERE ca.draft_id=NEW.draft_id;
 IF c.id IS NOT NULL AND NEW.command<>'abandon' AND (clock_timestamp()<c.opens_at OR clock_timestamp()>=c.closes_at) THEN
  RAISE EXCEPTION 'challenge command missed its deadline' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute('CREATE TRIGGER challenge_deadline BEFORE INSERT ON action_records FOR EACH ROW EXECUTE FUNCTION cd_challenge_action_guard()')


def downgrade():
    op.execute("""DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM accounts) OR EXISTS (SELECT 1 FROM daily_challenges) THEN
  RAISE EXCEPTION 'Phase 10 account or challenge history exists; retain ownership and competition protections' USING ERRCODE='23514';
 END IF;
END $$""")
    op.execute('DROP TRIGGER challenge_deadline ON action_records')
    # Restore the original guest-only guard before dropping account tables.
    op.execute(ORIGINAL_RUNTIME_GUARD)
    for table in ('challenge_submissions','challenge_attempts','daily_challenges','auth_throttles','account_ownership','account_sessions','accounts'):
        op.drop_table(table)
    for function in ('cd_challenge_action_guard','cd_challenge_submission_guard','cd_challenge_attempt_guard','cd_account_session_guard','cd_account_guard'):
        op.execute(f'DROP FUNCTION {function}()')


ORIGINAL_RUNTIME_GUARD="CREATE OR REPLACE FUNCTION cd_runtime_guard() RETURNS trigger LANGUAGE plpgsql AS $$\nDECLARE d drafts%ROWTYPE; c draft_catalogs%ROWTYPE; owner_hash text;\nBEGIN\n IF TG_OP='DELETE' THEN RAISE EXCEPTION 'retain draft creation history' USING ERRCODE='23514'; END IF;\n IF TG_OP='UPDATE' THEN\n  IF (to_jsonb(NEW)-ARRAY['current_offer_id','recast_cache']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['current_offer_id','recast_cache']) THEN\n   RAISE EXCEPTION 'draft ownership and creation receipt are frozen' USING ERRCODE='23514';\n  END IF;\n  RETURN NEW;\n END IF;\n SELECT * INTO d FROM drafts WHERE id=NEW.draft_id;\n SELECT * INTO c FROM draft_catalogs WHERE id=NEW.catalog_id AND sealed;\n SELECT token_hash INTO owner_hash FROM guest_sessions WHERE id=NEW.session_id AND revoked_at IS NULL AND expires_at>now();\n IF owner_hash IS NULL OR owner_hash IS DISTINCT FROM d.owner_key_hash OR c.id IS NULL\n OR (d.dataset_id,d.feature_id,d.pricing_id,d.graph_id,d.rules_id,d.scoring_id) IS DISTINCT FROM\n    (c.dataset_id,c.feature_id,c.pricing_id,c.graph_id,c.rules_id,c.scoring_id) THEN\n  RAISE EXCEPTION 'draft runtime requires matching owner and sealed catalog pins' USING ERRCODE='23514';\n END IF;\n RETURN NEW;\nEND $$"
