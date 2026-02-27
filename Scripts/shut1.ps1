$sleep_time = "00:00"
function SyncTime {
    $ntpServer = "172.28.14.52"
    w32tm /config /manualpeerlist:$ntpServer /syncfromflags:manual /reliable:YES /update
    w32tm /resync
}

