#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  autocommit.sh — FULLY AUTOMATIC: one commit per changed file, then push.
#  No prompts, no typing. Just run it.
#
#  For each changed file it makes a commit:  type(scope): <action> <path>
#    type   = auto-detected (fix / feat / docs / style / chore / refactor)
#    scope  = auto-detected from the path (ui, utils, components, tablet-js, ...)
#    action = add / update / remove / rename (from the file's git status)
#
#  Usage:
#    ./autocommit.sh            # commit every changed file + push
#    ./autocommit.sh --no-push  # commit only, don't push
#    ./autocommit.sh --dry-run  # show what it WOULD do, change nothing
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail   # NOTE: intentionally no `-e` — one failed git command must
                   # not abort the whole run; we handle failures per-command.

# ── Options ──────────────────────────────────────────────────────────────────
PUSH=true
DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --no-push) PUSH=false ;;
    --dry-run) DRY_RUN=true; PUSH=false ;;
    *) echo "❌ Unknown option: $arg"; echo "Usage: $0 [--no-push|--dry-run]"; exit 1 ;;
  esac
done

# ── Must be inside a git repo ────────────────────────────────────────────────
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo "❌ Not a git repository. Run this from inside your project folder."
  exit 1
fi

# ── Clear a STALE index.lock (only if no git process is actually running) ─────
clear_stale_lock() {
  local lock; lock="$(git rev-parse --git-dir)/index.lock"
  [ -f "$lock" ] || return 0
  if pgrep -x git >/dev/null 2>&1; then
    echo "❌ .git/index.lock exists and a git process is running."
    echo "   Close the other git/editor operation, then re-run."
    exit 1
  fi
  echo "⚠️  Removing stale .git/index.lock left by a previous interrupted run."
  rm -f "$lock"
}
clear_stale_lock

# Ignore permission-bit-only changes (e.g. 100644→100755) so they don't create
# noisy content-less commits.
git config core.fileMode false >/dev/null 2>&1 || true

# ── Push EVERY unpushed commit on the current branch ─────────────────────────
do_push() {
  $PUSH || return 0
  local branch unpushed push_args
  branch=$(git rev-parse --abbrev-ref HEAD)
  if git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' >/dev/null 2>&1; then
    unpushed=$(git rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo 0)
    push_args=(origin "$branch")
  else
    unpushed=$(git rev-list --count HEAD 2>/dev/null || echo 0)
    push_args=(-u origin "$branch")
  fi
  echo ""
  if [ "$unpushed" -gt 0 ]; then
    echo "Pushing $unpushed commit(s) to origin/$branch..."
    if git push "${push_args[@]}"; then
      echo "✅ Pushed successfully."
    else
      echo "❌ Push FAILED (commits are safe locally)."
      echo "   • remote ahead → git pull --rebase && git push"
      echo "   • auth/network → fix, then re-run ./autocommit.sh"
      exit 1
    fi
  else
    echo "Nothing to push — origin/$branch is already up to date."
  fi
}

# ── Auto commit TYPE for a file ──────────────────────────────────────────────
determine_type() {
  local f="$1"
  case "$f" in
    *.md|docs/*)                                           echo docs;  return ;;
    *.css|*.scss|*.less)                                   echo style; return ;;
    setup*.py|*.cfg|*.ini|*.toml|*.yml|*.yaml|Makefile|*.sh|*.bat|*.iss|*.spec)
                                                           echo chore; return ;;
  esac
  # Peek at the staged diff to guess fix vs feat.
  if git diff --cached -- "$f" 2>/dev/null | grep -qiE '^\+.*(fix|bug|error|crash|broken|patch)'; then
    echo fix; return
  fi
  if git diff --cached -- "$f" 2>/dev/null | grep -qiE '^\+.*(add|new|feat|feature|implement|create)'; then
    echo feat; return
  fi
  echo refactor
}

# ── Auto scope from the path ─────────────────────────────────────────────────
build_scope() {
  case "$1" in
    Catering_Present/*/components/*) echo components ;;
    Catering_Present/*/ui/*)         echo ui ;;
    Catering_Present/*/utils/*)      echo utils ;;
    Catering_Present/*/assets/*)     echo assets ;;
    Catering_Present/*)              echo desktop-app ;;
    Tablet_PWA/frontend/js/*)        echo tablet-js ;;
    Tablet_PWA/frontend/*)           echo tablet-pwa ;;
    Tablet_PWA/backend/*)            echo tablet-backend ;;
    Tablet_PWA/*)                    echo tablet-pwa ;;
    Tablet_Android_APK/*)            echo android-apk ;;
    docs/*|*.md)                     echo docs ;;
    *.sh|*.bat|*.spec|*.iss)         echo build ;;
    *)                               echo "$1" | cut -d'/' -f1 ;;
  esac
}

# ── Collect changed entries (staged + unstaged + untracked) ──────────────────
mapfile -t STATUS_LINES < <(git status --porcelain)

if [ "${#STATUS_LINES[@]}" -eq 0 ]; then
  echo "✅ Nothing to commit — working tree is clean."
  do_push          # still push commits stranded by an earlier run
  exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ${#STATUS_LINES[@]} changed file(s) — auto-committing one commit each."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

COMMITTED_COUNT=0
FAILED_COUNT=0

for line in "${STATUS_LINES[@]}"; do
  STATUS_CODE="${line:0:2}"
  REST="${line:3}"

  # Handle renames ("old -> new"); otherwise a single path.
  if [[ "$REST" == *" -> "* ]]; then
    OLD_PATH="${REST%% -> *}"; NEW_PATH="${REST##* -> }"
    PATHS=("$OLD_PATH" "$NEW_PATH")
    ACTION="rename"; TARGET="$NEW_PATH"
    DESC="rename ${OLD_PATH} to ${NEW_PATH}"
  else
    # git quotes paths containing special chars — strip surrounding quotes.
    REST="${REST%\"}"; REST="${REST#\"}"
    PATHS=("$REST"); TARGET="$REST"
    case "$STATUS_CODE" in
      "??"|*A*) ACTION="add" ;;
      *D*)      ACTION="remove" ;;
      *R*)      ACTION="rename" ;;
      *)        ACTION="update" ;;
    esac
    DESC="${ACTION} ${REST}"
  fi

  TYPE=$(determine_type "$TARGET")
  SCOPE=$(build_scope "$TARGET")
  COMMIT_MSG="${TYPE}(${SCOPE}): ${DESC}"

  if $DRY_RUN; then
    echo "  would commit → $COMMIT_MSG"
    continue
  fi

  # Stage just this file/pair, then commit just it.
  git add -A -- "${PATHS[@]}" 2>/dev/null

  if git commit -q -m "$COMMIT_MSG" -- "${PATHS[@]}" 2>/dev/null; then
    echo "  ✅ $COMMIT_MSG"
    COMMITTED_COUNT=$((COMMITTED_COUNT + 1))
  else
    echo "  ❌ FAILED: $COMMIT_MSG"
    git reset -q HEAD -- "${PATHS[@]}" >/dev/null 2>&1 || true
    FAILED_COUNT=$((FAILED_COUNT + 1))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if $DRY_RUN; then
  echo "  Dry run complete — nothing was committed."
else
  echo "  Done: $COMMITTED_COUNT commit(s) made, $FAILED_COUNT failed."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

do_push
