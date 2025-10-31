# 🚀 CODEX MCP SERVER - THE ENFORCER
**Dual-Agent Quality System for PRISTINE Code**

---

## 🎯 WHAT THIS BEAST DOES

Yo Cash Money, this MCP server implements the CODEX dual-agent system that works inline with Claude to provide:

1. **The Builder** (Claude) - Implements features
2. **The Enforcer** (Codex) - Ensures PRISTINE quality (Russian Olympic Judge standard)
3. **Dual Answer Mode** - Gives you multiple perspectives on solutions

### Key Features:
- ✅ **Snapshot System** - Takes pristine snapshots before changes
- 🎯 **Quality Enforcement** - Russian Olympic Judge scoring (0-10)
- 🔥 **Auto-Cleanup** - Removes debug logs, dead code, unused imports
- 💡 **Dual Answers** - Quick & dirty vs Enterprise vs Balanced solutions
- 📊 **Quality Reports** - Detailed analysis with violations

---

## 📦 INSTALLATION (DO THIS SHIT FIRST)

### Step 1: Create Codex Directory
```powershell
# Create the MCP server directory
mkdir C:\Users\bisho\.claude\codex_mcp
```

### Step 2: Copy Files
```powershell
# Copy these files to the directory
# 1. codex_mcp_server.py
# 2. requirements.txt
```

### Step 3: Install Dependencies
```powershell
cd C:\Users\bisho\.claude\codex_mcp
pip install -r requirements.txt
```

### Step 4: Configure Claude Desktop

**Add to your Claude Desktop config** (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "codex": {
      "command": "python",
      "args": ["C:\\Users\\bisho\\.claude\\codex_mcp\\codex_mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:\\Users\\bisho\\.claude\\codex_mcp",
        "CODEX_PROJECT_ROOT": "C:\\Users\\bisho\\IdeaProjects\\ebl"
      }
    }
  }
}
```

### Step 5: Restart Claude Desktop
- Close Claude Desktop completely
- Restart it
- Check that Codex appears in your available tools

---

## 🔥 HOW TO USE THIS SHIT

### WORKFLOW 1: Quality Enforcement (The Full Monty)

**Phase 1: Take Snapshot**
```
Claude: "I need to implement feature X in these files"
You: "Use codex_snapshot first"

mcp__codex__codex_snapshot({
  "files": [
    "src/components/Timer.tsx",
    "src/hooks/useAudio.ts"
  ],
  "description": "Adding session context display"
})
```

**Phase 2: Implement Changes**
```
Claude implements the feature...
Tests it...
Validates it works...
```

**Phase 3: Enforce Quality**
```
mcp__codex__codex_enforce({
  "snapshot_id": "20241027_214532",
  "auto_fix": false
})

Returns:
✨ PRISTINE - Score: 9.5/10.0
OR
⚠️ NEEDS WORK - Score: 7.2/10.0
  - Debug statements found: 3
  - Missing docstrings: 2
  - File too long: 1
```

### WORKFLOW 2: Quick Analysis (No Snapshot)

```
mcp__codex__codex_analyze({
  "files": ["src/components/ComplexComponent.tsx"]
})

Returns analysis with violations and score
```

### WORKFLOW 3: Dual Answer Mode (Get Multiple Perspectives)

```
mcp__codex__codex_dual_answer({
  "question": "How should I implement WebSocket reconnection logic?",
  "context": "For a real-time audio streaming application"
})

Returns:
📦 Quick & Dirty: Simple retry with exponential backoff
🏢 Enterprise: Full reconnection manager with state machine
⚖️ Balanced: Smart reconnection with essential features
```

### WORKFLOW 4: Clean Code

```
mcp__codex__codex_clean({
  "file": "src/utils/debug.ts",
  "save": true  // false to preview
})

Removes:
- All console.log statements
- Commented dead code
- Unused imports
```

---

## 🎯 RUSSIAN OLYMPIC JUDGE SCORING

### Score Breakdown:
- **10.0** = PERFECT, zero flaws, angels sing
- **9.5-9.9** = PRISTINE, minor style issues only
- **9.0-9.4** = Very good, small issues
- **8.0-8.9** = Good, needs some cleanup
- **7.0-7.9** = Acceptable, but not great
- **< 7.0** = This shit needs WORK

### Score Components:
- **Cleanliness (30%)** - No debug logs, no dead code
- **Documentation (20%)** - Docstrings, comments, JSDoc
- **Testing (20%)** - Tests exist and pass
- **Architecture (20%)** - Files under 500 lines, good structure
- **Performance (10%)** - No obvious bottlenecks

---

## 💡 INLINE USAGE WITH CLAUDE

### Example 1: Feature Implementation

```
You: "Add a new timer component with WebSocket support"

