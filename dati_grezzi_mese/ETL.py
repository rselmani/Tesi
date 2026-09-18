import csv
import datetime
import psycopg2
from psycopg2.extras import execute_batch
import os

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": os.environ.get("PGPASSWORD", ""),
    "host": "localhost",
    "port": 5432,  
}

CARTELLA = "dati_grezzi_mese"

def main():
    print("[1/4] Connessione a PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("[2/4] Popolamento automatico Dimensioni (Settembre 2026)...")
    
    cur.execute("TRUNCATE TABLE dim_data CASCADE;")
    data_rows = []
    giorni = {0: "lunedì", 1: "martedì", 2: "mercoledì", 3: "giovedì", 4: "venerdì", 5: "sabato", 6: "domenica"}

    # Festivita' civili e religiose italiane del 2026 (nessuna cade a settembre)
    festivita = {
        datetime.date(2026, 1, 1), datetime.date(2026, 1, 6), datetime.date(2026, 4, 6),
        datetime.date(2026, 4, 25), datetime.date(2026, 5, 1), datetime.date(2026, 6, 2),
        datetime.date(2026, 8, 15), datetime.date(2026, 11, 1), datetime.date(2026, 12, 8),
        datetime.date(2026, 12, 25), datetime.date(2026, 12, 26),
    }

    data_partenza = datetime.date(2026, 9, 1)
    for i in range(30): 
        d = data_partenza + datetime.timedelta(days=i)
        data_rows.append((int(d.strftime("%Y%m%d")), d, d.day, d.month, d.year, giorni[d.weekday()], int(d.strftime("%V")), d.weekday() >= 5, d in festivita))
    
    execute_batch(cur, "INSERT INTO dim_data (id_data, data, giorno, mese, anno, giorno_settimana, settimana_anno, is_weekend, is_festivo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", data_rows)

    cur.execute("TRUNCATE TABLE dim_turno RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO dim_turno (ora_inizio, ora_fine, durata_minuti, descrizione) VALUES (%s, %s, %s, %s)", [
        ("00:00:00", "08:00:00", 480, "Turno 1"),
        ("08:00:00", "16:00:00", 480, "Turno 2"),
        ("16:00:00", "00:00:00", 480, "Turno 3"),
    ])

    cur.execute("TRUNCATE TABLE dim_causale_fermo RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO dim_causale_fermo (codice_causale, descrizione, categoria) VALUES (%s, %s, %s)", [
        ("CAU-01", "Anomalia lettura termocoppia cassa d'anima", "Elettrico"),
        ("CAU-02", "Ugelli di sparo tappati", "Meccanico"),
        ("CAU-03", "Mancanza pressione linea pneumatica", "Pneumatico"),
        ("CAU-04", "Blocco slitta estrazione e ribaltamento", "Meccanico"),
        ("CAU-05", "Avaria resistenze elettriche semicassa", "Elettrico"),
    ])

    cur.execute("TRUNCATE TABLE dim_difetto RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO dim_difetto (codice_difetto, descrizione) VALUES (%s, %s)", [
        ("DIF-01", "Anima rotta"),
        ("DIF-02", "Anima piena"),
        ("DIF-03", "Anima fuori tolleranza"),
    ])

    cur.execute("TRUNCATE TABLE dim_macchina RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO dim_macchina (codice_macchina, modello, reparto) VALUES (%s, %s, %s)", [
        ("SOFF_ORIZZ_01", "ORIZZONTALE", "Animisteria"), ("SOFF_ORIZZ_02", "ORIZZONTALE", "Animisteria"), 
        ("SOFF_ORIZZ_03", "ORIZZONTALE", "Animisteria"), ("SOFF_VERT_01", "VERTICALE", "Animisteria"), ("SOFF_VERT_02", "VERTICALE", "Animisteria")
    ])

    cur.execute("TRUNCATE TABLE dim_stampo_anima RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO dim_stampo_anima (numero_figure, tempo_ciclo_ideale_sec) VALUES (%s, %s)", [
        (2, 42.0), (2, 38.0), (1, 55.0), (1, 62.0), (1, 48.0)
    ])

    cur.execute("TRUNCATE TABLE dim_operatore RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO dim_operatore (matricola, nome_operatore, qualifica) VALUES (%s, %s, %s)", [
        (f"MAT-{str(i).zfill(4)}", f"Operatore {i}", "Soffiatore") for i in range(1, 16)
    ])

    cur.execute("TRUNCATE TABLE dim_contenitore RESTART IDENTITY CASCADE;")
    cont_batch = []
    with open(f"{CARTELLA}/raw_dim_contenitore.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=';'):
            t_grezzo = str(r["tipo_contenitore"]).strip().lower()
            if "bancale" in t_grezzo: t_pulito = "bancale"
            elif "cassone" in t_grezzo or "metallico" in t_grezzo: t_pulito = "cassone"
            else: t_pulito = t_grezzo[:20]
            cont_batch.append((r["codice_contenitore"], t_pulito, int(r["numero_scatole_nel_bancale"])))
    execute_batch(cur, "INSERT INTO dim_contenitore (codice_contenitore, tipo_contenitore, numero_scatole_nel_bancale) VALUES (%s, %s, %s)", cont_batch)
    
    conn.commit()

    print("[3/4] Creazione Mapping per le chiavi...")
    cur.execute("SELECT codice_macchina, id_macchina FROM dim_macchina;")
    d_mac = {k.upper(): v for k, v in cur.fetchall()}

    cur.execute("SELECT matricola, id_operatore FROM dim_operatore;")
    d_op = {k.upper(): v for k, v in cur.fetchall()}
    
    cur.execute("SELECT codice_contenitore, id_contenitore FROM dim_contenitore;")
    d_box = {k.upper(): v for k, v in cur.fetchall()}

    cur.execute("SELECT descrizione, id_causale FROM dim_causale_fermo;")
    d_causale = {k.upper(): v for k, v in cur.fetchall()}

    cur.execute("SELECT codice_difetto, id_difetto FROM dim_difetto;")
    d_difetto = {k.upper(): v for k, v in cur.fetchall()}

    # turni ordinati per ora di inizio: l'id del turno si ricava dall'orario
    cur.execute("SELECT id_turno, ora_inizio FROM dim_turno ORDER BY ora_inizio;")
    turni = [(t[1].hour, t[0]) for t in cur.fetchall()]

    def id_turno_di(istante):
        """Turno a cui appartiene un evento, in base all'ora di inizio."""
        scelto = turni[0][1]
        for ora, id_t in turni:
            if istante.hour >= ora:
                scelto = id_t
        return scelto

    # CALENDARIO DI PRODUZIONE PIANIFICATA (tabella dei fatti senza misure)
    cur.execute("TRUNCATE TABLE fatto_calendario_produzione;")
    cur.execute("SELECT id_data FROM dim_data WHERE NOT is_weekend AND NOT is_festivo;")
    giorni_lavorativi = [r[0] for r in cur.fetchall()]
    calendario = [(g, t[1], m) for g in giorni_lavorativi for t in turni for m in d_mac.values()]
    execute_batch(cur, "INSERT INTO fatto_calendario_produzione (id_data, id_turno, id_macchina) VALUES (%s, %s, %s)", calendario)
    conn.commit()
    print(f"      Turni pianificati: {len(calendario)}")

    limite_inizio = datetime.datetime(2026, 9, 1, 0, 0, 0)
    limite_fine = datetime.datetime(2026, 9, 30, 23, 59, 59)

    def get_dataora(s): 
        s = s.strip()
        for fmt in ("%d/%m/%Y %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%Y/%m/%d %H:%M", "%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M"):
            try: 
                dt = datetime.datetime.strptime(s, fmt)
                if dt > limite_fine: return limite_fine
                if dt < limite_inizio: return limite_inizio
                return dt
            except ValueError: pass
        raise ValueError(f"Formato orario non riconosciuto: {s}")

    def get_data(s): 
        s = s.strip()
        for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d"):
            try: 
                dt = datetime.datetime.strptime(s, fmt).date()
                if dt > limite_fine.date(): return limite_fine.date()
                return dt
            except ValueError: pass
        raise ValueError(f"Formato data non riconosciuto: {s}")

    def get_f(s): return float(s.replace(",", "."))
    def get_s(s): return s.strip() if s and s.strip() else None

    print("[4/4] Caricamento Tabelle dei Fatti (Extract, Transform & Load)...")
    
    # 1. FATTO QUALITA' (CON NORMALIZZAZIONE PULITA DEI MOTIVI E CODICI DIFETTO)
    qual = []
    with open(f"{CARTELLA}/raw_qualita.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=';'):
            dt = get_dataora(r["orario_collaudo"])
            scartati = int(r["scartati"])
            
            c_dif = get_s(r["cod_difetto"])
            m_dif = get_s(r["motivo"])
            
            # Normalizzazione stringhe difetto a monte
            if c_dif:
                c_dif = c_dif.strip().upper()
                if c_dif in ["N/D", "N/A", "NESSUNO", "-", ""]:
                    c_dif = None
            if m_dif:
                m_dif = m_dif.strip().lower()
                if m_dif in ["n/d", "n/a", "nessuno", "-", "", " "]:
                    m_dif = None
                else:
                    m_dif = m_dif.capitalize() # Prima lettera maiuscola pulita
            
            if scartati == 0 or not c_dif or not m_dif:
                c_dif, m_dif = None, None

            id_difetto = d_difetto[c_dif] if c_dif else None

            qual.append((
                r["id_lotto"].strip().upper(),
                d_box[r["id_contenitore_rif"].strip().upper()], int(dt.strftime("%Y%m%d")), d_op[r["ispettore"].strip().upper()], 
                int(r["campione_pezzi"]), scartati, id_difetto, dt
            ))
            
    cur.execute("TRUNCATE TABLE fatto_qualita RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO fatto_qualita (id_lotto, id_contenitore, id_data, id_operatore, pezzi_controllati, pezzi_scartati, id_difetto, timestamp_controllo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", qual)

    # 2. FATTO MANUTENZIONE
    man = []
    with open(f"{CARTELLA}/raw_manutenzione.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=';'):
            ini = get_dataora(r["inizio_guasto"])
            fin = get_dataora(r["ripartenza"])
            if ini > fin: ini, fin = fin, ini
            man.append((
                int(ini.strftime("%Y%m%d")), id_turno_di(ini), 
                d_mac[r["impianto"].strip().upper()], d_op[r["matricola_tecnico"].strip().upper()], ini, fin,
                d_causale[r["descrizione_anomalia"].strip().upper()]
            ))
    cur.execute("TRUNCATE TABLE fatto_manutenzione RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO fatto_manutenzione (id_data, id_turno, id_macchina, id_operatore, timestamp_inizio, timestamp_fine, id_causale) VALUES (%s, %s, %s, %s, %s, %s, %s)", man)

    # 3. FATTO ATTREZZAGGI
    attr = []
    with open(f"{CARTELLA}/raw_attrezzaggi.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=';'):
            ini = get_dataora(r["inizio_setup"])
            fin = get_dataora(r["fine_setup"])
            if ini > fin: ini, fin = fin, ini
            attr.append((
                int(ini.strftime("%Y%m%d")), id_turno_di(ini), 
                d_mac[r["impianto"].strip().upper()], int(r["stampo_montato"]), d_op[r["matricola_addetto"].strip().upper()], ini, fin
            ))
    cur.execute("TRUNCATE TABLE fatto_attrezzaggi RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO fatto_attrezzaggi (id_data, id_turno, id_macchina, id_stampo, id_operatore, timestamp_inizio, timestamp_fine) VALUES (%s, %s, %s, %s, %s, %s, %s)", attr)

    # 4. FATTO CONSUMI
    cons = []
    with open(f"{CARTELLA}/raw_consumi.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=';'):
            dt = get_data(r["data_turno"])
            cons.append((
                int(dt.strftime("%Y%m%d")), int(r["turno"]), d_mac[r["macchina"].strip().upper()], 
                get_f(r["kwh"]), get_f(r["kg_sabbia"]), get_f(r["litri_legante"])
            ))
    cur.execute("TRUNCATE TABLE fatto_consumi_risorse RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO fatto_consumi_risorse (id_data, id_turno, id_macchina, consumo_elettrico_kwh, consumo_sabbia_kg, consumo_leganti_litri) VALUES (%s, %s, %s, %s, %s, %s)", cons)

    # 5. FATTO PRODUZIONE
    prod = []
    visti_macchina_tempo = set()
    
    with open(f"{CARTELLA}/raw_produzione.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=';'):
            ini = get_dataora(r["data_ora_avvio"])
            fin = get_dataora(r["data_ora_arresto"])
            
            if ini > fin: 
                ini, fin = fin, ini
            
            if ini == fin:
                fin = fin + datetime.timedelta(seconds=1)
            
            id_macchina = d_mac[r["linea"].strip().upper()]
            
            chiave_unica = (id_macchina, ini)
            while chiave_unica in visti_macchina_tempo:
                ini = ini + datetime.timedelta(seconds=1)
                if ini >= fin:  
                    fin = ini + datetime.timedelta(seconds=1)
                chiave_unica = (id_macchina, ini)
            
            visti_macchina_tempo.add(chiave_unica)
            
            prod.append((
                r["id_lotto"].strip().upper(),
                int(ini.strftime("%Y%m%d")), id_turno_di(ini), 
                id_macchina, int(r["cod_stampo_rif"]), d_op[r["badge_operatore"].strip().upper()], d_box[r["box_destinazione"].strip().upper()],
                ini, fin, int(r["pezzi_estratti"]), int(r["scarti_rilevati_plc"]), get_f(r["temperatura_letta"]), get_f(r["pressione_rilevata"])
            ))
            
    cur.execute("TRUNCATE TABLE fatto_produzione_processo RESTART IDENTITY CASCADE;")
    execute_batch(cur, "INSERT INTO fatto_produzione_processo (id_lotto, id_data, id_turno, id_macchina, id_stampo, id_operatore, id_contenitore, timestamp_inizio, timestamp_fine, pezzi_prodotti, pezzi_scartati_plc, temperatura_cassa_c, pressione_soffiaggio_bar) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", prod)
    conn.commit()
    cur.close()
    conn.close()
    print("\n[SUCCESSO] ETL Completato con pulizia stringhe e normalizzazione dati a monte!")

if __name__ == "__main__":
    main()
