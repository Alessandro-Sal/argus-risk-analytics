# ============================================================
# ARGUS Risk Analytics Platform — Desktop Native Launcher
# ============================================================
# Launches Streamlit in an isolated subprocess and renders the UI
# inside a native Windows WebView2 desktop window with active connection polling.
# Cleanly terminates the Streamlit subprocess on window close.
# ============================================================

import os
import sys
import time
import socket
import subprocess
import webview

def get_resource_path(relative_path):
    """Restituisce il percorso assoluto della risorsa, compatibile con PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def find_free_port():
    """Trova una porta locale libera dinamica su localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def wait_for_server(port, timeout=15):
    """Attende che il server Streamlit sia effettivamente pronto e in ascolto prima di aprire la finestra."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False

def main():
    port = find_free_port()
    
    # Individuazione entry point di Streamlit
    if os.path.exists(get_resource_path("src/0_Control_Room.py")):
        entry_point = get_resource_path("src/0_Control_Room.py")
    elif os.path.exists(get_resource_path("app.py")):
        entry_point = get_resource_path("app.py")
    else:
        entry_point = "app.py"

    print(f"[ARGUS Desktop] Avvio server quantitativo su http://127.0.0.1:{port}...")
    
    # Individuazione eseguibile Python per il sottoprocesso
    python_exe = sys.executable
    if getattr(sys, 'frozen', False):
        python_exe = "python.exe"

    cmd = [
        python_exe, "-m", "streamlit", "run", entry_point,
        f"--server.port={port}",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false"
    ]

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags
    )

    # Attesa attiva per verificare che la connessione sia pronta PRIMA di aprire la GUI
    if not wait_for_server(port, timeout=15):
        print("[ARGUS Desktop] Impossibile connettersi al server Streamlit locale.")
        try:
            process.terminate()
        except Exception:
            pass
        return

    print("[ARGUS Desktop] Server attivo e pronto. Apertura finestra nativa...")

    # Icona nativa (Occhio di Argus)
    icon_path = get_resource_path("docs/argus_icon.ico")

    # Creazione della finestra nativa pywebview
    window = webview.create_window(
        title="ARGUS — Risk Analytics Platform",
        url=f"http://127.0.0.1:{port}",
        width=1366,
        height=850,
        resizable=True,
        min_size=(1024, 700),
        confirm_close=False
    )

    def on_closed():
        print("[ARGUS Desktop] Chiusura finestra nativa. Arresto server in corso...")
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            process.kill()
        print("[ARGUS Desktop] Shutdown completato pulitamente.")

    window.events.closed += on_closed
    
    # Avvio del ciclo eventi GUI
    webview.start(private_mode=False)

if __name__ == "__main__":
    main()
