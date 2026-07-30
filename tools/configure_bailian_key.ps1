$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "配置阿里云百炼 API Key" -ForegroundColor Cyan
Write-Host "密钥仅保存到当前 Windows 用户的环境变量，不会写入项目文件或数据库。"
$secureKey = Read-Host "请输入百炼通用 API Key（输入内容不会显示）" -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw "API Key 不能为空。"
    }
    if (-not $plainKey.StartsWith("sk-")) {
        throw "API Key 格式不正确，应以 sk- 开头。"
    }
    [Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", $plainKey, [EnvironmentVariableTarget]::User)
    Write-Host "配置完成。请回到管理员页面刷新，然后测试连接。" -ForegroundColor Green
}
finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    Remove-Variable plainKey -ErrorAction SilentlyContinue
}
