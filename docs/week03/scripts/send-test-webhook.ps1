param(
    [ValidateSet("firing", "resolved")]
    [string]$Status = "firing",
    [string]$BaseUrl = "http://127.0.0.1:5000"
)

$body = @{
    version = "4"
    status  = $Status
    alerts  = @(
        @{
            status       = $Status
            labels       = @{
                alertname = "InstanceDown"
                instance  = "192.168.10.11:9100"
                job       = "node"
                severity  = "critical"
            }
            annotations  = @{
                summary     = "WEB01 exporter is down"
                description = "up == 0"
            }
            startsAt     = "2026-10-22T10:00:00.000Z"
            endsAt       = $(if ($Status -eq "resolved") { "2026-10-22T10:05:00.000Z" } else { "0001-01-01T00:00:00Z" })
            fingerprint  = "am-web01-down"
        }
    )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/alerts/webhook" -ContentType "application/json" -Body $body
