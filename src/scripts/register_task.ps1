# Windows 작업 스케줄러에 일별 데이터 갱신 작업을 등록한다 (SEO D5 로컬 대안).
# 실행: PowerShell을 관리자 권한으로 열고
#   powershell -ExecutionPolicy Bypass -File src\scripts\register_task.ps1
# 등록 내용: 매일 06:30 (KST 기준 - 미국 정규장 마감 직후) update_data.bat 실행
# 해제: schtasks /Delete /TN "ADR-Premium-DailyUpdate" /F

$batPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "update_data.bat"
if (-not (Test-Path $batPath)) {
    Write-Error "update_data.bat 를 찾을 수 없습니다: $batPath"
    exit 1
}

schtasks /Create /F /TN "ADR-Premium-DailyUpdate" /SC DAILY /ST 06:30 /TR "`"$batPath`""
if ($LASTEXITCODE -eq 0) {
    Write-Output "등록 완료: 매일 06:30 실행 (작업 이름: ADR-Premium-DailyUpdate)"
    Write-Output "확인: schtasks /Query /TN ADR-Premium-DailyUpdate"
} else {
    Write-Error "등록 실패 - 관리자 권한으로 실행했는지 확인하세요."
}
