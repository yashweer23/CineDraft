"""Phase 6 immutable collaboration graph and source-credit evidence.

Revision ID: 0003_phase6
Revises: 0002_phase4
DDL below is frozen; never import current application models into migrations.
"""
from alembic import op
revision = "0003_phase6"
down_revision = "0002_phase4"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("\nCREATE TABLE graph_versions (\n\tdataset_id VARCHAR(100) NOT NULL, \n\talgorithm_version VARCHAR(100) NOT NULL, \n\tid VARCHAR(100) NOT NULL, \n\tconfiguration JSONB NOT NULL, \n\tcontent_hash VARCHAR(64) NOT NULL, \n\tsealed BOOLEAN DEFAULT 'false' NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_graph_versions PRIMARY KEY (id), \n\tCONSTRAINT uq_graph_versions_id_dataset_id UNIQUE (id, dataset_id), \n\tCONSTRAINT ck_graph_versions_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT fk_graph_versions_dataset_id_dataset_versions FOREIGN KEY(dataset_id) REFERENCES dataset_versions (id)\n)\n\n")
    op.execute("\nCREATE TABLE graph_nodes (\n\tgraph_id VARCHAR(100) NOT NULL, \n\tperson_id UUID NOT NULL, \n\trole VARCHAR(24) NOT NULL, \n\tdataset_id VARCHAR(100) NOT NULL, \n\tfilm_count INTEGER NOT NULL, \n\tCONSTRAINT pk_graph_nodes PRIMARY KEY (graph_id, person_id, role), \n\tCONSTRAINT fk_graph_nodes_graph_id_graph_versions FOREIGN KEY(graph_id, dataset_id) REFERENCES graph_versions (id, dataset_id), \n\tCONSTRAINT fk_graph_nodes_dataset_id_person_snapshots FOREIGN KEY(dataset_id, person_id) REFERENCES person_snapshots (dataset_id, person_id), \n\tCONSTRAINT ck_graph_nodes_role CHECK (role IN ('director', 'actor', 'writer', 'cinematographer', 'composer')), \n\tCONSTRAINT ck_graph_nodes_film_count CHECK (film_count > 0)\n)\n\n")
    op.execute("\nCREATE TABLE graph_edges (\n\tgraph_id VARCHAR(100) NOT NULL, \n\tedge_id VARCHAR(64) NOT NULL, \n\tperson_a UUID NOT NULL, \n\trole_a VARCHAR(24) NOT NULL, \n\tperson_b UUID NOT NULL, \n\trole_b VARCHAR(24) NOT NULL, \n\tshared_movie_count INTEGER NOT NULL, \n\tbonus INTEGER NOT NULL, \n\tCONSTRAINT pk_graph_edges PRIMARY KEY (graph_id, edge_id), \n\tCONSTRAINT fk_graph_edges_node_a FOREIGN KEY(graph_id, person_a, role_a) REFERENCES graph_nodes (graph_id, person_id, role), \n\tCONSTRAINT fk_graph_edges_node_b FOREIGN KEY(graph_id, person_b, role_b) REFERENCES graph_nodes (graph_id, person_id, role), \n\tCONSTRAINT uq_graph_edge_pair UNIQUE (graph_id, person_a, role_a, person_b, role_b), \n\tCONSTRAINT ck_graph_edges_canonical_people CHECK (person_a < person_b), \n\tCONSTRAINT ck_graph_edges_edge_hash CHECK (edge_id ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT ck_graph_edges_bonus CHECK (shared_movie_count > 0 AND bonus = LEAST(12, 4 * shared_movie_count))\n)\n\n")
    op.execute('CREATE INDEX ix_graph_edges_count ON graph_edges (graph_id, shared_movie_count)')
    op.execute("\nCREATE TABLE graph_evidence (\n\tgraph_id VARCHAR(100) NOT NULL, \n\tedge_id VARCHAR(64) NOT NULL, \n\tmovie_id UUID NOT NULL, \n\tdataset_id VARCHAR(100) NOT NULL, \n\tjobs_a JSONB NOT NULL, \n\tjobs_b JSONB NOT NULL, \n\tCONSTRAINT pk_graph_evidence PRIMARY KEY (graph_id, edge_id, movie_id), \n\tCONSTRAINT fk_graph_evidence_graph_id_graph_edges FOREIGN KEY(graph_id, edge_id) REFERENCES graph_edges (graph_id, edge_id), \n\tCONSTRAINT fk_graph_evidence_graph_id_graph_versions FOREIGN KEY(graph_id, dataset_id) REFERENCES graph_versions (id, dataset_id), \n\tCONSTRAINT fk_graph_evidence_dataset_id_movie_snapshots FOREIGN KEY(dataset_id, movie_id) REFERENCES movie_snapshots (dataset_id, movie_id), \n\tCONSTRAINT ck_graph_evidence_jobs CHECK (jsonb_typeof(jobs_a) = 'array' AND jsonb_array_length(jobs_a) > 0 AND jsonb_typeof(jobs_b) = 'array' AND jsonb_array_length(jobs_b) > 0)\n)\n\n")
    op.execute("""
CREATE FUNCTION cd_graph_node_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE observed bigint;
BEGIN
 SELECT count(DISTINCT c.movie_id) INTO observed
 FROM credits c JOIN movie_snapshots ms ON ms.dataset_id=c.dataset_id AND ms.movie_id=c.movie_id
 WHERE c.dataset_id=NEW.dataset_id AND c.person_id=NEW.person_id AND c.role=NEW.role AND ms.eligibility='eligible';
 IF observed IS DISTINCT FROM NEW.film_count::bigint THEN
  RAISE EXCEPTION 'graph node needs its exact eligible role film count' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("""
CREATE FUNCTION cd_graph_film_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE edge graph_edges%ROWTYPE; expected_a jsonb; expected_b jsonb;
BEGIN
 SELECT * INTO edge FROM graph_edges WHERE graph_id=NEW.graph_id AND edge_id=NEW.edge_id;
 IF NOT FOUND OR NOT EXISTS (SELECT 1 FROM movie_snapshots WHERE dataset_id=NEW.dataset_id AND movie_id=NEW.movie_id AND eligibility='eligible') THEN
  RAISE EXCEPTION 'graph evidence needs an edge and an eligible source film' USING ERRCODE='23514';
 END IF;
 SELECT jsonb_agg(job ORDER BY job COLLATE "C") INTO expected_a FROM
  (SELECT DISTINCT job FROM credits WHERE dataset_id=NEW.dataset_id AND movie_id=NEW.movie_id AND person_id=edge.person_a AND role=edge.role_a) jobs;
 SELECT jsonb_agg(job ORDER BY job COLLATE "C") INTO expected_b FROM
  (SELECT DISTINCT job FROM credits WHERE dataset_id=NEW.dataset_id AND movie_id=NEW.movie_id AND person_id=edge.person_b AND role=edge.role_b) jobs;
 IF expected_a IS NULL OR expected_b IS NULL OR NEW.jobs_a IS DISTINCT FROM expected_a OR NEW.jobs_b IS DISTINCT FROM expected_b THEN
  RAISE EXCEPTION 'shared film jobs must match both exact credited roles' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("""
CREATE FUNCTION cd_graph_seal_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE node_count bigint; edge_count bigint; evidence_count bigint;
BEGIN
 SELECT count(*) INTO node_count FROM graph_nodes WHERE graph_id=NEW.id;
 SELECT count(*) INTO edge_count FROM graph_edges WHERE graph_id=NEW.id;
 SELECT count(*) INTO evidence_count FROM graph_evidence WHERE graph_id=NEW.id;
 IF node_count=0 OR node_count IS DISTINCT FROM (NEW.configuration->'report'->>'nodes')::bigint
 OR edge_count IS DISTINCT FROM (NEW.configuration->'report'->>'edges')::bigint
 OR evidence_count IS DISTINCT FROM (NEW.configuration->'report'->>'evidence_rows')::bigint THEN
  RAISE EXCEPTION 'graph publication counts do not match manifest' USING ERRCODE='23514';
 END IF;
 IF EXISTS (SELECT 1 FROM graph_edges e WHERE e.graph_id=NEW.id AND e.shared_movie_count <>
   (SELECT count(*) FROM graph_evidence f WHERE f.graph_id=e.graph_id AND f.edge_id=e.edge_id)) THEN
  RAISE EXCEPTION 'graph edge count must match its distinct film evidence' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$
""")
    op.execute("CREATE TRIGGER seal_guard BEFORE INSERT OR UPDATE OR DELETE ON graph_versions FOR EACH ROW EXECUTE FUNCTION cd_seal_guard()")
    op.execute("CREATE TRIGGER sealed_dependency BEFORE INSERT ON graph_versions FOR EACH ROW EXECUTE FUNCTION cd_sealed_dependency('dataset_versions', 'dataset_id')")
    op.execute("CREATE TRIGGER graph_seal_check BEFORE UPDATE ON graph_versions FOR EACH ROW WHEN (NEW.sealed AND NOT OLD.sealed) EXECUTE FUNCTION cd_graph_seal_check()")
    for table in ('graph_nodes', 'graph_edges', 'graph_evidence'):
        op.execute(f"CREATE TRIGGER member_guard BEFORE INSERT OR UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION cd_member_guard('graph_versions', 'graph_id')")
    op.execute("CREATE TRIGGER domain_guard BEFORE INSERT ON graph_nodes FOR EACH ROW EXECUTE FUNCTION cd_graph_node_evidence()")
    op.execute("CREATE TRIGGER domain_guard BEFORE INSERT ON graph_evidence FOR EACH ROW EXECUTE FUNCTION cd_graph_film_evidence()")


def downgrade():
    for table in ('graph_evidence', 'graph_edges', 'graph_nodes', 'graph_versions'):
        op.drop_table(table)
    op.execute("DROP FUNCTION cd_graph_seal_check()")
    op.execute("DROP FUNCTION cd_graph_film_evidence()")
    op.execute("DROP FUNCTION cd_graph_node_evidence()")
