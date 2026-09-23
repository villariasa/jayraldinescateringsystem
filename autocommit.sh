#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  autocommit.sh — Smart auto-commit with auto-generated commit message
#
#  Usage:
#    ./autocommit.sh
#    ./autocommit.sh --no-push
#    ./autocommit.sh --dry-run
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Options ──────────────────────────────────────────────────────────────────
PUSH=true
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --no-push)
      PUSH=false
      ;;
    --dry-run)
      DRY_RUN=true
      PUSH=false
      ;;
    *)
      echo "❌ Unknown option: $arg"
      echo "Usage: $0 [--no-push|--dry-run]"
      exit 1
      ;;
  esac
done


# ── Ensure we're inside a git repo ────────────────────────────────────────────
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo "❌ Not a git repository. Run this from inside your project folder."
  exit 1
fi


# ── Collect changed files ─────────────────────────────────────────────────────
mapfile -t ADDED < <(
  git status --short |
    awk '$1 ~ /A/ || $1 == "??" {print $2}'
)

mapfile -t MODIFIED < <(
  git status --short |
    awk '$1 ~ /M/ {print $2}'
)

mapfile -t DELETED < <(
  git status --short |
    awk '$1 ~ /D/ {print $2}'
)

mapfile -t RENAMED < <(
  git status --short |
    awk '$1 ~ /R/ {print $NF}'
)

ALL_FILES=(
  "${ADDED[@]}"
  "${MODIFIED[@]}"
  "${DELETED[@]}"
  "${RENAMED[@]}"
)


# ── Check if there are changes ────────────────────────────────────────────────
if [ "${#ALL_FILES[@]}" -eq 0 ]; then
  echo "✅ Nothing to commit — working tree is clean."
  exit 0
fi


# ── Determine commit TYPE from changed files ──────────────────────────────────
determine_type() {
  local files=("$@")

  local has_fix=false
  local has_feat=false
  local has_refactor=false
  local has_docs=false
  local has_style=false
  local has_chore=false

  for f in "${files[@]}"; do

    case "$f" in
      *.md|docs/*)
        has_docs=true
        ;;

      *.css|*.scss|*.less)
        has_style=true
        ;;

      */fix*|*/bug*|*_fix*|*fix_*)
        has_fix=true
        ;;

      setup*.py|*.cfg|*.ini|*.toml|*.yml|*.yaml|Makefile|*.sh|*.bat|*.iss|*.spec)
        has_chore=true
        ;;
    esac

    # Check staged diff for keywords related to fixes
    if git diff --cached -- "$f" 2>/dev/null |
      grep -qiE '^\+.*(fix|bug|error|crash|broken|patch)'; then
      has_fix=true
    fi

    # Check staged diff for keywords related to features
    if git diff --cached -- "$f" 2>/dev/null |
      grep -qiE '^\+.*(add|new|feat|feature|implement|create)'; then
      has_feat=true
    fi

  done

  # Priority:
  # fix > feat > style > docs > chore > refactor

  if $has_fix; then
    echo "fix"
    return
  fi

  if $has_feat; then
    echo "feat"
    return
  fi

  if $has_style; then
    echo "style"
    return
  fi

  if $has_docs; then
    echo "docs"
    return
  fi

  if $has_chore; then
    echo "chore"
    return
  fi

  echo "refactor"
}


