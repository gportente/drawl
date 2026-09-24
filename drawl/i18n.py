"""User-facing strings, in every language drawl speaks.

Qt ships a full translation system, but it needs a build step (`lupdate`,
`lrelease`) and compiled `.qm` files. For a couple of dozen strings in two
languages that machinery costs more than it gives, and a plain dictionary has
the advantage of being readable in a diff.

The language is chosen once at startup, from the `ui_language` setting. QML
reads these strings through the `i18n` context property, so a change only takes
effect on restart — which is fine for a setting nobody flips mid-sentence.
"""
from __future__ import annotations

import locale

FALLBACK = "en"

MESSAGES: dict[str, dict[str, str]] = {
    # --- lifecycle ----------------------------------------------------------
    "status.starting":      {"en": "Starting…",            "it": "Avvio…"},
    "status.ready":         {"en": "Ready",                "it": "Pronto"},
    "status.listening":     {"en": "Listening…",           "it": "In ascolto…"},
    "status.transcribing":  {"en": "Transcribing…",        "it": "Trascrivo…"},
    "status.downloading":   {"en": "Downloading model… {percent}%",
                             "it": "Scarico il modello… {percent}%"},
    "status.extracting":    {"en": "Extracting… {percent}%",
                             "it": "Estraggo… {percent}%"},

    # --- results ------------------------------------------------------------
    "status.tooShort":      {"en": "Too short",            "it": "Troppo breve"},
    "status.noSpeech":      {"en": "No speech detected",   "it": "Nessun parlato rilevato"},
    "status.copied":        {"en": "Copied to clipboard",  "it": "Copiato negli appunti"},
    "status.timing":        {"en": "{elapsed}s for {audio}s ({speed}×)",
                             "it": "{elapsed}s per {audio}s ({speed}×)"},

    # --- settings -----------------------------------------------------------
    "status.autoPasteOn":   {"en": "Auto-paste on",        "it": "Incolla automatico attivo"},
    "status.autoPasteOff":  {"en": "Clipboard only",       "it": "Solo appunti"},

    # --- failures -----------------------------------------------------------
    "error.engine":         {"en": "Engine unavailable: {detail}",
                             "it": "Motore non disponibile: {detail}"},
    "error.engineNotReady": {"en": "Engine not ready",     "it": "Motore non pronto"},
    "error.microphone":     {"en": "Microphone unavailable: {detail}",
                             "it": "Microfono non disponibile: {detail}"},
    "error.transcription":  {"en": "Transcription failed: {detail}",
                             "it": "Errore di trascrizione: {detail}"},
    "error.hotkey":         {"en": "Hotkey unavailable: {detail}",
                             "it": "Hotkey non disponibile: {detail}"},
    "error.hotkeySuffix":   {"en": "{status} — no hotkey",
                             "it": "{status} — hotkey non disponibile"},
    "error.hotkeyInUse":    {"en": "already in use (error {code})",
                             "it": "gia' in uso (errore {code})"},
    "error.qmlLoad":        {"en": "error: could not load the QML interface",
                             "it": "errore: impossibile caricare l'interfaccia QML"},
    "error.alreadyRunning": {"en": "drawl is already running",
                             "it": "drawl e' gia' in esecuzione"},

    # --- secondary buttons --------------------------------------------------
    "tip.copy":             {"en": "Copy the last transcription",
                             "it": "Copia l'ultima trascrizione"},
    "tip.autoPasteOn":      {"en": "Auto-paste: on",       "it": "Incolla automatico: attivo"},
    "tip.autoPasteOff":     {"en": "Auto-paste: off",      "it": "Incolla automatico: spento"},

    "tip.screenshot":       {"en": "Screenshot",           "it": "Screenshot"},
    "tip.record":           {"en": "Record the screen",    "it": "Registra lo schermo"},
    "tip.stopRecording":    {"en": "Stop recording",       "it": "Ferma la registrazione"},

    # --- screen capture -----------------------------------------------------
    "capture.hintShot":     {"en": "Click a window or drag an area  ·  Enter: whole screen  ·  Esc: cancel",
                             "it": "Clicca una finestra o trascina un'area  ·  Invio: tutto lo schermo  ·  Esc: annulla"},
    "capture.hintRecord":   {"en": "What to record? Click a window or drag an area  ·  Enter: whole screen  ·  Esc: cancel",
                             "it": "Cosa registrare? Clicca una finestra o trascina un'area  ·  Invio: tutto lo schermo  ·  Esc: annulla"},
    "capture.recording":    {"en": "Recording…",           "it": "Registrazione…"},
    # Short for the pill's status line; the tray notification has room for the name.
    "capture.recordSaved":  {"en": "Recording saved  ·  {seconds} s  ·  {size} MB",
                             "it": "Registrazione salvata  ·  {seconds} s  ·  {size} MB"},
    "capture.recordSavedAs": {"en": "Recording saved: {name} ({seconds} s, {size} MB)",
                              "it": "Registrazione salvata: {name} ({seconds} s, {size} MB)"},
    "capture.recordFailed": {"en": "Recording failed: {detail}",
                             "it": "Registrazione non riuscita: {detail}"},

    # --- screenshot editor --------------------------------------------------
    "editor.title":         {"en": "Screenshot",           "it": "Screenshot"},
    "editor.hint":          {"en": "Shift: straight lines, squares and circles  ·  double click a text to edit it  ·  Ctrl+Z: undo",
                             "it": "Shift: linee dritte, quadrati e cerchi  ·  doppio clic su un testo per modificarlo  ·  Ctrl+Z: annulla"},
    "editor.color":         {"en": "Colour",               "it": "Colore"},
    "editor.size1":         {"en": "Thin",                 "it": "Sottile"},
    "editor.size2":         {"en": "Medium",               "it": "Medio"},
    "editor.size3":         {"en": "Thick",                "it": "Spesso"},
    "editor.fill":          {"en": "Filled shapes",        "it": "Forme piene"},
    "editor.undo":          {"en": "Undo",                 "it": "Annulla"},
    "editor.redo":          {"en": "Redo",                 "it": "Ripeti"},
    "editor.delete":        {"en": "Delete the selection", "it": "Elimina la selezione"},
    "editor.copy":          {"en": "Copy the image",       "it": "Copia l'immagine"},
    "editor.save":          {"en": "Save",                 "it": "Salva"},
    "editor.saveAs":        {"en": "Save as…",             "it": "Salva con nome…"},
    "editor.copied":        {"en": "Image copied to the clipboard",
                             "it": "Immagine copiata negli appunti"},
    "editor.saved":         {"en": "Saved to {path} — click to show it",
                             "it": "Salvato in {path} — clicca per mostrarlo"},
    "editor.saveFailed":    {"en": "Could not save {path}",
                             "it": "Impossibile salvare {path}"},
    "tool.select":          {"en": "Select and move",      "it": "Seleziona e sposta"},
    "tool.arrow":           {"en": "Arrow",                "it": "Freccia"},
    "tool.line":            {"en": "Line",                 "it": "Linea"},
    "tool.rect":            {"en": "Rectangle",            "it": "Rettangolo"},
    "tool.ellipse":         {"en": "Ellipse",              "it": "Ellisse"},
    "tool.pen":             {"en": "Pen",                  "it": "Penna"},
    "tool.marker":          {"en": "Highlighter",          "it": "Evidenziatore"},
    "tool.text":            {"en": "Text",                 "it": "Testo"},
    "tool.step":            {"en": "Numbered steps",       "it": "Passaggi numerati"},
    "tool.pixelate":        {"en": "Pixelate, to hide sensitive data",
                             "it": "Pixel, per nascondere dati sensibili"},
    "tool.crop":            {"en": "Crop",                 "it": "Ritaglia"},

    # --- tray ---------------------------------------------------------------
    "tray.dictate":         {"en": "Dictate  ({hotkey})",  "it": "Detta  ({hotkey})"},
    "tray.screenshot":      {"en": "Screenshot  ({hotkey})",
                             "it": "Screenshot  ({hotkey})"},
    "tray.record":          {"en": "Record the screen  ({hotkey})",
                             "it": "Registra lo schermo  ({hotkey})"},
    "tray.stopRecording":   {"en": "Stop recording  ({hotkey})",
                             "it": "Ferma la registrazione  ({hotkey})"},
    "tray.noHotkey":        {"en": "no hotkey",            "it": "nessuna hotkey"},
    "tray.toggle":          {"en": "Show / hide",          "it": "Mostra / nascondi"},
    "tray.quit":            {"en": "Quit",                 "it": "Esci"},
    "tray.tooltip":         {"en": "drawl — {hotkey} to dictate",
                             "it": "drawl — {hotkey} per dettare"},
}

_language = FALLBACK


def available() -> list[str]:
    """Language codes with at least one translated string."""
    codes: set[str] = set()
    for variants in MESSAGES.values():
        codes.update(variants)
    return sorted(codes)


def set_language(code: str) -> str:
    """Pick the language. `auto` follows the system, falling back to English."""
    global _language
    if code == "auto":
        system, _ = locale.getdefaultlocale()
        code = (system or FALLBACK).split("_")[0].lower()
    _language = code if code in available() else FALLBACK
    return _language


def language() -> str:
    return _language


def t(key: str, **values) -> str:
    """Translate `key`, filling in any `{placeholders}`.

    An unknown key returns the key itself: a missing string then shows up in the
    interface as an obvious `status.something`, instead of silently disappearing.
    """
    variants = MESSAGES.get(key)
    if variants is None:
        return key
    text = variants.get(_language) or variants.get(FALLBACK, key)
    return text.format(**values) if values else text


def number(value: float, decimals: int = 1) -> str:
    """Format a number the way the chosen language writes it."""
    text = f"{value:.{decimals}f}"
    return text.replace(".", ",") if _language == "it" else text
