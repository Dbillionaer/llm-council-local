#!/usr/bin/env python3
"""
Software Development Organization MCP Server.

Provides tools for:
- Safe sandboxed app execution via Docker
- Project file management (write, read, list, archive)
- AI-driven development team workflow (mcp-dev-team)

Tools:
- safe-app-execution: Run code in a sandboxed Docker container
- write-file: Write content to a project file
- read-file: Read content from a project file
- list-files: List files in a project folder
- create-archive: Create bzip2 archive of a project
- mcp-dev-team: AI-driven MCP server development workflow
"""

import json
import os
import subprocess
import tarfile
import tempfile
import shutil
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from datetime import datetime


# Base directory for projects
PROJECTS_BASE = Path(__file__).parent.parent.parent / "data" / "dev_projects"
DOCKER_IMAGE_NAME = "llm-council-dev-env"


def ensure_projects_dir():
    """Ensure the projects directory exists."""
    PROJECTS_BASE.mkdir(parents=True, exist_ok=True)
    return PROJECTS_BASE


def get_project_path(project_name: str) -> Path:
    """Get the path for a project, creating it if needed."""
    # Sanitize project name
    safe_name = "".join(c for c in project_name if c.isalnum() or c in "-_").strip()
    if not safe_name:
        safe_name = "unnamed_project"
    
    project_path = ensure_projects_dir() / safe_name
    return project_path


def build_docker_image() -> Dict[str, Any]:
    """Build the development environment Docker image if it doesn't exist."""
    # Check if image exists
    result = subprocess.run(
        ["docker", "images", "-q", DOCKER_IMAGE_NAME],
        capture_output=True, text=True
    )
    
    if result.stdout.strip():
        return {"exists": True, "image": DOCKER_IMAGE_NAME}
    
    # Create Dockerfile
    dockerfile_content = '''
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install base tools
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    wget \\
    git \\
    bzip2 \\
    python3 \\
    python3-pip \\
    python3-venv \\
    nodejs \\
    npm \\
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Go
RUN wget -q https://go.dev/dl/go1.21.5.linux-amd64.tar.gz \\
    && tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz \\
    && rm go1.21.5.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"

# Create workspace
WORKDIR /workspace

# Default command
CMD ["/bin/bash"]
'''
    
    # Create temp directory for build
    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_path = Path(tmpdir) / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        
        # Build image
        result = subprocess.run(
            ["docker", "build", "-t", DOCKER_IMAGE_NAME, tmpdir],
            capture_output=True, text=True, timeout=600
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to build Docker image: {result.stderr}"
            }
    
    return {"success": True, "image": DOCKER_IMAGE_NAME, "built": True}


