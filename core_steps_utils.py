import shutil
import os
import sys
import shlex
import subprocess
import socket
import requests
import time, re
import asyncio
import webbrowser
from fastmcp import Client

# =========================================================
# TEMPLATE ENGINE (SINGLE SOURCE OF TRUTH)
# =========================================================
def resolve_value(value, ctx):
    if not isinstance(value, str):
        return value

    unresolved = []

    for k, v in ctx.items():
        if isinstance(v, (str, int, float)):
            value = value.replace(f"{{{{{k}}}}}", str(v))

    # detect leftover templates
    if "{{" in value and "}}" in value:
        unresolved.append(value)

    if unresolved:
        raise ValueError(f"Unresolved template variables in: {value}")

    return value

# =========================================================
# UNIFIED CHECK (Check the availability of any command using its arguments)
# e.g. git --version 
# =========================================================
def step_check_available(ctx, step):
    command = resolve_value(step["command"], ctx)
    args = step.get("args", [])
    print(f"Check Available CMD: {command} using param: {args}")
    if args is None:
        args = []

    args = [resolve_value(a, ctx) for a in args]

    try:
        result = subprocess.run(
            [command] + args,
            check=True,
            capture_output=True,
            text=True
        )

        output = (result.stdout or result.stderr).strip()
        first_line = output.splitlines()[0] if output else ""

        ctx["log"].append(f"{command} OK ({first_line})")

    except Exception:
        raise RuntimeError(f"{command} is not available or failed")

    return ctx
    
# =========================================================
# GENERIC CHECK
# =========================================================
def run_check(cmd, name, ok_msg, ctx):
    try:
        subprocess.run(cmd, check=True)
        ctx["log"].append(ok_msg)
    except Exception:
        raise RuntimeError(f"{name} is not available or failed")
    
# =========================================================
# PYTHON CHECK
# =========================================================
def step_check_python(ctx, step):
    min_version = step.get("min_version")

    version = sys.version_info
    current = f"{version.major}.{version.minor}.{version.micro}"

    if min_version:
        required = tuple(map(int, min_version.split(".")))
        if version < required:
            raise RuntimeError(
                f"Python version too low. Required >= {min_version}, got {current}"
            )

    subprocess.run(["python3", "--version"], check=True)
    ctx["log"].append(f"Python OK ({current})")
    return ctx

# =========================================================
# CLONE GIT
# =========================================================
def step_clone_git(ctx, step):
    repo = resolve_value(step["repo"], ctx)
    repo_dir = resolve_value(step["path"], ctx)

    workspace = ctx.get("workspace")

    if not os.path.isabs(repo_dir):
        repo_dir = os.path.join(workspace, repo_dir)

    repo_dir = os.path.abspath(repo_dir)

    ctx["repo_dir"] = repo_dir

    if os.path.exists(repo_dir):
        ctx["log"].append(f"Repo exists: {repo_dir}")
        return ctx

    subprocess.run(
        ["git", "clone", repo, repo_dir],
        check=True
    )

    ctx["log"].append(f"Cloned {repo} → {repo_dir}")
    return ctx

# =========================================================
# VENV
# =========================================================
def step_venv(ctx, step):
    venv_path = os.path.join(ctx["repo_dir"], ".venv")
    subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
    ctx["log"].append("venv created")
    return ctx

# =========================================================
# INSTALL Python Requirements
# =========================================================
def step_install_requirements(ctx, step):
    pip_path = os.path.join(ctx["repo_dir"], ".venv", "bin", "pip")

    subprocess.run(
        [pip_path, "install", "-r", os.path.join(ctx["repo_dir"], "requirements.txt")],
        check=True
    )

    ctx["log"].append("dependencies installed")
    return ctx

# =========================================================
# ENV
# =========================================================
def step_env(ctx, step):
    variables = step.get("variables", {})

    for k, v in variables.items():
        v = resolve_value(v, ctx)
        ctx["env"][k] = str(v)

    ctx["log"].append(f"env set: {list(variables.keys())}")
    return ctx

