# /upgrade-tls-libs

Upgrade the tls-client native library to a new version.

**Usage:** `/project:upgrade-tls-libs <new_version>`  
**Example:** `/project:upgrade-tls-libs 1.15.0`

## Steps to perform

1. **Validate the release exists.** Fetch `https://api.github.com/repos/bogdanfinn/tls-client/releases/tags/v$ARGS` and verify the response is not a 404. List the assets.

2. **Create new branch.** Find the highest existing `upd-libs-X.Y.Z` local branch. Create a new branch `upd-libs-$ARGS` from it:
   ```
   git checkout upd-libs-<current-highest>
   git checkout -b upd-libs-$ARGS
   ```

3. **Update `scripts/update_shared_libraries.py`.** Change `shared_library_version = "<old>"` to `shared_library_version = "$ARGS"`.

4. **Download new binaries.** Run:
   ```
   cd scripts && python update_shared_libraries.py
   ```
   Confirm all 7 files in `tls_client/dependencies/` are updated (non-zero size). If any download fails (HTTP error or tiny file), report which file failed and stop.

5. **Diff new identifiers.** Fetch:
   ```
   https://raw.githubusercontent.com/bogdanfinn/tls-client/refs/tags/v$ARGS/profiles/profiles.go
   ```
   Extract all string values inside `ClientIdentifier(...)` or quoted identifier patterns. Compare against the current `tls_client/settings.py` `ClientIdentifiers` list. Find new ones not yet present.

6. **Update `tls_client/settings.py`.** Append new identifiers in the correct section (Chrome, Brave, Safari, Firefox, etc.) after the existing entries for that browser family.

7. **Update default `client_identifier` in `tls_client/sessions.py`.** Set to the highest `chrome_NNN` (no PSK suffix) from the updated settings list.

8. **Bump `tls_client/__version__.py`.** Set `__version__` to `1.0.1.dev<NNNN>` where `<NNNN>` = version digits without dots (e.g. `1.15.0` → `1150`).

9. **Verify.** Run the verification script from the repo root:
   ```
   python scripts/verify_tls.py
   ```
   The script checks:
   - All 7 dependency binaries exist and are ≥ 1 MB
   - Key new identifiers are present in `ClientIdentifiers`
   - A live request with the default `chrome_146` identifier succeeds against `https://tls.peet.ws/api/all` and prints the JA3 hash + H2 Akamai fingerprint

   If any check fails, fix the issue before committing.

10. **Commit.** Stage all changed files and commit with message:
    ```
    update libs to $ARGS
    ```

11. **Report summary.** List: new identifiers added, new default client identifier, binaries updated, JA3 hash from verification.
