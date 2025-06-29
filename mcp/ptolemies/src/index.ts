#!/usr/bin/env node

/**
 * Ptolemies MCP Server - TypeScript Wrapper
 * ==========================================
 *
 * NPM package wrapper that launches the Python-based Ptolemies MCP server.
 * This provides a Node.js compatible interface for the DevQ.AI ecosystem
 * while leveraging the comprehensive Python implementation.
 */

import { spawn, ChildProcess } from "child_process";
import { resolve, join } from "path";
import { existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname } from "path";

// Get current directory for ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

interface ServerConfig {
  neo4jUri?: string;
  neo4jUsername?: string;
  neo4jPassword?: string;
  neo4jDatabase?: string;
  surrealdbUrl?: string;
  surrealdbNamespace?: string;
  surrealdbDatabase?: string;
  openaiApiKey?: string;
  pythonPath?: string;
  serverPath?: string;
  debug?: boolean;
  healthCheck?: boolean;
}

class PtolemiesMCPServer {
  private serverProcess: ChildProcess | null = null;
  private config: ServerConfig;
  private pythonServerPath: string;

  constructor(config: ServerConfig = {}) {
    this.config = config;

    // Determine Python server path
    const packageRoot = resolve(__dirname, "..");
    this.pythonServerPath =
      config.serverPath ||
      join(packageRoot, "python-server", "ptolemies_mcp_server.py");

    // Validate Python server exists
    if (!existsSync(this.pythonServerPath)) {
      throw new Error(`Python server not found at: ${this.pythonServerPath}`);
    }
  }

  /**
   * Start the Ptolemies MCP server
   */
  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const pythonCommand = this.config.pythonPath || "python3";
        const env = this.buildEnvironment();

        if (this.config.debug) {
          console.error(
            `[ptolemies] Starting server with Python: ${pythonCommand}`,
          );
          console.error(`[ptolemies] Server path: ${this.pythonServerPath}`);
          console.error(`[ptolemies] Environment:`, env);
        }

        // Spawn Python server process
        this.serverProcess = spawn(pythonCommand, [this.pythonServerPath], {
          env: { ...process.env, ...env },
          stdio: ["pipe", "pipe", "pipe"],
        });

        // Handle server startup
        this.serverProcess.on("spawn", () => {
          if (this.config.debug) {
            console.error("[ptolemies] Server process spawned successfully");
          }
          resolve();
        });

        // Handle server errors
        this.serverProcess.on("error", (error) => {
          console.error(`[ptolemies] Server error: ${error.message}`);
          reject(error);
        });

        // Handle server exit
        this.serverProcess.on("exit", (code, signal) => {
          if (this.config.debug) {
            console.error(
              `[ptolemies] Server exited with code ${code}, signal ${signal}`,
            );
          }
          this.serverProcess = null;
        });

        // Pipe server stdout/stderr
        if (this.serverProcess.stdout) {
          this.serverProcess.stdout.pipe(process.stdout);
        }

        if (this.serverProcess.stderr && this.config.debug) {
          this.serverProcess.stderr.pipe(process.stderr);
        }

