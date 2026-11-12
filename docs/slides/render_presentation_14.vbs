' Late-bound PowerPoint export, avoiding the machine's broken .NET type library.
' Run: cscript //Nologo docs\slides\render_presentation_14.vbs
Option Explicit
Dim fs, base, app, pres, countBefore, preview, pdf, sl, sh, tr, issues, report
Set fs = CreateObject("Scripting.FileSystemObject")
base = fs.GetParentFolderName(WScript.ScriptFullName)
preview = fs.BuildPath(base, "thuyet_trinh_14\preview")
pdf = fs.BuildPath(base, "BTL_XLA_ThuyetTrinh_14_Slide.pdf")
If Not fs.FolderExists(preview) Then fs.CreateFolder preview
Set app = CreateObject("PowerPoint.Application")
countBefore = app.Presentations.Count
Set pres = app.Presentations.Open(fs.BuildPath(base, "BTL_XLA_ThuyetTrinh_14_Slide.pptx"), True, False, False)
issues = 0
Set report = fs.CreateTextFile(fs.BuildPath(base, "thuyet_trinh_14\POWERPOINT_LAYOUT_CHECK.txt"), True, True)
For Each sl In pres.Slides
    For Each sh In sl.Shapes
        If sh.HasTextFrame Then
            If sh.TextFrame.HasText Then
                Set tr = sh.TextFrame2.TextRange
                If tr.BoundTop + tr.BoundHeight > sh.Top + sh.Height + 3 Or tr.BoundLeft + tr.BoundWidth > sh.Left + sh.Width + 3 Then
                    issues = issues + 1
                    report.WriteLine "SLIDE " & sl.SlideIndex & ": " & sh.TextFrame.TextRange.Text
                    report.WriteLine "Text height=" & tr.BoundHeight & " Box height=" & sh.Height
                End If
            End If
        End If
    Next
Next
report.WriteLine "Slides=" & pres.Slides.Count & "; overflow candidates=" & issues
report.Close
pres.Export preview, "PNG", 1600, 900
pres.SaveAs pdf, 32
WScript.Echo "Exported " & pres.Slides.Count & " slides using PowerPoint " & app.Version
WScript.Echo "Overflow candidates: " & issues
WScript.Echo "PDF: " & pdf
pres.Close
If countBefore = 0 Then
    If app.Presentations.Count = 0 Then app.Quit
End If
Set pres = Nothing
Set app = Nothing
