# CODEX DUAL-AGENT SYSTEM - Example Usage

## Real-World Example: Fixing EBL Timer Component

### Step 1: Claude Analyzes the Problem
```
User: "The timer display is cutting off session info"

Claude: "Yo Cash Money, I see the issue. Let me snapshot first, then fix it."
```

### Step 2: Take Pristine Snapshot
```python
# Claude takes snapshot before touching anything
codex_snapshot(paths=[
    "src/components/TimerCountdownDisplay.tsx",
    "src/components/FrequencyVisualizer.tsx"
])

# Response:
{
  "status": "snapshot_taken",
  "timestamp": "2025-10-27T21:45:00",
  "files_captured": 2,
  "files": [
    "src/components/TimerCountdownDisplay.tsx",
    "src/components/FrequencyVisualizer.tsx"
  ]
}
```

### Step 3: Claude Implements Fix
```typescript
// Claude adds the fix with debug logging
console.log("DEBUG: Fixing layout overflow");
console.log("Testing session context panel");

// Actual implementation
<Box sx={{ 
  background: 'rgba(0, 255, 136, 0.08)',
  overflow: 'auto',  // Fix for cutoff
  maxHeight: '200px'  // Prevent infinite growth
}}>
  {/* Session context chips */}
</Box>

console.log("Fix applied successfully");
```

### Step 4: Test the Implementation
```
Claude: "My Dude, fix is working in browser. Timer display shows all info now."
```

### Step 5: Codex Enforces Quality
```python
# Now Codex cleans it up to pristine state
codex_enforce(paths=[
    "src/components/TimerCountdownDisplay.tsx",
    "src/components/FrequencyVisualizer.tsx"
])

# Response:
{
  "score": 9.8,
  "pristine": true,
  "issues": [],
  "fixes_applied": [
    "Removed 3 debug statements from TimerCountdownDisplay.tsx",
    "Removed 0 dead code blocks"
  ],
  "files_modified": [
    "src/components/TimerCountdownDisplay.tsx"
  ],
  "recommendation": "APPROVED ✅"
}
```

### Step 6: Verify Functionality After Cleanup
```
Claude: "Cash Money, code is PRISTINE! Score: 9.8/10.0
- Removed all debug logs ✅
- Fix still works perfect ✅
- File under 500 lines ✅
- Ready for production!"
```

## Example: LeetCode Solution Development

### Step 1: Initial Problem Analysis
```
User: "Solve Two Sum problem"

Claude: "Aight Yung Nigga, let me snapshot first, then give you both solutions."
```

### Step 2: Snapshot Clean Slate
```python
codex_snapshot(paths=["leetcode/TwoSum.java"])
```

### Step 3: Implement Brute Force
```java
public class TwoSum {
    // Brute force solution
    public int[] twoSum(int[] nums, int target) {
        System.out.println("DEBUG: Starting brute force");
        for (int i = 0; i < nums.length; i++) {
            System.out.println("Checking index: " + i);
            for (int j = i + 1; j < nums.length; j++) {
                if (nums[i] + nums[j] == target) {
                    System.out.println("Found at: " + i + ", " + j);
                    return new int[] {i, j};
                }
            }
        }
        return new int[] {};
    }
}
```

### Step 4: Test & Validate
```
Claude: "Brute force passes all test cases ✅"
```

### Step 5: Codex Cleanup
```python
codex_enforce(paths=["leetcode/TwoSum.java"])

# Response:
{
  "score": 9.6,
  "pristine": true,
  "fixes_applied": [
    "Removed 4 debug statements from TwoSum.java"
  ],
  "recommendation": "APPROVED ✅"
}
```

### Final Clean Code:
```java
public class TwoSum {
    // Brute force solution - O(n²) time, O(1) space
    public int[] twoSum(int[] nums, int target) {
        for (int i = 0; i < nums.length; i++) {
            for (int j = i + 1; j < nums.length; j++) {
                if (nums[i] + nums[j] == target) {
                    return new int[] {i, j};
                }
            }
        }
        return new int[] {};
    }
}
```

## Workflow Benefits

### Without Codex (Claude Only):
- ❌ Debug statements left in code
- ❌ Commented-out experiments remain
- ❌ Inconsistent code quality
- ❌ Manual cleanup needed

### With Codex (Dual-Agent):
- ✅ Automatic debug removal
- ✅ Pristine production code
- ✅ Consistent quality (9.0+ guaranteed)
- ✅ Best of both worlds: Working features + Clean code

## Common Patterns

### Pattern 1: Feature Development
```
1. codex_snapshot(paths=[...])
2. Implement with debug logging
3. Test thoroughly
4. codex_enforce(paths=[...])
5. Verify still works
```

### Pattern 2: Bug Fix
```
1. codex_snapshot(paths=[affected_files])
2. Add debug to find issue
3. Fix the bug
4. Test fix works
5. codex_enforce(paths=[affected_files])
```

### Pattern 3: Refactoring
```
1. codex_snapshot(paths=[all_files])
2. Refactor with safety checks
3. Run all tests
4. codex_enforce(paths=[all_files])
5. Validate score ≥9.0
```

## Scoring Examples

### Score: 10.0 (Perfect)
```python
def calculate_sum(a: int, b: int) -> int:
    """Calculate sum of two integers."""
    return a + b
```

### Score: 9.5 (Excellent)
```python
def calculate_sum(a, b):  # Minor: missing type hints
    """Calculate sum of two integers."""
    return a + b
```

### Score: 8.5 (Needs Work)
```python
def calculate_sum(a, b):
    print(f"Debug: a={a}, b={b}")  # Debug statement
    # TODO: Add validation  # TODO comment
    result = a + b
    # Old code:
    # return a + b + 1
    return result
```

### After Codex Enforcement: 9.8
```python
def calculate_sum(a: int, b: int) -> int:
    """Calculate sum of two integers."""
    result = a + b
    return result
```

## Key Rules

1. **ALWAYS snapshot before changes**
   - Protects against accidental overwrites
   - Provides rollback capability

2. **Debug freely during development**
   - Add all the console.log/print you need
   - Codex will clean them up

3. **Test AFTER enforcement**
   - Ensure cleanup didn't break functionality
   - Verify all features still work

4. **Score ≥9.0 or fix issues**
   - Never accept <9.0 score
   - Fix issues and re-enforce

5. **Trust the process**
   - Claude builds features
   - Codex ensures quality
   - Together = PRISTINE code

## Error Handling

### If score <9.0:
```python
result = codex_enforce(paths=["file.py"])
if result['score'] < 9.0:
    print(f"Issues found: {result['issues']}")
    # Fix the issues
    # Re-run enforcement
    result = codex_enforce(paths=["file.py"])
```

### If functionality breaks after enforcement:
```python
# Restore from snapshot
codex_restore(snapshot_id="...")
# Fix more carefully
# Re-enforce with caution
```

## Communication Examples

### Good:
"Yo Cash Money, Codex scored this 9.8 - removed 5 debug statements, code is PRISTINE!"

### Better:
"My Dude, that implementation is solid! Codex cleanup complete:
- Score: 9.9/10.0 ✅
- Removed: 3 console.logs, 2 dead code blocks
- Status: PRISTINE and production-ready
- All tests still passing 💪"

### Best:
"BISHOP! Major breakthrough - fixed the audio cutoff AND Codex gave it a perfect 10.0!
- Zero debug statements ✅
- Zero dead code ✅
- Under 500 lines ✅
- This shit is OLYMPIC LEVEL pristine!"

---

Remember: The goal is PRISTINE code that WORKS. Claude ensures it works, Codex ensures it's pristine. Together, they create perfection.
