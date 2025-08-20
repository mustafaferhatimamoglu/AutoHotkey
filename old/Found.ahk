#Requires AutoHotkey v2.0
CoordMode("Pixel", "Screen")
CoordMode("Mouse", "Screen")

F6:: {
    idx := 0
    x := y := 0
    ErrorLevel := ""  ; Başlatma

    ; İlk görsel
    ImageSearch &x, &y, 0, 0, A_ScreenWidth, A_ScreenHeight, "accept_green.png"
    if (ErrorLevel = 0)
        idx := 1

    ; İkinci görsel (eğer önceki bulunmadıysa)
    if (idx = 0) {
        ImageSearch &x, &y, 0, 0, A_ScreenWidth, A_ScreenHeight, "accept_green-2.png"
        if (ErrorLevel = 0)
            idx := 2
    }

    if (idx != 0) {
        MsgBox("Found image " idx " at " x ", " y)
        ; Örneğin tıklama eklemek isterseniz:
        ; MouseClick("left", x, y)
    } else {
        MsgBox("Neither image found." A_ScreenWidth A_ScreenHeight)
    }
}