# ── Build human-readable scope ────────────────────────────────────────────────
build_scope() {
  local files=("$@")
  local raw_scopes=()

  for f in "${files[@]}"; do

    local scope=""

    case "$f" in

      Catering_Present/*/components/*)
        scope="components"
        ;;

      Catering_Present/*/ui/*)
        scope="ui"
        ;;

      Catering_Present/*/utils/*)
        scope="utils"
        ;;

      Catering_Present/*/assets/*)
        scope="assets"
        ;;

      Catering_Present/*)
        scope="desktop-app"
        ;;

      Tablet_PWA/frontend/js/*)
        scope="tablet-js"
        ;;

      Tablet_PWA/frontend/*)
        scope="tablet-pwa"
        ;;

      Tablet_PWA/backend/*)
        scope="tablet-backend"
        ;;

      Tablet_PWA/*)
        scope="tablet-pwa"
        ;;

      Tablet_Android_APK/*)
        scope="android-apk"
        ;;

      leasingsystem/js/*)
        scope="leasing-js"
        ;;

      leasingsystem/*)
        scope="leasing"
        ;;

      docs/*)
        scope="docs"
        ;;

      *.md)
        scope="docs"
        ;;

      *.sh|*.bat|*.spec|*.iss)
        scope="build"
        ;;

      *)
        scope=$(echo "$f" | cut -d'/' -f1)
        ;;
    esac

    raw_scopes+=("$scope")
  done


  # ── Deduplicate scopes ─────────────────────────────────────────────────────
  local unique_scopes
  unique_scopes=$(
    printf '%s\n' "${raw_scopes[@]}" |
      sort -u |
      tr '\n' ',' |
      sed 's/,$//'
  )

  local count
  count=$(
    printf '%s\n' "${raw_scopes[@]}" |
      sort -u |
      wc -l
  )

  if [ "$count" -gt 3 ]; then
    echo "multi"
  else
    echo "$unique_scopes"
  fi
}


# ── Build summary line ────────────────────────────────────────────────────────
build_summary() {
  local files=("$@")
  local parts=()

  # Count operations
  if [ "${#ADDED[@]}" -gt 0 ]; then
    parts+=("add ${#ADDED[@]} file(s)")
  fi

  if [ "${#MODIFIED[@]}" -gt 0 ]; then
    parts+=("update ${#MODIFIED[@]} file(s)")
  fi

  if [ "${#DELETED[@]}" -gt 0 ]; then
    parts+=("remove ${#DELETED[@]} file(s)")
  fi

  if [ "${#RENAMED[@]}" -gt 0 ]; then
    parts+=("rename ${#RENAMED[@]} file(s)")
  fi


  # Show up to 3 filenames
  local names=()

  for f in "${files[@]:0:3}"; do
    names+=("$(basename "$f")")
  done

  local name_str

  name_str=$(IFS=', '; echo "${names[*]}")

  if [ "${#files[@]}" -gt 3 ]; then
    name_str+=" and $((${#files[@]} - 3)) more"
  fi


  echo "$(IFS=', '; echo "${parts[*]}") → $name_str"
}


# ── Build full commit body ────────────────────────────────────────────────────
build_body() {
  local files=("$@")
  local body=""

  if [ "${#ADDED[@]}" -gt 0 ]; then
    body+="Added:\n"
    body+="$(printf '  + %s\n' "${ADDED[@]}")"
    body+="\n"
  fi

  if [ "${#MODIFIED[@]}" -gt 0 ]; then
    body+="Modified:\n"
    body+="$(printf '  ~ %s\n' "${MODIFIED[@]}")"
    body+="\n"
  fi

  if [ "${#DELETED[@]}" -gt 0 ]; then
    body+="Removed:\n"
    body+="$(printf '  - %s\n' "${DELETED[@]}")"
    body+="\n"
  fi

  if [ "${#RENAMED[@]}" -gt 0 ]; then
    body+="Renamed:\n"
    body+="$(printf '  → %s\n' "${RENAMED[@]}")"
    body+="\n"
  fi

  echo -e "$body"
}


# ── Stage everything ──────────────────────────────────────────────────────────
git add -A


# ── Re-collect after staging ──────────────────────────────────────────────────
mapfile -t ADDED < <(
  git diff --cached --name-only --diff-filter=A
)

mapfile -t MODIFIED < <(
  git diff --cached --name-only --diff-filter=M
)

mapfile -t DELETED < <(
  git diff --cached --name-only --diff-filter=D
)

mapfile -t RENAMED < <(
  git diff --cached --name-only --diff-filter=R
)

ALL_FILES=(
  "${ADDED[@]}"
  "${MODIFIED[@]}"
  "${DELETED[@]}"
  "${RENAMED[@]}"
)


# ── Check again after staging ─────────────────────────────────────────────────
if [ "${#ALL_FILES[@]}" -eq 0 ]; then
  echo "✅ Nothing to commit — working tree is clean."
  exit 0
fi


# ── Generate commit message ──────────────────────────────────────────────────
COMMIT_TYPE=$(determine_type "${ALL_FILES[@]}")
COMMIT_SCOPE=$(build_scope "${ALL_FILES[@]}")
COMMIT_SUMMARY=$(build_summary "${ALL_FILES[@]}")
COMMIT_BODY=$(build_body "${ALL_FILES[@]}")

COMMIT_MSG="${COMMIT_TYPE}(${COMMIT_SCOPE}): ${COMMIT_SUMMARY}"


# ── Preview ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Auto-generated commit message:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  $COMMIT_MSG"
echo ""

if [ -n "$COMMIT_BODY" ]; then
  echo -e "$COMMIT_BODY" | sed 's/^/  /'
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""


# ── Dry run ───────────────────────────────────────────────────────────────────
if $DRY_RUN; then

  echo "Dry run — nothing committed."

  git reset HEAD -- . > /dev/null 2>&1 || true

  exit 0
fi


# ── Confirm ───────────────────────────────────────────────────────────────────
read -r -p "  Commit with this message? [Y/n/e(dit)]: " CONFIRM

CONFIRM="${CONFIRM:-Y}"


case "$CONFIRM" in

  [Yy]*)

    git commit \
      -m "$COMMIT_MSG" \
      -m "$COMMIT_BODY"

    echo ""
    echo "Committed: $COMMIT_MSG"
    ;;


  [Ee]*)

    TMPFILE=$(mktemp /tmp/autocommit_msg.XXXXXX)

    echo "$COMMIT_MSG" > "$TMPFILE"
    echo "" >> "$TMPFILE"
    echo -e "$COMMIT_BODY" >> "$TMPFILE"

    "${EDITOR:-nano}" "$TMPFILE"

    git commit -F "$TMPFILE"

    rm -f "$TMPFILE"

    echo ""
    echo "Committed with edited message."
    ;;


  *)

    echo ""
    echo "Aborted. Changes are still staged."

    exit 0
    ;;

esac


# ── Push ──────────────────────────────────────────────────────────────────────
if $PUSH; then

  echo ""
  echo "Pushing to remote..."

  git push

  echo "Pushed successfully."

fi