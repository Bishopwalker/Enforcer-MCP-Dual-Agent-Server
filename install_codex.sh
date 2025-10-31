#!/bin/bash

# Codex MCP Server Installation Script
# The Enforcer - Pristine Code Quality

echo "🚀 Installing Codex Dual-Agent MCP Server..."
echo "================================================"

# Check Python installation
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.8+"
    exit 1
fi

# Create directory structure
CODEX_DIR="$HOME/.claude/codex"
mkdir -p "$CODEX_DIR"

# Copy server files
echo "📁 Setting up Codex directory..."
cp codex_mcp_server.py "$CODEX_DIR/"
cp requirements.txt "$CODEX_DIR/"

# Install dependencies
echo "📦 Installing Python dependencies..."
cd "$CODEX_DIR"
pip install -r requirements.txt

# Create MCP configuration
echo "⚙️ Configuring MCP server..."
MCP_CONFIG="$HOME/.claude/mcp_servers.json"

# Check if MCP config exists
if [ -f "$MCP_CONFIG" ]; then
    echo "Found existing MCP configuration"
    # Backup existing config
    cp "$MCP_CONFIG" "$MCP_CONFIG.backup"
else
    echo "Creating new MCP configuration"
    echo '{"mcpServers": {}}' > "$MCP_CONFIG"
fi

# Add Codex server to config using Python (more reliable for JSON)
python3 << EOF
import json
import os

config_path = os.path.expanduser("~/.claude/mcp_servers.json")
with open(config_path, 'r') as f:
    config = json.load(f)

# Add Codex server
config['mcpServers']['codex-enforcer'] = {
    "command": "python",
    "args": [os.path.expanduser("~/.claude/codex/codex_mcp_server.py")],
    "env": {
        "PYTHONUNBUFFERED": "1"
    },
    "description": "Codex Enforcer - Dual-agent code quality enforcement"
}

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("✅ Codex MCP server added to configuration")
EOF

echo ""
echo "================================================"
echo "✅ Codex MCP Server Installation Complete!"
echo "================================================"
echo ""
echo "📋 Quick Start Guide:"
echo "--------------------"
echo "1. Restart Claude desktop app"
echo "2. In your project, use these commands:"
echo ""
echo "   Take snapshot:"
echo "   codex_snapshot(paths=['file1.py', 'file2.js'])"
echo ""
echo "   Enforce quality:"
echo "   codex_enforce(paths=['file1.py', 'file2.js'])"
echo ""
echo "   Validate only:"
echo "   codex_validate(paths=['file1.py', 'file2.js'])"
echo ""
echo "🏆 Russian Olympic Judge Scoring:"
echo "   9.0+ = PRISTINE ✅"
echo "   <9.0 = NEEDS WORK ❌"
echo ""
echo "💪 Now go write some PRISTINE code, Cash Money!"
