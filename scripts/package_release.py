"""
Script per impacchettare la versione Standalone Desktop (dist/ARGUS_Desktop)
in un archivio distribuiscibile ZIP (dist/ARGUS_Desktop_v5.0.zip) per GitHub Releases.
"""

import os
import sys
import shutil
import subprocess

def package_release():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_dir = os.path.join(project_dir, "dist", "ARGUS_Desktop")
    zip_path = os.path.join(project_dir, "dist", "ARGUS_Desktop_v5.0.zip")
    
    print("=" * 60)
    print(" Preparazione Pacchetto GitHub Release per il Cliente")
    print("=" * 60)
    
    # 1. Se la cartella dist non esiste, esegue la compilazione PyInstaller
    if not os.path.exists(dist_dir):
        print("[1/2] Compilazione eseguibile ARGUS.exe in corso...")
        build_script = os.path.join(project_dir, "scripts", "build_desktop_app.py")
        subprocess.run([sys.executable, build_script], check=True)
    else:
        print("[1/2] Cartella compilata ARGUS_Desktop individuata.")

    # 2. Crea il file ZIP distribuiscibile
    print("[2/2] Creazione archivio ZIP per GitHub Releases...")
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    shutil.make_archive(
        base_name=os.path.join(project_dir, "dist", "ARGUS_Desktop_v5.0"),
        format="zip",
        root_dir=os.path.join(project_dir, "dist"),
        base_dir="ARGUS_Desktop"
    )
    
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print("=" * 60)
    print(f"[OK] ARCHIVIO PRONTO PER GITHUB RELEASES!")
    print(f"     Percorso: {zip_path}")
    print(f"     Dimensione: {zip_size_mb:.2f} MB")
    print("=" * 60)

if __name__ == "__main__":
    package_release()
