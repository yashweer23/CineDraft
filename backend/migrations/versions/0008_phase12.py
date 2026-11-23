"""Link explicitly requested practice replays; existing drafts are not rewritten."""
from alembic import op
revision='0008_phase12'
down_revision='0007_phase11'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('''CREATE TABLE draft_replays (
	source_id UUID NOT NULL, 
	request_id UUID NOT NULL, 
	child_id UUID NOT NULL, 
	CONSTRAINT pk_draft_replays PRIMARY KEY (source_id, request_id), 
	CONSTRAINT ck_draft_replays_distinct_drafts CHECK (source_id <> child_id), 
	CONSTRAINT fk_draft_replays_source_id_drafts FOREIGN KEY(source_id) REFERENCES drafts (id), 
	CONSTRAINT uq_draft_replays_child_id UNIQUE (child_id), 
	CONSTRAINT fk_draft_replays_child_id_drafts FOREIGN KEY(child_id) REFERENCES drafts (id)
)''')
    op.execute('CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON draft_replays FOR EACH ROW EXECUTE FUNCTION cd_append_only()')
    op.execute('''CREATE FUNCTION cd_replay_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM drafts parent JOIN draft_runtime pr ON pr.draft_id=parent.id
          JOIN drafts child ON child.id=NEW.child_id JOIN draft_runtime cr ON cr.draft_id=child.id
          JOIN results r ON r.draft_id=parent.id
          WHERE parent.id=NEW.source_id AND parent.status='results_available' AND child.revision=0
          AND parent.genre_id=child.genre_id AND parent.tier=child.tier AND pr.catalog_id=cr.catalog_id)
          OR EXISTS (SELECT 1 FROM challenge_attempts a JOIN daily_challenges d ON d.id=a.challenge_id
             WHERE a.draft_id=NEW.source_id AND clock_timestamp()<d.closes_at)
          OR EXISTS (SELECT 1 FROM challenge_attempts WHERE draft_id=NEW.child_id) THEN
             RAISE EXCEPTION 'invalid practice replay link' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END $$''')
    op.execute('CREATE TRIGGER replay_guard BEFORE INSERT ON draft_replays FOR EACH ROW EXECUTE FUNCTION cd_replay_guard()')

def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM draft_replays) THEN RAISE EXCEPTION 'preserve existing replay history' USING ERRCODE='23514'; END IF; END $$")
    op.drop_table('draft_replays');op.execute('DROP FUNCTION cd_replay_guard()')
