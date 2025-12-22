// unique constraints
// CREATE CONSTRAINT wa_account_id_unique IF NOT EXISTS
//  FOR (a:WAAccount) REQUIRE (a.phone_number_id) IS UNIQUE;

// CREATE CONSTRAINT contact_waid_unique IF NOT EXISTS
//  FOR (c:Contact) REQUIRE (c.wa_id) IS UNIQUE;

// CREATE CONSTRAINT message_id_unique IF NOT EXISTS
//  FOR (m:Message) REQUIRE (m.message_id) IS UNIQUE;

// optional: index on timestamp
// CREATE INDEX message_timestamp_idx IF NOT EXISTS FOR (m:Message) ON (m.timestamp);

// full-text index for keyword search on message body
// CALL db.index.fulltext.createNodeIndex("messages_fulltext", ["Message"], ["body"]);

// --- Unique constraints / indexes (safe to run) ---
CREATE CONSTRAINT wa_account_id_unique IF NOT EXISTS
  FOR (a:WAAccount) REQUIRE (a.phone_number_id) IS UNIQUE;

CREATE CONSTRAINT contact_waid_unique IF NOT EXISTS
  FOR (c:Contact) REQUIRE (c.wa_id) IS UNIQUE;

CREATE CONSTRAINT message_id_unique IF NOT EXISTS
  FOR (m:Message) REQUIRE (m.message_id) IS UNIQUE;

CREATE INDEX message_timestamp_idx IF NOT EXISTS FOR (m:Message) ON (m.timestamp);

// --- Full-text index: choose the appropriate line for your Neo4j version ---

// Option A: Neo4j 5+ native DDL (recommended for Neo4j 5.x)
CREATE FULLTEXT INDEX messages_fulltext IF NOT EXISTS
  FOR (m:Message)
  ON (m.body);
