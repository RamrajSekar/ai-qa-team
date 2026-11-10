# Isolated Linux mechanical smoke spike

Verified in Podman 6.1.4 on 2026-11-02: image built by the user, then

three agent-run sequential headless workflows completed with three PNGs each.

Cancellation was verified by the user; agent-run forced-stop and test-only timeout

checks exited as expected. See current results below. This is a small local

mechanical baseline, not cloud or customer readiness.

The existing Windows UI/API adapter remains unchanged and Windows latency is unresolved.

No M1B, AI, Mongo connection, cloud deployment or customer URL support is included.

Uses the existing Robot keywords, sample/proxy, direct HTTPX protocol and fixed

fixture actions. A separate container entrypoint injects Linux process-group

cleanup; Windows retains its Job Object default. Container termination is the final

process boundary, including after forced supervisor termination. This is not a

multi-host lease or durable orchestration implementation. Browser observations on

Linux explicitly report unavailable; do not interpret this as confirmed cleanup.

## Build and run (PowerShell at repository root)

Prerequisite: an operational Linux amd64 Docker or Podman engine. Installing an

engine/WSL distribution is a separate machine setup step. Substitute `podman` for

`docker` when available. Build requires network access to Debian, PyPI and official

CfT storage. Retain build logs and image ID. Historical 146 pin is intentional for

OS comparison, not a current-security recommendation; test/promote newer releases

separately. Complete browser bundle and matched driver are downloaded; Python

runtime dependencies are pinned. Base tag/apt packages remain mutable: resolve

digests and archive an SBOM/license review before any deployed image promotion.

```powershell

docker build --platform linux/amd64 -f visual-runner/linux/Dockerfile -t ai-qa-m1a-linux:local visual-runner

docker volume create ai-qa-m1a-output

docker run --name ai-qa-m1a-linux --network none --shm-size 512m --memory 2g --cpus 2 --pids-limit 256 --mount source=ai-qa-m1a-output,target=/output ai-qa-m1a-linux:local

# After exit: retain the container until collecting the evidence.

New-Item -ItemType Directory -Force tmp/m1a-linux-evidence | Out-Null

docker cp ai-qa-m1a-linux:/output/. tmp/m1a-linux-evidence

docker inspect --format '{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}}' ai-qa-m1a-linux

```

No ports are published. Runtime has no external network; its synthetic app and

driver communicate over container loopback. Do not mount Docker socket, home,

credentials or repository. Output includes per-run state.json and three PNGs on

completion; it is private local diagnostic data, not a public artifact service.

The fixed config contains only container executable paths. Unknown caller arguments

are rejected. Only one task-owned container should run at a time; host-wide/multi-

container scheduling is deliberately absent from this standalone spike.

Cancellation in a second terminal: `docker stop --time 20 ai-qa-m1a-linux`.

The entrypoint writes cancellation, maintains heartbeat, and grants bounded cleanup.

Each attempt needs a new container name or removal of the **stopped task container**.

The UUID output directory prevents replay/overwriting previous evidence. No workflow

retry occurs. A 90-second run budget and bounded outer deadline apply.

Run non-root with the Chrome sandbox enabled. This definition installs the bundled

setuid sandbox, but host policies/user namespaces can prevent it from operating.

Do not add `--no-sandbox`, privileged mode, broad capabilities or disable host

security to make it pass. Capture the failure and evaluate that host configuration.

Cloud Run sandbox feasibility is **unverified**, as are fonts/coordinates/resource

limits. Do not deploy this image merely because it builds.

## Verification gate

First build/pip check/dependency guard/version check, then one headless smoke with

three PNGs, a separate cancellation, forced container stop and timeout. Inspect

exit/OOM status and absence of remaining task container processes. A completed

workflow says **Browser smoke check completed**, never a QA business pass.

Repeat only a bounded Linux baseline after the first successful smoke. Existing

Windows 10/5 results remain historical failures, not replaced by this spike.

Cloud follow-up requires a designated development GCP project, billing/resource

approval, private artifact storage and an explicit deployment scope. No cloud deployment or project configuration was performed for this task. API/Mongo integration and cloud retries,

leases, evidence upload and cancellation are separate gates.

## Actual Linux verification — 2026-11-02

Image ID: `0ed93d0c910bb9a8769f34b3bd8b74e303aa24171292b15875162589ddec00dd`.

Podman client/server 6.1.4, Linux/amd64 server. Matched CfT/driver 146.0.7680.31.

User build output confirms pip/dependency/version build gates succeeded. User manual

normal run: completed, exit 0, no OOM, three PNG files; separate cancellation:

terminal cancelled, exit 1, no OOM. These are user-supplied evidence, not agent reruns.

Agent real-container checks: normal baseline **3/3 first-attempt completions**,

21.156/20.656/18.062 seconds including Podman control/copy overhead; three PNGs each.

One forced-stop attempt: running session observed, SIGKILL, exit 137; persisted state

remains running because no external reconciler exists. One test-only two-second

supervisor deadline: terminal timed_out, exit 1, 9.438 seconds including overhead.

All five containers exited, PID zero, no OOM; final running-container list empty.

No per-browser process observation is available. No production cleanup guarantee.

First baseline filled/confirmation PNGs visually inspected: synthetic inputs and $60

confirmation visible; this manual inspection is not an automated assertion engine.

Forced-stop artifact collection first failed because profile SingletonCookie is a

Linux symlink. The harness was corrected to copy only fixed state.json/PNG names;

