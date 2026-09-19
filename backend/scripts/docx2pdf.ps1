# Converts every .docx in a folder to .pdf using Microsoft Word (COM).
# Used only by scripts/generate_template_previews.py to build the
# template picker thumbnails. Requires Word installed locally.
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File docx2pdf.ps1 -Dir "C:\path\to\folder"

param(
    [Parameter(Mandatory = $true)]
    [string]$Dir
)

$ErrorActionPreference = "Stop"

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    Get-ChildItem -Path $Dir -Filter *.docx | ForEach-Object {
        $doc = $word.Documents.Open($_.FullName, $false, $true)
        try {
            $pdf = [IO.Path]::ChangeExtension($_.FullName, ".pdf")
            $doc.SaveAs2($pdf, 17)   # 17 = wdFormatPDF
            Write-Output "converted: $($_.Name)"
        }
        finally {
            $doc.Close($false)
        }
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