        // Pipe stdin to server
        process.stdin.pipe(this.serverProcess.stdin!);
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Stop the server
   */
  async stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.serverProcess) {
        this.serverProcess.on("exit", () => {
          this.serverProcess = null;
          resolve();
        });

        this.serverProcess.kill("SIGTERM");

        // Force kill after 5 seconds
        setTimeout(() => {
          if (this.serverProcess) {
            this.serverProcess.kill("SIGKILL");
          }
        }, 5000);
      } else {
        resolve();
      }
    });
  }

  /**
   * Perform health check
   */
  async healthCheck(): Promise<boolean> {
    return new Promise((resolve, reject) => {
      const pythonCommand = this.config.pythonPath || "python3";
      const env = this.buildEnvironment();

      // Run health check script
      const healthCheckScript = `
import sys
import os
sys.path.insert(0, '${dirname(this.pythonServerPath)}')

async def check_health():
    try:
        from ptolemies_integration import PtolemiesIntegration
        integration = PtolemiesIntegration()
        success = await integration.connect()
        health = await integration.get_system_health()
        await integration.disconnect()

        print(f"Health check: {'HEALTHY' if health.overall_healthy else 'DEGRADED'}")
        print(f"Neo4j: {'✅' if health.neo4j_status.connected else '❌'}")
        print(f"SurrealDB: {'✅' if health.surrealdb_status.connected else '❌'}")
        print(f"Dehallucinator: {'✅' if health.dehallucinator_status.connected else '❌'}")

        return health.overall_healthy
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

import asyncio
result = asyncio.run(check_health())
sys.exit(0 if result else 1)
      `;

      const healthProcess = spawn(pythonCommand, ["-c", healthCheckScript], {
        env: { ...process.env, ...env },
        stdio: ["pipe", "pipe", "pipe"],
      });

      let output = "";
      healthProcess.stdout?.on("data", (data) => {
        output += data.toString();
      });

      healthProcess.stderr?.on("data", (data) => {
        if (this.config.debug) {
          console.error(`[ptolemies] Health check: ${data}`);
        }
      });

      healthProcess.on("exit", (code) => {
        if (this.config.debug) {
          console.error(`[ptolemies] Health check output:\n${output}`);
        }
        resolve(code === 0);
      });

      healthProcess.on("error", (error) => {
        console.error(`[ptolemies] Health check error: ${error.message}`);
        reject(error);
      });
    });
  }

  /**
   * Build environment variables for the Python server
   */
  private buildEnvironment(): Record<string, string> {
    const env: Record<string, string> = {};

    // Neo4j configuration
    if (this.config.neo4jUri) env.NEO4J_URI = this.config.neo4jUri;
    if (this.config.neo4jUsername)
      env.NEO4J_USERNAME = this.config.neo4jUsername;
    if (this.config.neo4jPassword)
      env.NEO4J_PASSWORD = this.config.neo4jPassword;
    if (this.config.neo4jDatabase)
      env.NEO4J_DATABASE = this.config.neo4jDatabase;

    // SurrealDB configuration
    if (this.config.surrealdbUrl) env.SURREALDB_URL = this.config.surrealdbUrl;
    if (this.config.surrealdbNamespace)
      env.SURREALDB_NAMESPACE = this.config.surrealdbNamespace;
    if (this.config.surrealdbDatabase)
      env.SURREALDB_DATABASE = this.config.surrealdbDatabase;

    // OpenAI configuration
    if (this.config.openaiApiKey) env.OPENAI_API_KEY = this.config.openaiApiKey;

    // Python path configuration
    const packageRoot = resolve(__dirname, "..");
    const pythonServerDir = dirname(this.pythonServerPath);
    env.PYTHONPATH = `${pythonServerDir}:${env.PYTHONPATH || ""}`;

    return env;
  }
}

/**
 * Parse command line arguments
 */
function parseArgs(): ServerConfig {
  const args = process.argv.slice(2);
  const config: ServerConfig = {};

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    const nextArg = args[i + 1];

    switch (arg) {
      case "--neo4j-uri":
        config.neo4jUri = nextArg;
        i++;
        break;
      case "--neo4j-username":
        config.neo4jUsername = nextArg;
        i++;
        break;
      case "--neo4j-password":
        config.neo4jPassword = nextArg;
        i++;
        break;
      case "--neo4j-database":
        config.neo4jDatabase = nextArg;
        i++;
        break;
      case "--surrealdb-url":
        config.surrealdbUrl = nextArg;
        i++;
        break;
      case "--surrealdb-namespace":
        config.surrealdbNamespace = nextArg;
        i++;
        break;
      case "--surrealdb-database":
        config.surrealdbDatabase = nextArg;
        i++;
        break;
      case "--openai-api-key":
        config.openaiApiKey = nextArg;
        i++;
        break;
      case "--python-path":
        config.pythonPath = nextArg;
        i++;
        break;
      case "--server-path":
        config.serverPath = nextArg;
        i++;
        break;
      case "--debug":
        config.debug = true;
        break;
      case "--health-check":
        config.healthCheck = true;
        break;
      case "--help":
        showHelp();
        process.exit(0);
        break;
      case "--version":
        showVersion();
        process.exit(0);
        break;
      default:
        if (arg && arg.startsWith("--")) {
          console.error(`Unknown option: ${arg}`);
          process.exit(1);
        }
    }
  }

  return config;
}

