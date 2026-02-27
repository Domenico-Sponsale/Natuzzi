. ".\time.ps1"
$req = Hour -ntp "172.28.14.52"
$out = $req
$sleep_time = "15:21"

function Shutdown {
    # Write-Output "TEST"
    # Stop-Computer -Force
    Restart-Computer -Force
}

function Unix {
    param(
        [int]$unixSeconds
    )
    $date = (Get-Date "1970-01-01 00:00:00").AddSeconds($unixSeconds)
    return $date.ToLocalTime()
}

while ($true) {
    $hour = Unix($out)
    $out = $out+1
    Start-Sleep -Seconds 1
    Write-Output $hour.ToString("HH:mm")
    if ($hour -eq $sleep_time) {
        Shutdown
        break
    }
}