#!/usr/bin/env bash
# CI instrumentation around only the public README Quick Start commands.
# Run only in the separate disposable hosted runner defined by the workflow.
set -Eeuo pipefail

if [[ ${GITHUB_ACTIONS:-} != true || ${RUNNER_ENVIRONMENT:-} != github-hosted ]]; then
  echo 'Refusing to start: this walkthrough requires a disposable GitHub-hosted runner.' >&2
  exit 2
fi
if [[ ! ${COMPOSE_PROJECT_NAME:-} =~ ^acr-readme-[0-9]+-[0-9]+$ ]]; then
  echo "Refusing to start without this workflow run's unique Compose project." >&2
  exit 2
fi

ROOT=$(git rev-parse --show-toplevel)
EVIDENCE=${README_EVIDENCE:?README_EVIDENCE must be set by the workflow}
mkdir -p "$EVIDENCE"
cd "$ROOT/implementations/acr-control-plane"

# No Compose override, secrets, fixture executors, inherited deployment settings,
# or cache restoration is supplied by the workflow. Fresh checkout is required.
if [[ -e .env || -e .venv || -n ${COMPOSE_FILE:-} || -n ${COMPOSE_PROFILES:-} ]]; then
  echo 'Refusing a reused environment or Compose override.' > "$EVIDENCE/first-failure.txt"
  exit 2
fi

SEQ=0
COMPOSE_PID=''
COMPOSE_SEQ=''
COMPOSE_REAPED=false
COMPOSE_STARTED=false
CURRENT_STAGE=environment
LAST_LOG=''
printf 'sequence\tstage\tstarted_utc\texit_code\tcommand\toutput\n' > "$EVIDENCE/commands.tsv"
cat > "$EVIDENCE/scope.txt" <<'SCOPE'
Entry points: root README Quickstart and implementations/acr-control-plane/README.md Quick Start.
Fresh checkout on a separate GitHub-hosted Ubuntu runner; Python 3.12; no restored caches.
Only public .env.example settings and the README's dev-operator-key are used.
The documented `docker compose up --build` runs in the background to represent the
first terminal. Startup polling, timeouts, recording and teardown are CI harness
operations, not repairs to the README. No detached/wait flags or Compose overrides.
The runner checkout replaces `git clone`; revision and public-source hashes are recorded.
Console coverage is HTTP page availability only. No browser interaction is tested.
Sample output is recorded and expected ALLOW/DENY/ESCALATE labels checked. This is
not proof of protected downstream effects, approval resolution, audit durability,
all six pillars, production readiness, or full standard conformance.
A failing required command or assertion stops onboarding. No workaround is attempted.
Warmup probe failures are preserved separately and do not by themselves fail startup.
First failing required stage is initially classified unresolved; inspect its raw output.
SCOPE

fail() {
  local code=$1 message=$2
  if [[ ! -e "$EVIDENCE/first-failure.txt" ]]; then
    printf 'stage=%s\nclassification=unresolved\nexit_code=%s\n%s\n' \
      "$CURRENT_STAGE" "$code" "$message" > "$EVIDENCE/first-failure.txt"
  fi
  exit "$code"
}

# Every run records its actual argv, output and exit code. `export` and `source`
# deliberately run in this shell, exactly as in the two public command blocks.
run() {
  local kind=$1; shift
  local started command code
  SEQ=$((SEQ + 1))
  started=$(date -u +%FT%TZ)
  printf -v command '%q ' "$@"
  LAST_LOG="$EVIDENCE/$(printf '%03d' "$SEQ")-${CURRENT_STAGE}.log"
  printf '\n$ %s\n' "$command"
  if "$@" > "$LAST_LOG" 2>&1; then code=0; else code=$?; fi
  cat "$LAST_LOG"
  printf 'exit_code=%s\n' "$code"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$SEQ" "$CURRENT_STAGE" "$started" \
    "$code" "$command" "$(basename "$LAST_LOG")" >> "$EVIDENCE/commands.tsv"
  if [[ $code != 0 && $kind == required ]]; then
    fail "$code" "command=$command; output=$(basename "$LAST_LOG")"
  fi
  return 0
}

