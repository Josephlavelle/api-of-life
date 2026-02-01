#!/bin/bash
#
# API of Life - Daily Evolution Script
#
# This script orchestrates the daily evolution cycle:
# 1. Review the codebase and suggest a new feature
# 2. Implement the suggested feature
# 3. Run tests to verify
# 4. Commit changes if tests pass
# 5. Log everything for review

set -e

# Activate conda environment
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
conda activate api-of-life

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"
LOGS_DIR="$SCRIPT_DIR/logs"
HISTORY_FILE="$SCRIPT_DIR/history.md"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M:%S)
LOG_FILE="$LOGS_DIR/$DATE.log"
TEMP_DIR=$(mktemp -d)

# Rate limiting configuration (cost-based)
MAX_BUDGET_REVIEW=0.25      # Max dollars for review phase
MAX_BUDGET_IMPLEMENT=0.50   # Max dollars for implementation phase
TIMEOUT_REVIEW=120          # Max seconds for review phase (2 min)
TIMEOUT_IMPLEMENT=300       # Max seconds for implementation phase (5 min)

# Portable timeout function (works on macOS without coreutils)
run_with_timeout() {
    local timeout=$1
    shift

    # Run command in background
    "$@" &
    local pid=$!

    # Wait for completion or timeout
    local count=0
    while kill -0 $pid 2>/dev/null; do
        if [ $count -ge $timeout ]; then
            kill -9 $pid 2>/dev/null
            wait $pid 2>/dev/null
            return 124  # timeout exit code
        fi
        sleep 1
        ((count++))
    done

    wait $pid
    return $?
}

# Cleanup temp directory on exit
trap "rm -rf $TEMP_DIR" EXIT

# Logging function
log() {
    echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG_FILE"
}

# Initialize log file
mkdir -p "$LOGS_DIR"
echo "========================================" >> "$LOG_FILE"
echo "Evolution Run: $DATE $TIME" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

log "Starting evolution cycle..."
log "Rate limits: review=\$${MAX_BUDGET_REVIEW}/${TIMEOUT_REVIEW}s, implement=\$${MAX_BUDGET_IMPLEMENT}/${TIMEOUT_IMPLEMENT}s"

# Step 1: Review Phase - Suggest a feature
log "Phase 1: Reviewing codebase and generating feature suggestion..."

REVIEW_PROMPT="You are reviewing a FastAPI codebase to suggest ONE new feature to implement.

IMPORTANT CONSTRAINTS (budget-conscious):
- Suggest a SMALL, SIMPLE feature (max 50 lines of code changes)
- Must be implementable in under 5 minutes
- NO complex features like authentication, databases, external APIs, or caching
- NO refactoring or architectural changes
- Think: add a field, add a simple endpoint, add basic validation

Guidelines for your suggestion:
- Suggest an incremental, buildable feature that adds genuine value
- Avoid breaking existing functionality
- Prefer simple enhancements: new query parameters, additional fields, basic filtering
- Keep it focused - one clear, small feature

The codebase has two files: main.py (the API) and tests/test_main.py (the tests).
Suggest ONE specific small feature.

Format your response as:
FEATURE: [Short feature name - max 5 words]
DESCRIPTION: [1-2 sentences only]
IMPLEMENTATION: [Brief bullet points of what to change]"

# Run Claude from src/ directory so it can only see/edit those files
cd "$SRC_DIR"
SUGGESTION_FILE="$TEMP_DIR/suggestion.txt"

if ! run_with_timeout $TIMEOUT_REVIEW claude --print --max-budget-usd $MAX_BUDGET_REVIEW "$REVIEW_PROMPT" > "$SUGGESTION_FILE" 2>> "$LOG_FILE"; then
    log "ERROR: Failed to generate feature suggestion (timeout or budget exceeded)"
    exit 1
fi

log "Feature suggestion generated:"
cat "$SUGGESTION_FILE" >> "$LOG_FILE"
cat "$SUGGESTION_FILE"

# Extract feature name for commit message
FEATURE_NAME=$(grep -m1 "^FEATURE:" "$SUGGESTION_FILE" | sed 's/FEATURE: *//' || echo "New feature")

# Step 2: Implementation Phase
log "Phase 2: Implementing feature: $FEATURE_NAME"

IMPLEMENT_PROMPT="Implement the following feature:

$(cat "$SUGGESTION_FILE")

IMPORTANT CONSTRAINTS (budget-conscious):
- Keep changes MINIMAL - aim for under 50 lines changed
- ONLY modify main.py and tests/test_main.py in the current directory
- Do NOT create new files
- Do NOT install new dependencies
- Do NOT navigate to parent directories or other folders
- Add 1-3 tests maximum
- If the feature seems too complex, implement a simpler version

Guidelines:
- Follow the existing code style and patterns
- Ensure backward compatibility with existing endpoints
- Keep changes focused on the suggested feature only

Implement this feature now. Be concise."

# Still in src/ directory - Claude can only see/edit files here
if ! run_with_timeout $TIMEOUT_IMPLEMENT claude --print --max-budget-usd $MAX_BUDGET_IMPLEMENT "$IMPLEMENT_PROMPT" --allowedTools Edit,Read,Grep >> "$LOG_FILE" 2>&1; then
    log "ERROR: Failed to implement feature (timeout or budget exceeded)"
    # Revert any partial changes
    cd "$PROJECT_DIR"
    git checkout -- . 2>/dev/null || true
    exit 1
fi

log "Implementation complete"

# Step 3: Verification Phase - Run tests
log "Phase 3: Running tests..."

cd "$SRC_DIR"
if ! python -m pytest tests/ -v >> "$LOG_FILE" 2>&1; then
    log "ERROR: Tests failed! Aborting commit."
    log "Check $LOG_FILE for test output"

    # Revert changes
    cd "$PROJECT_DIR"
    git checkout -- . 2>/dev/null || true

    exit 1
fi

log "All tests passed!"

# Step 4: Commit Phase
log "Phase 4: Committing changes..."

cd "$PROJECT_DIR"

# Check if there are changes to commit
if git diff --quiet && git diff --cached --quiet; then
    log "No changes to commit"
    exit 0
fi

# Stage all changes
git add -A

# Create commit message
COMMIT_MSG="feat: $FEATURE_NAME

Auto-evolved on $DATE at $TIME

$(grep -A10 "^DESCRIPTION:" "$SUGGESTION_FILE" | head -5 || echo "See evolution log for details")"

git commit -m "$COMMIT_MSG"

log "Changes committed successfully"

# Step 5: Logging Phase - Update history
log "Phase 5: Updating evolution history..."

# Get list of changed files
CHANGED_FILES=$(git diff --name-only HEAD~1 2>/dev/null || echo "Unknown")

# Append to history
cat >> "$HISTORY_FILE" << EOF

## $DATE - $FEATURE_NAME

**Time:** $TIME

**Description:**
$(grep -A10 "^DESCRIPTION:" "$SUGGESTION_FILE" | head -5 || echo "See log for details")

**Files Changed:**
\`\`\`
$CHANGED_FILES
\`\`\`

---
EOF

log "Evolution cycle complete!"
log "Feature: $FEATURE_NAME"
log "Log file: $LOG_FILE"
log "History updated: $HISTORY_FILE"

echo ""
echo "✓ Evolution successful: $FEATURE_NAME"
