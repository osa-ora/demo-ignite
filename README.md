# DemoIgnite

## Introduction

DemoIgnite is an open-source AI-powered demo automation platform that automates the provisioning and lifecycle management of demo environments.

It does not replace existing tools. Instead, it adds a lightweight AI orchestration layer that allows existing automation assets (scripts, CLI tools, GitOps manifests, and SDKs) to be executed using natural language.
## Benefits

The advantages of using this project can be summarized as follows:

1. **Build a centralized demo catalog**, where all demos are described using a simple YAML format and can be easily discovered, shared, and reused.
2. **Provision demos using natural language** through any AI chat interface.
3. **Reuse your existing automation assets**, including scripts, `oc` commands, GitOps YAML files, cloud provider SDKs, Ansible playbooks, and other deployment tools.
4. **Make technical demos accessible to non-technical users**, allowing anyone to provision and run demos without requiring deep platform expertise.
5. **Share standardized demos with customers**, providing a simple and repeatable way to deploy demonstration environments.
6. **Quickly customize demos using AI** by creating or modifying simple YAML demo definitions instead of writing new automation from scratch.
7. **Reduce the time and effort required to prepare customer-specific demos**, enabling faster and more consistent demo delivery.
8. **Standardize demo provisioning across teams**, ensuring demos are reproducible, maintainable, and easy to share.

By combining AI with a lightweight YAML-based demo definition, the project transforms existing deployment knowledge into a reusable demo catalog that can be executed consistently through natural language by anyone.

## System Overview

The simplest setup uses:
- A local Ollama server (or any MaaS provider)
- A chat application (e.g., ChatBox or equivalent)
- A running Demo MCP Server (this project)

By default, the system loads the demo catalog from a local `index.yaml` file. If not available, it can fetch it from a remote repository. The source location is configurable via environment variables or code configuration.

## Demo Catalog Structure

Each demo entry can define multiple environments (local, Podman, OpenShift). Each environment contains its own execution instructions.

> 💡 You can use any environment name/tag. It is simply an identifier for execution instructions.

```
  - id: 8
    name: NodeJS Deployment Demo
    description: This demo deploy nodejs application either to Podman using source code or Mac Image or OpenShift S2I
    keywords:
      - nodejs
    environments:
      openshift:
        file: https://raw.githubusercontent.com/osa-ora/demo-mcp-server/refs/heads/main/demos/nodejs-demo_ocp.yaml
      podman:
        file: https://raw.githubusercontent.com/osa-ora/demo-mcp-server/refs/heads/main/demos/nodejs-demo_podman.yaml
      local:
        file: https://raw.githubusercontent.com/osa-ora/demo-mcp-server/refs/heads/main/demos/nodejs-demo_local.yaml
```


The demos list reference a dedicated demo yaml file structured like the following example: 
```
name: Weather MCP Server Demo
repo: https://github.com/osa-ora/weather-mcp-server
port: 8060
prerequisites:
  steps:
    - type: check_python
      min_version: "3.10"
    - type: check_available
      command: pip
      args: ["--version"]
    - type: check_available
      command: git
      args: ["--version"]
install:
  steps:
    - type: clone_git
      .... # removed
run:
  steps:
    - type: env
      .... # removed
health:
  steps:
    - type: mcp_check
      endpoint: "http://localhost:{{port}}/mcp"
      retries: 10
      delay_seconds: 2
cleanup:
  steps:
    - type: kill_port
      port: "{{port}}"
      
    - type: delete_directory
      path: "{{workspace}}/weather-mcp-server-demo"
```

## Architecture: 

The overall architecture looks like: 

<img width="2528" height="1684" alt="Gemini_Generated_Image_2tq45f2tq45f2tq4" src="https://github.com/user-attachments/assets/91dbdd62-8760-418f-aa90-ad0939f3320e" />

## Demo MCP Server

The core component of the AI Demo automation is the demo MCP server.

It is dedicated to build any custom demos, either locally or on OpenShift cluster through configurable yaml file.

