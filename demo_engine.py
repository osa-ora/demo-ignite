import os
import sys
import requests
import yaml
import inspect
import time, random
import core_steps_utils as core_steps
import custom_steps_utils as custom_steps
from config import BASE_RAW_URL

# =========================================================
# AUTO STEP REGISTRY
# =========================================================
def build_step_handlers():
    handlers = {}

    print("Loading supported core_steps + custom_steps:")

    for module in [core_steps, custom_steps]:
        for name, obj in inspect.getmembers(module):
            if not callable(obj):
                continue

            if not name.startswith("step_"):
                continue

            step_name = name[len("step_"):]

            if step_name in handlers:
                print(
                    f"WARNING: Step '{step_name}' from module "
                    f"'{module.__name__}' overrides an existing implementation."
                )

            print(f"adding step: {step_name}")
            handlers[step_name] = obj

    return handlers


STEP_HANDLERS = build_step_handlers()

# =========================================================
# LOGGING
# =========================================================
def add_log(log, message):
    print(f"[DEMO] {message}")
    log.append(message)


# =========================================================
# FETCH INDEX
# =========================================================
def fetch_index():
    file_name = "index.yaml"

    if os.path.exists(file_name):
        print(f"[DEMO] Loading local index: {file_name}")
        with open(file_name, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    cache_buster = f"?force={int(time.time())}_{random.randint(1000, 9999)}"
    url = f"{BASE_RAW_URL}/{file_name}{cache_buster}"

    print(f"[DEMO] Fetching index: {url}")

    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise Exception("Failed to fetch index.yaml")

    return yaml.safe_load(r.text)

# =========================================================
# FIND DEMO
# =========================================================
def find_demo(keyword: str):
    index = fetch_index()
    keyword_l = keyword.strip().lower()

    results = []

    for demo in index.get("demos", []):
        score = 0

        if keyword_l in str(demo.get("name", "")).lower():
            score += 5

        if keyword_l in str(demo.get("description", "")).lower():
            score += 3

        for k in demo.get("keywords", []):
            if keyword_l == str(k).lower():
                score += 10
            elif keyword_l in str(k).lower():
                score += 6

        if score:
            results.append({**demo, "score": score})

    return sorted(results, key=lambda x: x["score"], reverse=True)


# =========================================================
# RESOLVE DEMO
# =========================================================
def resolve_demo(key: str, environment="local"):
    index = fetch_index()

    key_str = str(key).strip().lower()
    env_str = str(environment).strip().lower()

    print(f"[DEMO] Getting demo: {key_str} for environment {env_str}")

    for demo in index.get("demos", []):

        # normalize environment keys once
        demo_envs = {str(k).strip().lower(): v for k, v in demo.get("environments", {}).items()}

        if env_str not in demo_envs:
            continue

        demo_id = str(demo.get("id", "")).strip().lower()
        demo_name = str(demo.get("name", "")).strip().lower()
        keywords = [str(k).strip().lower() for k in demo.get("keywords", [])]

        if demo_id == key_str:
            return demo

        if demo_name == key_str:
            return demo

        if key_str in keywords:
            return demo

    raise Exception(f"Demo not found: {key}")

# =========================================================
# FETCH DEMO YAML
# =========================================================
def fetch_demo_file(key: str, environment="local"):
    demo = resolve_demo(key, environment)

    env_str = str(environment).strip().lower()

    envs = demo.get("environments", {})
    envs_norm = {str(k).strip().lower(): v for k, v in envs.items()}

    if env_str not in envs_norm:
        raise Exception(f"Environment '{environment}' not available")

    demo_url = envs_norm[env_str]["file"]

    # cache-buster
    cache_buster = f"?force={int(time.time())}_{random.randint(1000, 9999)}"

    # preserve existing query params if any
    if "?" in demo_url:
        demo_url += f"&{cache_buster[1:]}"
    else:
        demo_url += cache_buster

    r = requests.get(demo_url, timeout=10)

    if r.status_code != 200:
        raise Exception(f"Failed to fetch demo YAML: {demo_url}")
    print(f"Fetched demo YAML: {demo_url}")
    return yaml.safe_load(r.text)


# =========================================================
# STEP EXECUTION CORE
# =========================================================
def execute_step(ctx, step):
    step_type = step["type"]
    handler = STEP_HANDLERS.get(step_type)

    if not handler:
        add_log(ctx["log"], f"[WARN] Unknown step: {step_type}")
        return ctx

    if ctx.get("dry_run"):
        add_log(ctx["log"], f"[DRY-RUN] {step_type} -> {step}")
        return ctx

    add_log(ctx["log"], f"[STEP] {step_type}")
    return handler(ctx, step)

    
# =========================================================
# VALIDATION PHASE
# =========================================================
def validate_demo_prerequisites(demo_def, ctx):
    add_log(ctx["log"], "[PHASE] prerequisites")

    steps = demo_def.get("prerequisites", {}).get("steps", [])
    print(f"[DEBUG] prerequisite steps count = {len(steps)}")

    for step in steps:
        execute_step(ctx, step)

    add_log(ctx["log"], "[PHASE] prerequisites OK")
    return ctx


# =========================================================
# INSTALL
# =========================================================
def install_demo(key: str, workspace: str, environment="local", dry_run=False):
    workspace = os.path.abspath(os.path.expanduser(workspace))
    demo = fetch_demo_file(key, environment)
    print(f"[DEBUG] Dry run = {dry_run}")
    
    ctx = {
        "workspace": workspace,
        "repo_dir": demo.get("repo", ""),
        "log": [],
        "env": {},
        "port": demo.get("port", 8080),
        "dry_run": False   # Ignore it during validation
    }
    validate_demo_prerequisites(demo, ctx)
    
    # use the dry run param for install
    ctx["dry_run"] = dry_run
    
    print(f"[DEBUG] workspace BEFORE makedirs = {workspace}")
    if not dry_run:
        os.makedirs(workspace, exist_ok=True)

    steps = demo.get("install", {}).get("steps", [])
    print(f"[DEBUG] install steps count = {len(steps)}")

    for step in steps:
        execute_step(ctx, step)

    return {"status": "success", "log": ctx["log"]}


# =========================================================
# RUN
# =========================================================
def run_demo(key: str, workspace: str, environment="local"):
    workspace = os.path.abspath(os.path.expanduser(workspace))
    demo = fetch_demo_file(key, environment)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": [],
        "env": {},
        "port": demo.get("port", 8080)
    }

    run_steps = demo.get("run", {}).get("steps", [])
    print(f"[DEBUG] run steps count = {len(run_steps)}")

    for step in run_steps:
        execute_step(ctx, step)

    health_steps = demo.get("health", {}).get("steps", [])
    print(f"[DEBUG] health steps count = {len(health_steps)}")

    for step in health_steps:
        execute_step(ctx, step)

    return {"status": "success", "log": ctx["log"]}


# =========================================================
# HEALTH ONLY
# =========================================================
def health_check_demo(key: str, workspace: str, environment="local"):
    demo = fetch_demo_file(key, environment)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": [],
        "env": os.environ.copy(),
        "port": demo.get("port", 8080)
    }

    steps = demo.get("health", {}).get("steps", [])
    print(f"[DEBUG] health steps count = {len(steps)}")

    for step in steps:
        execute_step(ctx, step)

    return {"status": "success", "log": ctx["log"]}

# =========================================================
# CLEANUP
# =========================================================
def cleanup_demo(key: str, workspace: str, environment="local"):
    workspace = os.path.abspath(os.path.expanduser(workspace))
    demo = fetch_demo_file(key, environment)

    ctx = {
        "workspace": workspace,
        "repo_dir": None,
        "log": [],
        "env": {},
        "port": demo.get("port", 8080)
    }

    cleanup_steps = demo.get("cleanup", {}).get("steps", [])
    print(f"[DEBUG] cleanup steps count = {len(cleanup_steps)}")

    for step in cleanup_steps:
        execute_step(ctx, step)

    return {"status": "success", "log": ctx["log"]}
