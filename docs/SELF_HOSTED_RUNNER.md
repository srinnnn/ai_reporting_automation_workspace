# Self-hosted Runner

Status: `USER_ACTION_REQUIRED`

Required labels:

- `self-hosted`
- `windows`
- `x64`
- `middle-platform-prod-native`

Required capabilities:

- repository checkout
- Python 3.12
- Node.js 20.19+
- npm
- access to `C:\MiddlePlatformDeploy`
- access to `C:\MiddlePlatformData`
- access to `127.0.0.1:8785`

PR jobs must not run on this runner. Only trusted `deploy` and `rollback` workflows target it.

Register Windows startup after a successful release deploy:

```powershell
powershell.exe -ExecutionPolicy Bypass -File C:\MiddlePlatformDeploy\register-startup-task.ps1
```

If Task Scheduler registration requires elevation, status is `USER_ACTION_REQUIRED: REGISTER_WINDOWS_STARTUP_TASK`.

Do not store registration tokens, credentials, cookies, or production secrets in the repository.
