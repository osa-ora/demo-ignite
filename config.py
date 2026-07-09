import os
from dotenv import load_dotenv
load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

MCP_SCHEME = os.getenv("MCP_SCHEME", "http")
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8080"))
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "http")

DEFAULT_WORKSPACE = os.getenv("DEFAULT_WORKSPACE","/tmp/demos")
DEFAULT_ENV = os.getenv("DEFAULT_ENV","Openshift")
                        
BASE_RAW_URL = os.getenv("BASE_RAW_URL","https://raw.githubusercontent.com/osa-ora/demo-ignite/main")

