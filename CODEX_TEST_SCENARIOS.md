# 🔥 CODEX MCP TEST SCENARIOS
**Real Examples of Dual-Agent System in Action**

---

## SCENARIO 1: WebSocket Reconnection Implementation

### User Query:
"Implement WebSocket reconnection with exponential backoff for the EBL audio streaming"

### Step 1: Claude Gets Dual Answer
```javascript
mcp__codex__codex_dual_answer({
  "question": "How to implement WebSocket reconnection with exponential backoff?",
  "context": "Real-time audio streaming app with critical latency requirements"
})
```

### Codex Returns:
```
🤖 DUAL ANSWER ANALYSIS
====================

📦 APPROACH 1: Quick & Dirty (Score: 6.5/10)
Simple setTimeout with doubling delays
✅ Pros: Fast to implement, Easy to understand, Works immediately
❌ Cons: No jitter, No max retries, Memory leaks possible

🏢 APPROACH 2: Enterprise Grade (Score: 9.5/10)
Full state machine with connection manager
✅ Pros: Handles all edge cases, Observable pattern, Circuit breaker
❌ Cons: 500+ lines of code, Complex state management, Overkill for MVP

⚖️ APPROACH 3: Balanced (Score: 8.5/10)
Clean reconnection with jitter and max retries
✅ Pros: Production-ready, Maintainable, Reasonable complexity
❌ Cons: Still needs monitoring integration

🎯 RECOMMENDATION: For audio streaming, use BALANCED approach with focus on latency
```

### Step 2: Claude Takes Snapshot
```javascript
mcp__codex__codex_snapshot({
  "files": [
    "src/services/websocket.ts",
    "src/hooks/useWebSocket.ts"
  ],
  "description": "Implementing balanced WebSocket reconnection"
})
// Returns: Snapshot ID: 20241027_223045
```

### Step 3: Claude Implements (Balanced Approach)
```typescript
// src/services/websocket.ts
export class WebSocketManager {
  private retryCount = 0;
  private maxRetries = 10;
  private baseDelay = 1000;
  private maxDelay = 30000;
  
  private calculateBackoff(): number {
    const exponentialDelay = Math.min(
      this.baseDelay * Math.pow(2, this.retryCount),
      this.maxDelay
    );
    // Add jitter to prevent thundering herd
    const jitter = Math.random() * 0.3 * exponentialDelay;
    return exponentialDelay + jitter;
  }
  
  async reconnect(): Promise<void> {
    if (this.retryCount >= this.maxRetries) {
      this.emit('max_retries_exceeded');
      return;
    }
    
    const delay = this.calculateBackoff();
    console.log(`Reconnecting in ${delay}ms (attempt ${this.retryCount + 1})`); // KEEP - Production logging
    
    await new Promise(resolve => setTimeout(resolve, delay));
    this.retryCount++;
    
    try {
      await this.connect();
      this.retryCount = 0; // Reset on success
    } catch (error) {
      await this.reconnect(); // Recursive retry
    }
  }
}
```

### Step 4: Codex Enforces Quality
```javascript
mcp__codex__codex_enforce({
  "snapshot_id": "20241027_223045",
  "auto_fix": false
})
```

### Codex Returns:
```
🎯 CODEX ENFORCEMENT REPORT
========================
Status: ✨ PRISTINE
Overall Score: 9.2/10.0
Files Analyzed: 2
Pristine Files: 2

FILE SCORES:
📄 websocket.ts: 9.2/10.0
  ✓ Clean code (no debug statements)
  ✓ Proper error handling
  ✓ Good architecture
  Minor: Could add JSDoc for calculateBackoff

📄 useWebSocket.ts: 9.2/10.0
  ✓ React hooks properly used
  ✓ Cleanup in useEffect
  ✓ Type safety maintained
```

---

## SCENARIO 2: LeetCode Problem Solving

### User Query:
"Solve Two Sum problem in Java"

### Claude + Codex Workflow:
```javascript
// First, get dual answer for approach
mcp__codex__codex_dual_answer({
  "question": "Best approach for Two Sum LeetCode problem?",
  "context": "Need both brute force and optimized solutions"
})
```

### Returns Multiple Solutions:
```
📦 BRUTE FORCE: Nested loops, O(n²) time, O(1) space
🏢 OPTIMIZED: HashMap, O(n) time, O(n) space
⚖️ BALANCED: Sort + two pointers, O(n log n) time, O(1) space
```

### Claude Implements Both:
```java
// SOLUTION 1: Brute Force (Score: 7.0/10)
public int[] twoSumBrute(int[] nums, int target) {
    for (int i = 0; i < nums.length; i++) {
        for (int j = i + 1; j < nums.length; j++) {
            if (nums[i] + nums[j] == target) {
                return new int[]{i, j};
            }
        }
    }
    return new int[0];
}

// SOLUTION 2: Optimized (Score: 9.5/10)
public int[] twoSumOptimized(int[] nums, int target) {
    Map<Integer, Integer> map = new HashMap<>();
    for (int i = 0; i < nums.length; i++) {
        int complement = target - nums[i];
        if (map.containsKey(complement)) {
            return new int[]{map.get(complement), i};
        }
        map.put(nums[i], i);
    }
    return new int[0];
}
```

---

## SCENARIO 3: Quick Code Cleanup

