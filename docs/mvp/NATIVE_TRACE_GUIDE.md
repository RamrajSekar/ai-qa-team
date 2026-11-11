# Scoped Windows startup trace

Prepared 2026-11-02. Process Monitor 4.12 was downloaded from Microsoft's official Sysinternals archive to ignored tmp/native-tools/procmon. Authenticode status Valid, signer Microsoft Corporation. No capture or driver launch has been performed by the agent. The current execution token is not an elevated administrator; a user-approved UAC launch is required for the tracer. Browser/runner processes must remain non-admin.

## Start with capture stopped

In PowerShell, launch the downloaded tracer (UAC approval required):

```powershell
Start-Process -FilePath 'F:\ai-qa-team\tmp\native-tools\procmon\Procmon64.exe' -ArgumentList '/NoConnect' -Verb RunAs
```

Review/accept Microsoft's license if prompted. Confirm capture is stopped before proceeding. /NoConnect prevents automatic initial capture. Do not run a generic unfiltered trace.

## Configure a narrow capture

1. Open Filter → Filter (Ctrl+L). Remove broad Include rules left from earlier tasks.
2. Add **Image Path is** `F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chrome-win64\chrome.exe` → Include. This covers that task binary's browser/renderers/helpers, not all normal Chrome.
3. Enable **Filter → Drop Filtered Events** before starting capture. Keep file-system, registry and process/thread activity enabled. Do not limit capture to ACCESS DENIED only: successful operations and time gaps are necessary evidence. No boot logging or profiling of unrelated processes.
4. Clear old events (Ctrl+X), start capture (Ctrl+E), then run exactly one probe below from a **normal non-admin terminal**. Stop capture (Ctrl+E) immediately when the probe exits. If that binary is already used by an unrelated process, stop and refine the filter to task-owned PIDs before capturing.
5. Save displayed/included events privately under `F:\ai-qa-team\tmp\m1a-native-fresh.pml`. Keep raw PML local: it can contain command lines, registry values and personal paths. Do not upload it or put it in API/UI responses.

```powershell
cd F:\ai-qa-team\visual-runner
..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe tests/startup_series.py --chrome 'F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chrome-win64\chrome.exe' --driver 'F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chromedriver-win64\chromedriver.exe' --headless 1 --headed 0 --output '../tmp/m1a-native-fresh-summary.json'
```

Do not launch a second browser if cleanup is reported unverified. Resolve that observation first.

## Cached control

After fresh cleanup, replace the Image Path filter with the cached binary's exact path, clear the old trace, and capture one control using the **same driver**:

```powershell
..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe tests/startup_series.py --chrome 'C:\Users\ram\.cache\puppeteer\chrome\win64-146.0.7680.31\chrome-win64\chrome.exe' --driver 'F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chromedriver-win64\chromedriver.exe' --headless 1 --headed 0 --output '../tmp/m1a-native-cached-summary.json'
```

Save this filtered control locally as tmp/m1a-native-cached.pml. Capture neither normal Chrome nor a mixed-version browser/driver pair. No full 10/5 series, retries, antivirus exclusion, sandbox bypass or warm-up.

## Interpret and share safely

Correlate the sanitized harness run ID/stage timings with Process Start, Load Image and file/registry operations for that browser and its renderer processes. Compare long-duration operations/gaps and repeated failures with the cached control. ACCESS DENIED, NAME NOT FOUND and background warnings alone do not establish cause; inspect the associated operation/stack and compare controls. A restricted image-path filter may omit a helper service responsible for waiting; identify the task relationship before broadening any filter.

Share only a sanitized summary: relative times, operation, result, duration and task-relative filename/module. Preserve failures and distinguish process exits before cleanup from exits caused by cleanup. No credentials, full command lines, registry data or unrelated paths. Native trace analysis must precede a claimed Windows/security fix. Close Process Monitor after saving the task captures.
