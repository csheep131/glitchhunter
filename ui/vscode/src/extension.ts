/**
 * GlitchHunter VS Code Extension
 *
 * AI-powered code analysis with:
 * - Multi-Agent Swarm
 * - ML Bug Prediction
 * - Auto-Refactoring
 */

import * as vscode from 'vscode';
import axios, { AxiosInstance } from 'axios';

// Global state
let resultsPanel: vscode.WebviewPanel | undefined;
let axiosClient: AxiosInstance;

// Server URL from config
function getServerUrl(): string {
    const config = vscode.workspace.getConfiguration('glitchhunter');
    return config.get('serverUrl', 'http://localhost:8000');
}

// Initialize axios client
function initAxios() {
    axiosClient = axios.create({
        baseURL: getServerUrl(),
        timeout: 300000, // 5 minutes
    });
}

/**
 * Activate extension
 */
export function activate(context: vscode.ExtensionContext) {
    console.log('GlitchHunter extension is now active');
    
    initAxios();
    
    // Register commands
    const analyzeWorkspaceCmd = vscode.commands.registerCommand(
        'glitchhunter.analyzeWorkspace',
        analyzeWorkspace
    );
    
    const analyzeCurrentFileCmd = vscode.commands.registerCommand(
        'glitchhunter.analyzeCurrentFile',
        analyzeCurrentFile
    );
    
    const showResultsCmd = vscode.commands.registerCommand(
        'glitchhunter.showResults',
        showResults
    );
    
    const applyRefactoringCmd = vscode.commands.registerCommand(
        'glitchhunter.applyRefactoring',
        applyRefactoring
    );
    
    const openDashboardCmd = vscode.commands.registerCommand(
        'glitchhunter.openDashboard',
        openDashboard
    );
    
    context.subscriptions.push(
        analyzeWorkspaceCmd,
        analyzeCurrentFileCmd,
        showResultsCmd,
        applyRefactoringCmd,
        openDashboardCmd
    );
    
    // Create results view
    createResultsView(context);
}

/**
 * Analyze entire workspace
 */
async function analyzeWorkspace() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }
    
    const folder = workspaceFolders[0].uri.fsPath;
    
    vscode.window.showInformationMessage(`Starting GlitchHunter analysis for ${folder}...`);
    
    try {
        const config = vscode.workspace.getConfiguration('glitchhunter');
        
        const response = await axiosClient.post('/api/v1/analyze', {
            repo_path: folder,
            use_parallel: config.get('enableParallelAnalysis', true),
            enable_ml_prediction: config.get('enableMlPrediction', true),
            enable_auto_refactor: config.get('autoApplyRefactoring', false),
            max_workers: config.get('maxWorkers', 4),
        });
        
        const jobId = response.data.job_id;
        
        vscode.window.showInformationMessage(
            `Analysis started! Job ID: ${jobId.substring(0, 8)}...`
        );
        
        // Poll for results
        pollResults(jobId);
        
    } catch (error: any) {
        vscode.window.showErrorMessage(
            `Analysis failed: ${error.response?.data?.message || error.message}`
        );
    }
}

/**
 * Analyze current file
 */
async function analyzeCurrentFile() {
    const editor = vscode.window.activeTextEditor;
    
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }
    
    const filePath = editor.document.uri.fsPath;
    
    vscode.window.showInformationMessage(`Analyzing ${filePath}...`);
    
    // TODO: Single file analysis endpoint
    // For now, use workspace analysis
    analyzeWorkspace();
}

/**
 * Show results in webview
 */
async function showResults() {
    if (!resultsPanel) {
        vscode.window.showInformationMessage('No analysis results available');
        return;
    }
    
    resultsPanel.reveal(vscode.ViewColumn.Two);
}

/**
 * Apply refactoring to file
 */
async function applyRefactoring(findingId: string, filePath: string) {
    try {
        const response = await axiosClient.post('/api/v1/refactor', {
            finding_id: findingId,
            file_path: filePath,
            apply: true,
        });
        
        if (response.data.success) {
            vscode.window.showInformationMessage('Refactoring applied successfully');
            
            // Reload file
            const doc = await vscode.workspace.openTextDocument(filePath);
            await vscode.window.showTextDocument(doc);
        } else {
            vscode.window.showErrorMessage('Refactoring failed');
        }
        
    } catch (error: any) {
        vscode.window.showErrorMessage(
            `Refactoring failed: ${error.response?.data?.message || error.message}`
        );
    }
}

/**
 * Open web dashboard in browser
 */
function openDashboard() {
    const serverUrl = getServerUrl();
    vscode.env.openExternal(vscode.Uri.parse(serverUrl));
}

/**
 * Poll for analysis results
 */