record_compose_exit() {
  local code=$1 reason=$2
  # Complete the original start row without changing command execution order.
  awk -F '\t' -v OFS='\t' -v sequence="$COMPOSE_SEQ" -v code="$code" \
    '$1 == sequence {$4 = code} {print}' "$EVIDENCE/commands.tsv" > "$EVIDENCE/commands.tsv.tmp"
  mv "$EVIDENCE/commands.tsv.tmp" "$EVIDENCE/commands.tsv"
  printf 'exit_code=%s\nreason=%s\n' "$code" "$reason" > "$EVIDENCE/compose-up-exit.txt"
  COMPOSE_REAPED=true
}

cleanup() {
  local result=$? code
  trap - EXIT INT TERM
  set +e
  if [[ $result != 0 && ! -e "$EVIDENCE/first-failure.txt" ]]; then
    printf 'stage=%s\nclassification=unresolved\nexit_code=%s\nUnexpected harness failure or cancellation.\n' \
      "$CURRENT_STAGE" "$result" > "$EVIDENCE/first-failure.txt"
  fi
  if [[ $COMPOSE_STARTED == true ]]; then
    CURRENT_STAGE=diagnostics
    run diagnostic timeout 20s docker compose ps -a
    run diagnostic timeout 20s docker compose images
    run diagnostic timeout 20s docker compose logs --no-color --tail 200
    # Only narrowly selected image metadata; never dump container environments.
    run diagnostic timeout 20s docker compose exec -T acr-gateway python --version
    run diagnostic timeout 20s docker compose exec -T acr-gateway python -m pip freeze
    run diagnostic timeout 20s docker compose exec -T postgres postgres --version
    run diagnostic timeout 20s docker compose exec -T redis redis-server --version
    run diagnostic timeout 20s docker compose exec -T opa /opa version
    CURRENT_STAGE=teardown
    run diagnostic timeout --kill-after=10s 90s docker compose down --volumes --remove-orphans
    code=$(tail -n 1 "$EVIDENCE/commands.tsv" | cut -f 4)
    if [[ $code != 0 && $result == 0 ]]; then
      result=$code
      printf 'stage=teardown\nclassification=environment\nexit_code=%s\nDisposable stack teardown failed.\n' \
        "$code" > "$EVIDENCE/first-failure.txt"
    fi
    if [[ $COMPOSE_REAPED == false ]]; then
      # down normally ends the attached Compose process. Bound its final wait.
      for _ in {1..10}; do
        kill -0 "$COMPOSE_PID" 2>/dev/null || break
        sleep 1
      done
      if kill -0 "$COMPOSE_PID" 2>/dev/null; then
        kill -TERM "$COMPOSE_PID"
        for _ in {1..10}; do
          kill -0 "$COMPOSE_PID" 2>/dev/null || break
          sleep 1
        done
        if kill -0 "$COMPOSE_PID" 2>/dev/null; then kill -KILL "$COMPOSE_PID"; fi
      fi
      if wait "$COMPOSE_PID"; then code=0; else code=$?; fi
      record_compose_exit "$code" "Stopped after walkthrough by this run's teardown (not a startup exit)."
    fi
  fi
  printf 'walkthrough_exit_code=%s\n' "$result" > "$EVIDENCE/result.txt"
  if [[ $result == 0 ]]; then
    printf 'PASS: public Compose startup, healthy response, console HTTP, and sample-agent labels.\n' >> "$EVIDENCE/result.txt"
  else
    printf 'FAIL/BLOCKED: see first-failure.txt and commands.tsv; no workaround applied.\n' >> "$EVIDENCE/result.txt"
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

run required git rev-parse HEAD
run required git status --porcelain
run required sha256sum "$ROOT/README.md" README.md .env.example docker-compose.yml
run required uname -a
run required cat /etc/os-release
run required bash --version
run required python --version
run required python -m pip --version
run required docker version
run required docker compose version
run required curl --version
printf 'cwd=%s\nrun_id=%s\nrun_attempt=%s\n' "$PWD" "$GITHUB_RUN_ID" "$GITHUB_RUN_ATTEMPT" > "$EVIDENCE/context.txt"

CURRENT_STAGE=readme-environment
run required cp .env.example .env
run required export OPERATOR_API_KEYS_JSON='{"dev-operator-key":{"subject":"dev-operator","roles":["agent_admin","approver","security_admin","auditor","killswitch_operator"]}}'
run required export SERVICE_OPERATOR_API_KEY=dev-operator-key

CURRENT_STAGE=startup
COMPOSE_STARTED=true
COMPOSE_STARTED_AT=$(date -u +%FT%TZ)
SEQ=$((SEQ + 1))
COMPOSE_SEQ=$SEQ
printf '%s\tstartup\t%s\tpending\tdocker compose up --build\tcompose-up.log\n' \
  "$COMPOSE_SEQ" "$COMPOSE_STARTED_AT" >> "$EVIDENCE/commands.tsv"
printf '\n$ docker compose up --build\n'
docker compose up --build > "$EVIDENCE/compose-up.log" 2>&1 &
COMPOSE_PID=$!
printf 'started_utc=%s\npid=%s\ncommand=docker compose up --build\n' \
  "$COMPOSE_STARTED_AT" "$COMPOSE_PID" > "$EVIDENCE/compose-up-start.txt"

# The README says to continue when the gateway is healthy. Preserve each probe,
# but do not invent application settings to make it start. Allow first image builds.
deadline=$((SECONDS + 720))
ready=false
while (( SECONDS < deadline )); do
  if ! kill -0 "$COMPOSE_PID" 2>/dev/null; then
    if wait "$COMPOSE_PID"; then code=0; else code=$?; fi
    record_compose_exit "$code" 'Exited before the gateway became reachable.'
    fail 1 "Compose exited early with code $code; output=compose-up.log"
  fi
  printf '\n%s $ curl --fail --silent --show-error --max-time 5 http://localhost:8000/acr/health\n' \
    "$(date -u +%FT%TZ)" >> "$EVIDENCE/readiness-probes.log"
  if curl --fail --silent --show-error --max-time 5 http://localhost:8000/acr/health \
    >> "$EVIDENCE/readiness-probes.log" 2>&1; then
    printf '\nexit_code=0\n' >> "$EVIDENCE/readiness-probes.log"
    ready=true
    break
  else
    printf '\nexit_code=%s\n' "$?" >> "$EVIDENCE/readiness-probes.log"
  fi
  sleep 5
done
[[ $ready == true ]] || fail 124 'Gateway did not become reachable within 720 seconds; see compose-up.log and readiness-probes.log.'

CURRENT_STAGE=health
run required curl --max-time 20 http://localhost:8000/acr/health
# Capture a clean JSON body, then check the README's stated response fields.
run required curl --fail --silent --show-error --max-time 20 --output "$EVIDENCE/health.json" http://localhost:8000/acr/health
run required python -c 'import json,sys; h=json.load(open(sys.argv[1])); assert h.get("status")=="healthy" and h.get("version")=="1.1.0" and h.get("env")=="development", h; print(h)' "$EVIDENCE/health.json"

CURRENT_STAGE=console-http
run required curl --fail --location --silent --show-error --max-time 20 --dump-header "$EVIDENCE/console-headers.txt" --output "$EVIDENCE/console.html" http://localhost:8000/console
run required grep -iE '^content-type:.*text/html' "$EVIDENCE/console-headers.txt"
run required grep -qi '<html' "$EVIDENCE/console.html"

CURRENT_STAGE=sample-install
run required timeout --kill-after=10s 45s python -m venv .venv
run required source .venv/bin/activate
run required timeout --kill-after=10s 240s python -m pip install -e .
run required python --version
run required python -m pip freeze
run required export ACR_OPERATOR_API_KEY=dev-operator-key
CURRENT_STAGE=sample-agent
run required timeout --kill-after=10s 90s python examples/sample_agent/agent.py
sample_log=$LAST_LOG
run required python -c 'import pathlib,sys; t=pathlib.Path(sys.argv[1]).read_text(); expected=["[ALLOW] query_customer_db", "[ALLOW] send_email", "[ALLOW] create_ticket", "[DENY] delete_customer", "[ESCALATE] issue_refund"]; missing=[x for x in expected if x not in t]; assert not missing, f"Missing documented sample outcomes: {missing}"; print("Observed expected sample decision labels; downstream effects and full pillar claims are not validated.")' "$sample_log"
