# ============================================================
# ARGUS Risk Analytics Platform — Desktop Native Launcher
# ============================================================
# Launches Streamlit in an isolated subprocess and renders the UI
# inside a native Windows WebView2 desktop window with active connection polling.
# Automatically falls back to default browser if WebView2 is busy/unavailable.
# Cleanly terminates the Streamlit subprocess on window close.
# ============================================================

import os
import sys
import time
import socket
import subprocess
import shutil
import tempfile
import webbrowser

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

def find_python_executable():
    """Trova un interprete Python valido sul sistema."""
    if not getattr(sys, 'frozen', False):
        return sys.executable
    
    candidates = [
        shutil.which("python"),
        shutil.which("py"),
        os.path.expandvars(r"%LOCALAPPDATA%\Python\bin\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python314\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python313\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python310\python.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return "python"

def main():
    # 1. Configura una cartella utente WebView2 dedicata e isolata per evitare conflitti 0x800700AA
    udf_dir = os.path.join(tempfile.gettempdir(), f"argus_wv2_{os.getpid()}")
    try:
        os.makedirs(udf_dir, exist_ok=True)
        os.environ["WEBVIEW2_USER_DATA_FOLDER"] = udf_dir
    except Exception:
        pass

    # 2. Individuazione entry point di Streamlit
    if os.path.exists(get_resource_path("src/0_Control_Room.py")):
        entry_point = get_resource_path("src/0_Control_Room.py")
    elif os.path.exists(get_resource_path("app.py")):
        entry_point = get_resource_path("app.py")
    else:
        entry_point = "app.py"

    python_exe = find_python_executable()

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    server_ready = False
    process = None
    port = None

    # Tenta l'avvio su fino a 3 porte dinamiche libere
    for attempt in range(1, 4):
        port = find_free_port()
        print(f"[ARGUS Desktop] Tentativo {attempt}/3: Avvio server su http://127.0.0.1:{port}...")
        
        cmd = [
            python_exe, "-m", "streamlit", "run", entry_point,
            f"--server.port={port}",
            "--server.headless=true",
            "--server.address=127.0.0.1",
            "--global.developmentMode=false",
            "--browser.gatherUsageStats=false"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags
        )

        if wait_for_server(port, timeout=12):
            server_ready = True
            break
        else:
            print(f"[ARGUS Desktop] Tentativo {attempt} fallito. Chiusura processo e retry...")
            try:
                process.terminate()
            except Exception:
                pass

    if not server_ready:
        print("[ARGUS Desktop] Errore critico: Impossibile connettersi al server Streamlit locale dopo 3 tentativi.")
        return

    app_url = f"http://127.0.0.1:{port}"
    print(f"[ARGUS Desktop] Server attivo e pronto su {app_url}.")

    # 3. Tentativo di apertura finestra nativa WebView2 con pywebview
    webview_success = False
    try:
        import webview
        # Abilita esplicitamente il download di file (PDF, Excel, CSV) in WebView2
        webview.settings['ALLOW_DOWNLOADS'] = True
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
        
        print("[ARGUS Desktop] Inizializzazione finestra nativa Desktop (Download abilitati)...")
        window = webview.create_window(
            title="ARGUS — Risk Analytics Platform",
            url=app_url,
            width=1366,
            height=850,
            resizable=True,
            maximized=True,
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
            try:
                shutil.rmtree(udf_dir, ignore_errors=True)
            except Exception:
                pass
            print("[ARGUS Desktop] Shutdown completato pulitamente.")

        window.events.closed += on_closed
        webview.start(private_mode=False, storage_path=udf_dir)
        webview_success = True

    except Exception as e:
        print(f"\n[ARGUS Desktop] Avviso: WebView2 non avviabile ({e}).")
        print("[ARGUS Desktop] Apertura automatica nel browser predefinito in corso...")

    # 4. Fallback su browser predefinito se WebView2 non e' disponibile o genera eccezioni
    if not webview_success:
        try:
            webbrowser.open(app_url)
            print("=" * 60)
            print(f"🚀 ARGUS e' attivo nel tuo browser all'indirizzo:")
            print(f"   {app_url}")
            print("=" * 60)
            print("Premi Ctrl+C nella console per terminare la piattaforma.\n")
            
            # Mantiene in vita il processo finche' l'utente non invia Ctrl+C
            while process.poll() is None:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[ARGUS] Ricevuto segnale di interruzione. Arresto del server...")
        finally:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                process.kill()
            try:
                shutil.rmtree(udf_dir, ignore_errors=True)
            except Exception:
                pass
            print("[ARGUS] Shutdown completato.")

if __name__ == "__main__":
    main()
