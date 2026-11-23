-- If transaction-start timestamps reverse, do not expose a later revision until its predecessors are visible.
CREATE TEMP VIEW e AS SELECT * FROM (SELECT ev.*,MAX(ev.at_us) OVER (PARTITION BY ev.session_key ORDER BY ev.revision,ev.kind='whatif',ev.at_us,ev.event_key ROWS UNBOUNDED PRECEDING) visible_us
FROM events ev JOIN cohort c USING(session_key)) WHERE visible_us <= (SELECT as_of FROM cut);
CREATE TEMP VIEW o AS SELECT op.* FROM opportunities op JOIN e issuer ON issuer.event_key=op.event_key;
CREATE TEMP VIEW progress AS SELECT c.*,COUNT(CASE WHEN e.kind='pick' THEN 1 END) picks,
 MAX(CASE WHEN e.kind='finalize' THEN 1 ELSE 0 END) finalized,
 MAX(CASE WHEN e.kind='release' THEN 1 ELSE 0 END) released,
 MAX(CASE WHEN e.kind='abandon' THEN 1 ELSE 0 END) abandoned
 FROM cohort c LEFT JOIN e USING(session_key) GROUP BY c.session_key;
CREATE TEMP VIEW final_roster AS SELECT * FROM (
 SELECT e.*,ROW_NUMBER() OVER(PARTITION BY e.session_key,e.slot ORDER BY revision DESC) AS slot_rank
 FROM e WHERE e.kind IN ('pick','confirm_recast')) WHERE slot_rank=1;
