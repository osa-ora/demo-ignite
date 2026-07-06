from fastmcp import FastMCP
import demo_engine as engine
from config import MCP_HOST, MCP_PORT, MCP_TRANSPORT, DEBUG, DEFAULT_WORKSPACE
import os
from typing import Optional

mcp = FastMCP("demo-ignite-v1")

# -----------------------------------------------------
# DEBUG HELPER
# -----------------------------------------------------
def debug(msg: str):
    if DEBUG:
        print("DEBUG:" + msg)


# =========================================================
# DEMO REGISTRY
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

List all available demos.
"""
)
def list_demos():
    debug("Invoke list_demos.")
    return engine.fetch_index()


# =========================================================
# DEMO SEARCH
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Search demos by keyword.

The search checks the demo keywords, name and description,
and returns all matching demos together with their available
deployment environments.
"""
)
def find_demo(keyword: str):
    debug(f"Invoke find_demo {keyword}.")
    return engine.find_demo(keyword)

# =========================================================
# DEMO DETAILS
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Get the full demo definition using its name or ID.

Optionally specify the deployment environment.
Defaults to "local".
"""
)
def get_demo_details(key: str, environment: str = "local"):
    debug(f"Invoke get_demo_details {key}.")
    return engine.fetch_demo_file(key, environment)


# =========================================================
# DEMO PREREQUISITES
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

List the prerequisites required to install and run a demo.

The demo can be identified by name or ID.

Optionally specify the deployment environment.
Defaults to "local".
"""
)
def get_demo_prerequisites(key: str, environment: str = "local"):
    debug(f"Invoke get_demo_prerequisites {key}.")

    demo_def = engine.fetch_demo_file(key, environment)

    # FIX: support BOTH formats (list OR dict with steps)
    prereqs = demo_def.get("prerequisites", [])

    steps = prereqs.get("steps", []) if isinstance(prereqs, dict) else prereqs

    return {
        "demo": demo_def.get("name", key),
        "environment": environment,
        "prerequisites": steps or []
    }


# =========================================================
# VALIDATE PREREQUISITES
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Validate prerequisites required to install and run a demo.

This does NOT install anything.
It only checks system readiness (python, pip, git, etc).
"""
)
def validate_demo_prerequisites(key: str, environment: str = "local"):
    debug(f"Invoke validate_demo_prerequisites {key}.")

    demo_def = engine.fetch_demo_file(key, environment)

    ctx = {
        "log": [],
        "env": {},
        "repo_dir": None,
        "workspace": DEFAULT_WORKSPACE,
        "port": demo_def.get("port", 8080)
    }

    return engine.validate_demo_prerequisites(
        demo_def=demo_def,
        ctx=ctx
    )


# =========================================================
# INSTALL DEMO
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Install a demo.

This will:
- validate prerequisites
- clone repository
- create virtual environment
- install dependencies
"""
)
def install_demo(
    key: str,
    workspace: Optional[str] = None,
    environment: str = "local"
):
    workspace = workspace or DEFAULT_WORKSPACE
    environment = environment or "local"

    debug(f"Invoke install_demo {key}.")

    return engine.install_demo(
        key=key,
        workspace=workspace,
        environment=environment,
        dry_run=False
    )

# =========================================================
# DRY RUN INSTALL DEMO
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Dry run a demo.

This will dry run the following:
- validate prerequisites
- clone repository
- create virtual environment
- install dependencies
"""
)
def dry_run_demo(
    key: str,
    workspace: Optional[str] = None,
    environment: str = "local"
):
    workspace = workspace or DEFAULT_WORKSPACE
    environment = environment or "local"

    debug(f"Invoke dry_run_demo {key}.")

    return engine.install_demo(
        key=key,
        workspace=workspace,
        environment=environment,
        dry_run=True
    )
    
# =========================================================
# RUN DEMO
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Run an already installed demo.

This will start the application process.
"""
)
def run_demo(
    key: str,
    workspace: Optional[str] = None,
    environment: str = "local"
):
    workspace = workspace or DEFAULT_WORKSPACE
    environment = environment or "local"

    debug(f"Invoke run_demo {key}.")

    return engine.run_demo(
        key=key,
        workspace=workspace,
        environment=environment
    )


# =========================================================
# HEALTH CHECK
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Run only the health check phase of a demo.

This validates that the application is reachable and working.
"""
)
def health_check_demo(
    key: str,
    workspace: Optional[str] = None,
    environment: str = "local"
):
    workspace = workspace or DEFAULT_WORKSPACE
    environment = environment or "local"

    debug(f"Invoke health_check_demo {key} in {workspace}.")

    return engine.health_check_demo(
        key=key,
        workspace=workspace,
        environment=environment
    )

# =========================================================
# CLEANUP DEMO
# SKILL: demo_registry
# =========================================================
@mcp.tool(
    annotations={"skill": "demo_registry"},
    description="""
ROLE: ANY USER

Clean up a demo.

This will:
- execute the demo cleanup steps
- remove local resources
- remove temporary files
"""
)
def cleanup_demo(
    key: str,
    workspace: Optional[str] = None,
    environment: str = "local"
):
    workspace = workspace or DEFAULT_WORKSPACE
    environment = environment or "local"

    debug(f"Invoke cleanup_demo {key}.")

    return engine.cleanup_demo(
        key=key,
        workspace=workspace,
        environment=environment
    )
    
# =========================================================
# MAIN ENTRY
# =========================================================
if __name__ == "__main__":
    print("Debug is set:", DEBUG)

    mcp.run(
        transport=MCP_TRANSPORT,
        host=MCP_HOST,
        port=MCP_PORT
    )