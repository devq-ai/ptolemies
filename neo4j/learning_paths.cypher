// Learning Paths for Ptolemies Knowledge Graph
// ============================================
// Intelligent learning path generation based on graph relationships

// 1. PREREQUISITE CHAINS
// ======================

// Basic prerequisite chain for API development
MATCH path = (start:Topic {name: "database"})-[:RELATED_TO*1..4 {relationship_type: "prerequisite"}]->(end:Topic)
RETURN [node in nodes(path) | node.name] as learning_path,
       length(path) as steps,
       "prerequisite chain" as path_type
ORDER BY steps;

// All possible learning paths to "deployment"
MATCH path = (start:Topic)-[:RELATED_TO*1..3]->(end:Topic {name: "deployment"})
WHERE start <> end
RETURN [node in nodes(path) | node.name] as learning_path,
       start.name as starting_point,
       length(path) as difficulty
ORDER BY difficulty, starting_point;

// 2. FRAMEWORK LEARNING PROGRESSIONS
// ==================================

// Learning path for web development
WITH ["Python", "JavaScript", "API", "user interface", "database", "deployment"] as web_dev_topics
MATCH (t:Topic)
WHERE t.name IN web_dev_topics
OPTIONAL MATCH (t)-[r:RELATED_TO]->(next:Topic)
WHERE next.name IN web_dev_topics
RETURN t.name as current_topic,
       COLLECT(next.name) as next_topics,
       t.category as topic_type
ORDER BY 
  CASE t.name
    WHEN "Python" THEN 1
    WHEN "JavaScript" THEN 2  
    WHEN "database" THEN 3
    WHEN "API" THEN 4
    WHEN "user interface" THEN 5
    WHEN "deployment" THEN 6
  END;

// Framework learning sequence by integration dependencies
MATCH (f1:Framework)-[r:INTEGRATES_WITH]->(f2:Framework)
RETURN f2.name as learn_first,
       f1.name as then_learn,
       r.integration_type as relationship,
       "dependency order" as reason
ORDER BY f2.name;

// 3. SKILL-BASED LEARNING PATHS
// =============================

// Backend development path
MATCH (backend:Topic {name: "backend"})
MATCH (backend)-[:RELATED_TO*0..2]-(related:Topic)
MATCH (related)<-[:COVERS_TOPIC]-(content)
MATCH (content)<-[:HAS_CHUNK]-(source:Source)
RETURN related.name as skill,
       related.category as skill_type,
       COUNT(content) as content_available,
       COLLECT(DISTINCT source.name) as learning_sources
ORDER BY content_available DESC;

// Frontend development path  
MATCH (frontend:Topic {name: "frontend"})
MATCH (frontend)-[:RELATED_TO*0..2]-(related:Topic)
WHERE related.category IN ["concept", "language"]
RETURN related.name as skill,
       related.category as skill_type,
       "frontend development" as learning_track
ORDER BY related.category, related.name;

// 4. CUSTOMIZED LEARNING PATHS
// ============================

// Learning path generator function
// Input: starting knowledge level and target framework
WITH "beginner" as level, "NextJS" as target_framework

MATCH (target:Framework {name: target_framework})
MATCH (target)-[:INTEGRATES_WITH*0..1]-(required:Framework)

// Get associated topics
OPTIONAL MATCH (required)<-[:DOCUMENTS]-(source:Source)
OPTIONAL MATCH (source)-[:HAS_CHUNK]->(chunk)
OPTIONAL MATCH (chunk)-[:COVERS_TOPIC]->(topic:Topic)

RETURN target_framework as goal,
       COLLECT(DISTINCT required.name) as required_frameworks,
       COLLECT(DISTINCT topic.name) as concepts_to_learn,
       COUNT(DISTINCT chunk) as available_content
LIMIT 1;

// 5. DIFFICULTY-BASED PROGRESSIONS
// ================================

