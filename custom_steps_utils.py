from datetime import datetime, timezone

# =========================================================
# ECHO STEP (DEBUG)
# =========================================================
def step_echo(ctx, step):

    message = step.get("message", "echo")
    timestamp = datetime.now(timezone.utc).isoformat()

    output = f"[ECHO] {timestamp} -> {message}"

    print(output)
    if ctx and "log" in ctx:
        ctx["log"].append(output)

    return ctx

# =========================================================
# AWS COMMAND
# =========================================================
def step_aws_command(ctx, step):
    command = resolve_value(step["command"], ctx)

    full_cmd = f"aws {command}"

    ctx["log"].append(f"AWS CMD: {full_cmd}")
    print(f"AWS CMD: {full_cmd}")

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

        raise Exception(f"AWS command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output

    ctx["log"].append(output)
    return ctx

# =========================================================
# AZURE COMMAND
# =========================================================
def step_az_command(ctx, step):
    command = resolve_value(step["command"], ctx)

    full_cmd = f"az {command}"

    ctx["log"].append(f"AZ CMD: {full_cmd}")
    print(f"AZ CMD: {full_cmd}")

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

        raise Exception(f"AZ command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output

    ctx["log"].append(output)
    return ctx

# =========================================================
# GCLOUD COMMAND
# =========================================================
def step_gcloud_command(ctx, step):
    command = resolve_value(step["command"], ctx)

    full_cmd = f"gcloud {command}"

    ctx["log"].append(f"GCLOUD CMD: {full_cmd}")
    print(f"GCLOUD CMD: {full_cmd}")

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

        raise Exception(f"GCLOUD command failed: {e.output}") from e

    register_key = step.get("register")
    if register_key:
        ctx[register_key] = output

    ctx["log"].append(output)
    return ctx
