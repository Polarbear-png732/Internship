$projectPath = "D:\ioeyu\Internship\HeNan\web_app1"
$excludedFolders = @("__pycache__", "logs", ".git", "node_modules", ".venv", "venv")
$excludedFiles = @("vue.global.js")
$includedExtensions = @("*.py", "*.js", "*.html", "*.css", "*.json", "*.txt", "*.vue", "*.ts", "*.tsx", "*.jsx")

$totalLines = 0
$fileCount = 0
$folderStats = @{}
$fileResults = @()

Get-ChildItem -Path $projectPath -Recurse -File | Where-Object {
    $exclude = $false
    foreach ($folder in $excludedFolders) {
        if ($_.FullName -like "*\$folder\*" -or $_.FullName -like "*\$folder") {
            $exclude = $true
            break
        }
    }
    -not $exclude
} | Where-Object {
    $include = $false
    foreach ($ext in $includedExtensions) {
        if ($_.Name -like $ext) {
            $include = $true
            break
        }
    }
    $include
} | Where-Object {
    $excludeFile = $false
    foreach ($file in $excludedFiles) {
        if ($_.Name -eq $file) {
            $excludeFile = $true
            break
        }
    }
    -not $excludeFile
} | ForEach-Object {
    $lines = (Get-Content $_.FullName | Measure-Object -Line).Lines
    $totalLines += $lines
    $fileCount++
    
    $relativePath = $_.FullName.Replace($projectPath, "").TrimStart('\')
    $folderName = $relativePath.Split('\')[0]
    if ($relativePath.Contains('\')) {
        $folderName = $relativePath.Split('\')[0]
    } else {
        $folderName = "[root]"
    }
    
    if (-not $folderStats.ContainsKey($folderName)) {
        $folderStats[$folderName] = @{ Lines = 0; Files = 0 }
    }
    $folderStats[$folderName].Lines += $lines
    $folderStats[$folderName].Files++
    
    $fileResults += [PSCustomObject]@{
        Folder = $folderName
        File = $relativePath
        Lines = $lines
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         Code Statistics Report         " -ForegroundColor Cyan
Write-Host "      Project: $projectPath             " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "--- Statistics by Folder ---" -ForegroundColor Yellow
$folderOutput = @()
foreach ($key in $folderStats.Keys) {
    $folderOutput += [PSCustomObject]@{
        Folder = $key
        Files = $folderStats[$key].Files
        Lines = $folderStats[$key].Lines
    }
}
$folderOutput | Sort-Object Lines -Descending | Format-Table -AutoSize

Write-Host "--- File Details ---" -ForegroundColor Yellow
$fileResults | Sort-Object { $_.Folder }, { $_.Lines } -Descending | Format-Table -AutoSize

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Total Files: $fileCount" -ForegroundColor Yellow
Write-Host "Total Lines: $totalLines" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