async function pollResults(jobId: string) {
    const maxAttempts = 60; // 5 minutes
    let attempts = 0;
    
    const interval = setInterval(async () => {
        try {
            const response = await axiosClient.get(`/api/v1/jobs/${jobId}`);
            const job = response.data.job;
            
            if (job.status === 'completed') {
                clearInterval(interval);
                
                vscode.window.showInformationMessage(
                    `Analysis complete! Found ${job.result?.findings_count || 0} issues`
                );
                
                // Update results view
                updateResultsView(job);
                
            } else if (job.status === 'failed') {
                clearInterval(interval);
                
                vscode.window.showErrorMessage(
                    `Analysis failed: ${job.errors?.join(', ') || 'Unknown error'}`
                );
            }
            
            attempts++;
            if (attempts >= maxAttempts) {
                clearInterval(interval);
                vscode.window.showErrorMessage('Analysis timeout after 5 minutes');
            }
            
        } catch (error: any) {
            clearInterval(interval);
            vscode.window.showErrorMessage(
                `Failed to get results: ${error.response?.data?.message || error.message}`
            );
        }
    }, 5000); // Poll every 5 seconds
}

/**
 * Create results webview panel
 */
function createResultsView(context: vscode.ExtensionContext) {
    resultsPanel = vscode.window.createWebviewPanel(
        'glitchhunterResults',
        'GlitchHunter Results',
        vscode.ViewColumn.Two,
        {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.joinPath(context.extensionUri, 'media')
            ]
        }
    );
    
    resultsPanel.onDidDispose(
        () => {
            resultsPanel = undefined;
        },
        null,
        context.subscriptions
    );
}

/**
 * Update results webview with job data
 */
function updateResultsView(job: any) {
    if (!resultsPanel) return;
    
    const findings = job.result?.findings || [];
    
    resultsPanel.webview.html = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>GlitchHunter Results</title>
            <style>
                body {
                    font-family: var(--vscode-font-family);
                    padding: 20px;
                    color: var(--vscode-foreground);
                    background-color: var(--vscode-editor-background);
                }
                h2 {
                    border-bottom: 1px solid var(--vscode-widget-border);
                    padding-bottom: 10px;
                }
                .finding {
                    border: 1px solid var(--vscode-widget-border);
                    border-radius: 4px;
                    padding: 15px;
                    margin-bottom: 15px;
                }
                .finding.critical {
                    border-left: 4px solid #ef4444;
                }
                .finding.high {
                    border-left: 4px solid #f59e0b;
                }
                .finding.medium {
                    border-left: 4px solid #3b82f6;
                }
                .finding.low {
                    border-left: 4px solid #10b981;
                }
                .severity {
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                    text-transform: uppercase;
                }
                .severity.critical { background: #ef4444; color: white; }
                .severity.high { background: #f59e0b; color: white; }
                .severity.medium { background: #3b82f6; color: white; }
                .severity.low { background: #10b981; color: white; }
                .meta {
                    font-size: 12px;
                    color: var(--vscode-descriptionForeground);
                    margin: 10px 0;
                }
                button {
                    background: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    border: none;
                    padding: 8px 16px;
                    border-radius: 2px;
                    cursor: pointer;
                }
                button:hover {
                    background: var(--vscode-button-hoverBackground);
                }
            </style>
        </head>
        <body>
            <h2>🐛 GlitchHunter Analysis Results</h2>
            <p><strong>Repository:</strong> ${job.repo_path}</p>
            <p><strong>Execution Time:</strong> ${(job.result?.execution_time || 0).toFixed(2)}s</p>
            <p><strong>Findings:</strong> ${findings.length}</p>
            
            <h3>Findings</h3>
            ${findings.length > 0 ? findings.map((finding: any) => `
                <div class="finding ${finding.severity}">
                    <div class="severity ${finding.severity}">${finding.severity}</div>
                    <h4>${finding.title}</h4>
                    <div class="meta">
                        📁 ${finding.file_path}:${finding.line_start}
                        | 🎯 Confidence: ${(finding.confidence * 100).toFixed(0)}%
                    </div>
                    <p>${finding.description}</p>
                    <button onclick="applyRefactor('${finding.id}', '${finding.file_path}')">
                        Apply Auto-Fix
                    </button>
                </div>
            `).join('') : '<p>No findings found</p>'}
            
            <script>
                const vscode = acquireVsCodeApi();
                
                function applyRefactor(findingId, filePath) {
                    vscode.postMessage({
                        command: 'applyRefactor',
                        findingId,
                        filePath
                    });
                }
            </script>
        </body>
        </html>
    `;
}

/**
 * Deactivate extension
 */
export function deactivate() {
    if (resultsPanel) {
        resultsPanel.dispose();
    }
}