// Progressive difficulty based on documentation complexity
MATCH (s:Source)-[:DOCUMENTS]->(f:Framework)
RETURN f.name as framework,
       f.type as category,
       s.chunk_count as complexity_score,
       CASE 
         WHEN s.chunk_count < 10 THEN "beginner"
         WHEN s.chunk_count < 25 THEN "intermediate" 
         ELSE "advanced"
       END as difficulty_level,
       s.avg_quality as learning_quality
ORDER BY s.chunk_count;

// Learning progression within a language ecosystem
MATCH (python:Topic {name: "Python"})
MATCH (python_frameworks:Framework {language: "Python"})
MATCH (python_frameworks)<-[:DOCUMENTS]-(docs:Source)
RETURN python_frameworks.name as framework,
       python_frameworks.type as framework_type,
       docs.chunk_count as documentation_depth,
       CASE docs.chunk_count
         WHEN docs.chunk_count < 15 THEN 1
         WHEN docs.chunk_count < 30 THEN 2
         ELSE 3
       END as suggested_order
ORDER BY suggested_order, docs.avg_quality DESC;

// 6. COMPREHENSIVE LEARNING JOURNEY
// =================================

// Full-stack development learning journey
MATCH (concepts:Topic)
WHERE concepts.name IN ["Python", "JavaScript", "database", "API", "frontend", "backend", "deployment"]

OPTIONAL MATCH (concepts)<-[:COVERS_TOPIC]-(content)
OPTIONAL MATCH (content)<-[:HAS_CHUNK]-(source:Source)
OPTIONAL MATCH (frameworks:Framework)
WHERE frameworks.language = concepts.name OR frameworks.type = concepts.name

RETURN concepts.name as learning_phase,
       concepts.category as concept_type,
       COUNT(DISTINCT content) as practice_content,
       COLLECT(DISTINCT source.name)[0..3] as learning_sources,
       COLLECT(DISTINCT frameworks.name)[0..2] as relevant_frameworks,
       CASE concepts.name
         WHEN "Python" THEN "Phase 1: Programming Fundamentals"
         WHEN "database" THEN "Phase 2: Data Management" 
         WHEN "API" THEN "Phase 3: Backend Development"
         WHEN "frontend" THEN "Phase 4: User Interface"
         WHEN "deployment" THEN "Phase 5: Production Deployment"
         ELSE "Supporting Concept"
       END as learning_stage
ORDER BY 
  CASE concepts.name
    WHEN "Python" THEN 1
    WHEN "database" THEN 2
    WHEN "API" THEN 3  
    WHEN "frontend" THEN 4
    WHEN "deployment" THEN 5
    ELSE 6
  END;

// 7. ADAPTIVE LEARNING SUGGESTIONS
// ================================

// Dynamic next steps based on current knowledge
// Usage: Replace "API" with user's current focus
WITH "API" as current_focus

MATCH (current:Topic {name: current_focus})

// Find next logical steps
OPTIONAL MATCH (current)-[:RELATED_TO {relationship_type: "parent"}]->(next_concepts:Topic)
OPTIONAL MATCH (current)-[:RELATED_TO {relationship_type: "sibling"}]->(related_concepts:Topic)

// Find practical applications
OPTIONAL MATCH (current)<-[:COVERS_TOPIC]-(content)
OPTIONAL MATCH (content)<-[:HAS_CHUNK]-(practice_sources:Source)

// Find relevant frameworks
OPTIONAL MATCH (frameworks:Framework)
WHERE frameworks.name CONTAINS current_focus OR frameworks.type CONTAINS current_focus

RETURN current_focus as current_learning,
       COLLECT(DISTINCT next_concepts.name) as suggested_next_topics,
       COLLECT(DISTINCT related_concepts.name) as related_topics,
       COLLECT(DISTINCT practice_sources.name)[0..3] as practice_with,
       COLLECT(DISTINCT frameworks.name) as applicable_frameworks
LIMIT 1;