function Hour {    
    param(
        [string]$ntp
    )
    try {
        if (-not $ntp) {
            throw "Il server NTP non è stato immesso, per favore riprovare aggiungendo l'argomento '-ntp <indirizzo>'"
        }
        $ntpData = New-Object byte[] 48
        $ntpData[0] = 0x1B
        $endpoint = New-Object System.Net.IPEndPoint ([System.Net.Dns]::GetHostAddresses($ntp)[0], 123)
        $udp = New-Object System.Net.Sockets.UdpClient
        $udp.Client.ReceiveTimeout = 5000

        try {
            $udp.Connect($endpoint)
            $null = $udp.Send($ntpData, $ntpData.Length)
            $ntpData = $udp.Receive([ref]$endpoint)
        }
        finally {
            $udp.Close()
        }
        $Ipart = [System.BitConverter]::ToUInt32($ntpData[43..40], 0)
        $unix = $Ipart - 2208988800
        $unix += $incrementSeconds
        return $unix
    }
    catch {
        Write-Output "Errore: $_"
    }
}
