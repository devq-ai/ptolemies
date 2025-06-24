CREATE CONSTRAINT source_name_unique IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT topic_name_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE;
CREATE INDEX source_url IF NOT EXISTS FOR (s:Source) ON (s.url);
CREATE INDEX chunk_quality IF NOT EXISTS FOR (c:Chunk) ON (c.quality_score);
CREATE INDEX chunk_created IF NOT EXISTS FOR (c:Chunk) ON (c.created_at);
CREATE TEXT INDEX chunk_content IF NOT EXISTS FOR (c:Chunk) ON (c.content);
CREATE INDEX topic_category IF NOT EXISTS FOR (t:Topic) ON (t.category);