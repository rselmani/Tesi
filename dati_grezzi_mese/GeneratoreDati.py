import csv
import datetime
import math
import os
import random

cartella_out = "dati_grezzi_mese"
os.makedirs(cartella_out, exist_ok=True)

# -------------------------------------------------------------------------
# 1. PARCO ASSET FISSI E REGOLE
# -------------------------------------------------------------------------
macchine = ["SOFF_ORIZZ_01", "SOFF_ORIZZ_02", "SOFF_ORIZZ_03", "SOFF_VERT_01", "SOFF_VERT_02"]

stampi = {
    1: {"figure": 2, "ciclo": 42.0, "pezzi_scatola": 20, "cap_cassone": 300, "nome": "Anima Scatola Guida"},
    2: {"figure": 2, "ciclo": 38.0, "pezzi_scatola": 24, "cap_cassone": 350, "nome": "Anima Collettore Scarico"},
    3: {"figure": 1, "ciclo": 55.0, "pezzi_scatola": 32, "cap_cassone": 400, "nome": "Anima Monoblocco Cilindri"},
    4: {"figure": 1, "ciclo": 62.0, "pezzi_scatola": 20, "cap_cassone": 250, "nome": "Anima Testa Motore"},
    5: {"figure": 1, "ciclo": 48.0, "pezzi_scatola": 40, "cap_cassone": 450, "nome": "Anima Pompa Olio"}
}

operatori = [f"MAT-{str(i).zfill(4)}" for i in range(1, 16)]
turni_orari = [(0, 8), (8, 16), (16, 24)]

guasti_catalogo = [
    "Anomalia lettura termocoppia cassa d'anima", "Ugelli di sparo tappati",
    "Mancanza pressione linea pneumatica", "Blocco slitta estrazione e ribaltamento",
    "Avaria resistenze elettriche semicassa"
]

# -------------------------------------------------------------------------
# 2. FUNZIONI PER "SPORCARE" I DATI (Simulazione rumore industriale)
# -------------------------------------------------------------------------
def sporca_stringa(s):
    if not isinstance(s, str): return s
    rand = random.random()
    if rand < 0.10: return f"  {s} "     
    elif rand < 0.20: return s.lower()   
    elif rand < 0.25: return s.capitalize() 
    return s

def sporca_dataora(dt):
    """Genera formati data/ora disomogenei"""
    rand = random.random()
    if rand < 0.15: return dt.strftime("%d-%m-%Y %H:%M:%S")    # Trattini
    elif rand < 0.30: return dt.strftime("%Y/%m/%d %H:%M:%S")  # Anno prima
    elif rand < 0.45: return dt.strftime("%d/%m/%Y %H:%M")     # Senza secondi
    else: return dt.strftime("%d/%m/%Y %H:%M:%S")              # Standard grezzo

def sporca_data_semplice(dt):
    """Genera formati data disomogenei"""
    rand = random.random()
    if rand < 0.20: return dt.strftime("%d-%m-%Y")
    elif rand < 0.40: return dt.strftime("%Y/%m/%d")
    else: return dt.strftime("%d/%m/%Y")

def format_f(val): return f"{val:.2f}".replace(".", ",")

# -------------------------------------------------------------------------
# 3. PARCO CONTENITORI (20 Bancali + 15 Cassoni)
# -------------------------------------------------------------------------
parco_contenitori = {}
contatore_lotti = {}
lotto_corrente = None
dati_dim_contenitore = []

for i in range(1, 21):
    cod = f"BANC_{str(i).zfill(4)}"
    parco_contenitori[cod] = {"tipo": "bancale in polistirolo", "disponibile_dal": datetime.datetime(2026, 9, 1, 0, 0, 0), "in_uso": False}
    dati_dim_contenitore.append({"codice_contenitore": cod, "tipo_contenitore": "bancale in polistirolo", "numero_scatole_nel_bancale": 8})

for i in range(1, 16):
    cod = f"CASS_{str(i).zfill(4)}"
    parco_contenitori[cod] = {"tipo": "cassone metallico", "disponibile_dal": datetime.datetime(2026, 9, 1, 0, 0, 0), "in_uso": False}
    dati_dim_contenitore.append({"codice_contenitore": cod, "tipo_contenitore": "cassone metallico", "numero_scatole_nel_bancale": 0})

def assegna_contenitore(istante_richiesta):
    candidati = [cod for cod, info in parco_contenitori.items() if not info["in_uso"] and info["disponibile_dal"] <= istante_richiesta]
    if not candidati: candidati = sorted([c for c in parco_contenitori if not parco_contenitori[c]["in_uso"]], key=lambda x: parco_contenitori[x]["disponibile_dal"])
    scelto = random.choice(candidati[:5])
    parco_contenitori[scelto]["in_uso"] = True
    return scelto, parco_contenitori[scelto]["tipo"]

