# logger.py
"""Zapis logów testów w formacie zgodnym z Chroma 19052 Test Report"""
import os
from datetime import datetime


_DEFAULT_LOG_DIR = "logs"

ERROR_CODES = {
    "1":   "Hardware Fail",
    "2":   "GFI Trip",
    "4":   "ARC Fail",
    "8":   "Check Low Fail",
    "16":  "DC Mode High Fail",
    "17":  "AC Mode High Fail",
    "18":  "AC Mode Low Fail",
    "32":  "Ground Continuity Fail",
    "64":  "IR Low Fail",
    "116": "Pass",
    "128": "IR High Fail",
    "256": "ADV Over",
    "512": "ADI Over",
}


def _get_error_description(error_code: str) -> str:
    if not error_code:
        return ""
    return ERROR_CODES.get(str(error_code).strip(), f"Error code {error_code}")


def save_report(operator: str, program: str, serial: str,
                mode: str, vtm: float, im: float,
                low: float, high: float,
                result: str, error_code: str = "",
                log_dir: str = _DEFAULT_LOG_DIR) -> str:
    """
    Zapisuje raport TXT w formacie Chroma 19052.
    Nazwa pliku: SN_YYYYMMDDHHmmss.txt  np. 21BDA26773_20260408143647.txt
    Zwraca ścieżkę do pliku.

    Parametry:
        log_dir - ścieżka folderu zapisu (domyślnie lokalny 'logs').
                  Przekaż config.LOG_DIR aby używać ścieżki sieciowej IFS.
    """
    os.makedirs(log_dir, exist_ok=True)

    now          = datetime.now()
    datetime_str = now.strftime("%Y/%m/%d %H:%M:%S")
    error_desc   = _get_error_description(error_code)
    result_cap   = "Pass" if str(result).upper() == "PASS" else "Fail"

    # Format zgodny 1:1 z oryginalnym plikiem Chroma
    lines = [
        "Chroma 19052 Test report",
        "",
        f"Program:\t{program}",
        f"S/N:\t\t{serial}",
        f"TIME:\t\t{datetime_str}",
        f"Total result:\t{result_cap}",
        "",
        "STEP:\t\t1",
        f"MODE:\t\t{mode}",
        "EXT Name:\t",
        f"Vtm:\t\t{vtm:.3f}\tKV",
        f"Im:\t\t{im:.3f}\tmA",
        f"Low:\t\t{low:.3f}\tmA",
        f"High:\t\t{high:.3f}\tmA",
        f"Result:\t\t{result_cap}",
        f"Error Code:\t{error_code}",
        "",
        f"Error Description: {error_desc}",
    ]

    # Nazwa pliku: SN_YYYYMMDDHHmmss.txt
    filename = f"{serial}_{now.strftime('%Y%m%d%H%M%S')}.txt"
    filepath = os.path.join(log_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines))

    print(f"[LOG] Zapisano: {filepath}")
    return filepath