/**
 * Show help message
 */
function showHelp(): void {
  console.log(`
Ptolemies MCP Server - Unified AI Knowledge Access

USAGE:
    ptolemies-mcp [OPTIONS]

OPTIONS:
    --neo4j-uri <URI>              Neo4j connection URI (default: bolt://localhost:7687)
    --neo4j-username <USERNAME>    Neo4j username (default: neo4j)
    --neo4j-password <PASSWORD>    Neo4j password (default: ptolemies)
    --neo4j-database <DATABASE>    Neo4j database (default: ptolemies)

    --surrealdb-url <URL>          SurrealDB connection URL (default: ws://localhost:8000/rpc)
    --surrealdb-namespace <NS>     SurrealDB namespace (default: ptolemies)
    --surrealdb-database <DB>      SurrealDB database (default: knowledge)

    --openai-api-key <KEY>         OpenAI API key for embeddings (optional)

    --python-path <PATH>           Python executable path (default: python3)
    --server-path <PATH>           Python server script path

    --debug                        Enable debug logging
    --health-check                 Perform health check and exit
    --help                         Show this help message
    --version                      Show version information

ENVIRONMENT VARIABLES:
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
    SURREALDB_URL, SURREALDB_NAMESPACE, SURREALDB_DATABASE
    OPENAI_API_KEY

EXAMPLES:
    # Start with default configuration
    ptolemies-mcp

    # Start with custom Neo4j settings
    ptolemies-mcp --neo4j-uri bolt://remote:7687 --neo4j-password mypassword

    # Perform health check
    ptolemies-mcp --health-check

    # Start with debug logging
    ptolemies-mcp --debug

For more information, visit: https://docs.devq.ai/ptolemies-mcp
  `);
}

/**
 * Show version information
 */
function showVersion(): void {
  // Read version from package.json
  try {
    const packagePath = resolve(__dirname, "..", "package.json");
    const packageJson = JSON.parse(
      require("fs").readFileSync(packagePath, "utf8"),
    );
    console.log(`${packageJson.name} v${packageJson.version}`);
    console.log(`DevQ.AI Ptolemies MCP Server`);
    console.log(`https://devq.ai`);
  } catch (error) {
    console.log("Ptolemies MCP Server v1.0.0");
  }
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  const config = parseArgs();

  try {
    const server = new PtolemiesMCPServer(config);

    // Handle health check
    if (config.healthCheck) {
      console.log("Performing health check...");
      const healthy = await server.healthCheck();
      console.log(`Health status: ${healthy ? "HEALTHY" : "DEGRADED"}`);
      process.exit(healthy ? 0 : 1);
    }

    // Start the server
    if (config.debug) {
      console.error("[ptolemies] Starting Ptolemies MCP Server...");
    }

    await server.start();

    // Handle graceful shutdown
    process.on("SIGINT", async () => {
      if (config.debug) {
        console.error("[ptolemies] Received SIGINT, shutting down...");
      }
      await server.stop();
      process.exit(0);
    });

    process.on("SIGTERM", async () => {
      if (config.debug) {
        console.error("[ptolemies] Received SIGTERM, shutting down...");
      }
      await server.stop();
      process.exit(0);
    });
  } catch (error) {
    console.error(`[ptolemies] Failed to start server: ${error}`);
    process.exit(1);
  }
}

// Export for programmatic use
export { PtolemiesMCPServer, ServerConfig };

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
}
