# Rollback

Current production rollback is Windows native and must select an existing release directory:

```text
C:\MiddlePlatformDeploy\releases\<commit-sha>
```

Minimum rollback evidence:

- previous successful SHA
- target rollback SHA
- health check result
- readiness check result
- version SHA check result
- operator or workflow run id

Automatic rollback is implemented in `ops/windows-native/deploy-release.ps1`: if the new release fails health, readiness, or version verification, it restores `previous_successful_sha`.

Manual rollback uses:

```powershell
.\ops\windows-native\rollback.ps1 -TargetSha <existing-release-sha>
```

Database backups are created before deployment when the SQLite file exists. Application rollback and database rollback are separate decisions; the rollback script does not automatically restore an older database.
