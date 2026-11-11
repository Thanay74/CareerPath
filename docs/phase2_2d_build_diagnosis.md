# CareerPath Phase 2.2D — Vite Build Diagnosis

## Finding

**Most likely cause: sandbox filesystem enforcement affecting Vite/Rollup path resolution. Confidence: high for an environment restriction; the precise enforcement layer is not established.** No source or Vite configuration defect was found that explains the reported `EPERM`.

## Evidence

- The repeated sandbox build failure recorded in `docs/phase2_1_high_priority_remediation_report.md`, `docs/phase2_1_build_recovery_and_catalog_release_report.md`, and `docs/phase2_2c_integration_verification_report.md` is `EPERM` while Vite realpath-resolves `frontend/src/main.jsx`.
- The Phase 2.1 build recovery report says direct Node `statSync`, `lstatSync`, and `realpathSync` succeeded in the sandbox, while the same production build passed outside that sandbox and transformed 30 modules. That is historical evidence from the earlier run, not a new Phase 2.2D build result.
- In this read-only inspection, Node `v24.19.0` again resolved the exact entry path and reported a regular file; PowerShell `Resolve-Path` also succeeded. The path casing matches `frontend/index.html`'s `/src/main.jsx` reference. `lstatSync` reports that it is not a symlink.
- The file and parent ACLs grant the current user `FullControl`; no permission change is supported. Parent directories are owned by the Codex sandbox account, and the entry file by the offline sandbox account. This is consistent with a sandbox boundary, but does not identify its internal mechanism.
- `frontend/vite.config.js` only sets the dev-server API proxy. There is no custom root, alias, build input, or filesystem allowance that redirects entry resolution.
- `frontend/node_modules/` exists; Node, npm, and installed Vite versions were read without reinstalling dependencies. `pnpm-lock.yaml` resolves Vite 5.4.21. The Vite 5.4.21 package satisfies the declared `^5.4.14` range.

## Causes not established

- No evidence supports a symlink, path-case mismatch, missing entry, or custom Vite root/configuration issue.
- No antivirus or file-locking diagnostics were available. Those remain hypotheses, not findings.
- Direct filesystem metadata access succeeding does not explain why the bundler's resolver is denied. The prior outside-sandbox success supports—but does not prove—the sandbox explanation for this exact current checkout/run.

## Build decision and next verification

### Successful Windows build (2026-10-22)

The project owner supplied evidence of a successful production build in the approved Windows environment, outside the sandbox:

```powershell
npm.cmd run build -- --outDir "C:\Users\THANAY\Documents\Codex\.phase2_2d_frontend_build"
```

- Result: **PASS** with Vite 5.4.21; 30 modules transformed in 894 ms.
- `Test-Path` confirmed `C:\Users\THANAY\Documents\Codex\.phase2_2d_frontend_build\index.html` exists; `Get-ChildItem` confirmed `index.html` and `assets/` in the output directory.
- This output path is outside the project and outside `frontend/dist/`. The build evidence does not indicate that the pre-existing `frontend/dist/` was modified.
- This records the supplied Windows verification; the build was not rerun in this sandbox. The historical sandbox `EPERM` remains documented, and its precise underlying enforcement mechanism remains unconfirmed.

The earlier sandbox build was not retried in this phase because the sandbox boundary remained in effect. The successful Windows run resolves the production compilation check for that approved environment, but does not verify browser behavior, MySQL integration, or production deployment.

The original isolated-output command recorded for future verification was:

```powershell
cd C:\Users\THANAY\Documents\Codex\2026-09-29\files-pasted-by-the-user-build\outputs\CareerPath\frontend
npm run build -- --outDir C:/Users/THANAY/Documents/Codex/.phase2_2d_frontend_build
```

Do not move the checkout, alter ACLs, disable security controls, reinstall packages, or overwrite the existing `frontend/dist/` as a workaround.
