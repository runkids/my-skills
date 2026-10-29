#!/usr/bin/env bash
# Feature Radar Validation Script
# Validates SKILL.md frontmatter and .feature-radar/ SPEC.md compliance
# Exit 0 = pass, Exit 1 = errors found
set -euo pipefail

RED='\033[0;31m'
YLW='\033[0;33m'
GRN='\033[0;32m'
RST='\033[0m'

errors=0
warnings=0

error() { echo -e "  ${RED}ERROR${RST}: $1"; errors=$((errors + 1)); }
warn()  { echo -e "  ${YLW}WARN${RST}:  $1"; warnings=$((warnings + 1)); }
pass()  { echo -e "  ${GRN}OK${RST}:    $1"; }

# ─── Layer 1: SKILL.md Frontmatter ──────────────────────────────────────────

echo ""
echo "=== Layer 1: SKILL.md Frontmatter ==="
echo ""

for skill_file in skills/*/SKILL.md; do
  [ -f "$skill_file" ] || continue
  skill_dir=$(basename "$(dirname "$skill_file")")
  echo "[$skill_dir]"

  # Extract frontmatter (between first pair of ---)
  frontmatter=$(awk '/^---$/{n++; next} n==1' "$skill_file")

  # Check name field
  name=$(echo "$frontmatter" | grep -E '^name:' | head -1 | sed 's/^name:[[:space:]]*//')
  if [ -z "$name" ]; then
    error "missing 'name' field"
  elif ! echo "$name" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$'; then
    error "name '$name' is not kebab-case"
  elif [ "${#name}" -gt 64 ]; then
    error "name is ${#name} chars (max 64)"
  elif [ "$name" != "$skill_dir" ]; then
    error "name '$name' does not match directory '$skill_dir'"
  else
    pass "name: $name"
  fi

  # Extract description (handles multi-line | syntax)
  desc=$(awk '
    /^---$/ { n++; next }
    n != 1 { next }
    /^description:/ {
      # Check for inline value vs block scalar
      sub(/^description:[[:space:]]*/, "")
      if ($0 == "|" || $0 == ">") { capture = 1; next }
      if ($0 != "") { print; next }
      capture = 1; next
    }
    capture && /^[a-z]/ { capture = 0 }
    capture && /^[[:space:]]/ { sub(/^[[:space:]]+/, ""); print }
  ' "$skill_file")

  if [ -z "$desc" ]; then
    error "missing 'description' field"
  else
    desc_len=${#desc}
    if [ "$desc_len" -gt 1024 ]; then
      error "description is ${desc_len} chars (max 1024)"
    else
      pass "description: ${desc_len} chars"
    fi

    # Warning: description should contain "Use when" or "Trigger phrases"
    if ! echo "$desc" | grep -qiE 'Use when|Trigger phrases'; then
      warn "description lacks 'Use when' or 'Trigger phrases'"
    fi
  fi

  # Warning: body length (lines after frontmatter closing ---)
  body_lines=$(awk '/^---$/{n++; next} n>=2' "$skill_file" | wc -l | tr -d ' ')
  if [ "$body_lines" -gt 500 ]; then
    warn "body is ${body_lines} lines (recommended max 500)"
  fi

  echo ""
done

# ─── Layer 2: SPEC.md Compliance (.feature-radar/) ──────────────────────────

if [ -d ".feature-radar" ]; then
  echo "=== Layer 2: .feature-radar/ SPEC Compliance ==="
  echo ""

  # Check archive/ and opportunities/ filename format: {nn}-{slug}.md
  for dir in archive opportunities; do
    dirpath=".feature-radar/$dir"
    [ -d "$dirpath" ] || continue

    for f in "$dirpath"/*.md; do
      [ -f "$f" ] || continue
      fname=$(basename "$f")
      echo "[$dir/$fname]"

      if ! echo "$fname" | grep -qE '^[0-9]{2}-[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
        error "filename '$fname' does not match {nn}-{slug}.md format"
      else
        pass "filename format OK"
      fi

      # Check required fields based on directory
      content=$(cat "$f")
      if ! echo "$content" | grep -q '^\*\*Status\*\*:'; then
        error "missing **Status**: field"
      fi

      if [ "$dir" = "opportunities" ]; then
        for field in Impact Effort; do
          if ! echo "$content" | grep -q "^\*\*${field}\*\*:"; then
            error "missing **${field}**: field"
          fi
        done
      fi
      echo ""
    done
  done

  # Warning: base.md Tracking Summary count reconciliation
  if [ -f ".feature-radar/base.md" ]; then
    echo "[base.md count reconciliation]"
    for dir in archive opportunities specs references; do
      dirpath=".feature-radar/$dir"
      if [ -d "$dirpath" ]; then
        actual=$(find "$dirpath" -name '*.md' -type f | wc -l | tr -d ' ')
      else
        actual=0
      fi

      # Extract count from base.md tracking table
      # Format: | archive/ | {n} | ...
      reported=$(grep -E "^\|[[:space:]]*${dir}/" ".feature-radar/base.md" 2>/dev/null \
        | head -1 \
        | awk -F'|' '{gsub(/[[:space:]]/, "", $3); print $3}')

      if [ -n "$reported" ] && [ "$reported" != "$actual" ]; then
        warn "${dir}/ count mismatch: base.md says ${reported}, actual ${actual}"
      elif [ -n "$reported" ]; then
        pass "${dir}/ count: ${actual}"
      fi
    done
    echo ""
  fi
else
  echo ""
  echo "=== Layer 2: Skipped (.feature-radar/ not found) ==="
  echo ""
fi

# ─── Summary ────────────────────────────────────────────────────────────────

echo "─────────────────────────────────────"
if [ "$errors" -gt 0 ]; then
  echo -e "${RED}FAILED${RST}: ${errors} error(s), ${warnings} warning(s)"
  exit 1
elif [ "$warnings" -gt 0 ]; then
  echo -e "${YLW}PASSED${RST}: 0 errors, ${warnings} warning(s)"
  exit 0
else
  echo -e "${GRN}PASSED${RST}: all checks passed"
  exit 0
fi