# -------------------------------------------------------------------------
# 4. MOTORE DI SIMULAZIONE E SCHEDULAZIONE
# -------------------------------------------------------------------------
random.seed(42)
slot_disponibili = [(g, t, m) for g in range(1, 31) if datetime.date(2026, 9, g).weekday() < 5 for t in range(3) for m in macchine]
random.shuffle(slot_disponibili)
slot_guasti = slot_disponibili[:15]

data_inizio = datetime.datetime(2026, 9, 1, 0, 0, 0)
dati_prod, dati_cons, dati_man, dati_attr, dati_qual = [], [], [], [], []

def genera_nuovo_lotto(): return random.randint(1800, 3800)
stato_macchine = {m: {"stampo": (i % 5) + 1, "pezzi_residui_lotto": genera_nuovo_lotto()} for i, m in enumerate(macchine)}

# Stati interni per simulare il rumore stocastico dei sensori per ciascuna macchina
sensori_macchine = {m: {"temp": 290.0, "press": 5.80} for m in macchine}

for giorno in range(30):
    data_cur = data_inizio + datetime.timedelta(days=giorno)
    if data_cur.weekday() >= 5: continue

    for idx_t, (h_in, h_out) in enumerate(turni_orari):
        id_turno = idx_t + 1
        ops_turno = operatori[idx_t*5 : (idx_t+1)*5]
        t_inizio = data_cur.replace(hour=h_in)
        t_fine = data_cur.replace(hour=0) + datetime.timedelta(days=1) if h_out == 24 else data_cur.replace(hour=h_out)

        for idx_m, cod_m in enumerate(macchine):
            operatore = ops_turno[idx_m]
            is_vert = "VERT" in cod_m
            orologio = t_inizio
            pezzi_turno = 0
            
            cod_box, tipo_box, pezzi_nel_box = None, None, 0

            def scarica_contenitore(orario, fine_turno_senza_collaudo=False):
                global cod_box, tipo_box, pezzi_nel_box, lotto_corrente
                if pezzi_nel_box > 0 and cod_box is not None:
                    st_info = stampi[stato_macchine[cod_m]["stampo"]]
                    
                    # Taratura al ~3.2% di scarto per la resa del ~96.8%
                    scarti = int(round(pezzi_nel_box * random.uniform(0.025, 0.040)))
                    if scarti < 1 and pezzi_nel_box > 10: scarti = 1
                    if scarti > pezzi_nel_box: scarti = pezzi_nel_box
                    
                    c_dif, m_dif = ("", "")
                    if scarti > 0:
                        scelta = random.randint(1, 3)
                        if scelta == 1: c_dif, m_dif = "DIF-01", "anima rotta"
                        elif scelta == 2: c_dif, m_dif = "DIF-02", "anima piena"
                        else: c_dif, m_dif = "DIF-03", "anima fuori tolleranza"
                    else:
                        c_dif = random.choice(["", "", "", "N/D", "N/A", "nessuno", " "])

                    dati_qual.append({
                        "id_lotto": lotto_corrente,
                        "id_contenitore_rif": sporca_stringa(cod_box),
                        "data_verifica": sporca_data_semplice(orario),
                        "ispettore": sporca_stringa(operatore),
                        "campione_pezzi": pezzi_nel_box,
                        "scartati": scarti,
                        "cod_difetto": sporca_stringa(c_dif),
                        "motivo": sporca_stringa(m_dif),
                        "orario_collaudo": sporca_dataora(orario)
                    })
                    parco_contenitori[cod_box]["in_uso"] = False
                    parco_contenitori[cod_box]["disponibile_dal"] = orario + datetime.timedelta(hours=6)

                elif cod_box is not None and fine_turno_senza_collaudo:
                    parco_contenitori[cod_box]["in_uso"] = False

                pezzi_nel_box, cod_box, tipo_box, lotto_corrente = 0, None, None, None

            guasto_corrente = None
            if (giorno + 1, idx_t, cod_m) in slot_guasti:
                guasto_corrente = (random.randint(25, 55), random.choice(guasti_catalogo))

            while orologio < t_fine:
                if guasto_corrente and (t_inizio + datetime.timedelta(hours=2, minutes=30)) <= orologio:
                    dur_g = guasto_corrente[0]
                    fine_g = orologio + datetime.timedelta(minutes=dur_g)
                    dati_man.append({
                        "inizio_guasto": sporca_dataora(orologio),
                        "ripartenza": sporca_dataora(fine_g),
                        "impianto": sporca_stringa(cod_m),
                        "matricola_tecnico": sporca_stringa(operatore),
                        "descrizione_anomalia": sporca_stringa(guasto_corrente[1])
                    })
                    orologio = fine_g
                    guasto_corrente = None
                    continue

                if stato_macchine[cod_m]["pezzi_residui_lotto"] <= 0:
                    scarica_contenitore(orologio)
                    dur_setup = random.randint(30, 45)
                    fine_setup = orologio + datetime.timedelta(minutes=dur_setup)

                    stampo_prec = stato_macchine[cod_m]["stampo"]
                    nuovo_s = random.choice([s for s in stampi.keys() if s != stampo_prec])
                    dati_attr.append({
                        "inizio_setup": sporca_dataora(orologio),
                        "fine_setup": sporca_dataora(fine_setup),
                        "impianto": sporca_stringa(cod_m),
                        "stampo_montato": nuovo_s,
                        "matricola_addetto": sporca_stringa(operatore)
                    })
                    stato_macchine[cod_m]["stampo"] = nuovo_s
                    stato_macchine[cod_m]["pezzi_residui_lotto"] = genera_nuovo_lotto()
                    orologio = fine_setup
                    continue

                if cod_box is None:
                    cod_box, tipo_box = assegna_contenitore(orologio)
                    contatore_lotti[cod_box] = contatore_lotti.get(cod_box, 0) + 1
                    lotto_corrente = f"{cod_box}-{contatore_lotti[cod_box]:04d}"   # chiave di lotto

                st_info = stampi[stato_macchine[cod_m]["stampo"]]
                durata_ciclo = st_info["ciclo"] + random.uniform(0.8, 2.2)
                fine_sparo = orologio + datetime.timedelta(seconds=durata_ciclo)

                # --- SIMULAZIONE REALISTICA CON RUMORE CASUALE (SENZA SINUSOIDI) ---
                sensori_macchine[cod_m]["temp"] += random.uniform(-0.25, 0.25)
                sensori_macchine[cod_m]["temp"] = max(287.0, min(293.0, sensori_macchine[cod_m]["temp"]))

                sensori_macchine[cod_m]["press"] += random.uniform(-0.03, 0.03)
                sensori_macchine[cod_m]["press"] = max(5.60, min(6.00, sensori_macchine[cod_m]["press"]))

                temp = sensori_macchine[cod_m]["temp"]
                press = sensori_macchine[cod_m]["press"]
                # -----------------------------------------------------------------

                dati_prod.append({
                    "id_lotto": lotto_corrente,
                    "linea": sporca_stringa(cod_m),
                    "cod_stampo_rif": stato_macchine[cod_m]["stampo"],
                    "badge_operatore": sporca_stringa(operatore),
                    "box_destinazione": sporca_stringa(cod_box),
                    "data_ora_avvio": sporca_dataora(orologio),
                    "data_ora_arresto": sporca_dataora(fine_sparo),
                    "pezzi_estratti": st_info["figure"],
                    "scarti_rilevati_plc": 0,
                    "temperatura_letta": format_f(temp),
                    "pressione_rilevata": format_f(press)
                })

                pezzi_estratti = st_info["figure"]
                pezzi_turno += pezzi_estratti
                pezzi_nel_box += pezzi_estratti
                stato_macchine[cod_m]["pezzi_residui_lotto"] -= pezzi_estratti

                cap_limite = (st_info["pezzi_scatola"] * 8) if tipo_box == "bancale in polistirolo" else st_info["cap_cassone"]
                if pezzi_nel_box >= cap_limite:
                    scarica_contenitore(fine_sparo)

                orologio = fine_sparo + datetime.timedelta(seconds=14)

            scarica_contenitore(t_fine, fine_turno_senza_collaudo=True)

            if pezzi_turno > 0:
                mult = 1.28 if is_vert else 1.0
                kwh = (95.0 + (pezzi_turno * 0.35)) * mult
                sabbia = (pezzi_turno * 4.4) * mult
                resina = sabbia * 0.018

                dati_cons.append({
                    "data_turno": sporca_data_semplice(data_cur),
                    "turno": id_turno,
                    "macchina": sporca_stringa(cod_m),
                    "kwh": format_f(kwh),
                    "kg_sabbia": format_f(sabbia),
                    "litri_legante": format_f(resina)
                })

# -------------------------------------------------------------------------
# 5. SALVATAGGIO CSV
# -------------------------------------------------------------------------
def salva_csv(nome, dati):
    if not dati: return
    p = os.path.join(cartella_out, f"{nome}.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dati[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(dati)

salva_csv("raw_dim_contenitore", dati_dim_contenitore)
salva_csv("raw_produzione", dati_prod)
salva_csv("raw_consumi", dati_cons)
salva_csv("raw_manutenzione", dati_man)
salva_csv("raw_attrezzaggi", dati_attr)
salva_csv("raw_qualita", dati_qual)
print("\nDati grezzi rigenerati con successo (Sensori stocastici realistici e resa ~96.8%)!")