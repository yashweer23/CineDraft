-- Independent reconstruction for the shipped demonstration, with no report views or Python aggregation.
-- Each stable start key contributes once to the denominator. Each official release key contributes once to the numerator.
SELECT s.session_key, st.event_key AS start_evidence, r.event_key AS official_release_evidence
FROM sessions s
JOIN events st ON st.session_key=s.session_key AND st.kind IN ('start','replay_start')
LEFT JOIN events r ON r.session_key=s.session_key AND r.kind='release' AND r.at_us<=strftime('%s','2026-11-01')*1000000
WHERE s.cohort='demo' AND st.at_us<=strftime('%s','2026-11-01')*1000000
ORDER BY s.started,s.session_key;
