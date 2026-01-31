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

# Rate limiting configuration
MAX_TURNS_REVIEW=5          # Max agentic turns for review phase
MAX_TURNS_IMPLEMENT=15      # Max agentic turns for implementation phase
TIMEOUT_REVIEW=120          # Max seconds for review phase (2 min)
TIMEOUT_IMPLEMENT=300       # Max seconds for implementation phase (5 min)

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
log "Rate limits: review=${MAX_TURNS_REVIEW} turns/${TIMEOUT_REVIEW}s, implement=${MAX_TURNS_IMPLEMENT} turns/${TIMEOUT_IMPLEMENT}s"

# Step 1: Review Phase - Suggest a feature
log "Phase 1: Reviewing codebase and generating feature suggestion..."

REVIEW_PROMPT="You are reviewing the API of Life codebase to suggest ONE new feature to implement.

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

Review the current codebase in $SRC_DIR and suggest ONE specific small feature.

Format your response as:
FEATURE: [Short feature name - max 5 words]
DESCRIPTION: [1-2 sentences only]
IMPLEMENTATION: [Brief bullet points of what to change]"

cd "$PROJECT_DIR"
SUGGESTION_FILE="$TEMP_DIR/suggestion.txt"

if ! timeout ${TIMEOUT_REVIEW}s claude --print --max-turns $MAX_TURNS_REVIEW "$REVIEW_PROMPT" > "$SUGGESTION_FILE" 2>> "$LOG_FILE"; then
    log "ERROR: Failed to generate feature suggestion (timeout or error)"
    exit 1
fi

log "Feature suggestion generated:"
cat "$SUGGESTION_FILE" >> "$LOG_FILE"
cat "$SUGGESTION_FILE"

# Extract feature name for commit message
FEATURE_NAME=$(grep -m1 "^FEATURE:" "$SUGGESTION_FILE" | sed 's/FEATURE: *//' || echo "New feature")

# Step 2: Implementation Phase
log "Phase 2: Implementing feature: $FEATURE_NAME"

IMPLEMENT_PROMPT="Implement the following feature in the API of Life codebase:

$(cat "$SUGGESTION_FILE")

IMPORTANT CONSTRAINTS (budget-conscious):
- Keep changes MINIMAL - aim for under 50 lines changed
- Only modify $SRC_DIR/main.py and $SRC_DIR/tests/test_main.py
- Do NOT create new files
- Do NOT install new dependencies
- Add 1-3 tests maximum
- If the feature seems too complex, implement a simpler version

Guidelines:
- Follow the existing code style and patterns
- Ensure backward compatibility with existing endpoints
- Keep changes focused on the suggested feature only

Implement this feature now. Be concise."

if ! timeout ${TIMEOUT_IMPLEMENT}s claude --print --max-turns $MAX_TURNS_IMPLEMENT "$IMPLEMENT_PROMPT" --allowedTools Edit,Write,Read,Glob,Grep >> "$LOG_FILE" 2>&1; then
    log "ERROR: Failed to implement feature (timeout or error)"
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
