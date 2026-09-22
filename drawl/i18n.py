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

    # --- tray ---------------------------------------------------------------
    "tray.dictate":         {"en": "Dictate  ({hotkey})",  "it": "Detta  ({hotkey})"},
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