def safe_app_execution(archive_path: str, run_script: str = "run.sh") -> Dict[str, Any]:
    """
    Execute code in a sandboxed Docker container.
    
    Args:
        archive_path: Path to bzip2 archive to unpack and run
        run_script: Name of the script to execute (default: run.sh)
    
    Returns:
        Execution log with all actions and results
    """
    log = []
    log.append(f"[{datetime.now().isoformat()}] Starting safe app execution")
    
    try:
        # Ensure Docker image exists
        log.append("Checking/building Docker image...")
        image_result = build_docker_image()
        if not image_result.get("success", True) and not image_result.get("exists"):
            return {"success": False, "error": image_result.get("error"), "log": log}
        
        if image_result.get("built"):
            log.append(f"Built Docker image: {DOCKER_IMAGE_NAME}")
        else:
            log.append(f"Using existing Docker image: {DOCKER_IMAGE_NAME}")
        
        # Verify archive exists
        archive = Path(archive_path)
        if not archive.exists():
            return {"success": False, "error": f"Archive not found: {archive_path}", "log": log}
        
        log.append(f"Found archive: {archive_path}")
        
        # Create temp directory for extraction
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract archive
            log.append("Extracting archive...")
            try:
                with tarfile.open(archive_path, "r:bz2") as tar:
                    tar.extractall(tmpdir)
                log.append("Archive extracted successfully")
            except Exception as e:
                return {"success": False, "error": f"Failed to extract archive: {e}", "log": log}
            
            # Check for run script
            run_script_path = Path(tmpdir) / run_script
            if not run_script_path.exists():
                # Look in subdirectories
                for subdir in Path(tmpdir).iterdir():
                    if subdir.is_dir():
                        candidate = subdir / run_script
                        if candidate.exists():
                            run_script_path = candidate
                            break
            
            if not run_script_path.exists():
                return {
                    "success": False,
                    "error": f"Run script not found: {run_script}",
                    "log": log,
                    "files": list(str(p) for p in Path(tmpdir).rglob("*"))
                }
            
            log.append(f"Found run script: {run_script_path}")
            
            # Run in Docker container
            log.append("Starting Docker container...")
            container_name = f"llm-council-sandbox-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Run container with mounted directory
            result = subprocess.run(
                [
                    "docker", "run",
                    "--rm",
                    "--name", container_name,
                    "-v", f"{tmpdir}:/workspace",
                    "--workdir", "/workspace",
                    "--network", "none",  # No network access for security
                    "--memory", "512m",   # Memory limit
                    "--cpus", "1",        # CPU limit
                    DOCKER_IMAGE_NAME,
                    "bash", "-c", f"chmod +x {run_script} && ./{run_script}"
                ],
                capture_output=True, text=True, timeout=300
            )
            
            log.append(f"Container exited with code: {result.returncode}")
            
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "log": log
            }
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out (5 minutes)", "log": log}
    except Exception as e:
        log.append(f"Error: {str(e)}")
        return {"success": False, "error": str(e), "log": log}