# =========================================================
# TERMINAL MODE (macOS)
# =========================================================
def run_terminal_mac(repo_dir, command, env=None):
    env_prefix = ""

    if env:
        env_prefix = " ".join(
            f'{k}={shlex.quote(str(v))}'
            for k, v in env.items()
        )

    full_cmd = f'cd "{repo_dir}" && {env_prefix} {command}'

    # IMPORTANT: escape for AppleScript, NOT shell
    applescript_cmd = full_cmd.replace('"', '\\"')

    script = f'''
tell application "Terminal"
    activate
    do script "{applescript_cmd}"
end tell
'''.strip()

    subprocess.run(["osascript", "-e", script], check=True)

# =========================================================
# RUN
# =========================================================
def step_run_process(ctx, step):
    repo_dir = resolve_value(step["path"], ctx)
    command = resolve_value(step["command"], ctx)
    mode = step.get("mode", "background")

    ctx["repo_dir"] = repo_dir

    ctx["log"].append(f"Dir: {repo_dir}")
    ctx["log"].append(f"Cmd: {command}")
    ctx["log"].append(f"Mode: {mode}")

    # TERMINAL MODE (VISIBLE)
    if mode == "terminal" and sys.platform == "darwin":
        ctx["log"].append("Launching macOS Terminal")
        run_terminal_mac(repo_dir, command, ctx["env"])
        return ctx

    # BACKGROUND MODE
    if mode == "background":
        log_file = os.path.join(repo_dir, "app.log")

        with open(log_file, "w") as f:
            proc = subprocess.Popen(
                ["bash", "-c", command],
                cwd=repo_dir,
                stdout=f,
                stderr=subprocess.STDOUT,
                env=ctx["env"],
                start_new_session=True
            )

        ctx["log"].append(f"PID={proc.pid}")
        ctx["log"].append(f"Logs={log_file}")

    return ctx

# =========================================================
# HEALTH
# =========================================================
def step_health(ctx, step):
    url = resolve_value(step["url"], ctx)
    print(f"Heath check at: {url}")
    retries = step.get("retries", 5)
    delay = step.get("delay_seconds", 2)

    for _ in range(retries):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                ctx["log"].append("health OK")
                return ctx
        except Exception:
            pass
        time.sleep(delay)

    raise Exception("Health check failed")

# =========================================================
# MCP CHECK
# =========================================================

def step_mcp_check(ctx, step):
    endpoint = resolve_value(step.get("endpoint"), ctx)

    if not endpoint:
        raise Exception("Missing MCP endpoint")

    print(f"Check mcp server at: {endpoint}")

    retries = step.get("retries", 5)
    delay = step.get("delay_seconds", 2)

    last_error = None

    async def _mcp_call():
        async with Client(endpoint) as client:
            return await client.list_tools()

    for _ in range(retries):
        try:
            tools = asyncio.run(_mcp_call())  # ONLY place asyncio exists

            if isinstance(tools, dict):
                tools = tools.get("tools", tools)

            ctx["mcp_tools"] = tools

            ctx["log"].append(f"mcp OK - tools loaded ({len(tools)})")

            # optional debug print
            print(f"[DEMO] MCP tools loaded: {tools}")

            return ctx

        except Exception as e:
            last_error = str(e)
            time.sleep(delay)

    raise Exception(f"MCP check failed: {last_error}")

# =========================================================
# PORT RUNNING CHECK
# =========================================================
def step_port_check(ctx, step):
    host = resolve_value(step.get("host", "localhost"), ctx)
    port = int(resolve_value(step["port"], ctx))
    retries = step.get("retries", 5)
    delay = step.get("delay_seconds", 2)

    for _ in range(retries):
        try:
            with socket.create_connection((host, port), timeout=2):
                ctx["log"].append("port open")
                return ctx
        except Exception:
            time.sleep(delay)

    raise Exception("port check failed")

# =========================================================
# PORT NOT RUNNING CHECK
# =========================================================
def step_no_running_check(ctx, step):
    host = resolve_value(step.get("host", "localhost"), ctx)
    port = int(resolve_value(step["port"], ctx))
    retries = int(step.get("retries", 5))
    delay = int(step.get("delay_seconds", 2))

    import socket
    import time

    for attempt in range(retries):
        try:
            # if we can connect → service is still running
            with socket.create_connection((host, port), timeout=1):
                ctx["log"].append(
                    f"attempt {attempt+1}: service still running on {host}:{port}"
                )
                print(f"attempt {attempt+1}: service still running on {host}:{port}")

        except OSError:
            # cannot connect → service is down → SUCCESS
            ctx["log"].append(
                f"service confirmed stopped on {host}:{port}"
            )
            return ctx

        time.sleep(delay)

    # if loop finishes → still running
    raise RuntimeError(f"Service did not stop after {retries} retries on {host}:{port}")
    
