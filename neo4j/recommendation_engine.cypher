// Recommendation Engine for Ptolemies Knowledge Graph
// ===================================================
// Advanced graph-based recommendation queries

// 1. FRAMEWORK RECOMMENDATIONS
// ============================

// Recommend frameworks based on integration patterns
// "Users who use FastAPI also use..."
MATCH (f1:Framework {name: "FastAPI"})-[:INTEGRATES_WITH]->(common:Framework)
MATCH (common)<-[:INTEGRATES_WITH]-(recommended:Framework)
WHERE f1 <> recommended
RETURN recommended.name as recommendation, 
       common.name as reason,
       "integrates with same framework" as recommendation_type
ORDER BY recommended.name;

// Recommend by language ecosystem
MATCH (f:Framework {language: "Python"})
WHERE f.name <> "FastAPI"
RETURN f.name as recommendation,
       f.type as framework_type,
       "same language ecosystem" as recommendation_type
ORDER BY f.name;

// Recommend by documentation quality
MATCH (s:Source)-[:DOCUMENTS]->(f:Framework)
WHERE s.chunk_count > 20 AND s.avg_quality > 0.9
RETURN f.name as recommendation,
       s.chunk_count as documentation_quality,
       s.avg_quality as quality_score,
       "well documented" as recommendation_type
ORDER BY s.chunk_count DESC, s.avg_quality DESC;

// 2. LEARNING PATH RECOMMENDATIONS
// ================================

// Prerequisites for learning a framework
MATCH (target:Framework {name: "NextJS"})
MATCH (target)-[:INTEGRATES_WITH]->(prereq:Framework)
RETURN prereq.name as learn_first,
       "required integration" as reason
UNION
MATCH (js:Topic {name: "JavaScript"})-[:RELATED_TO*1..2]->(prereq:Topic)
RETURN prereq.name as learn_first,
       "foundational concept" as reason;

// Topic learning progression
MATCH path = (start:Topic)-[:RELATED_TO*1..3 {relationship_type: "prerequisite"}]->(end:Topic)
WHERE start.name = "API"
RETURN [node in nodes(path) | node.name] as learning_path,
       length(path) as complexity
ORDER BY complexity;

// 3. CONTENT RECOMMENDATIONS
// ==========================

// Recommend sources based on topic interest
MATCH (topic:Topic {name: "authentication"})
MATCH (topic)<-[:COVERS_TOPIC]-(chunk:Chunk)
MATCH (chunk)<-[:HAS_CHUNK]-(source:Source)
RETURN source.name as recommended_source,
       COUNT(chunk) as relevant_chunks,
       AVG(source.avg_quality) as avg_quality,
       "covers topic of interest" as reason
ORDER BY relevant_chunks DESC, avg_quality DESC;

// Recommend by framework stack
MATCH (user_framework:Framework {name: "FastAPI"})
MATCH (user_framework)-[:INTEGRATES_WITH*1..2]-(related:Framework)
MATCH (related)<-[:DOCUMENTS]-(source:Source)
RETURN DISTINCT source.name as recommended_source,
       related.name as related_framework,
       source.chunk_count as content_available,
       "complements your stack" as reason
ORDER BY content_available DESC;

// 4. SIMILARITY-BASED RECOMMENDATIONS
// ===================================

// Find frameworks with similar documentation patterns
MATCH (f1:Framework)<-[:DOCUMENTS]-(s1:Source)
MATCH (f2:Framework)<-[:DOCUMENTS]-(s2:Source)
WHERE f1 <> f2 
  AND abs(s1.chunk_count - s2.chunk_count) < 10
  AND abs(s1.avg_quality - s2.avg_quality) < 0.1
RETURN f1.name as framework,
       f2.name as similar_framework,
       s1.chunk_count as docs1,
       s2.chunk_count as docs2,
       "similar documentation patterns" as reason
ORDER BY abs(s1.chunk_count - s2.chunk_count);

// 5. PERSONALIZED RECOMMENDATIONS FUNCTION
// ========================================

// Recommendation function for a specific user interest
// Usage: Replace "FastAPI" with user's primary framework
WITH "FastAPI" as user_framework
MATCH (f:Framework {name: user_framework})

// Get direct integrations
OPTIONAL MATCH (f)-[:INTEGRATES_WITH]->(direct:Framework)

// Get language ecosystem
OPTIONAL MATCH (ecosystem:Framework {language: f.language})
WHERE ecosystem <> f

// Get high-quality documentation in same category
OPTIONAL MATCH (similar:Framework {type: f.type})<-[:DOCUMENTS]-(s:Source)
WHERE similar <> f AND s.avg_quality > 0.9

RETURN 
  COLLECT(DISTINCT direct.name) as direct_integrations,
  COLLECT(DISTINCT ecosystem.name)[0..3] as language_ecosystem,
  COLLECT(DISTINCT {framework: similar.name, quality: s.avg_quality})[0..3] as high_quality_docs
LIMIT 1;

// 6. TRENDING/POPULAR RECOMMENDATIONS
// ==================================

// Most documented frameworks (popularity proxy)
MATCH (s:Source)-[:DOCUMENTS]->(f:Framework)
RETURN f.name as framework,
       f.type as category,
       s.chunk_count as documentation_volume,
       s.avg_quality as quality,
       "trending/well-supported" as reason
ORDER BY s.chunk_count DESC
LIMIT 5;

// Best quality/effort ratio
MATCH (s:Source)-[:DOCUMENTS]->(f:Framework)
WHERE s.chunk_count > 5
RETURN f.name as framework,
       s.avg_quality as quality_score,
       s.chunk_count as documentation_volume,
       round(s.avg_quality * 100) as quality_percentage,
       "high quality documentation" as reason
ORDER BY s.avg_quality DESC, s.chunk_count DESC
LIMIT 10;