def write_file(project_name: str, filename: str, content: str) -> Dict[str, Any]:
    """
    Write content to a file in a project folder.
    
    Args:
        project_name: Name of the project folder
        filename: Name of the file to write
        content: Content to write to the file
    """
    try:
        project_path = get_project_path(project_name)
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Handle subdirectories in filename
        file_path = project_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(content)
        
        return {
            "success": True,
            "project": project_name,
            "file": filename,
            "path": str(file_path),
            "size": len(content)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_file(project_name: str, filename: str) -> Dict[str, Any]:
    """
    Read content from a file in a project folder.
    
    Args:
        project_name: Name of the project folder
        filename: Name of the file to read
    """
    try:
        project_path = get_project_path(project_name)
        file_path = project_path / filename
        
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {filename}"}
        
        content = file_path.read_text()
        
        return {
            "success": True,
            "project": project_name,
            "file": filename,
            "content": content,
            "size": len(content)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(project_name: str) -> Dict[str, Any]:
    """
    List all files in a project folder.
    
    Args:
        project_name: Name of the project folder
    """
    try:
        project_path = get_project_path(project_name)
        
        if not project_path.exists():
            return {"success": False, "error": f"Project not found: {project_name}"}
        
        files = []
        for path in project_path.rglob("*"):
            if path.is_file():
                rel_path = path.relative_to(project_path)
                files.append({
                    "name": str(rel_path),
                    "size": path.stat().st_size
                })
        
        return {
            "success": True,
            "project": project_name,
            "path": str(project_path),
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_archive(project_name: str) -> Dict[str, Any]:
    """
    Create a bzip2 archive of a project folder.
    
    Args:
        project_name: Name of the project folder
    """
    try:
        project_path = get_project_path(project_name)
        
        if not project_path.exists():
            return {"success": False, "error": f"Project not found: {project_name}"}
        
        # Create archive in parent directory
        archive_path = project_path.parent / f"{project_name}.tar.bz2"
        
        with tarfile.open(archive_path, "w:bz2") as tar:
            tar.add(project_path, arcname=project_name)
        
        return {
            "success": True,
            "project": project_name,
            "archive": str(archive_path),
            "size": archive_path.stat().st_size
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def mcp_dev_team(
    query: str, 
    config: Optional[Dict] = None, 
    on_event: Optional[Callable] = None,
    user_response: Optional[str] = None
) -> Dict[str, Any]:
    """
    AI-driven MCP server development workflow with memory recording.
    
    Uses multiple LLM roles:
    - software_architect: Analyzes requirements, creates task lists with expectations
    - software_dev_engineer: Writes code
    - qa_analyst: Tests and evaluates against expectations
    
    Features:
    - Plan validation step with user interaction
    - Test task after each development task
    - Expectations and evaluation for each task
    - Progress reporting with metrics
    - Memory recording via Graphiti
    
    Args:
        query: Description of the MCP server to develop
        config: Optional config overrides for LLM roles
        on_event: Optional callback for emitting UI events
        user_response: Optional user response for plan validation
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    try:
        from backend.llm_interface import query_model
        from backend.mcp_registry import get_mcp_registry
    except ImportError as e:
        return {"success": False, "error": f"Could not import backend modules: {e}"}
    
    # Try to import memory service for recording
    memory_service = None
    try:
        from backend.memory_service import MemoryService
        memory_service = MemoryService()
    except ImportError:
        pass  # Memory service not available
    
    # Helper to emit events
    def emit(event_type: str, data: Dict[str, Any]):
        if on_event:
            on_event({"type": event_type, **data})
    
    # Helper to record to memory
    async def record_memory(content: str, source: str):
        if memory_service and memory_service._available:
            try:
                await memory_service.record_episode(
                    content=content,
                    source_description=f"mcp-dev-team:{source}",
                    episode_type="dev_workflow",
                    data_label="intelligence"
                )
            except Exception as e:
                print(f"[mcp-dev-team] Memory recording failed: {e}")
    
    log = []
    progress_reports = []  # For UI frames
    
    def add_progress(status: str, message: str, metrics: Optional[Dict] = None):
        """Add a progress report entry."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": status,  # "working", "success", "failed", "complete"
            "message": message,
            "metrics": metrics or {}
        }
        progress_reports.append(report)
        log.append(f"[{report['timestamp']}] [{status.upper()}] {message}")
        emit("dev_team_progress", {
            "report": report,
            "total_reports": len(progress_reports)
        })
    
    add_progress("working", f"Starting MCP Dev Team for: {query[:100]}...")
    await record_memory(f"Starting development project: {query}", "init")
    
    # Load config
    config_path = Path(__file__).parent.parent.parent / "config.json"
    try:
        with open(config_path) as f:
            app_config = json.load(f)
    except Exception:
        app_config = {}
    
    # Get LLM models from config (with fallbacks)
    models_config = app_config.get("models", {})
    chairman = models_config.get("chairman", {})
    
    # Use dedicated role models if configured, otherwise fall back to chairman
    architect_model = models_config.get("software_architect", chairman)
    engineer_model = models_config.get("software_dev_engineer", architect_model)
    qa_model = models_config.get("qa_analyst", architect_model)
    
    # Override with config param if provided
    if config:
        architect_model = config.get("software_architect", architect_model)
        engineer_model = config.get("software_dev_engineer", engineer_model)
        qa_model = config.get("qa_analyst", qa_model)
    
    # =============================================
    # PHASE 1: Research and Planning
    # =============================================
    add_progress("working", "Phase 1: Research and Planning")
    emit("dev_team_phase", {"phase": 1, "name": "Research and Planning"})
    
    # Initial analysis with architect - now includes expectations
    architect_prompt = f"""You are a Software Architect analyzing a request to create an MCP (Model Context Protocol) server.

REQUEST: {query}

Analyze this request and create a detailed development plan:

1. Identify what tools need to be created
2. List any external APIs or services needed
3. Create a DETAILED task list where each development task MUST include:
   - Clear description of what to do
   - Expected outcomes after completion (measurable)
   - A corresponding test task immediately after it

IMPORTANT: Each development task must be followed by a test task that validates the expectations.

Respond in JSON format:
{{
  "project_name": "suggested-project-name",
  "tools_needed": ["tool1", "tool2"],
  "external_apis": ["api1"],
  "task_list": [
    {{
      "id": 1, 
      "type": "develop", 
      "description": "Create server.py with basic structure",
      "expectations": [
        "File server.py exists",
        "Contains proper imports",
        "Has handle_request function"
      ]
    }},
    {{
      "id": 2,
      "type": "test",
      "description": "Verify server.py structure",
      "validates_task": 1,
      "test_criteria": [
        "Check file exists",
        "Check imports are valid",
        "Check function signature"
      ]
    }}
  ],
  "needs_research": true/false,
  "research_queries": ["what to search for"],
  "summary": "Brief summary of the plan"
}}"""
    
    task_list = []
    project_name = "new-mcp-server"
    plan_summary = ""
    
    try:
        response = await query_model(architect_model, [{"role": "user", "content": architect_prompt}], timeout=120)
        if response and response.get('content'):
            content = response['content']
            await record_memory(f"Architect analysis: {content[:500]}", "architect")
            
            # Parse JSON
            try:
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]
                analysis = json.loads(content)
                task_list = analysis.get('task_list', [])
                project_name = analysis.get('project_name', 'new-mcp-server')
                plan_summary = analysis.get('summary', '')
                
                add_progress("success", f"Architect analysis complete: {len(task_list)} tasks identified")
                add_progress("success", f"Project name: {project_name}")
            except json.JSONDecodeError:
                add_progress("failed", "Could not parse architect response as JSON")
                task_list = [{"id": 1, "type": "develop", "description": query, "expectations": ["Code completes"]}]
    except Exception as e:
        add_progress("failed", f"Architect analysis failed: {e}")
        task_list = [{"id": 1, "type": "develop", "description": query, "expectations": ["Code completes"]}]
    
    # =============================================
    # PLAN VALIDATION STEP
    # =============================================
    emit("dev_team_plan_validation", {
        "project_name": project_name,
        "task_list": task_list,
        "summary": plan_summary,
        "awaiting_response": True
    })
    
    # If no user response provided, return with plan for validation
    if user_response is None:
        return {
            "success": True,
            "status": "awaiting_plan_validation",
            "project_name": project_name,
            "task_list": task_list,
            "summary": plan_summary,
            "log": log,
            "progress_reports": progress_reports,
            "instructions": "Respond with 'approved' to implement, 'refine' to improve the plan, or provide specific feedback"
        }
    
    # Handle user response to plan
    if user_response.lower().strip() == "refine":
        # Refine the plan
        refine_prompt = f"""Think through this development plan again and refine it.

ORIGINAL REQUEST: {query}
CURRENT PLAN:
{json.dumps(task_list, indent=2)}

Consider:
1. Are there any missing steps?
2. Are the expectations measurable and clear?
3. Are test tasks properly paired with development tasks?
4. Can any tasks be optimized or combined?

Provide an improved plan in the same JSON format, plus a summary of changes made."""

        try:
            response = await query_model(architect_model, [{"role": "user", "content": refine_prompt}], timeout=120)
            if response and response.get('content'):
                content = response['content']
                try:
                    if '```json' in content:
                        content = content.split('```json')[1].split('```')[0]
                    refined = json.loads(content)
                    task_list = refined.get('task_list', task_list)
                    add_progress("success", "Plan refined based on review")
                    await record_memory(f"Plan refined: {content[:500]}", "refinement")
                except json.JSONDecodeError:
                    add_progress("failed", "Could not parse refined plan")
        except Exception as e:
            add_progress("failed", f"Plan refinement failed: {e}")
        
        # Return for another validation round
        return {
            "success": True,
            "status": "awaiting_plan_validation",
            "project_name": project_name,
            "task_list": task_list,
            "summary": "Plan has been refined. Please review again.",
            "log": log,
            "progress_reports": progress_reports,
            "instructions": "Respond with 'approved' to implement, 'refine' again, or provide specific feedback"
        }
    
    elif user_response.lower().strip() != "approved":
        # User provided specific feedback - incorporate it
        feedback_prompt = f"""Revise the development plan based on user feedback.

ORIGINAL REQUEST: {query}
CURRENT PLAN:
{json.dumps(task_list, indent=2)}

USER FEEDBACK: {user_response}

Update the plan to address the user's feedback. Respond in the same JSON format."""

        try:
            response = await query_model(architect_model, [{"role": "user", "content": feedback_prompt}], timeout=120)
            if response and response.get('content'):
                content = response['content']
                try:
                    if '```json' in content:
                        content = content.split('```json')[1].split('```')[0]
                    revised = json.loads(content)
                    task_list = revised.get('task_list', task_list)
                    add_progress("success", "Plan updated based on user feedback")
                    await record_memory(f"User feedback incorporated: {user_response}", "feedback")
                except json.JSONDecodeError:
                    add_progress("failed", "Could not parse revised plan")
        except Exception as e:
            add_progress("failed", f"Plan revision failed: {e}")
        
        return {
            "success": True,
            "status": "awaiting_plan_validation",
            "project_name": project_name,
            "task_list": task_list,
            "summary": "Plan has been updated based on your feedback.",
            "log": log,
            "progress_reports": progress_reports,
            "instructions": "Respond with 'approved' to implement, 'refine', or provide more feedback"
        }
    
    # Plan approved - proceed with implementation
    add_progress("success", "Plan approved by user - proceeding with implementation")
    await record_memory(f"Plan approved. Starting implementation of {len(task_list)} tasks.", "approval")
    
    # =============================================
    # PHASE 2: Development with Testing Loop
    # =============================================
    add_progress("working", "Phase 2: Development and Testing")
    emit("dev_team_phase", {"phase": 2, "name": "Development and Testing"})
    
    files_created = []
    tool_definitions = []
    task_results = []
    
    # Process tasks in order
    current_task_idx = 0
    max_iterations = 100  # Safety limit
    iteration = 0
    
    while current_task_idx < len(task_list) and iteration < max_iterations:
        iteration += 1
        task = task_list[current_task_idx]
        task_id = task.get('id', current_task_idx + 1)
        task_type = task.get('type', 'develop')
        task_desc = task.get('description', '')
        expectations = task.get('expectations', [])
        
        add_progress("working", f"Task {task_id}: {task_desc[:80]}...")
        emit("dev_team_task", {
            "task_id": task_id,
            "type": task_type,
            "description": task_desc,
            "expectations": expectations
        })
        
        if task_type == "develop":
            # Development task
            dev_prompt = f"""You are a Software Development Engineer.

PROJECT: {project_name}
TASK: {task_desc}

EXPECTATIONS AFTER COMPLETION:
{json.dumps(expectations, indent=2)}

FILES CREATED SO FAR:
{json.dumps(files_created, indent=2)}

Create the required code. For each file, provide complete content.

Respond in JSON format:
{{
  "files": [
    {{"path": "filename.py", "content": "...full code..."}}
  ],
  "tool_definitions": [
    {{"name": "tool-name", "description": "...", "parameters": {{}}}}
  ],
  "completion_notes": "What was accomplished"
}}"""
            
            try:
                response = await query_model(engineer_model, [{"role": "user", "content": dev_prompt}], timeout=180)
                if response and response.get('content'):
                    content = response['content']
                    try:
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0]
                        elif '```' in content:
                            content = content.split('```')[1].split('```')[0]
                        dev_result = json.loads(content)
                        
                        # Write files
                        for file_info in dev_result.get('files', []):
                            file_path = file_info.get('path', '')
                            file_content = file_info.get('content', '')
                            if file_path and file_content:
                                result = write_file(project_name, file_path, file_content)
                                if result.get('success'):
                                    files_created.append(file_path)
                                    add_progress("success", f"Created: {file_path}")
                        
                        # Collect tool definitions
                        tool_definitions.extend(dev_result.get('tool_definitions', []))
                        
                        task_results.append({
                            "task_id": task_id,
                            "type": "develop",
                            "status": "completed",
                            "files": [f.get('path') for f in dev_result.get('files', [])],
                            "notes": dev_result.get('completion_notes', '')
                        })
                        await record_memory(f"Task {task_id} completed: {task_desc[:100]}", "development")
                        
                    except json.JSONDecodeError:
                        add_progress("failed", f"Task {task_id}: Could not parse response")
                        task_results.append({"task_id": task_id, "type": "develop", "status": "parse_error"})
            except Exception as e:
                add_progress("failed", f"Task {task_id} failed: {e}")
                task_results.append({"task_id": task_id, "type": "develop", "status": "error", "error": str(e)})
        
        elif task_type == "test":
            # Test task - evaluate expectations from the previous dev task
            validates_task = task.get('validates_task', task_id - 1)
            test_criteria = task.get('test_criteria', expectations)
            
            # Find the dev task result
            dev_result = next((r for r in task_results if r.get('task_id') == validates_task), None)
            
            # QA evaluation
            qa_prompt = f"""You are a QA Analyst evaluating a development task.

PROJECT: {project_name}
TASK BEING VALIDATED: Task {validates_task}
TEST CRITERIA:
{json.dumps(test_criteria, indent=2)}

FILES IN PROJECT:
{json.dumps(files_created, indent=2)}

DEVELOPMENT RESULT:
{json.dumps(dev_result, indent=2) if dev_result else "No result found"}

Evaluate whether the expectations were met. For each criterion:
1. Check if it was satisfied
2. Explain why or why not
3. Suggest fixes if not met

Respond in JSON format:
{{
  "overall_pass": true/false,
  "criteria_results": [
    {{"criterion": "...", "passed": true/false, "reason": "..."}}
  ],
  "suggestions": ["fix suggestion 1", "..."],
  "needs_rework": true/false
}}"""
            
            try:
                response = await query_model(qa_model, [{"role": "user", "content": qa_prompt}], timeout=120)
                if response and response.get('content'):
                    content = response['content']
                    try:
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0]
                        qa_result = json.loads(content)
                        
                        overall_pass = qa_result.get('overall_pass', False)
                        
                        if overall_pass:
                            add_progress("success", f"Test {task_id}: PASSED - expectations met")
                            emit("dev_team_test_result", {
                                "task_id": task_id,
                                "validates_task": validates_task,
                                "passed": True,
                                "criteria_results": qa_result.get('criteria_results', [])
                            })
                        else:
                            add_progress("failed", f"Test {task_id}: FAILED - needs rework")
                            emit("dev_team_test_result", {
                                "task_id": task_id,
                                "validates_task": validates_task,
                                "passed": False,
                                "criteria_results": qa_result.get('criteria_results', []),
                                "suggestions": qa_result.get('suggestions', [])
                            })
                            
                            # If needs rework, we could add a rework task
                            if qa_result.get('needs_rework'):
                                suggestions = qa_result.get('suggestions', [])
                                rework_task = {
                                    "id": len(task_list) + 1,
                                    "type": "develop",
                                    "description": f"Rework task {validates_task}: " + "; ".join(suggestions[:3]),
                                    "expectations": test_criteria
                                }
                                task_list.append(rework_task)
                                add_progress("working", f"Added rework task based on test feedback")
                        
                        task_results.append({
                            "task_id": task_id,
                            "type": "test",
                            "validates_task": validates_task,
                            "passed": overall_pass,
                            "details": qa_result
                        })
                        await record_memory(f"Test {task_id}: {'PASSED' if overall_pass else 'FAILED'}", "testing")
                        
                    except json.JSONDecodeError:
                        add_progress("failed", f"Test {task_id}: Could not parse QA response")
                        task_results.append({"task_id": task_id, "type": "test", "status": "parse_error"})
            except Exception as e:
                add_progress("failed", f"Test {task_id} failed: {e}")
                task_results.append({"task_id": task_id, "type": "test", "status": "error", "error": str(e)})
        
        else:
            # Research or other task type - skip for now
            add_progress("working", f"Task {task_id}: Skipping {task_type} task")
        
        current_task_idx += 1
    
    # =============================================
    # PHASE 3: Final Testing and Archive
    # =============================================
    add_progress("working", "Phase 3: Final Testing and Packaging")
    emit("dev_team_phase", {"phase": 3, "name": "Final Testing and Packaging"})
    
    test_result = None
    archive_path = None
    
    if files_created:
        # Create archive
        archive_result = create_archive(project_name)
        if archive_result.get('success'):
            archive_path = archive_result.get('archive')
            add_progress("success", f"Created archive: {archive_path}")
            
            # Run in sandbox if run.sh exists
            if 'run.sh' in files_created:
                test_result = safe_app_execution(archive_path)
                if test_result.get('success'):
                    add_progress("success", "Sandbox tests passed!")
                else:
                    add_progress("failed", f"Sandbox tests failed: {test_result.get('stderr', test_result.get('error', 'Unknown'))[:200]}")
    
    # Calculate final metrics
    total_tasks = len(task_results)
    dev_tasks = [r for r in task_results if r.get('type') == 'develop']
    test_tasks = [r for r in task_results if r.get('type') == 'test']
    passed_tests = [r for r in test_tasks if r.get('passed')]
    
    metrics = {
        "total_tasks": total_tasks,
        "development_tasks": len(dev_tasks),
        "test_tasks": len(test_tasks),
        "tests_passed": len(passed_tests),
        "tests_failed": len(test_tasks) - len(passed_tests),
        "files_created": len(files_created),
        "tools_defined": len(tool_definitions)
    }
    
    add_progress("complete", f"Development complete. {len(files_created)} files, {len(passed_tests)}/{len(test_tasks)} tests passed", metrics)
    await record_memory(f"Project {project_name} completed. Files: {len(files_created)}, Tests: {len(passed_tests)}/{len(test_tasks)}", "completion")
    
    # Emit final result
    emit("dev_team_complete", {
        "project_name": project_name,
        "metrics": metrics,
        "files": files_created,
        "success": len(test_tasks) == 0 or len(passed_tests) > 0
    })
    
    return {
        "success": True,
        "status": "completed",
        "project_name": project_name,
        "files_created": files_created,
        "tool_definitions": tool_definitions,
        "task_results": task_results,
        "metrics": metrics,
        "test_result": {
            "success": test_result.get('success') if test_result else None,
            "stdout": test_result.get('stdout', '')[:1000] if test_result else None,
            "stderr": test_result.get('stderr', '')[:500] if test_result else None
        } if test_result else None,
        "archive_path": archive_path,
        "log": log,
        "progress_reports": progress_reports,
        "integration_instructions": f"""
To integrate this MCP server:

1. Add to mcp_servers.json:
{{
  "name": "{project_name}",
  "command": ["python3", "-m", "mcp_servers.{project_name.replace('-', '_')}.server"],
  "port": null,
  "description": "{query[:100]}"
}}

2. Copy files from data/dev_projects/{project_name}/ to mcp_servers/{project_name.replace('-', '_')}/

3. Restart the application
"""
    }


