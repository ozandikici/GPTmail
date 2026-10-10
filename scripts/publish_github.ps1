# One-command public GitHub publication helper for the repository owner.
# Requires Git and GitHub CLI: https://cli.github.com/
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
foreach ($tool in @('git', 'gh')) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
    throw "$tool gerekli. Git ve GitHub CLI (gh) kurup yeniden dene."
  }
}
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'GitHub oturumunu aç: gh auth login' }
if (-not (Test-Path .git)) {
  & git init -b main
  if ($LASTEXITCODE -ne 0) { throw 'git init basarisiz.' }
}
& git add .
if ($LASTEXITCODE -ne 0) { throw 'git add basarisiz.' }
& git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
  & git commit -m 'feat: initial GPTmail open-source release'
  if ($LASTEXITCODE -ne 0) { throw 'Commit olusturulamadi. Git user.name ve user.email ayarlarini kontrol et.' }
}
& gh repo create ozandikici/GPTmail --public --source . --remote origin --push
if ($LASTEXITCODE -ne 0) { throw 'Repo oluşturulamadı. Önceden varsa git remote -v ve git push -u origin main komutlarını kontrol et.' }
Write-Host 'Public repo: https://github.com/ozandikici/GPTmail'
