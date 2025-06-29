#!/usr/bin/env node
export class DeploymentValidator {
    results: {
        passed: number;
        failed: number;
        warnings: number;
        errors: never[];
    };
    log(level: any, message: any, details?: null): void;
    runCommand(command: any, args?: any[], options?: {}): Promise<any>;
    validateFileExists(filePath: any, description: any): boolean;
    validatePackageJson(): void;
    validateBuild(): Promise<void>;
    validateCLI(): Promise<void>;
    validatePythonServer(): Promise<void>;
    validateDocumentation(): void;
    validatePackaging(): Promise<void>;
    validateSecurity(): void;
    run(): Promise<void>;
}
//# sourceMappingURL=validate-deployment.d.ts.map