def mcp_dev_team_sync(
    query: str, 
    config: Optional[Dict] = None,
    user_response: Optional[str] = None
) -> Dict[str, Any]:
    """Synchronous wrapper for mcp_dev_team."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(mcp_dev_team(query, config, user_response=user_response))


# Tool definitions
TOOLS = [
    {
        "name": "safe-app-execution",
        "description": "Execute code in a sandboxed Docker container. Unpacks a bzip2 archive, makes run.sh executable, and runs it with resource limits and no network access.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "archive_path": {
                    "type": "string",
                    "description": "Path to the bzip2 archive (.tar.bz2) to unpack and run"
                },
                "run_script": {
                    "type": "string",
                    "description": "Name of the script to execute (default: run.sh)"
                }
            },
            "required": ["archive_path"]
        }
    },
    {
        "name": "write-file",
        "description": "Write content to a file in a project folder. Creates the project folder if it doesn't exist.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project folder"
                },
                "filename": {
                    "type": "string",
                    "description": "Name of the file to write (can include subdirectories)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["project_name", "filename", "content"]
        }
    },
    {
        "name": "read-file",
        "description": "Read content from a file in a project folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project folder"
                },
                "filename": {
                    "type": "string",
                    "description": "Name of the file to read"
                }
            },
            "required": ["project_name", "filename"]
        }
    },
    {
        "name": "list-files",
        "description": "List all files in a project folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project folder"
                }
            },
            "required": ["project_name"]
        }
    },
    {
        "name": "create-archive",
        "description": "Create a bzip2 archive (.tar.bz2) of a project folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project folder to archive"
                }
            },
            "required": ["project_name"]
        }
    },
    {
        "name": "mcp-dev-team",
        "description": "AI-driven MCP server development workflow with plan validation. Uses architect, engineer, and QA LLM roles. First call creates a plan, then user responds with 'approved', 'refine', or feedback.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Description of the MCP server to develop (what tools it should provide, what it should do)"
                },
                "user_response": {
                    "type": "string",
                    "description": "User response for plan validation: 'approved' to proceed, 'refine' to improve plan, or specific feedback"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "send-response-to-dev-team",
        "description": "Send a response to an ongoing mcp-dev-team workflow for plan validation or feedback",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project being developed"
                },
                "response": {
                    "type": "string",
                    "description": "User response: 'approved', 'refine', or specific feedback"
                }
            },
            "required": ["project_name", "response"]
        }
    }
]


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a JSON-RPC request."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    response = {"jsonrpc": "2.0", "id": request_id}
    
    try:
        if method == "initialize":
            response["result"] = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "software-dev-org", "version": "1.0.0"}
            }
        
        elif method == "notifications/initialized":
            return None
        
        elif method == "tools/list":
            response["result"] = {"tools": TOOLS}
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "safe-app-execution":
                result = safe_app_execution(
                    arguments.get("archive_path"),
                    arguments.get("run_script", "run.sh")
                )
            elif tool_name == "write-file":
                result = write_file(
                    arguments.get("project_name"),
                    arguments.get("filename"),
                    arguments.get("content")
                )
            elif tool_name == "read-file":
                result = read_file(
                    arguments.get("project_name"),
                    arguments.get("filename")
                )
            elif tool_name == "list-files":
                result = list_files(arguments.get("project_name"))
            elif tool_name == "create-archive":
                result = create_archive(arguments.get("project_name"))
            elif tool_name == "mcp-dev-team":
                result = mcp_dev_team_sync(
                    arguments.get("query"),
                    user_response=arguments.get("user_response")
                )
            elif tool_name == "send-response-to-dev-team":
                # This is a convenience tool - it just calls mcp-dev-team with a response
                # In practice, the project context should be maintained by the caller
                result = {
                    "success": True,
                    "message": f"Response '{arguments.get('response')}' received for project '{arguments.get('project_name')}'. Use mcp-dev-team with user_response parameter to continue."
                }
            else:
                response["error"] = {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                return response
            
            response["result"] = {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            }
        
        else:
            response["error"] = {"code": -32601, "message": f"Unknown method: {method}"}
    
    except Exception as e:
        response["error"] = {"code": -32000, "message": str(e)}
    
    return response


def main():
    """Main entry point for the MCP server."""
    from mcp_servers.http_wrapper import stdio_main
    stdio_main(handle_request, "Software Dev Org MCP")


if __name__ == "__main__":
    main()
