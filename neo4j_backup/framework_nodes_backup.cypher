// Backup of Framework Nodes from Neo4j (before reinstall)
// Run this after fresh Neo4j installation to restore the Framework nodes

CREATE (fastapi:Framework {name: "FastAPI", type: "backend", language: "Python"});
CREATE (nextjs:Framework {name: "NextJS", type: "fullstack", language: "JavaScript"});
CREATE (surrealdb:Framework {name: "SurrealDB", type: "database", language: "Rust"});
CREATE (tailwind:Framework {name: "Tailwind CSS", type: "frontend", language: "CSS"});
CREATE (shadcn:Framework {name: "Shadcn/UI", type: "frontend", language: "TypeScript"});
CREATE (pydantic:Framework {name: "Pydantic AI", type: "backend", language: "Python"});
CREATE (logfire:Framework {name: "Logfire", type: "backend", language: "Python"});
CREATE (pygad:Framework {name: "PyGAD", type: "backend", language: "Python"});
CREATE (bokeh:Framework {name: "bokeh", type: "backend", language: "Python"});
CREATE (panel:Framework {name: "Panel", type: "backend", language: "Python"});
CREATE (wildwood:Framework {name: "Wildwood", type: "tool", language: "Various"});
CREATE (crawl4ai:Framework {name: "Crawl4AI", type: "tool", language: "Python"});
CREATE (fastmcp:Framework {name: "FastMCP", type: "tool", language: "Python"});
CREATE (animejs:Framework {name: "AnimeJS", type: "frontend", language: "JavaScript"});
CREATE (pymc:Framework {name: "PyMC", type: "backend", language: "Python"});
CREATE (circom:Framework {name: "circom", type: "tool", language: "Various"});
CREATE (claudecode:Framework {name: "Claude Code", type: "tool", language: "Various"});