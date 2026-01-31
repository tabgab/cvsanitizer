/**
 * CV Sanitizer - Node.js Wrapper
 * 
 * This module provides a Node.js interface to the Python CV Sanitizer,
 * allowing it to be used in npm/Node.js environments.
 */

import { spawn, ChildProcess } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';

export interface PIIDetection {
  id: number;
  category: string;
  text: string;
  start: number;
  end: number;
  confidence: number;
  countryCode?: string;
  metadata?: any;
}

export interface SanitizerOptions {
  country?: string;
  pdfLibrary?: string;
  outputDir?: string;
  autoConfirm?: boolean;
}

export interface SanitizerResult {
  redactedJson: string;
  piiMappingJson: string;
  summary: {
    totalItems: number;
    byCategory: Record<string, number>;
    processingTime: number;
  };
}

export class CVSanitizer {
  private pythonPath: string;
  private scriptPath: string;
  
  constructor(options: { pythonPath?: string } = {}) {
    this.pythonPath = options.pythonPath || 'python3';
    this.scriptPath = path.join(__dirname, '..', 'python', 'wrapper.py');
  }
  
  /**
   * Sanitize a PDF file by detecting and redacting PII
   * 
   * @param pdfPath Path to the PDF file
   * @param options Configuration options
   * @returns Promise resolving to sanitizer result
   */
  async sanitizePDF(pdfPath: string, options: SanitizerOptions = {}): Promise<SanitizerResult> {
    if (!fs.existsSync(pdfPath)) {
      throw new Error(`PDF file not found: ${pdfPath}`);
    }
    
    const args = [
      this.scriptPath,
      pdfPath,
      '--country', options.country || 'GB',
      '--pdf-library', options.pdfLibrary || 'auto'
    ];
    
    if (options.outputDir) {
      args.push('--output-dir', options.outputDir);
    }
    
    if (options.autoConfirm) {
      args.push('--auto-confirm');
    }
    
    try {
      const result = await this.runPythonScript(args);
      return this.parseResult(result);
    } catch (error) {
      throw new Error(`CV Sanitizer failed: ${error.message}`);
    }
  }
  
  /**
   * Preview PII detections without performing redaction
   * 
   * @param pdfPath Path to the PDF file
   * @param options Configuration options
   * @returns Promise resolving to PII detections
   */
  async previewPII(pdfPath: string, options: Omit<SanitizerOptions, 'autoConfirm'> = {}): Promise<PIIDetection[]> {
    if (!fs.existsSync(pdfPath)) {
      throw new Error(`PDF file not found: ${pdfPath}`);
    }
    
    const args = [
      this.scriptPath,
      pdfPath,
      '--preview-only',
      '--country', options.country || 'GB',
      '--pdf-library', options.pdfLibrary || 'auto'
    ];
    
    if (options.outputDir) {
      args.push('--output-dir', options.outputDir);
    }
    
    try {
      const result = await this.runPythonScript(args);
      return JSON.parse(result).detections || [];
    } catch (error) {
      throw new Error(`PII preview failed: ${error.message}`);
    }
  }
  
  /**
   * Get information about a PDF file
   * 
   * @param pdfPath Path to the PDF file
   * @returns Promise resolving to PDF information
   */
  async getPDFInfo(pdfPath: string): Promise<any> {
    if (!fs.existsSync(pdfPath)) {
      throw new Error(`PDF file not found: ${pdfPath}`);
    }
    
    const args = [
      this.scriptPath,
      pdfPath,
      '--info-only'
    ];
    
    try {
      const result = await this.runPythonScript(args);
      return JSON.parse(result);
    } catch (error) {
      throw new Error(`PDF info retrieval failed: ${error.message}`);
    }
  }
  
  /**
   * Check if the Python dependencies are available
   * 
   * @returns Promise resolving to availability status
   */
  async checkDependencies(): Promise<{ available: boolean; missingDeps?: string[] }> {
    const args = [
      this.scriptPath,
      '--check-deps'
    ];
    
    try {
      const result = await this.runPythonScript(args);
      const parsed = JSON.parse(result);
      return parsed;
    } catch (error) {
      return { available: false, missingDeps: ['python-wrapper'] };
    }
  }
  
  private async runPythonScript(args: string[]): Promise<string> {
    return new Promise((resolve, reject) => {
      const child = spawn(this.pythonPath, args, {
        stdio: ['pipe', 'pipe', 'pipe']
      });
      
      let stdout = '';
      let stderr = '';
      
      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      child.on('close', (code) => {
        if (code === 0) {
          resolve(stdout.trim());
        } else {
          reject(new Error(`Python script exited with code ${code}: ${stderr}`));
        }
      });
      
      child.on('error', (error) => {
        reject(new Error(`Failed to spawn Python script: ${error.message}`));
      });
    });
  }
  
  private parseResult(result: string): SanitizerResult {
    const parsed = JSON.parse(result);
    
    return {
      redactedJson: parsed.redacted_json,
      piiMappingJson: parsed.pii_mapping_json,
      summary: {
        totalItems: parsed.summary?.total_items || 0,
        byCategory: parsed.summary?.by_category || {},
        processingTime: parsed.summary?.processing_time || 0
      }
    };
  }
}

/**
 * Convenience function for quick PDF sanitization
 * 
 * @param pdfPath Path to the PDF file
 * @param options Configuration options
 * @returns Promise resolving to sanitizer result
 */
export async function sanitizePDF(pdfPath: string, options?: SanitizerOptions): Promise<SanitizerResult> {
  const sanitizer = new CVSanitizer();
  return sanitizer.sanitizePDF(pdfPath, options);
}

/**
 * Convenience function for PII preview
 * 
 * @param pdfPath Path to the PDF file
 * @param options Configuration options
 * @returns Promise resolving to PII detections
 */
export async function previewPII(pdfPath: string, options?: Omit<SanitizerOptions, 'autoConfirm'>): Promise<PIIDetection[]> {
  const sanitizer = new CVSanitizer();
  return sanitizer.previewPII(pdfPath, options);
}

// Export all types and the main class
export default CVSanitizer;
