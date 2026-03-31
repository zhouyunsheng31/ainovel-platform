[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"

$ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")
$BACKEND = Join-Path $ROOT "backend"

$PASS = 0
$FAIL = 0

function Run-Check {
    param([string]$Name, [scriptblock]$Block)

    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  $Name" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan

    try {
        & $Block
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[PASS] $Name" -ForegroundColor Green
            $script:PASS++
        } else {
            Write-Host "[FAIL] $Name (exit code: $LASTEXITCODE)" -ForegroundColor Red
            $script:FAIL++
        }
    } catch {
        Write-Host "[FAIL] $Name ($_)" -ForegroundColor Red
        $script:FAIL++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  AI小说拆书系统 - 质量门禁检查" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

Run-Check "Ruff 代码规范检查" {
    Set-Location $BACKEND
    python -m ruff check . --output-format=github 2>&1
}

Run-Check "Pytest 单元测试" {
    Set-Location $BACKEND
    python -m pytest tests/ -v --tb=short 2>&1
}

Run-Check "OpenAPI 契约校验" {
    Set-Location $ROOT
    npx --yes spectral lint docs/openapi.yaml --ruleset .spectral.yaml 2>&1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  门禁结果汇总" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  通过: $PASS" -ForegroundColor Green
Write-Host "  失败: $FAIL" -ForegroundColor $(if ($FAIL -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($FAIL -gt 0) {
    Write-Host ">>> 门禁未通过，请修复上述问题后重新运行 <<<" -ForegroundColor Red
    exit 1
} else {
    Write-Host ">>> 门禁全部通过 <<<" -ForegroundColor Green
    exit 0
}
