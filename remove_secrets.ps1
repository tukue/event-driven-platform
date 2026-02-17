# PowerShell script to remove leaked Redis credentials from Git history
# WARNING: This will rewrite Git history and require force push

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Git History Secret Removal Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "1. Remove leaked Redis credentials from all commits"
Write-Host "2. Rewrite Git history"
Write-Host "3. Require force push to remote"
Write-Host ""
Write-Host "⚠️  WARNING: This is a destructive operation!" -ForegroundColor Red
Write-Host "⚠️  All collaborators will need to re-clone the repository" -ForegroundColor Red
Write-Host ""

$confirm = Read-Host "Do you want to continue? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Operation cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Step 1: Creating backup..." -ForegroundColor Green
Set-Location ..
git clone event-driven-platform event-driven-platform-backup
Set-Location event-driven-platform

Write-Host ""
Write-Host "Step 2: Checking for git-filter-repo..." -ForegroundColor Green
$filterRepoExists = Get-Command git-filter-repo -ErrorAction SilentlyContinue

if (-not $filterRepoExists) {
    Write-Host "Installing git-filter-repo via pip..." -ForegroundColor Yellow
    pip install git-filter-repo
}

Write-Host ""
Write-Host "Step 3: Creating replacement file..." -ForegroundColor Green
$replacementContent = @"
redis-13869.crce175.eu-north-1-1.ec2.cloud.redislabs.com==>your-redis-host.cloud.redislabs.com
QnWViHMDGLtL4iKN3CwW9XtaP8oll0TQ==>your-redis-password
regex:REDIS_HOST=redis-\d+\.crce\d+\.eu-north-1-1\.ec2\.cloud\.redislabs\.com==>REDIS_HOST=your-redis-host.cloud.redislabs.com
regex:REDIS_PORT=13869==>REDIS_PORT=your-port
"@

$tempFile = "$env:TEMP\secrets-to-remove.txt"
$replacementContent | Out-File -FilePath $tempFile -Encoding UTF8

Write-Host ""
Write-Host "Step 4: Removing secrets from Git history..." -ForegroundColor Green
Write-Host "This may take a few minutes..." -ForegroundColor Yellow
git filter-repo --replace-text $tempFile --force

Write-Host ""
Write-Host "Step 5: Cleaning up..." -ForegroundColor Green
Remove-Item $tempFile -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Git history has been cleaned!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Verify the changes: git log --all --oneline"
Write-Host "2. Check for secrets: git log -S 'redis-13869' --all"
Write-Host "3. Re-add remote: git remote add origin YOUR_GITHUB_URL"
Write-Host "4. Force push: git push --force --all"
Write-Host "5. Force push tags: git push --force --tags"
Write-Host ""
Write-Host "⚠️  IMPORTANT: Notify all team members to:" -ForegroundColor Red
Write-Host "   - Delete their local repository"
Write-Host "   - Re-clone from GitHub"
Write-Host ""
Write-Host "Backup location: ..\event-driven-platform-backup" -ForegroundColor Cyan
