# 동시성 결재 요청 테스트 스크립트 (Windows PowerShell 5.1 호환)
# 사용: powershell -File .\scripts\concurrency_test.ps1 [-Repeat 1]
# 포트포워딩: kubectl port-forward svc/approval-request-service 8002:8000 -n erp

param(
  [int]$Repeat = 1,
  [int]$Port = 8002,
  [string]$BaseUri = $null
)

if (-not $BaseUri) { $BaseUri = "http://localhost:$Port" }
$uri = "$BaseUri/approvals"

if ($Repeat -lt 1) { $Repeat = 1 }

Write-Host "[INFO] Running concurrency test with $Repeat batch(es) of 3 parallel requests (URI=$uri)" -ForegroundColor Cyan

$allResults = @()

for ($batch=1; $batch -le $Repeat; $batch++) {
  Write-Host "[BATCH $batch] Starting 3 parallel approval requests..." -ForegroundColor Yellow

  $payloads = @(
    @{ label = 'A'; title = '결재 요청 A'; content = '동시 처리 테스트 A' },
    @{ label = 'B'; title = '결재 요청 B'; content = '동시 처리 테스트 B' },
    @{ label = 'C'; title = '결재 요청 C'; content = '동시 처리 테스트 C' }
  )

  $jobs = @()
  foreach ($p in $payloads) {
    $bodyObj = [ordered]@{
      requesterId = 1
      title       = $p.title
      content     = $p.content
      steps       = @(@{ step = 1; approverId = 2 })
      requestType = 'GENERAL'
    }
    $jsonBody = ($bodyObj | ConvertTo-Json -Depth 10)
    $label = $p.label
    $job = Start-Job -Name "req-$label" -ScriptBlock {
      param($u, $b, $lbl)
      $start = Get-Date
      try {
        $resp = Invoke-RestMethod -Method POST -Uri $u -ContentType 'application/json' -Body $b -TimeoutSec 15
        [pscustomobject]@{
          Label      = $lbl
          Status     = 'OK'
          RequestId  = $resp.requestId
          StartedAt  = $start
          EndedAt    = Get-Date
          Raw        = ($resp | ConvertTo-Json -Depth 10)
        }
      }
      catch {
        $msg = $_.Exception.Message
        [pscustomobject]@{
          Label      = $lbl
          Status     = 'ERROR'
          RequestId  = $null
          StartedAt  = $start
          EndedAt    = Get-Date
          Raw        = $msg
        }
      }
    } -ArgumentList $uri, $jsonBody, $label
    $jobs += $job
  }

  # 대기
  Wait-Job -Job $jobs | Out-Null

  # 결과 수집
  foreach ($j in $jobs) {
    $result = Receive-Job -Job $j
    $allResults += $result
    Remove-Job -Job $j -Force
  }

  Write-Host "[BATCH $batch] Completed." -ForegroundColor Green
}

# 결과 출력
Write-Host "\n=== 개별 결과 ===" -ForegroundColor Cyan
$allResults | Sort-Object StartedAt | Format-Table Label, Status, RequestId, StartedAt, EndedAt -AutoSize

# 집계
$ok = $allResults | Where-Object { $_.Status -eq 'OK' }
$err = $allResults | Where-Object { $_.Status -ne 'OK' }
$ids = $ok.RequestId | Sort-Object
$dupIds = $ids | Group-Object | Where-Object { $_.Count -gt 1 } | Select-Object -ExpandProperty Name

Write-Host "\n=== 집계 ===" -ForegroundColor Cyan
Write-Host ("총 요청: {0}, 성공: {1}, 실패: {2}" -f $allResults.Count, $ok.Count, $err.Count)
Write-Host ("생성된 requestId들: {0}" -f ($ids -join ', '))
if ($dupIds) {
  Write-Host ("중복 ID 발생: {0}" -f ($dupIds -join ', ')) -ForegroundColor Red
} else {
  Write-Host "중복 ID 없음" -ForegroundColor Green
}

# 퍼포먼스 (단순 지연 계산)
$durations = $allResults | ForEach-Object { ($_.EndedAt - $_.StartedAt).TotalMilliseconds }
if ($durations.Count -gt 0) {
  $avg = [Math]::Round(($durations | Measure-Object -Average).Average,2)
  $max = [Math]::Round(($durations | Measure-Object -Maximum).Maximum,2)
  $min = [Math]::Round(($durations | Measure-Object -Minimum).Minimum,2)
  Write-Host ("지연(ms): min={0} avg={1} max={2}" -f $min, $avg, $max)
}

  if ($err.Count -gt 0) {
    Write-Host "\n=== 오류 상세 ===" -ForegroundColor Red
    foreach ($e in $err) {
      Write-Host ("[Label {0}] {1}" -f $e.Label, $e.Raw) -ForegroundColor Red
    }
  }

Write-Host "\n[INFO] 더 많은 동시성 테스트: -Repeat 10 로 30건 테스트 가능" -ForegroundColor Yellow

# 레이스 컨디션 설명 안내
Write-Host "\n[NOTE] 현재 requestId 생성은 최대값 조회 후 +1 방식으로 두 요청이 거의 동시에 들어오면 중복 위험이 있습니다. MongoDB findOneAndUpdate + $inc 카운터 컬렉션으로 개선 권장." -ForegroundColor Magenta
