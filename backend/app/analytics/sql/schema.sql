PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS meta(version TEXT PRIMARY KEY CHECK(version='bi-1.0'));
INSERT OR IGNORE INTO meta VALUES('bi-1.0');
CREATE TABLE IF NOT EXISTS sessions(
 session_key TEXT PRIMARY KEY, cohort TEXT NOT NULL CHECK(cohort IN ('demo','internal','playtest')),
 started INTEGER NOT NULL,captured INTEGER NOT NULL,genre TEXT NOT NULL,tier TEXT NOT NULL,catalog TEXT NOT NULL,
 rules TEXT NOT NULL,scoring TEXT NOT NULL,simulation TEXT NOT NULL,fixture INTEGER NOT NULL,mode TEXT NOT NULL,
 total INTEGER NOT NULL,allowance INTEGER NOT NULL,reserve INTEGER NOT NULL, CHECK(total=allowance+reserve));
CREATE TABLE IF NOT EXISTS events(
 event_key TEXT PRIMARY KEY, session_key TEXT NOT NULL REFERENCES sessions,kind TEXT NOT NULL,
 at_us INTEGER NOT NULL,revision INTEGER NOT NULL,slot TEXT,person TEXT,offer TEXT,fee INTEGER,score INTEGER,profit INTEGER);
CREATE INDEX IF NOT EXISTS ix_event_session ON events(session_key,revision);
CREATE TABLE IF NOT EXISTS opportunities(
 offer TEXT NOT NULL,person TEXT NOT NULL,session_key TEXT NOT NULL REFERENCES sessions,name TEXT NOT NULL,
 slot TEXT NOT NULL,kind TEXT NOT NULL,at_us INTEGER NOT NULL,event_key TEXT NOT NULL REFERENCES events,
 PRIMARY KEY(offer,person));
