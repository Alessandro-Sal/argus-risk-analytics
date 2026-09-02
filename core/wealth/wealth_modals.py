# ============================================================
# core/wealth/wealth_modals.py
# ARGUS — Wealth Informative & Educational Modals (@st.dialog)
# Modali informativi, metodologie di calcolo e guide per i moduli Wealth
# ============================================================

import streamlit as st


@st.dialog("🏛️ Metodologia Stato Patrimoniale & Net Worth Consolidato", width="large")
def render_wealth_methodology_modal():
    """Modale informativo sulla metodologia di calcolo del Patrimonio Netto Consolidato."""
    st.markdown("""
    ### 🏛️ Architettura del Patrimonio Netto Consolidato (Net Worth)
    
    Il **Patrimonio Netto Consolidato** di ARGUS aggrega la totalità degli attivi e delle passività secondo i principi di contabilità patrimoniale internazionale (**IFRS / GIPS Wealth Guidelines**):

    $$\\text{Net Worth} = \\text{Liquidità} + \\text{Investimenti Quotati} + \\text{Immobili Net Equity} + \\text{Asset Illiquidi} + \\text{Previdenza} - \\text{Passività}$$

    #### 📊 I 5 Pilastri del Wealth Health Score (0 - 100):
    1. **Liquidità & Runway (Peso 25%)**: Copertura autonoma del fondo di emergenza su base mensile ($> 6$ mesi = punteggio massimo).
    2. **Tasso di Risparmio (Peso 25%)**: Percentuale di risparmio netto rispetto alle entrate totali ($> 20\%$ = eccellente).
    3. **Indebitamento & Leva DTI (Peso 20%)**: Rapporto tra rate di debito e reddito lordo ($< 30\%$ = ottimale).
    4. **Diversificazione Multi-Asset (Peso 15%)**: Assenza di concentrazione eccessiva su un singolo asset o classe illiquida.
    5. **Efficienza Previdenziale & Fiscale (Peso 15%)**: Saturazione deducibilità fondo pensione (€ 5.164,57) e gestione dello zainetto fiscale.
    """)
    st.caption("Standard di calcolo: ARGUS Family Office Engine • Certificazione IFRS/GIPS.")


@st.dialog("💸 Guida Metodologica: Cash Flow, 50/30/20 & Envelope Budgeting", width="large")
def render_budget_rule_methodology_modal():
    """Modale informativo sulla regola 50/30/20 e l'Envelope Budgeting."""
    st.markdown("""
    ### 💸 Metodologia di Gestione Flussi di Cassa & Budgeting
    
    #### ⚖️ La Regola Aurea 50 / 30 / 20:
    - **50% Bisogni Primari (Needs)**: Spese essenziali e non comprimibili (Affitto/Mutuo, Bollette, Alimentari, Trasporti, Assicurazioni).
    - **30% Desideri Discrezionali (Wants)**: Spese legate allo stile di vita e svago (Ristoranti, Viaggi, Shopping, Hobbies).
    - **20% Risparmio & Investimenti (Savings)**: Accantonamenti per il futuro (PAC su ETF, Fondo Pensione, Riserva di Liquidità).

    #### ✉️ Envelope Budgeting Dinamico:
    Assegna un massimale mensile a ciascuna categoria di spesa. Gli sforamenti vengono evidenziati in tempo reale con avviso di **Cash Drag** o sovracosto.
    """)
    st.caption("Standard di allocazione: Consumer Finance & Wealth Optimization Standards.")


@st.dialog("⌚ Metodologia Valutazione Asset Illiquidi, PE & Private Debt", width="large")
def render_illiquids_methodology_modal():
    """Modale informativo per la valutazione di orologi di lusso, private equity e private debt."""
    st.markdown("""
    ### ⌚ Valutazione Asset Illiquidi, Private Markets & Caveau
    
    #### 🔍 Metodologie di Perizia Applicate:
    1. **Orologi di Lusso & Collezionismo**: Valutazione basata sui prezzi transati effettivi di mercato secondario (WatchCharts / Chrono24 Index), tenendo conto di referenza, condizioni (Unworn / Very Good) e presenza di Corredo Completo (*Box & Papers*).
    2. **Private Equity & Venture Capital**:
       - **J-Curve Modeling**: Tracciamento del drawdown iniziale nei primi anni di investimento dovuto ai richiami di capitale e commissioni di gestione, seguito dalla fase di realizzo e maturazione dell'IRR.
       - **Metriche Istituzionali**: MOIC (*Multiple on Invested Capital*), DPI (*Distributed to Paid-In*) e RVPI (*Residual Value to Paid-In*).
    3. **Private Debt & Direct Lending**:
       - **Cash Flow Waterfall**: Priorità di pagamento sequenziale (Senior Secured $\\to$ Unitranche $\\to$ Mezzanino $\\to$ Equity).
       - **Covenants Tracking**: Monitoraggio continuo di Leva (Net Debt/EBITDA), Copertura Interessi (ICR) e Debt Service Coverage (DSCR).
    """)


