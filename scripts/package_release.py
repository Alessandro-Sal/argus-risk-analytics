"""
Script di packaging per la creazione dell'archivio ZIP della release v6.0.0 di ARGUS.
Esegue un'ispezione preventiva di sicurezza per garantire che NESSUN file sensibile
(credenziali, chiavi, .env, token, database locali, file temporanei o cache) venga incluso.
"""

import os
import sys
import zipfile
import re

def create_secure_release_zip():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_dir = os.path.join(project_dir, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    
    zip_filename = "ARGUS_v6.0.0.zip"
    zip_path = os.path.join(dist_dir, zip_filename)
    
    print("=" * 70)
    print(" [ARGUS v6.0.0] Generazione Archivio Release ZIP con Audit di Sicurezza")
    print("=" * 70)
    
    # Cartelle e file rigorosamente ESCLUSI
    EXCLUDED_DIRS = {
        ".git", ".github", ".agents", ".dsp", ".pytest_cache", ".ruff_cache",
        "__pycache__", "scratch", "logs", "build", "dist", ".venv", "venv",
        "ENV", ".gemini", ".idea", ".vscode"
    }
    
    EXCLUDED_FILE_PATTERNS = [
        r"^\.env$",
        r"^\.env\..*$",
        r".*\.sqlite$",
        r".*\.sqlite3$",
        r".*\.db$",
        r".*\.py[cod]$",
        r".*\.log$",
        r".*credentials.*\.json$",
        r".*service_account.*\.json$",
        r".*\.pem$",
        r".*\.key$",
        r"Thumbs\.db$",
        r"\.DS_Store$"
    ]
    
    # Eccezioni ammesse esplicitamente (non sensibili)
    ALLOWED_SPECIAL_FILES = {
        ".env.example",
        "config.json",
        "argus-architecture.json",
        ".dockerignore",
        ".nojekyll",
        ".gitkeep"
    }

    files_to_zip = []
    
    for root, dirs, files in os.walk(project_dir):
        # Filtra cartelle escluse inline
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".agent")]
        
        rel_root = os.path.relpath(root, project_dir)
        if rel_root == ".":
            rel_root = ""
            
        for f in files:
            rel_file_path = os.path.normpath(os.path.join(rel_root, f)).replace("\\", "/")
            
            # Controllo blacklist pattern
            is_excluded = False
            if f not in ALLOWED_SPECIAL_FILES:
                for pattern in EXCLUDED_FILE_PATTERNS:
                    if re.match(pattern, f, re.IGNORECASE):
                        is_excluded = True
                        break
                        
            if is_excluded:
                print(f"  [ESCLUSO SICUREZZA] -> {rel_file_path}")
                continue
                
            full_path = os.path.join(root, f)
            files_to_zip.append((full_path, rel_file_path))
            
    print(f"\n[INFO] Totale file validati per l'inclusione: {len(files_to_zip)}")
    
    # Controllo di sicurezza aggiuntivo sul contenuto
    sensitive_keywords = [
        "sk" + "-proj-",
        "AI" + "zaSy",
        "BEGIN" + " PRIVATE KEY",
        "BEGIN" + " RSA PRIVATE KEY"
    ]
    flagged_files = []
    for full_p, rel_p in files_to_zip:
        if rel_p == "scripts/package_release.py":
            continue
        try:
            with open(full_p, "r", encoding="utf-8", errors="ignore") as file_handle:
                content = file_handle.read()
                for kw in sensitive_keywords:
                    if kw in content:
                        flagged_files.append((rel_p, kw))
        except Exception:
            pass
            
    if flagged_files:
        print("\n[ERRORE CRITICO SICUREZZA] Rilevate potenziali credenziali nei seguenti file:")
        for fp, kw in flagged_files:
            print(f"  [X] {fp} (Keyword: {kw})")
        sys.exit(1)
        
    print("[SICUREZZA CERTIFICATA] Nessuna chiave o credenziale sensibile rilevata nei file ammessi.")
    
    # Creazione del file ZIP
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full_p, rel_p in files_to_zip:
            archive_name = f"ARGUS_v6.0.0/{rel_p}"
            zf.write(full_p, archive_name)
            
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print("\n" + "=" * 70)
    print(f" [OK] ARCHIVIO ZIP DELLA RELEASE V.6.0.0 CREATO CON SUCCESSO!")
    print(f"      Percorso:    {zip_path}")
    print(f"      Dimensione:  {zip_size_mb:.2f} MB")
    print(f"      File inclusi: {len(files_to_zip)}")
    print("=" * 70)

if __name__ == "__main__":
    create_secure_release_zip()
