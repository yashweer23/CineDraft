"""Persistent cooperative rooms and exact command receipts."""
from alembic import op
revision = '0009_phase15'
down_revision = '0008_phase12'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""CREATE TABLE draft_rooms (
	id UUID NOT NULL, 
	draft_id UUID NOT NULL, 
	host_id UUID NOT NULL, 
	guest_id UUID, 
	invite_hash VARCHAR(64) NOT NULL, 
	creation_request_id UUID NOT NULL, 
	creation_hash VARCHAR(64) NOT NULL, 
	creation_response JSONB NOT NULL, 
	state VARCHAR(16) NOT NULL, 
	revision INTEGER NOT NULL, 
	turn_seconds INTEGER NOT NULL, 
	deadline TIMESTAMP WITH TIME ZONE, 
	events JSONB NOT NULL, 
	CONSTRAINT pk_draft_rooms PRIMARY KEY (id), 
	CONSTRAINT uq_room_creation UNIQUE (host_id, creation_request_id), 
	CONSTRAINT ck_draft_rooms_different_seats CHECK (guest_id IS NULL OR guest_id <> host_id), 
	CONSTRAINT ck_draft_rooms_bounds CHECK (revision >= 0 AND turn_seconds BETWEEN 30 AND 180), 
	CONSTRAINT ck_draft_rooms_state CHECK (state IN ('waiting', 'active', 'complete', 'cancelled')), 
	CONSTRAINT ck_draft_rooms_deadline CHECK ((state = 'active') = (deadline IS NOT NULL)), 
	CONSTRAINT ck_draft_rooms_two_players CHECK (state <> 'active' OR guest_id IS NOT NULL), 
	CONSTRAINT ck_draft_rooms_hashes CHECK (invite_hash ~ '^[0-9a-f]{64}$' AND creation_hash ~ '^[0-9a-f]{64}$'), 
	CONSTRAINT uq_draft_rooms_draft_id UNIQUE (draft_id), 
	CONSTRAINT fk_draft_rooms_draft_id_drafts FOREIGN KEY(draft_id) REFERENCES drafts (id), 
	CONSTRAINT fk_draft_rooms_host_id_guest_sessions FOREIGN KEY(host_id) REFERENCES guest_sessions (id), 
	CONSTRAINT fk_draft_rooms_guest_id_guest_sessions FOREIGN KEY(guest_id) REFERENCES guest_sessions (id)
)""")
    op.execute('CREATE INDEX ix_room_deadlines ON draft_rooms (state, deadline)')
    op.execute("""CREATE TABLE room_receipts (
	room_id UUID NOT NULL, 
	request_id UUID NOT NULL, 
	actor_id UUID NOT NULL, 
	body_hash VARCHAR(64) NOT NULL, 
	response JSONB NOT NULL, 
	CONSTRAINT pk_room_receipts PRIMARY KEY (room_id, request_id), 
	CONSTRAINT ck_room_receipts_hash CHECK (body_hash ~ '^[0-9a-f]{64}$'), 
	CONSTRAINT fk_room_receipts_room_id_draft_rooms FOREIGN KEY(room_id) REFERENCES draft_rooms (id), 
	CONSTRAINT fk_room_receipts_actor_id_guest_sessions FOREIGN KEY(actor_id) REFERENCES guest_sessions (id)
)""")
    op.execute('CREATE TRIGGER immutable_row BEFORE UPDATE OR DELETE ON room_receipts FOR EACH ROW EXECUTE FUNCTION cd_append_only()')

def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM draft_rooms) THEN RAISE EXCEPTION 'preserve room history' USING ERRCODE='23514'; END IF; END $$")
    op.drop_table('room_receipts')
    op.drop_table('draft_rooms')