# =========================================================
# SHELL COMMAND
# =========================================================
def step_shell_command(ctx, step):
    command = resolve_value(step["command"], ctx)

    raw_cwd = step.get("path")
    if raw_cwd is None:
        raw_cwd = "{{workspace}}"

    cwd = resolve_value(raw_cwd, ctx)

    ctx["log"].append(f"SHELL CMD: {command} (cwd={cwd})")
    print(f"Shell CMD: {command} on {cwd}")

    try:
        output = subprocess.check_output(
            command,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            cwd=cwd
        ).strip()

    except subprocess.CalledProcessError as e:
        if step.get("ignore_error"):
            ctx["log"].append(f"[IGNORED ERROR] {e.output.strip()}")
            return ctx

        raise Exception(f"SHELL command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output

    ctx["log"].append(output)
    print(f"Output: {output}")

    return ctx

# =========================================================
# OC COMMAND
# =========================================================
def step_oc_command(ctx, step):
    command = resolve_value(step["command"], ctx)

    full_cmd = f"oc {command}"

    ctx["log"].append(f"OC CMD: {full_cmd}")
    print(f"OC CMD: {full_cmd}")

    try:
        output = subprocess.check_output(
            full_cmd,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT
        ).strip()

    except subprocess.CalledProcessError as e:
        if step.get("ignore_error"):
            ctx["log"].append(f"[IGNORED ERROR] {e.output.strip()}")
            return ctx

        raise Exception(f"OC command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output

    ctx["log"].append(output)

    return ctx

# =========================================================
# OC CRD Check
# =========================================================
def step_check_oc_crd(ctx, step):
    import subprocess

    kind = step.get("kind")
    api_group = step.get("api_group")
    print(f"Check for CRD: Kind: {kind} in API_Group {api_group}...")
    
    if not kind:
        raise ValueError("check_oc_crd requires 'kind'")

    if not api_group:
        raise ValueError("check_oc_crd requires 'api_group' (e.g. kafka.strimzi.io)")

    # Clean the kind name
    kind_lower = kind.lower()
    
    # Simple pluralization fallback helper
    if not kind_lower.endswith('s'):
        if kind_lower.endswith('y'):
            plural_kind = kind_lower[:-1] + "ies"  # e.g., Gateway -> gateways
        else:
            plural_kind = kind_lower + "s"         # e.g., Kafka -> kafkas
    else:
        plural_kind = kind_lower

    # CRD name format in Kubernetes is ALWAYS plural.group
    crd_name = f"{plural_kind}.{api_group}"

    try:
        result = subprocess.check_output(
            ["oc", "get", "crd", crd_name],
            text=True,
            stderr=subprocess.STDOUT
        ).strip()

        ctx["log"].append(f"[CRD OK] {crd_name} exists")

        ctx.setdefault("crds", {})
        ctx["crds"][kind] = crd_name

        return ctx

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"CRD check failed: {crd_name}\n{e.output}"
        ) from e
        
# =========================================================
# DELETE DIRECTORY TREE
# =========================================================
def step_delete_directory(ctx, step):
    path = resolve_value(step["path"], ctx)

    if not path:
        raise ValueError("delete_directory requires 'path'")

    if not os.path.exists(path):
        ctx["log"].append(f"delete_directory skipped (not found): {path}")
        return ctx

    shutil.rmtree(path)

    ctx["log"].append(f"deleted directory: {path}")
    return ctx
    
# =========================================================
# KILL RUNNING APP ON THAT PORT
# =========================================================    
def step_kill_port(ctx, step):
    try:
        port = resolve_value(step["port"], ctx)

        result = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            text=True
        ).strip()

        if result:
            for pid in result.splitlines():
                subprocess.run(["kill", "-9", pid], check=False)

        ctx["log"].append(f"cleanup done on port {port}")

    except Exception:
        pass  # fully ignore

    return ctx

