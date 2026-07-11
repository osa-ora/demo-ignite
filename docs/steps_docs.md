# Demo Steps Reference

The Demo MCP Server executes YAML-based workflows by mapping each step type to a Python implementation. The following step types are currently supported.

| Step | Purpose |
|------|---------|
| `check_available` | Verifies that any executable command is available (for example `git`, `pip`, `uv`, `oc`, `kubectl`, `ansible`, etc.). |
| `check_python` | Verifies that Python is installed and optionally checks a minimum version. |
| `check_java` | Verifies that Java is installed and optionally checks a minimum major version. |
| `clone_git` | Clones a Git repository into the workspace if it does not already exist. |
| `venv` | Creates a Python virtual environment inside the repository. |
| `install_requirements` | Installs Python dependencies from `requirements.txt`. |
| `env` | Defines environment variables that will be used by subsequent steps. |
| `run_process` | Starts an application either in the background or in a visible macOS Terminal window. |
| `health` | Performs an HTTP health check with configurable retries. |
| `curl` | Executes an HTTP GET request, prints the response body, and optionally ignores failures. |
| `mcp_check` | Connects to an MCP server and verifies that tools are available. |
| `port_check` | Waits until a TCP port becomes reachable. |
| `no_running_check` | Waits until a TCP port is no longer accepting connections. |
| `shell_command` | Executes any shell command. |
| `oc_command` | Executes an OpenShift CLI (`oc`) command. |
| `kubectl_command` | Executes a Kubernetes CLI (`kubectl`) command. |
| `check_oc_crd` | Verifies that a required OpenShift/Kubernetes Custom Resource Definition exists. |
| `delete_directory` | Deletes a directory recursively. |
| `kill_port` | Terminates any process currently listening on a specified TCP port. |
| `wait` | Pauses execution for a configurable number of seconds. |
| `echo` | Prints a message to the console and execution log. |
| `open_url` | Opens a URL in the system's default web browser. |
| `download_file` | Downloads a remote file to a local destination. |
| `ansible_command` | Executes an Ansible CLI command. |
| `ansible_playbook` | Executes an Ansible playbook with optional extra variables. |

## Common YAML Pattern

Each step is represented as a YAML object with a `type` field and any parameters required by that step.

```yaml
steps:
  - type: echo
    message: Starting demo...

  - type: wait
    seconds: 5

  - type: shell_command
    command: ls -la

  - type: curl
    url: http://localhost:8080/health

  - type: oc_command
    command: get pods -A
```

## Common Features

Several step types share common capabilities:

### Variable Resolution

String values may reference variables using template syntax.

```yaml
command: curl http://{{HOST}}:{{PORT}}/health
```

Variables can originate from:

- Environment variables created using the `env` step
- Values registered by previous steps
- Built-in execution context variables (for example `workspace`)

### Register Output

Some command-based steps support storing their output for later use.

```yaml
- type: oc_command
  command: get route myapp -o jsonpath='{.spec.host}'
  register: APP_ROUTE

- type: curl
  url: http://{{APP_ROUTE}}/health
```

Supported by:

- `shell_command`
- `oc_command`
- `kubectl_command`

### Ignore Errors

Most command and network operations support continuing even if they fail.

```yaml
- type: curl
  url: http://localhost:8080/test
  ignore_error: true
```

Supported by:

- `curl`
- `shell_command`
- `oc_command`
- `kubectl_command`
- `ansible_command`
- `ansible_playbook`

### Retries

Network-related checks support configurable retry behavior.

```yaml
- type: health
  url: http://localhost:8080/health
  retries: 20
  delay_seconds: 3
```

Supported by:

- `health`
- `curl`
- `mcp_check`
- `port_check`
- `no_running_check`
