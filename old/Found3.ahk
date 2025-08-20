#Requires AutoHotkey v2.0
; ---------- SETTINGS ----------
images := ["accept_green.png", "accept_green-2.png"]  ; try in order
tol := 30                                             ; *n variation (0–255)
retryMs := 120
timeoutMs := 6000

; Coordinate modes: screen-based for multi-monitor work.
CoordMode("Pixel", "Screen")
CoordMode("Mouse", "Screen")

; Search the full virtual desktop (all monitors)
bounds := GetVirtualBounds()
ok := FindAndClick(
    images
  , bounds["left"], bounds["top"]
  , bounds["right"], bounds["bottom"]
  , tol, retryMs, timeoutMs
)
if !ok {
    SoundBeep(750, 300)
    ShowAlert("Image not found", 1800)
}

; ---------- HOTKEYS ----------
; F8 → show live tooltip with coords + monitor index (hold to see; release to hide)
F8::{
    ToolTip("")
    SetTimer(TT_Update, 30)
    KeyWait("F8")
    SetTimer(TT_Update, 0)
    ToolTip()
    return
    TT_Update(){
        MouseGetPos(&mx, &my)
        mon := MonitorFromPoint(mx, my)
        ToolTip("X: " mx "  Y: " my "  |  Monitor: " mon)
    }
}

; Ctrl+Shift+C → copy current coords as "x,y"
^+c::{
    MouseGetPos(&mx, &my)
    A_Clipboard := mx "," my
    ShowAlert("Copied: " A_Clipboard, 900)
}

; ---------- FUNCTIONS ----------
FindAndClick(imgList, X1, Y1, X2, Y2, tol := 0, retryMs := 150, timeoutMs := 5000) {
    start := A_TickCount
    opt := "*" tol " "  ; e.g. "*30 "
    while (A_TickCount - start < timeoutMs) {
        for img in imgList {
            try {
                if ImageSearch(&fx, &fy, X1, Y1, X2, Y2, opt img) {
                    MouseMove(fx, fy)
                    Click()
                    return true
                }
            } catch as e {
                ToolTip("ImageSearch error: " e.Message)
                Sleep(700), ToolTip()
            }
        }
        Sleep(retryMs)
    }
    return false
}

ShowAlert(txt, ms := 1500) {
    ; Kapanış yerine bound function kullan: ObjBindMethod(g,"Destroy")
    g := Gui("+AlwaysOnTop -Caption +ToolWindow")
    g.BackColor := "Red"
    g.SetFont("s11", "Segoe UI")
    g.Add("Text", "cWhite w320 Center", txt)
    g.Show("x" A_ScreenWidth-340 " y20")
    SetTimer(ObjBindMethod(g, "Destroy"), -ms)  ; ✅ scope sorunu yok
}

GetVirtualBounds() {
    count := MonitorGetCount()   ; v2: parametre almaz
    minX :=  2147483647
    minY :=  2147483647
    maxX := -2147483648
    maxY := -2147483648

    Loop count {
        MonitorGet(A_Index, &l, &t, &r, &b)
        if (l < minX) minX := l
        if (t < minY) minY := t
        if (r > maxX) maxX := r
        if (b > maxY) maxY := b
    }
    return Map("left", minX, "top", minY, "right", maxX, "bottom", maxY)
}

MonitorFromPoint(x, y) {
    count := MonitorGetCount()
    Loop count {
        MonitorGet(A_Index, &l, &t, &r, &b)
        if (x >= l && x < r && y >= t && y < b)
            return A_Index
    }
    return 0
}