@st.dialog("🎯 Metodologia Goal-Based Investing & Merton Jump-Diffusion", width="large")
def render_goal_methodology_modal():
    """Modale informativo per Goal-Based Investing e Merton Model."""
    st.markdown("""
    ### 🎯 Goal-Based Investing & Success Probability Index (SPI %)
    
    #### 🎲 Simulazione Stocastica a 5.000 Scenari:
    Il motore stocastico ARGUS modella l'accumulazione patrimoniale per ciascun traguardo di vita mediante il **Processo di Diffusione con Salti di Merton (1976)**:

    $$dS_t = \\mu S_t dt + \\sigma S_t dW_t + J_t S_t dN_t$$

    - $dW_t$: Moto Browniano Standard (fluttuazione ordinaria di mercato).
    - $dN_t$: Processo di Poisson per crash e shock di mercato asimmetrici.
    - $J_t$: Ampiezza log-normale dei salti.

    #### 🛡️ Target-Date Glide Path:
    Algoritmo di de-risking sigmoideo che riduce progressivamente l'esposizione azionaria all'avvicinarsi della data target per proteggere il capitale accumulato.
    """)


@st.dialog("🏡 Metodologia Real Estate Net Equity & Dynamic LTV", width="large")
def render_real_estate_methodology_modal():
    """Modale informativo per la gestione immobiliare e mutui."""
    st.markdown("""
    ### 🏡 Immobili, Net Equity & Sostenibilità Finanziaria
    
    #### 📐 Calcolo del Net Home Equity:
    $$\\text{Net Home Equity} = \\text{Valore di Mercato Attuale dell'Immobile} - \\text{Debito Residuo del Mutuo}$$

    #### 📊 Indicatori Chiave di Rischio:
    - **Loan-to-Value (LTV %)**: Rapporto percentuale tra debito residuo e valore di perizia attuale ($< 60\%$ = soglia di sicurezza bancaria).
    - **Cap Rate Netto (Rendimento da Locazione)**: Rapporto tra canoni netti annui e valore di acquisto/mercato.
    - **Piano di Ammortamento alla Francese**: Rata costante con quota interessi decrescente e quota capitale crescente.
    """)


@st.dialog("📑 Metodologia Fiscalità, Quadro RW & Scudo Fiscale", width="large")
def render_fiscal_methodology_modal():
    """Modale informativo sulla fiscalità patrimoniale e internazionale."""
    st.markdown("""
    ### 📑 Fiscalità Patrimoniale, Monitoraggio Fiscale & Tax Alpha
    
    #### 🇮🇹 Regime Fiscale Italiano (TUIR):
    - **Quadro RW / RT**: Monitoraggio delle attività finanziarie e conti correnti detenuti all'estero.
    - **IVAFE**: Imposta sul valore delle attività finanziarie estere (0,20% su dossier titoli, € 34,20 su c/c con giacenza $> € 5.000$).
    - **Zainetto Fiscale & Minusvalenze**: Compensabilità delle perdite pregresse entro i 4 anni successivi esclusivamente con *Redditi Diversi* (Azioni, ETC, Certificati con maxicedola).

    #### 🌍 Regimi Speciali HNWI & Cross-Border:
    - **Art. 24-bis TUIR (Neo-Residenti)**: Imposta forfettaria sostitutiva annuale (€ 100k/200k) su tutti i redditi esteri ed esenzione da successione estera.
    - **Svizzera (Zugo/Zurigo)**: 0% capital gain su investimenti privati mobiliari.
    - **Lussemburgo SOPARFI**: Regime holding di partecipazione con azzeramento ritenute infragruppo DTT.
    """)


@st.dialog("👨‍👩‍👧‍👦 Metodologia Successione, Patti di Famiglia & Holding", width="large")
def render_succession_methodology_modal():
    """Modale informativo sulla pianificazione successoria e family office."""
    st.markdown("""
    ### 👨‍👩‍👧‍👦 Passaggio Generazionale & Strutture di Holding
    
    #### ⚖️ Imposte di Successione & Franchigie (Italia):
    - **Linea Retta (Coniuge e Figli)**: Aliquota 4% con franchigia di **€ 1.000.000** per ciascun beneficiario.
    - **Fratelli e Sorelle**: Aliquota 6% con franchigia di **€ 100.000**.
    - **Altri Parenti**: Aliquota 6% senza franchigia.
    - **Estranei**: Aliquota 8% senza franchigia.

    #### 🛡️ Strumenti di Protezione Patrimoniale:
    - **Patti di Famiglia (Art. 768-bis c.c.)**: Trasferimento anticipato e irrevocabile dell'azienda o delle quote di holding all'erede designato senza rischio di future azioni di riduzione.
    - **Holding Familiare**: Centralizzazione del controllo, governance a patti parasociali e ottimizzazione dei flussi divisori tra rami familiari.
    """)


@st.dialog("🤖 Metodologia AI Wealth Copilot & Diagnostica Autonoma", width="large")
def render_ai_health_score_modal():
    """Modale informativo per l'AI Copilot e Wealth Health Score."""
    st.markdown("""
    ### 🤖 Intelligenza Artificiale Applicata alla Gestione Patrimoniale
    
    #### 🔍 Motore Diagnostico a Due Livelli:
    1. **NLG Deterministico Offline (100% Locale & Privato)**: Elaborazione immediata e rigorosa di regole matematiche per rilevare colli di bottiglia su liquidità, debito, concentrazione e scadenze fiscali.
    2. **AI Copilot & Advisor**: Assistente interattivo integrato per rispondere a domande complesse sul patrimonio in tempo reale senza dispersioni o latenze.

    #### 📑 Executive Quarterly Review NLG:
    Generazione automatica del Memorandum Direzionale trimestrale per Family Office, strutturato in 5 sezioni conformi agli standard di Private Banking svizzero e internazionale.
    """)