### User Has Messy Code:
```javascript
// Messy component with debug logs
function Timer() {
  console.log("rendering timer");
  const [time, setTime] = useState(0);
  
  // const oldCode = "something"; // Dead code
  console.debug("time is", time);
  
  useEffect(() => {
    console.log("effect running");
    // More code...
  }, []);
  
  return <div>{time}</div>;
}
```

### Claude Uses Codex Clean:
```javascript
mcp__codex__codex_clean({
  "file": "src/components/Timer.tsx",
  "save": false  // Preview first
})
```

### Preview Shows:
```
🔍 PREVIEW: Timer.tsx
Would remove: 4 violations
- Debug statement: console.log("rendering timer")
- Dead code: // const oldCode = "something"
- Debug statement: console.debug("time is", time)
- Debug statement: console.log("effect running")
```

### Apply Cleanup:
```javascript
mcp__codex__codex_clean({
  "file": "src/components/Timer.tsx",
  "save": true
})
```

### Clean Result:
```javascript
function Timer() {
  const [time, setTime] = useState(0);
  
  useEffect(() => {
    // More code...
  }, []);
  
  return <div>{time}</div>;
}
```

---

## SCENARIO 4: Architecture Decision

### User Query:
"Should I use Redux or Context API for state management?"

### Codex Dual Answer:
```javascript
mcp__codex__codex_dual_answer({
  "question": "Redux vs Context API for state management?",
  "context": "Medium-sized app with 50+ components"
})
```

### Returns Analysis:
```
📦 QUICK: Context API only (Score: 6.5/10)
- Simple, built-in, no dependencies
- Performance issues at scale
- When: Small apps, prototype phase

🏢 ENTERPRISE: Redux Toolkit + RTK Query (Score: 9.5/10)
- Full state management solution
- Time-travel debugging, middleware
- When: Large teams, complex state

⚖️ BALANCED: Zustand or Valtio (Score: 8.5/10)
- Modern, simple API
- Good performance, small bundle
- When: Most real-world apps

🎯 RECOMMENDATION: For 50+ components, use Zustand
```

---

## SCENARIO 5: Full Development Cycle

### Complete Feature Implementation:

```javascript
// 1. PLAN
"Add real-time notifications to the app"

// 2. GET APPROACH
mcp__codex__codex_dual_answer({
  "question": "Best way to add real-time notifications?",
  "context": "React app with existing WebSocket connection"
})

// 3. SNAPSHOT
mcp__codex__codex_snapshot({
  "files": [
    "src/components/NotificationCenter.tsx",
    "src/hooks/useNotifications.ts",
    "src/services/notification.service.ts"
  ],
  "description": "Adding real-time notification system"
})

// 4. IMPLEMENT
// Claude writes the code...

// 5. ANALYZE QUALITY
mcp__codex__codex_analyze({
  "files": ["src/components/NotificationCenter.tsx"]
})
// Shows: Missing JSDoc, 1 debug statement

// 6. CLEAN
mcp__codex__codex_clean({
  "file": "src/components/NotificationCenter.tsx",
  "save": true
})

// 7. ENFORCE
mcp__codex__codex_enforce({
  "snapshot_id": "20241027_224512",
  "auto_fix": false
})
// Score: 9.3/10 - PRISTINE!

// 8. COMMIT
"Feature complete with 9.3/10 quality score"
```

---

## 🎯 KEY TESTING COMMANDS

### Quick Test Suite:
```bash
# Test 1: Check if server is accessible
python C:\Users\bisho\.claude\codex_mcp\codex_mcp_server.py

# Test 2: In Claude, check available tools
"What tools do you have available?"
# Should see: codex_snapshot, codex_enforce, codex_analyze, etc.

# Test 3: Simple analysis
mcp__codex__codex_analyze({
  "files": ["any_file.ts"]
})

# Test 4: Dual answer
mcp__codex__codex_dual_answer({
  "question": "How to optimize React rendering?"
})
```

---

## 🔥 INTEGRATION WITH YOUR EBL PROJECT

### For Your Current Timer Display Enhancement:

```javascript
// 1. Before making changes
mcp__codex__codex_snapshot({
  "files": ["src/components/TimerCountdownDisplay.tsx"],
  "description": "Testing enhanced timer display in browser"
})

// 2. After testing in browser
mcp__codex__codex_enforce({
  "snapshot_id": "YOUR_SNAPSHOT_ID",
  "auto_fix": true
})

// 3. Get quality score
// If < 9.0, fix issues
// If >= 9.0, you're PRISTINE!
```

---

## 💡 POWER USER TIPS

1. **Chain Commands:**
   ```javascript
   snapshot → implement → enforce → clean → enforce
   ```

2. **Use Dual Answers for Architecture:**
   - Always get multiple perspectives
   - Choose based on project phase
   - Document why you chose specific approach

3. **Enforce Early and Often:**
   - Don't wait until end to check quality
   - Run enforce after each function
   - Fix immediately while context is fresh

4. **Mark Production Logs:**
   ```javascript
   console.error('Critical error', error); // KEEP
   logger.info('User action', data); // KEEP
   ```

5. **Split Large Files Proactively:**
   - Before hitting 400 lines, plan split
   - Enforce will penalize at 500+
   - Keep components focused

---

**Ready to test, My Dude?** This dual-agent system will keep your code PRISTINE while giving you multiple perspectives on every decision! 🔥