# =========================================================
# WAIT STEP
# =========================================================
def step_wait(ctx, step):
    seconds = int(step.get("seconds", 10))
    time.sleep(seconds)
    ctx["log"].append(f"waited {seconds}s")
    return ctx
    
# =========================================================
# ECHO STEP
# =========================================================
def step_echo(ctx, step):
    message = step.get("message", "echo")
    print(message)

    if ctx and "log" in ctx:
        ctx["log"].append(message)

    return ctx

# =========================================================
# OPEN URL STEP
# =========================================================
def step_open_url(ctx, step):
    url = step.get("url")

    if not url:
        raise ValueError("open_url requires 'url'")

    resolved_url = resolve_value(url, ctx)

    webbrowser.open(resolved_url)

    ctx["log"].append(f"opened browser: {resolved_url}")
    return ctx

# =========================================================
# JAVA CHECK
# =========================================================
def step_check_java(ctx, step):
    min_version = step.get("min_version")

    result = subprocess.run(
        "java -version 2>&1 | head -n 1",
        shell=True,
        capture_output=True,
        text=True,
        check=True
    )

    line = result.stdout.strip()

    # extract "21.0.8"
    match = re.search(r'"(\d+\.\d+\.\d+)"', line)
    if not match:
        raise RuntimeError(f"Cannot parse Java version from: {line}")

    version = match.group(1)
    major = int(version.split(".")[0])

    if min_version:
        required_major = int(min_version)

        if major < required_major:
            raise RuntimeError(
                f"Java version too low. Required >= {min_version}, got {version}"
            )

    ctx["log"].append(f"Java OK ({version})")
    return ctx
    
# =========================================================
# DOWNLOAD FILE
# =========================================================
def step_download_file(ctx, step):
    url = resolve_value(step["url"], ctx)
    destination = resolve_value(step["path"], ctx)

    os.makedirs(os.path.dirname(destination), exist_ok=True)

    print(f"[DEMO] Downloading {url}")

    r = requests.get(url, timeout=60)
    r.raise_for_status()

    with open(destination, "wb") as f:
        f.write(r.content)

    ctx["log"].append(f"downloaded: {destination}")
    return ctx

# =========================================================
# KUBECTL COMMAND
# =========================================================
def step_kubectl_command(ctx, step):
    command = resolve_value(step["command"], ctx)

    full_cmd = f"kubectl {command}"

    ctx["log"].append(f"KUBECTL CMD: {full_cmd}")
    print(full_cmd)

    try:
        output = subprocess.check_output(
            full_cmd,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT
        ).strip()

    except subprocess.CalledProcessError as e:
        if step.get("ignore_error"):
            ctx["log"].append(f"[IGNORED ERROR] {e.output.strip()}")
            return ctx

        raise Exception(f"kubectl command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output

    ctx["log"].append(output)
    return ctx
    
# =========================================================
# ANSIBLE COMMAND
# =========================================================
def step_ansible_command(ctx, step):
    command = resolve_value(step["command"], ctx)

    full_cmd = f"ansible {command}"

    ctx["log"].append(f"ANSIBLE CMD: {full_cmd}")
    print(full_cmd)

    try:
        output = subprocess.check_output(
            full_cmd,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT
        ).strip()

    except subprocess.CalledProcessError as e:
        if step.get("ignore_error"):
            ctx["log"].append(f"[IGNORED ERROR] {e.output.strip()}")
            return ctx

        raise Exception(f"ansible command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output

    ctx["log"].append(output)
    return ctx

# =========================================================
# ANSIBLE PLAYBOOK
# =========================================================
def step_ansible_playbook(ctx, step):
    playbook = resolve_value(step["playbook"], ctx)

    extra = step.get("extra_vars", "")
    extra_vars = f"--extra-vars \"{extra}\"" if extra else ""

    cmd = f"ansible-playbook {playbook} {extra_vars}"

    ctx["log"].append(f"ANSIBLE PLAYBOOK: {cmd}")
    print(cmd)

    try:
        output = subprocess.check_output(
            cmd,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT
        ).strip()

    except subprocess.CalledProcessError as e:
        if step.get("ignore_error"):
            ctx["log"].append(f"[IGNORED ERROR] {e.output.strip()}")
            return ctx

        raise Exception(f"ansible playbook failed: {e.output}") from e

    ctx["log"].append(output)
    return ctx