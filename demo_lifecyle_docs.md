## Demo Lifecycle

Each demo is described by a YAML file composed of independent lifecycle sections. Every section contains a list of executable `steps`. The same step types may be reused across multiple lifecycle phases.

### Prerequisites

The `prerequisites` section validates that the execution environment satisfies all required dependencies before installation begins.

Typical tasks include:

- Verifying required tools are installed (`git`, `python`, `oc`, `kubectl`, `ansible`, etc.)
- Checking minimum software versions
- Validating cluster access
- Verifying required CRDs
- Ensuring required services are available

Example:

```yaml
prerequisites:
  steps:
    - type: check_available
      command: git
      args:
        - --version

    - type: check_python
      min_version: "3.11"

    - type: check_available
      command: oc
      args:
        - version
```

---

### Install

The `install` section provisions everything required by the demo.

Typical tasks include:

- Cloning repositories
- Creating virtual environments
- Installing dependencies
- Deploying applications
- Applying Kubernetes/OpenShift resources
- Downloading files
- Setting environment variables

Example:

```yaml
install:
  steps:
    - type: clone_git
      repo: https://github.com/example/demo.git
      path: demo

    - type: venv

    - type: install_requirements

    - type: shell_command
      command: python app.py
```

---

### Run

The `run` section executes the actual demonstration.

Typical tasks include:

- Executing commands
- Calling APIs
- Deploying or modifying resources
- Printing explanatory messages
- Waiting for resources
- Running validation scenarios

Example:

```yaml
run:
  steps:
    - type: echo
      message: Running demo...

    - type: oc_command
      command: apply -f policy.yaml

    - type: curl
      url: http://{{APP_ROUTE}}/health
```

---

### Health

The `health` section validates that the deployed application or service is operational.

Typical tasks include:

- HTTP health checks
- MCP connectivity checks
- Port availability checks
- Application verification

Example:

```yaml
health:
  steps:
    - type: health
      url: http://localhost:8080/health

    - type: mcp_check
      endpoint: http://localhost:8080/mcp
```

---

### Cleanup

The `cleanup` section removes resources created by the demo and restores the environment.

Typical tasks include:

- Deleting projects or namespaces
- Removing temporary files
- Killing background processes
- Deleting cloned repositories
- Waiting for resources to terminate

Example:

```yaml
cleanup:
  steps:
    - type: kill_port
      port: 8080

    - type: delete_directory
      path: "{{workspace}}/demo"
```

---

### Dry Run

The Demo MCP Server also supports a **dry run** mode during installation.

When enabled:

- All prerequisite checks are executed normally.
- Installation steps are **not executed**.
- Each install step is logged exactly as it would have been executed.
- No files, repositories, deployments, or resources are created or modified.

This mode is useful for validating a demo definition before executing it.

Example:

```text
[DRY-RUN] clone_git -> {...}
[DRY-RUN] install_requirements -> {...}
[DRY-RUN] shell_command -> {...}
```
