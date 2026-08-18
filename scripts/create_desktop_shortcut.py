"""
Script per la creazione automatica del collegamento Desktop di Windows (ARGUS.lnk)
con l'icona applicativa personalizzata 'Occhio di Argus' e refresh cache icone.
"""

import os
import sys
import subprocess

def create_shortcut():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    desktop_dir = os.path.join(os.environ["USERPROFILE"], "Desktop")
    shortcut_path = os.path.join(desktop_dir, "ARGUS Risk Analytics.lnk")
    
    icon_path = os.path.join(project_dir, "docs", "argus_icon.ico")
    if not os.path.exists(icon_path):
        gen_script = os.path.join(project_dir, "scripts", "generate_icon.py")
        if os.path.exists(gen_script):
            subprocess.run([sys.executable, gen_script], check=False)
            
    # Utilizza pythonw.exe per lanciare desktop_launcher.py in finestra nativa senza CMD
    pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pythonw_path):
        pythonw_path = sys.executable
        
    target_path = pythonw_path
    args = f'"{os.path.join(project_dir, "desktop_launcher.py")}"'

    ps_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
    $Shortcut.TargetPath = "{target_path}"
    $Shortcut.Arguments = '{args}'
    $Shortcut.WorkingDirectory = "{project_dir}"
    $Shortcut.IconLocation = "{icon_path}, 0"
    $Shortcut.Description = "ARGUS — Risk Analytics Platform Desktop App"
    $Shortcut.Save()

    # Notifica la Shell di Windows per aggiornare istantaneamente la cache delle icone Desktop
    $code = @"
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
"@
    $type = Add-Type -MemberDefinition $code -Name Shell32 -Namespace Win32 -PassThru
    $type::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    """
    
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
        print(f"[OK] Scorciatoia Desktop creata con successo in: {shortcut_path}")
        print(f"     Destinazione: {target_path}")
        print(f"     Icona associata: {icon_path}")
    except Exception as e:
        print(f"[ERRORE] Creazione collegamento fallita: {e}")

if __name__ == "__main__":
    create_shortcut()