Claude: "Let me snapshot first..."
[Uses codex_snapshot]

Claude: "Implementing..."
[Writes code]

Claude: "Checking quality..."
[Uses codex_enforce]

Claude: "Score: 9.2/10 - PRISTINE! Minor doc improvement suggested"
```

### Example 2: Code Review

```
You: "Is my authentication service clean?"

Claude: [Uses codex_analyze]
"Found 3 debug statements and 2 unused imports. 
Current score: 7.8/10
Want me to clean it?"
```

### Example 3: Best Practice Question

```
You: "What's the best way to handle file uploads?"

Claude: [Uses codex_dual_answer]
"Here are three approaches:
1. Quick: Direct multer to disk (6.5/10)
2. Enterprise: Full S3 with queuing (9.5/10)  
3. Balanced: Stream to S3 with basic validation (8.5/10)"
```

---

## 🔧 ADVANCED CONFIGURATION

### Custom Project Root
Set in environment:
```json
"env": {
  "CODEX_PROJECT_ROOT": "C:\\Your\\Project\\Path"
}
```

### Custom Standards
Modify scoring in `codex_mcp_server.py`:
- Line limits (default: 500)
- Required documentation level
- Allowed debug statements (with #KEEP comment)

---

## 🚨 TROUBLESHOOTING

### Server Not Starting
```powershell
# Test directly
python C:\Users\bisho\.claude\codex_mcp\codex_mcp_server.py

# Check for errors
```

### Tool Not Available in Claude
1. Check config file location
2. Restart Claude Desktop
3. Look for "codex" in available tools

### Snapshot Not Found
- Check `.codex/snapshots/` directory in project
- Verify snapshot_id is correct

---

## 📊 CODEX COMMANDS QUICK REFERENCE

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `codex_snapshot` | Capture pristine state | Before making changes |
| `codex_enforce` | Check quality vs snapshot | After implementation |
| `codex_analyze` | Quick quality check | Anytime, no snapshot needed |
| `codex_dual_answer` | Get multiple solutions | For architecture decisions |
| `codex_clean` | Remove debug/dead code | Before committing |

---

## 🎯 THE ENFORCER'S RULES

1. **NEVER LIE** - If code is shit, it gets a shit score
2. **BE HARSH** - 9.0+ is HARD to achieve
3. **DOCUMENT EVERYTHING** - Missing docs = point deduction
4. **500 LINE LIMIT** - Fat files get penalized
5. **NO DEBUG IN PROD** - console.log = instant deduction
6. **TEST OR DIE** - Untested code can't be pristine

---

## 💪 INTEGRATION WITH EXISTING WORKFLOW

Your current dual-agent workflow becomes:

1. **Claude takes snapshot** (codex_snapshot)
2. **Claude implements feature**
3. **Codex enforces quality** (codex_enforce)
4. **If score < 9.0, Claude fixes issues**
5. **Repeat until PRISTINE**

This gives you:
- Automated quality control
- Consistent code standards
- No manual cleanup needed
- Russian Olympic Judge honesty

---

## 🔥 EXAMPLE SESSION

```
You: "Yo Cash Money, implement WebSocket reconnection"

Claude: "My Dude, let me snapshot these files first..."
*Uses codex_snapshot*
"Snapshot taken: ID 20241027_220145"

Claude: "Implementing reconnection logic..."
*Writes code*

Claude: "Let me check quality..."
*Uses codex_enforce*
"Score: 8.3/10 - Found 2 debug logs and missing JSDoc"

Claude: "Fixing issues..."
*Cleans code*

Claude: "Final check..."
*Uses codex_enforce*
"✨ PRISTINE! Score: 9.6/10"

You: "That's what I'm talking about!"
```

---

## 🎯 BOTTOM LINE

This MCP server makes Claude and Codex work together to:
1. Give you MULTIPLE solution perspectives
2. Enforce PRISTINE code quality
3. Automate cleanup and validation
4. Provide Russian Olympic Judge honesty

No more bullshit, no more lies, just COLD HARD TRUTH about your code quality.

---

**Last Updated:** October 27, 2025
**Version:** 1.0.0
**Status:** READY TO ENFORCE

Yo Yung Nigga, this shit is READY TO ROLL! 🔥
