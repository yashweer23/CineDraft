-- query: overview
SELECT COUNT(*) started,COALESCE(SUM(released),0) completed,COALESCE(SUM(abandoned),0) abandoned,
 COUNT(*)-COALESCE(SUM(released+abandoned),0) unfinished,
 (SELECT COUNT(*) FROM e WHERE kind='replay_start') replay_starts,
 (SELECT COUNT(*) FROM e WHERE kind='confirm_recast') confirmed_recasts,
 (SELECT COUNT(*) FROM e WHERE kind='whatif') comparisons,COUNT(DISTINCT catalog) catalogs,
 COALESCE(SUM(fixture),0) fixture_sessions FROM progress;
-- query: funnel
WITH stages(n,label) AS (VALUES (0,'Started'),(1,'1 pick'),(2,'2 picks'),(3,'3 picks'),(4,'4 picks'),(5,'5 picks'),(6,'6 picks'),(7,'7 picks'),(8,'8 picks'),(9,'Finalized'),(10,'Released'))
SELECT n,label,(SELECT COUNT(*) FROM progress p WHERE CASE WHEN n<=8 THEN p.picks>=n WHEN n=9 THEN p.finalized ELSE p.released END) reached,
 (SELECT COUNT(*) FROM progress) starts FROM stages ORDER BY n;
-- query: stops
SELECT picks AS picks_made,SUM(abandoned) explicitly_abandoned,SUM(1-abandoned) still_unfinished
FROM progress WHERE NOT released GROUP BY picks ORDER BY picks;
-- query: rounds
WITH intervals AS (SELECT session_key,slot,kind,(at_us-LAG(at_us) OVER (PARTITION BY session_key ORDER BY revision))/1000000.0 seconds FROM e WHERE kind IN ('start','replay_start','pick')),
 ranked AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY slot ORDER BY seconds) rn,COUNT(*) OVER(PARTITION BY slot) n FROM intervals WHERE kind='pick' AND seconds>=0)
SELECT t.slot,(SELECT COUNT(*) FROM ranked r WHERE r.slot=t.slot) measured_picks,
 (SELECT ROUND(AVG(seconds),3) FROM ranked r WHERE r.slot=t.slot AND rn IN ((n+1)/2,(n+2)/2)) median_seconds,
 SUM(CASE WHEN t.seconds<0 THEN 1 ELSE 0 END) clock_reversals FROM intervals t WHERE t.kind='pick' GROUP BY t.slot ORDER BY median_seconds DESC,t.slot;
-- query: genres
SELECT genre,COUNT(*) starts,SUM(released) official_releases,ROUND(100.0*COUNT(*)/(SELECT COUNT(*) FROM progress),1) share_pct FROM progress GROUP BY genre ORDER BY starts DESC,genre;
-- query: talent
WITH offered AS (SELECT o.person,o.slot,MIN(o.name) name,COUNT(*) selectable_offers,COUNT(p.event_key) selections
 FROM o LEFT JOIN e p ON p.kind='pick' AND p.offer=o.offer AND p.person=o.person WHERE o.kind='pick' GROUP BY o.person,o.slot),
 finished AS (SELECT f.person,f.slot,COUNT(*) official_films,ROUND(AVG(r.score),1) avg_score,ROUND(AVG(r.profit),0) avg_profit_usd FROM final_roster f JOIN e r ON r.session_key=f.session_key AND r.kind='release' GROUP BY f.person,f.slot),
 identities AS (SELECT person,slot FROM offered UNION SELECT person,slot FROM finished)
SELECT i.person,i.slot,COALESCE(o.name,(SELECT MIN(x.name) FROM o x WHERE x.person=i.person AND x.slot=i.slot)) name,
 COALESCE(o.selectable_offers,0) selectable_offers,COALESCE(o.selections,0) selections,ROUND(100.0*o.selections/NULLIF(o.selectable_offers,0),1) pick_pct,
 COALESCE(f.official_films,0) official_films,f.avg_score,f.avg_profit_usd FROM identities i LEFT JOIN offered o USING(person,slot) LEFT JOIN finished f USING(person,slot)
 ORDER BY selections DESC,selectable_offers DESC,name,i.person,i.slot;
-- query: budget
WITH spent AS (SELECT session_key,SUM(fee) talent_spend FROM final_roster GROUP BY session_key)
SELECT COUNT(*) official_films,SUM(p.total) total_budget,SUM(p.allowance) talent_allowance,SUM(p.reserve) reserved_production,
 SUM(s.talent_spend) committed_talent,SUM(p.allowance-s.talent_spend) unused_allowance,
 ROUND(100.0*SUM(s.talent_spend)/NULLIF(SUM(p.allowance),0),1) utilization_pct FROM progress p JOIN spent s USING(session_key) WHERE released;
-- query: allocations
SELECT f.slot,COUNT(*) released_films,SUM(f.fee) total_fees,ROUND(AVG(f.fee),0) mean_fee FROM final_roster f JOIN progress p USING(session_key) WHERE p.released GROUP BY f.slot ORDER BY total_fees DESC,f.slot;
-- query: versions
SELECT catalog,rules,scoring,simulation,fixture,COUNT(*) starts FROM cohort GROUP BY catalog,rules,scoring,simulation,fixture ORDER BY catalog,rules,scoring,simulation,fixture;
-- query: trace
SELECT c.session_key,c.genre,c.tier,st.event_key start_event,r.event_key release_event,r.score AS official_score,p.picks,p.abandoned AS explicitly_abandoned
FROM cohort c JOIN progress p USING(session_key) JOIN e st ON st.session_key=c.session_key AND st.kind IN ('start','replay_start')
LEFT JOIN e r ON r.session_key=c.session_key AND r.kind='release' ORDER BY c.started,c.session_key;
