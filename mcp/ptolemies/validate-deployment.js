#!/usr/bin/env node

/**
 * Ptolemies MCP Server - Deployment Validation Script
 * ==================================================
 *
 * Comprehensive validation script to verify package readiness
 * for production deployment to the DevQ.AI ecosystem.
 */

import { spawn } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import { resolve, join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class DeploymentValidator {
  constructor() {
    this.results = {
      passed: 0,
      failed: 0,
      warnings: 0,
      errors: []
    };
  }

  log(level, message, details = null) {
    const timestamp = new Date().toISOString();
    const prefix = {
      'PASS': '✅',
      'FAIL': '❌',
      'WARN': '⚠️',
      'INFO': '📋'
    }[level] || '  ';

    console.log(`${prefix} [${timestamp}] ${message}`);

    if (details) {
      console.log(`   Details: ${details}`);
    }

    if (level === 'PASS') this.results.passed++;
    if (level === 'FAIL') {
      this.results.failed++;
      this.results.errors.push(message);
    }
    if (level === 'WARN') this.results.warnings++;
  }

  async runCommand(command, args = [], options = {}) {
    return new Promise((resolve, reject) => {
      const process = spawn(command, args, {
        stdio: 'pipe',
        ...options
      });

      let stdout = '';
      let stderr = '';

      process.stdout?.on('data', (data) => {
        stdout += data.toString();
      });

      process.stderr?.on('data', (data) => {
        stderr += data.toString();
      });

      process.on('close', (code) => {
        resolve({
          code,
          stdout: stdout.trim(),
          stderr: stderr.trim()
        });
      });

      process.on('error', (error) => {
        reject(error);
      });
    });
  }

  validateFileExists(filePath, description) {
    const fullPath = resolve(__dirname, filePath);
    if (existsSync(fullPath)) {
      this.log('PASS', `${description} exists`, filePath);
      return true;
    } else {
      this.log('FAIL', `${description} missing`, filePath);
      return false;
    }
  }

  validatePackageJson() {
    this.log('INFO', 'Validating package.json structure...');

    try {
      const packagePath = resolve(__dirname, 'package.json');
      const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));

      // Required fields
      const required = ['name', 'version', 'description', 'main', 'bin'];
      for (const field of required) {
        if (packageJson[field]) {
          this.log('PASS', `package.json has required field: ${field}`);
        } else {
          this.log('FAIL', `package.json missing required field: ${field}`);
        }
      }

      // Validate specific values
      if (packageJson.name === '@devq-ai/ptolemies-mcp') {
        this.log('PASS', 'Package name is correct');
      } else {
        this.log('FAIL', 'Package name incorrect', packageJson.name);
      }

      if (packageJson.type === 'module') {
        this.log('PASS', 'Package configured as ES module');
      } else {
        this.log('FAIL', 'Package should be configured as ES module');
      }

      if (packageJson.engines && packageJson.engines.node) {
        this.log('PASS', 'Node.js engine requirement specified');
      } else {
        this.log('WARN', 'Node.js engine requirement not specified');
      }

    } catch (error) {
      this.log('FAIL', 'Failed to parse package.json', error.message);
    }
  }

  async validateBuild() {
    this.log('INFO', 'Validating build process...');

    try {
      const result = await this.runCommand('npm', ['run', 'build']);

      if (result.code === 0) {
        this.log('PASS', 'Build completed successfully');
      } else {
        this.log('FAIL', 'Build failed', result.stderr);
      }

      // Check if dist files exist
      this.validateFileExists('dist/index.js', 'Built JavaScript file');
      this.validateFileExists('dist/index.d.ts', 'TypeScript declarations');

    } catch (error) {
      this.log('FAIL', 'Build process error', error.message);
    }
  }

  async validateCLI() {
    this.log('INFO', 'Validating CLI functionality...');

    try {
      // Test version command
      const versionResult = await this.runCommand('node', ['dist/index.js', '--version']);
      if (versionResult.code === 0 && versionResult.stdout.includes('Ptolemies MCP Server')) {
        this.log('PASS', 'Version command works correctly');
      } else {
        this.log('FAIL', 'Version command failed', versionResult.stderr);
      }

      // Test help command
      const helpResult = await this.runCommand('node', ['dist/index.js', '--help']);
      if (helpResult.code === 0 && helpResult.stdout.includes('USAGE:')) {
        this.log('PASS', 'Help command works correctly');
      } else {
        this.log('FAIL', 'Help command failed', helpResult.stderr);
      }

    } catch (error) {
      this.log('FAIL', 'CLI validation error', error.message);
    }
  }

  async validatePythonServer() {
    this.log('INFO', 'Validating Python server components...');

    // Check Python server files
    const pythonFiles = [
      'python-server/ptolemies_mcp_server.py',
      'python-server/ptolemies_integration.py',
      'python-server/ptolemies_tools.py',
      'python-server/ptolemies_types.py'
    ];

    for (const file of pythonFiles) {
      this.validateFileExists(file, `Python server file: ${file}`);
    }

    try {
      // Test Python import
      const importTest = await this.runCommand('python3', ['-c', `
import sys
sys.path.insert(0, 'python-server')
try:
    import ptolemies_types
    import ptolemies_integration
    import ptolemies_tools
    print("All imports successful")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
      `]);

      if (importTest.code === 0) {
        this.log('PASS', 'Python server imports work correctly');
      } else {
        this.log('FAIL', 'Python server import failed', importTest.stderr);
      }

    } catch (error) {
      this.log('WARN', 'Python validation skipped', 'Python3 not available');
    }
  }

  validateDocumentation() {
    this.log('INFO', 'Validating documentation...');

    // Check required documentation files
    const docFiles = [
      'README.md',
      'INSTALLATION.md',
      'LICENSE',
      'mcp-manifest.json',
      'REGISTRY_SUMMARY.md'
    ];

    for (const file of docFiles) {
      this.validateFileExists(file, `Documentation file: ${file}`);
    }

    // Validate manifest structure
    try {
      const manifestPath = resolve(__dirname, 'mcp-manifest.json');
      const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

      if (manifest.server && manifest.server.name === 'ptolemies') {
        this.log('PASS', 'MCP manifest has correct server name');
      } else {
        this.log('FAIL', 'MCP manifest server name incorrect');
      }

      if (manifest.capabilities && manifest.capabilities.tools) {
        const toolCount = manifest.capabilities.tools.length;
        if (toolCount === 10) {
          this.log('PASS', `MCP manifest lists all 10 tools`);
        } else {
          this.log('WARN', `MCP manifest lists ${toolCount} tools, expected 10`);
        }
      }

    } catch (error) {
      this.log('FAIL', 'Failed to validate MCP manifest', error.message);
    }
  }

  async validatePackaging() {
    this.log('INFO', 'Validating package for publication...');

    try {
      // Test npm pack
      const packResult = await this.runCommand('npm', ['pack', '--dry-run']);

      if (packResult.code === 0) {
        this.log('PASS', 'Package can be built for publication');

        // Check package size
        if (packResult.stdout.includes('package size:')) {
          const sizeMatch = packResult.stdout.match(/package size:\s*([0-9.]+\s*[kMG]B)/);
          if (sizeMatch) {
            this.log('INFO', `Package size: ${sizeMatch[1]}`);
          }
        }
      } else {
        this.log('FAIL', 'Package build failed', packResult.stderr);
      }

    } catch (error) {
      this.log('FAIL', 'Package validation error', error.message);
    }
  }

  validateSecurity() {
    this.log('INFO', 'Validating security considerations...');

    try {
      const packagePath = resolve(__dirname, 'package.json');
      const packageJson = JSON.parse(readFileSync(packagePath, 'utf8'));

      // Check for common security issues
      if (!packageJson.scripts || !packageJson.scripts.prepublishOnly) {
        this.log('WARN', 'No prepublishOnly script to prevent accidental publishing');
      } else {
        this.log('PASS', 'prepublishOnly script configured');
      }

      // Check files array
      if (packageJson.files && Array.isArray(packageJson.files)) {
        this.log('PASS', 'Files array specified to control package contents');
      } else {
        this.log('WARN', 'No files array specified - entire directory will be published');
      }

    } catch (error) {
      this.log('FAIL', 'Security validation error', error.message);
    }
  }

  async run() {
    console.log('🚀 Ptolemies MCP Server - Deployment Validation');
    console.log('='.repeat(50));

    // Run all validations
    this.validatePackageJson();
    await this.validateBuild();
    await this.validateCLI();
    await this.validatePythonServer();
    this.validateDocumentation();
    await this.validatePackaging();
    this.validateSecurity();

    // Summary
    console.log('\n' + '='.repeat(50));
    console.log('📊 VALIDATION SUMMARY');
    console.log('='.repeat(50));
    console.log(`✅ Passed: ${this.results.passed}`);
    console.log(`❌ Failed: ${this.results.failed}`);
    console.log(`⚠️  Warnings: ${this.results.warnings}`);

    if (this.results.failed > 0) {
      console.log('\n❌ VALIDATION FAILED');
      console.log('Errors that must be fixed:');
      for (const error of this.results.errors) {
        console.log(`  • ${error}`);
      }
      process.exit(1);
    } else if (this.results.warnings > 0) {
      console.log('\n⚠️  VALIDATION PASSED WITH WARNINGS');
      console.log('Consider addressing warnings before deployment.');
      process.exit(0);
    } else {
      console.log('\n🎉 VALIDATION PASSED COMPLETELY');
      console.log('Package is ready for production deployment!');
      console.log('\nNext steps:');
      console.log('  1. npm publish --access public');
      console.log('  2. Add to DevQ.AI MCP registry');
      console.log('  3. Test with MCP clients');
      process.exit(0);
    }
  }
}

// Run validation if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const validator = new DeploymentValidator();
  validator.run().catch((error) => {
    console.error('💥 Validation script error:', error);
    process.exit(1);
  });
}

export { DeploymentValidator };