the **same stopped attempt** was recovered, never replayed. Whole-output copying

can still hit that Windows privilege issue after forced kill. Prefer the harness.

Stopped task containers/volumes are retained for diagnosis, not automatically pruned.

Reproduce from repository root (new output directory required):

```powershell

& .\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe visual-runner/tests/linux_container_checks.py --podman "$env:LOCALAPPDATA\Programs\Podman\podman.exe" --output tmp/m1a-linux-checks-next

# Mocked process/dependency guard unit checks, from visual-runner:

..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe -m unittest discover -s tests -p test_linux_spike.py -v

```

The harness refuses other running containers, runs fixed cases sequentially with

network none and limits, preserves stopped containers/evidence and does not retry

browser workflows. Timeout is a diagnostic-only entrypoint override using the same

supervisor with a two-second deadline; normal image/API deadlines are unchanged.

It is not a test of the normal entrypoint's outer 100-second watchdog or a hung

browser. Full image dependency graph is checked during build; unit checks use mocks.

Still NOT RUN: API/UI/Mongo Linux dispatch, container-external stale-run reconciliation,

outer watchdog fault injection, cloud sandbox/network/artifact/lease behavior,

production durability, current-release security validation and licensing/SBOM review.

Windows startup latency is unresolved. M1B remains deferred.



## Guard image: local reconciliation and unchanged outer watchdog

Build separately; the original tested :local image is retained:

```powershell
podman build --platform linux/amd64 -f visual-runner/linux/Dockerfile -t ai-qa-m1a-linux:guard visual-runner
& .\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe -X utf8 visual-runner/tests/linux_guard_checks.py --podman "$env:LOCALAPPDATA\Programs\Podman\podman.exe" --output tmp/m1a-linux-guard-next
```

This opt-in harness creates only labeled task containers and dedicated named
volumes, refuses other running containers, tests forced termination/reconciliation,
a frozen supervisor and completed-state preservation in sequence. It freezes only
the container's child supervisor, not the host or Podman VM. The actual normal
100-second parent deadline plus ten-second grace remains unchanged. This tests
containment of an unresponsive supervisor; it is not a reproduction of a Chrome
hang. Helpers perform no browser actions and run without external networking.

Local control command for a stopped, harness-managed run:

```powershell
& .\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe -X utf8 visual-runner/tests/linux_reconcile_control.py --podman "$env:LOCALAPPDATA\Programs\Podman\podman.exe" --container <m1a-guard-container-name> --run <32-character-run-id>
```

The controller requires the exact managed name/label, exited status, PID zero and
its dedicated output volume; the helper uses the original immutable image ID.
It refuses active/unmanaged containers. It changes only nonterminal state to
interrupted, records the exit provenance/no replay, and preserves existing evidence
and terminal metadata. Repeating reconciliation is a no-op. No browser is restarted.
The entrypoint now also preserves diagnostics/screenshots when finalizing a child
exit; an outer-watchdog forced termination records timed_out.

Single local operator only: do not manually restart the stopped container during
reconciliation. There is no cross-controller fencing or distributed lease, automatic
startup sweep, Mongo persistence or API artifact authorization in this standalone
tool. This helper is intentionally not exposed through the web application.
Raw profiles may remain in the dedicated volume after forced termination; private
retention/deletion is still manual. Keep those volumes local and do not publish them.
No browser-specific cleanup observation or production durability is established.


Guard verification results (2026-11-02): image ID
`ec46ed0f56ad43fcbc07122fbe5450e42bd755f9a7862027ba57556a2d6723fc`.
Three real cases passed, one first attempt each: forced-stop reconciliation,
frozen-supervisor outer watchdog (111.375s, timed_out/exit 1), normal completion
(14.391s, completed/exit 0/three screenshot references). All exited/PID zero/no OOM;
active reconciliation rejected in each case; terminal records byte-identical;
second reconciliation no-op. Eight focused unit tests passed. Detailed evidence:
[guard report](../../docs/mvp/evidence/linux-guard-checks-nov02.json).


## Backend batch adapter (2026-11-02)

New separate :batch image entrypoint `python -m linux.batch` consumes only the fixed
server-owned manifest in its private output volume. The API owns creation/start,
two-slot dispatch and private evidence collection. Do not start it without a valid
manifest or reuse an existing started batch volume. One fresh supervisor/session per
case, up to ten sequential cases, with cleanup uncertainty ending the container.
[Canonical models, build/settings and tests](../../docs/mvp/EXECUTION_CONTRACTS.md).
Successful image ID: b5d5e83e29ec11e6d2e34ce387f1e2f6f7108acdbd31bf22d96e4418a4dbb66c.
Real fixture verified ten cases and two overlapping batches; ASGI authentication is
a double. Original :local and :guard image tags remain; no UI or cloud deployment.


## Per-check dispatch from the API (2026-11-02)

New batches use one container per check. The API sends this existing v1 batch
entrypoint a manifest containing exactly one server-owned case, with its own
volume/profile and unchanged 90-second case/110-second outer bounds. The same
immutable :batch image is reused; no dependency or protocol rebuild is needed.
The API aggregates parent results and owns the configurable five-slot default pool.
Old sequential batch containers drain before this pool launches. See
../../docs/mvp/EXECUTION_CONTRACTS.md for configuration, verification and limitations.
Five configured slots do not establish sufficient VM memory/CPU or successful
parallel browser startup; retain failures and measure actual overlapping sessions.
