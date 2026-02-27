. ".\time.ps1"
$oraChiusura = "00:00"
$oraStandby = "00:30"
$oraRiavvio = "05:45"
$url = "http://itandon"

function Unix {
    param(
        [int]$unixSeconds
    )
    $date = (Get-Date "1970-01-01 00:00:00").AddSeconds($unixSeconds)
    return $date.ToLocalTime()
}

function AvviaChrome {
    Start-Process -FilePath "chrome.exe" -ArgumentList "--kiosk", $url
    Start-Sleep -Seconds 5
    $chrome = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
    return $chrome.Id
}

function Standby {
    (Add-Type '[DllImport("user32.dll")]public static extern int SendMessage(int hWnd,int hMsg,int wParam,int lParam);' -Name a -Pas)::SendMessage(-1, 0x0112, 0xF170, 2)
}
function ChiudiChrome {
    $chrome = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
    try {        
        if ($chrome) {
            Stop-Process -Id $chrome.Id -Force
            Write-Output "Chrome chiuso alle $oraChiusura."
        }
        else {
            $null
        }
    }
    catch {
        $null
    }
}

function RiavviaSistema {
    Restart-Computer -Force
}

$chromePid = AvviaChrome
Write-Output "Chrome avviato con PID $chromePid."
$out = Hour -ntp  "172.128.112.140"

while ($true) {
    $oraAttuale = Unix($out+1)
    $oraAttuale = $oraAttuale.ToString("HH:mm")
    if ($oraAttuale -eq $oraChiusura) {
        ChiudiChrome
    }
    if ($oraAttuale -eq $oraStandby) {
        Standby
    }
    if ($oraAttuale -eq $oraRiavvio) {
        RiavviaSistema
    }
}
