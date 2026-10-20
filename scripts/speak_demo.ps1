param(
    [Parameter(Mandatory=$true)][string]$Config,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$settings = Get-Content -Raw -LiteralPath $Config | ConvertFrom-Json
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$speaker = New-Object -ComObject SAPI.SpVoice
$matching = @($speaker.GetVoices() | Where-Object { $_.GetDescription() -eq $settings.voice })
if ($matching.Count -ne 1) { throw "Required demo voice is unavailable: $($settings.voice)" }
$speaker.Voice = $matching[0]
$speaker.Rate = 0
for ($index = 0; $index -lt $settings.cues.Count; $index++) {
    $stream = New-Object -ComObject SAPI.SpFileStream
    $target = Join-Path $OutputDirectory ("line-{0}.wav" -f $index)
    $stream.Open($target, 3, $false)
    try {
        $speaker.AudioOutputStream = $stream
        $speaker.Speak($settings.cues[$index].text) | Out-Null
    } finally { $stream.Close() }
}
Write-Output 'Synthetic speech generated.'
