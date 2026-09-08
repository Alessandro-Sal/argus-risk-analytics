import pytest
import re
import glob
import os
from core.ui_utils import resolve_metric_knowledge, KNOWN_METRICS_KNOWLEDGE_BASE, metric_card

def test_critical_metrics_no_false_positive_collisions():
    """Verifica che parole simili non collidano con metriche non correlate per via di sottostringhe."""
    
    # 1. Variazione Controvalore non deve essere VaR
    res_vc = resolve_metric_knowledge("Variazione Controvalore")
    assert "Value at Risk" not in res_vc
    assert "Variazione" in res_vc
    
    # 2. Variazione Peso non deve essere VaR
    res_vp = resolve_metric_knowledge("Variazione Peso")
    assert "Value at Risk" not in res_vp
    assert "Peso" in res_vp
    
    # 3. Interessi Risparmiati non deve essere TCO / Fee Drag
    res_ir = resolve_metric_knowledge("Interessi Risparmiati")
    assert "Fee Drag" not in res_ir
    assert "Interessi Risparmiati" in res_ir
    
    # 4. Carried Interest non deve essere TCO / Fee Drag
    res_ci = resolve_metric_knowledge("Carried Interest GP")
    assert "Fee Drag" not in res_ci
    assert "Carried Interest" in res_ci
    
    # 5. Duplicati Rilevati non deve essere Debt-to-Asset
    res_dup = resolve_metric_knowledge("Duplicati Rilevati")
    assert "Debt-to-Asset" not in res_dup
    assert "Duplicati" in res_dup
    
    # 6. Controvalore Incassato non deve essere Liquidità / Buffer
    res_inc = resolve_metric_knowledge("Controvalore Incassato")
    assert "Buffer" not in res_inc
    assert "Incassato" in res_inc
    
    # 7. Risparmio Extra / Mese non deve essere il Tasso di Risparmio %
    res_rx = resolve_metric_knowledge("Risparmio Extra / Mese")
    assert "Extra Investibile" in res_rx or "Extra" in res_rx
    
    # 8. VaR 95% deve matchare esattamente VaR
    res_var = resolve_metric_knowledge("VaR 95% Giornaliero")
    assert "Value at Risk" in res_var


def test_every_modal_has_strict_5_institutional_points():
    """Verifica che ogni modale prodotto contenga rigorosamente le 5 sezioni standard."""
    sample_labels = [
        "Patrimonio Netto",
        "Liquidità & Depositi",
        "Burn Rate Giornaliero",
        "Opportunity Drag (10y)",
        "Pareggio di Bilancio",
        "Totale Attivo (Assets)",
        "Indice di Solvibilità",
        "Yield to Maturity (YTM)",
        "Modified Duration",
        "Order Flow Imbalance (OFI)",
        "Zainetto Minus",
        "IVAFE Estero",
        "Target FIRE Number",
        "Safe Withdrawal Rate",
        "Etichetta Sconosciuta Test XYZ"
    ]
    
    required_sections = [
        "📌 Cos'è:",
        "📐 Come si calcola:",
        "🎯 A cosa serve:",
        "⚙️ Come viene calcolato da ARGUS:",
        "🔍 Come leggerlo:"
    ]
    
    for lbl in sample_labels:
        html = resolve_metric_knowledge(lbl)
        for sec in required_sections:
            assert sec in html, f"Sezione '{sec}' mancante per il label '{lbl}'"


def test_zero_generic_boilerplate_in_entire_project():
    """Scansiona tutti i file del progetto per garantire 0 occorrenze del vecchio testo boilerplate fisso."""
    files = sorted(glob.glob('src/pages/*.py') + glob.glob('core/**/*.py', recursive=True))
    all_cards = []
    
    for path in files:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        pattern = r'metric_card\s*\(\s*([^,\r\n\)]+)(?:,\s*([^,\r\n\)]+))?(?:,\s*([^,\r\n\)]+))?(?:,\s*([^,\r\n\)]+))?(?:,\s*help_text=([^\r\n\)]+))?'
        matches = re.finditer(pattern, content)
        for m in matches:
            raw_label = m.group(1).strip().strip("'\"")
            ht = m.group(5)
            if ht:
                ht = ht.strip().strip("'\"")
            all_cards.append((os.path.basename(path), raw_label, ht))

    assert len(all_cards) > 100, "Dovrebbero esserci oltre 100 card censite"
    
    old_boilerplate_1 = "Calcolato attraverso l'aggregazione certificata dei conti"
    old_boilerplate_2 = "Valore ottimale allineato con gli obiettivi strategici del profilo"
    
    for filename, lbl, ht in all_cards:
        res = resolve_metric_knowledge(lbl, ht)
        assert old_boilerplate_1 not in res, f"Boilerplate 1 trovato in {filename} per label '{lbl}'"
        assert old_boilerplate_2 not in res, f"Boilerplate 2 trovato in {filename} per label '{lbl}'"


def test_dynamic_fallback_differentiation():
    """Verifica che card differenti che vanno in fallback non ricevano la stessa identica spiegazione."""
    res_cost = resolve_metric_knowledge("Costo Inatteso Manutenzione Impianti")
    res_ratio = resolve_metric_knowledge("Quota di Conversione Lead")
    res_days = resolve_metric_knowledge("Tempo di Attesa Pratica Burocratica")
    
    # Il costo deve avere semaforo per metriche inverse (bassi = verdi)
    assert "Valori bassi o contenuti" in res_cost
    
    # Il ratio deve avere semaforo per percentuali/benchmark (alti = verdi)
    assert "Valore superiore al target" in res_ratio
    
    # La durata deve avere semaforo su orizzonte temporale
    assert "Orizzonte" in res_days
