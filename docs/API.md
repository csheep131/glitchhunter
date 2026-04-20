# GlitchHunter v2.0 - API Documentation

## Overview

GlitchHunter provides a RESTful API for programmatic access to all Problem-Solver and Bug-Hunting features.

**Base URL:** `http://localhost:8000`  
**API Version:** `v2.0`  
**Content Type:** `application/json`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Problems API](#problems-api)
3. [Analysis API](#analysis-api)
4. [Reports API](#reports-api)
5. [Stack API](#stack-api)
6. [WebSocket API](#websocket-api)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

---

## Authentication

Currently, the API does not require authentication for local usage. For production deployments, configure API keys in `config.yaml`:

```yaml
api:
  authentication:
    enabled: true
    api_key: "your-api-key"
```

Include in requests:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/...
```

---

## Problems API

### Create Problem

**POST** `/api/problems`

Create a new problem case.

#### Request Body

```json
{
  "description": "The application startup is too slow",
  "title": "Slow Startup (optional)",
  "source": "api"
}
```

#### Response

**201 Created**
```json
{
  "id": "prob_20260415_001",
  "title": "Slow Startup",
  "raw_description": "The application startup is too slow",
  "problem_type": "performance",
  "severity": "medium",
  "status": "intake",
  "created_at": "2026-04-15T10:30:00",
  "source": "api"
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/problems \
  -H "Content-Type: application/json" \
  -d '{
    "description": "The application startup is too slow"
  }'
```

---

### List Problems

**GET** `/api/problems`

Retrieve all problems with optional filtering.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (intake, diagnosis, planning, implementation, validation, closed) |
| `type` | string | Filter by problem type (bug, performance, etc.) |
| `limit` | integer | Maximum results (default: 50) |
| `offset` | integer | Pagination offset |

#### Response

**200 OK**
```json
{
  "problems": [
    {
      "id": "prob_20260415_001",
      "title": "Slow Startup",
      "problem_type": "performance",
      "status": "diagnosis",
      "created_at": "2026-04-15T10:30:00"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### Example

```bash
# List all
curl http://localhost:8000/api/problems

# Filter by status
curl "http://localhost:8000/api/problems?status=intake"

# Filter by type
curl "http://localhost:8000/api/problems?type=performance"
```

---

### Get Problem

**GET** `/api/problems/{problem_id}`

Retrieve detailed problem information.

#### Response

**200 OK**
```json
{
  "id": "prob_20260415_001",
  "title": "Slow Startup",
  "raw_description": "The application startup is too slow",
  "problem_type": "performance",
  "severity": "medium",
  "status": "diagnosis",
  "goal_state": "Startup should complete in <5 seconds",
  "affected_components": ["startup", "initialization"],
  "success_criteria": [
    "Startup time < 5 seconds",
    "No errors in logs"
  ],
  "risk_level": "medium",
  "target_stack": "auto",
  "created_at": "2026-04-15T10:30:00",
  "updated_at": "2026-04-15T10:35:00"
}
```

#### Example

```bash
curl http://localhost:8000/api/problems/prob_20260415_001
```

---

### Classify Problem

**POST** `/api/problems/{problem_id}/classify`

Automatically classify a problem.

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "problem_type": "performance",
  "confidence": 0.87,
  "keywords_found": ["slow", "startup", "performance"],
  "affected_components": ["startup", "initialization"],
  "alternatives": [
    {"problem_type": "reliability", "confidence": 0.45}
  ],
  "recommended_actions": [
    "Performance measurement",
    "Identify bottlenecks",
    "Analyze startup sequence"
  ]
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/problems/prob_20260415_001/classify
```

---

### Get Diagnosis

**GET** `/api/problems/{problem_id}/diagnosis`

Retrieve diagnosis for a problem.

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "status": "complete",
  "summary": "Diagnosis for 'Slow Startup': 3 causes identified",
  "root_cause_summary": "- Inefficient initialization (Confidence: 75%)\n- Blocking I/O (Confidence: 60%)",
  "causes": [
    {
      "id": "cause_001",
      "description": "Inefficient initialization",
      "cause_type": "root_cause",
      "confidence": 0.75,
      "evidence": ["Startup takes 30 seconds"],
      "is_blocking": true
    }
  ],
  "data_flows": [
    {
      "id": "flow_001",
      "name": "Startup Sequence",
      "source": "main()",
      "sink": "App.init()",
      "issues": ["Blocking I/O in init"]
    }
  ],
  "uncertainties": [
    {
      "id": "unc_001",
      "question": "Is this the actual root cause?",
      "impact": "high",
      "resolution_steps": ["Profile startup", "Analyze logs"]
    }
  ],
  "recommended_next_steps": [
    "Verify root cause",
    "Profile startup sequence"
  ]
}
```

#### Example

```bash
curl http://localhost:8000/api/problems/prob_20260415_001/diagnosis
```

---

### Decompose Problem

**POST** `/api/problems/{problem_id}/decompose`

Decompose problem into subproblems.

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "subproblems": [
    {
      "id": "sub_001",
      "title": "Performance Measurement",
      "description": "Measure current startup performance",
      "subproblem_type": "analysis",
      "priority": 1,
      "effort": "low",
      "status": "open",
      "dependencies": []
    },
    {
      "id": "sub_002",
      "title": "Bottleneck Identification",
      "description": "Identify performance bottlenecks",
      "subproblem_type": "analysis",
      "priority": 2,
      "effort": "medium",
      "status": "open",
      "dependencies": ["sub_001"]
    }
  ],
  "summary": "Problem decomposed into 6 subproblems",
  "statistics": {
    "total_subproblems": 6,
    "blocking_count": 1,
    "ready_count": 3
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/problems/prob_20260415_001/decompose
```

---

### Create Solution Plan

**POST** `/api/problems/{problem_id}/plan`

Generate solution plan with multiple paths.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_decomposition` | boolean | true | Use decomposition if available |

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "solution_paths": {
    "sub_001": [
      {
        "id": "path_001",
        "title": "Manual Profiling",
        "description": "Manual performance profiling",
        "solution_type": "analysis",
        "effectiveness": 8,
        "invasiveness": 2,
        "risk": "low",
        "effort": 3,
        "testability": 9,
        "estimated_hours": 2.0,
        "overall_score": 7.8
      },
      {
        "id": "path_002",
        "title": "Automated Profiling",
        "description": "Use automated profiling tools",
        "solution_type": "automation",
        "effectiveness": 9,
        "invasiveness": 3,
        "risk": "low",
        "effort": 4,
        "testability": 8,
        "estimated_hours": 4.0,
        "overall_score": 7.5
      }
    ]
  },
  "selected_paths": {
    "sub_001": "path_001"
  },
  "overall_strategy": "Solution strategy with 6/6 selected paths",
  "statistics": {
    "total_subproblems": 6,
    "total_paths": 18,
    "selected_count": 6,
    "quick_wins": 2,
    "high_risk_paths": 0
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/problems/prob_20260415_001/plan
```

---

### Select Solution Path

**PATCH** `/api/problems/{problem_id}/plan/select`

Select a specific solution path for a subproblem.

#### Request Body

```json
{
  "subproblem_id": "sub_001",
  "path_id": "path_002"
}
```

#### Response

**200 OK**
```json
{
  "success": true,
  "subproblem_id": "sub_001",
  "selected_path_id": "path_002"
}
```

#### Example

```bash
curl -X PATCH http://localhost:8000/api/problems/prob_20260415_001/plan/select \
  -H "Content-Type: application/json" \
  -d '{
    "subproblem_id": "sub_001",
    "path_id": "path_002"
  }'
```

---

### Get Stack Recommendation

**GET** `/api/problems/{problem_id}/stack/recommend`

Get recommended stack for a problem.

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "recommended_stack": "stack_b",
  "reason": "Performance analysis requires enhanced capabilities",
  "profile": {
    "stack_id": "stack_b",
    "name": "Stack B (Enhanced)",
    "description": "Enhanced stack for 24GB GPU configuration",
    "resources": {
      "max_memory_gb": 64,
      "max_cpu_cores": 16,
      "gpu_available": true,
      "gpu_memory_gb": 24.0
    }
  }
}
```

#### Example

```bash
curl http://localhost:8000/api/problems/prob_20260415_001/stack/recommend
```

---

### Execute Auto-Fix

**POST** `/api/problems/{problem_id}/fix`

Execute auto-fix based on solution plan.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dry_run` | boolean | true | Don't apply actual changes |
| `validate` | boolean | true | Validate after applying |

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "overall_status": "completed",
  "summary": "Auto-Fix: 6/6 patches successful (100% Success-Rate)",
  "patches": [
    {
      "id": "patch_001",
      "subproblem_id": "sub_001",
      "file_path": "src/startup.py",
      "status": "completed",
      "validation_passed": true,
      "rollback_available": true
    }
  ],
  "statistics": {
    "total_patches": 6,
    "applied": 6,
    "failed": 0,
    "rolled_back": 0,
    "success_rate": 100.0
  }
}
```

#### Example

```bash
# Dry run
curl -X POST "http://localhost:8000/api/problems/prob_20260415_001/fix?dry_run=true"

# Apply fixes
curl -X POST "http://localhost:8000/api/problems/prob_20260415_001/fix?dry_run=false"
```

---

### Rollback Auto-Fix

**POST** `/api/problems/{problem_id}/rollback`

Rollback applied auto-fix.

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "overall_status": "rolled_back",
  "summary": "Rollback: 6/6 patches rolled back",
  "patches": [
    {
      "id": "patch_001",
      "status": "rolled_back"
    }
  ]
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/problems/prob_20260415_001/rollback
```

---

### Goal Validation

**POST** `/api/problems/{problem_id}/validate`

Perform goal validation.

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "overall_status": "passed",
  "summary": "Goal Validation: 5/5 criteria met (100%)",
  "results": [
    {
      "criterion": "Startup time < 5 seconds",
      "status": "passed",
      "evidence": ["Measured: 3.2 seconds"],
      "metrics": {"startup_time_ms": 3200}
    }
  ],
  "statistics": {
    "total_criteria": 5,
    "passed": 5,
    "failed": 0,
    "completion_percentage": 100.0
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/problems/prob_20260415_001/validate
```

---

### Intent Validation

**POST** `/api/problems/{problem_id}/intent`

Perform intent validation (detect superficial fixes).

#### Request Body

```json
{
  "solution_description": "Implemented caching for startup sequence"
}
```

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "original_problem_description": "The application startup is too slow",
  "original_intent": "Startup should complete in <5 seconds",
  "problem_addressed": true,
  "symptoms_resolved": true,
  "root_cause_fixed": true,
  "no_side_effects": true,
  "analysis": "✅ Problem was addressed\n✅ Symptoms resolved\n✅ Root cause fixed\n✅ No side effects",
  "concerns": [],
  "overall_status": "passed"
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/problems/prob_20260415_001/intent \
  -H "Content-Type: application/json" \
  -d '{
    "solution_description": "Implemented caching"
  }'
```

---

### Delete Problem

**DELETE** `/api/problems/{problem_id}`

Delete a problem case.

#### Response

**200 OK**
```json
{
  "success": true,
  "problem_id": "prob_20260415_001"
}
```

#### Example

```bash
curl -X DELETE http://localhost:8000/api/problems/prob_20260415_001
```

---

## Analysis API

### Start Analysis

**POST** `/api/analysis`

Start code analysis (Bug-Hunting mode).

#### Request Body

```json
{
  "path": "/path/to/code",
  "incremental": true,
  "security_only": false
}
```

#### Response

**202 Accepted**
```json
{
  "analysis_id": "analysis_20260415_001",
  "status": "running",
  "path": "/path/to/code",
  "started_at": "2026-04-15T10:30:00"
}
```

#### Example

```bash
curl -X POST http://localhost:8000/api/analysis \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/code"
  }'
```

---

### Get Analysis Results

**GET** `/api/analysis/{analysis_id}`

Retrieve analysis results.

#### Response

**200 OK**
```json
{
  "analysis_id": "analysis_20260415_001",
  "status": "completed",
  "findings": [
    {
      "id": "finding_001",
      "type": "security",
      "severity": "high",
      "file_path": "src/auth.py",
      "line": 42,
      "message": "SQL Injection vulnerability"
    }
  ],
  "summary": {
    "total_findings": 5,
    "security": 3,
    "correctness": 2
  }
}
```

---

## Reports API

### Generate Report

**POST** `/api/problems/{problem_id}/report`

Generate all reports for a problem.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `classify` | boolean | false | Include classification |
| `output_dir` | string | default | Custom output directory |

#### Response

**200 OK**
```json
{
  "problem_id": "prob_20260415_001",
  "reports": {
    "problem_case": "/path/to/problem_case.json",
    "diagnosis_stub": "/path/to/diagnosis_stub.md",
    "constraints": "/path/to/constraints.md"
  }
}
```

---

## Stack API

### List Stacks

**GET** `/api/stacks`

List available stacks.

#### Response

**200 OK**
```json
{
  "stacks": [
    {
      "stack_id": "stack_a",
      "name": "Stack A (Standard)",
      "description": "Standard stack for 8GB GPU",
      "capabilities": {
        "total": 15,
        "supported": 14
      },
      "resources": {
        "max_memory_gb": 32,
        "max_cpu_cores": 8,
        "gpu_available": true,
        "gpu_memory_gb": 8.0
      }
    },
    {
      "stack_id": "stack_b",
      "name": "Stack B (Enhanced)",
      "description": "Enhanced stack for 24GB GPU",
      "capabilities": {
        "total": 15,
        "supported": 15
      },
      "resources": {
        "max_memory_gb": 64,
        "max_cpu_cores": 16,
        "gpu_available": true,
        "gpu_memory_gb": 24.0
      }
    }
  ]
}
```

---

### Compare Stacks

**GET** `/api/stacks/compare`

Compare both stacks.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `capability` | string | Compare specific capability |

#### Response

**200 OK**
```json
{
  "stack_a": {
    "name": "Stack A (Standard)",
    "capabilities": {
      "total_capabilities": 15,
      "supported_capabilities": 14,
      "capability_coverage": 93.3
    }
  },
  "stack_b": {
    "name": "Stack B (Enhanced)",
    "capabilities": {
      "total_capabilities": 15,
      "supported_capabilities": 15,
      "capability_coverage": 100.0
    }
  },
  "differences": {
    "capability_coverage": {
      "stack_a": 93.3,
      "stack_b": 100.0,
      "difference": 6.7
    },
    "resources": {
      "memory": {"stack_a": 32, "stack_b": 64},
      "cpu": {"stack_a": 8, "stack_b": 16},
      "gpu": {"stack_a": 8.0, "stack_b": 24.0}
    }
  }
}
```

---

## WebSocket API

### Real-time Updates

Connect to WebSocket for real-time progress updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/problems/prob_20260415_001');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

#### Message Types

```json
{
  "type": "classification_complete",
  "problem_id": "prob_20260415_001",
  "data": {...}
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "PROBLEM_NOT_FOUND",
    "message": "Problem prob_20260415_001 not found",
    "details": {...}
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (processing) |
| 400 | Bad Request |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

### Error Codes

| Code | Description |
|------|-------------|
| `PROBLEM_NOT_FOUND` | Problem ID doesn't exist |
| `INVALID_STATUS` | Invalid problem status |
| `INVALID_TYPE` | Invalid problem type |
| `VALIDATION_FAILED` | Validation errors |
| `FIX_FAILED` | Auto-fix failed |

---

## Rate Limiting

Default rate limits:

- **100 requests/minute** per endpoint
- **1000 requests/hour** total

Exceeded limits return `429 Too Many Requests`.

---

## SDK Examples

### Python

```python
import requests

# Create problem
response = requests.post(
    'http://localhost:8000/api/problems',
    json={'description': 'Performance issue'}
)
problem = response.json()

# Classify
response = requests.post(
    f'http://localhost:8000/api/problems/{problem["id"]}/classify'
)
classification = response.json()

# Get diagnosis
response = requests.get(
    f'http://localhost:8000/api/problems/{problem["id"]}/diagnosis'
)
diagnosis = response.json()

# Execute fix (dry-run)
response = requests.post(
    f'http://localhost:8000/api/problems/{problem["id"]}/fix?dry_run=true'
)
fix_result = response.json()
```

### JavaScript

```javascript
const API_BASE = 'http://localhost:8000/api';

// Create problem
const response = await fetch(`${API_BASE}/problems`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({description: 'Performance issue'})
});
const problem = await response.json();

// Classify
const classResponse = await fetch(
  `${API_BASE}/problems/${problem.id}/classify`,
  {method: 'POST'}
);
const classification = await classResponse.json();
```

---

**GlitchHunter v2.0 API** - Complete programmatic access to all features.