The MCP Server expose the following demo lifecyle managment operations:
```
- list_demos
- find_demo
- get_demo_details
- get_demo_prerequisites
- validate_demo_prerequisites
- install_demo
- dry_run_demo: to dry run the installation
- run_demo
- health_check_demo
- cleanup_demo
```

It utilzies the demo_engine.py as the engine for all these use cases behind the scene.
You can easily add your custom steps or override core_steps_utils.py by adding it to the custom_steps_utils.py file.


<img width="2760" height="1504" alt="components-diagram" src="https://github.com/user-attachments/assets/1871b8e7-fb47-4483-bc3c-7494388c0e3c" />


The list of Demos are stored in the index.yaml file which in turn reference the demo detailed file inside the /demos folder or any other location.

---

## 🛠️ Configuration (.env)
Create a `.env` file in the root folder if you need to override the defaults, otherwise you can keep the defaults or you can export any of these as env variables:

```
DEBUG=false
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_PORT=8085
DEFAULT_WORKSPACE = "/tmp/demos"
BASE_RAW_URL = "https://raw.githubusercontent.com/osa-ora/demo-mcp-server/main"

```

---

## 🚀 Quick Start

```bash
git clone https://github.com/osa-ora/demo-mcp-server.git
cd demo-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py

```

Then Open any chat client like ChatBox:

Configure the Ollama with a local model such as 'llama3.1:latest' (or any other MAAS API Key and Endpoint).

<img width="837" height="820" alt="Screenshot 2026-07-02 at 10 49 16 PM" src="https://github.com/user-attachments/assets/c65bbf22-46a4-4988-b8e9-ee7d177cc291" />

Configure the Demo MCP server as the following screen shot:

<img width="840" height="835" alt="Screenshot 2026-07-02 at 10 52 25 PM" src="https://github.com/user-attachments/assets/f53ac812-840d-4d59-82f3-b68a575fcf3c" />


## 👉 Chat with the server:

You can try the following examples:

```text
List all demos
List prerequisites for MCP Server Client Orchestrator on local environment
Details of demo: HR 
Details of demo: HR environment: openshift
What prerequisites for demo 3
Install Weather Demo on local at /tmp/demos/
Run Weather demo on /tmp/demos/
Cleanup Weather demo on /tmp/demos/
Can you list openshift demos?
```

<img width="839" height="820" alt="Screenshot 2026-07-02 at 10 51 11 PM" src="https://github.com/user-attachments/assets/27fb1895-63dc-4cde-ad89-edc993cd4702" />

---

## 💡 Notes on Tools

* **Flexible Lookups:** Every tool takes a `key` parameter. The LLM can automatically look up your demos using either the string **Name** (e.g., `Local HR MCP Server Demo`) or the numeric **ID** (e.g., `3`) or even by **keywords** (e.g.,`HR`, `Weather`,`helm`,`client`).

* **Workspaces:** If you don't provide a custom workspace path to the install, run, or health check tools, they will automatically default to `/tmp/mcp-workspace`.
 
* **Environments:** If you don't provide the target environment, it will automatically default to `local`.


---

# 🧩 Supported Steps (Demo Engine)

The engine dynamically loads steps from `core_steps_utils` and `custom_steps_utils`.

Custom steps can override core implementations (last-loaded wins) or you can add your own customer steps.

# 🧩 Supported Core + Custom Steps

## 🧪 System / Environment Checks
- check_available
- check_python
- check_java

## ⚙️ Core Execution Steps
- clone_git
- install_requirements # for python
- venv
- run_process
- shell_command
- env
- wait
- health
- open_url

## ☸️ Kubernetes / OpenShift
- oc_command
- kubectl_command
- check_oc_crd

## 🔌 MCP / Runtime Control
- mcp_check
- port_check
- no_running_check

## 🧰 Utility Operations
- download_file
- delete_directory
- kill_port
- echo 

## ⚙️ Tools
- ansible_command
- ansible_playbook
- aws_command
- az_command
- gcloud_command

## 🧪 Notes
- Steps are auto-registered at runtime from both core and custom modules
- Custom steps can override core steps (watch for duplicates like `echo`)
- Prefer structured steps over raw shell commands when possible.

