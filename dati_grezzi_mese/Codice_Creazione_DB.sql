DROP TABLE IF EXISTS fatto_attrezzaggi CASCADE;
DROP TABLE IF EXISTS fatto_manutenzione CASCADE;
DROP TABLE IF EXISTS fatto_qualita CASCADE;
DROP TABLE IF EXISTS fatto_consumi_risorse CASCADE;
DROP TABLE IF EXISTS fatto_produzione_processo CASCADE;
DROP TABLE IF EXISTS dim_contenitore CASCADE;
DROP TABLE IF EXISTS dim_operatore CASCADE;
DROP TABLE IF EXISTS dim_stampo_anima CASCADE;
DROP TABLE IF EXISTS dim_macchina CASCADE;
DROP TABLE IF EXISTS dim_turno CASCADE;
DROP TABLE IF EXISTS dim_data CASCADE;

CREATE TABLE dim_data (
    id_data INTEGER PRIMARY KEY, -- formato AAAAMMGG
    data DATE NOT NULL UNIQUE,
    giorno SMALLINT NOT NULL CHECK (giorno BETWEEN 1 AND 31),
    mese SMALLINT NOT NULL CHECK (mese BETWEEN 1 AND 12),
    anno SMALLINT NOT NULL,
    giorno_settimana VARCHAR(9) NOT NULL,
    settimana_anno SMALLINT NOT NULL CHECK (settimana_anno BETWEEN 1 AND 53),
    is_festivo BOOLEAN NOT NULL
);

CREATE TABLE dim_turno (
    id_turno BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fascia_oraria TIME NOT NULL,
    descrizione VARCHAR(50) NOT NULL
);

CREATE TABLE dim_macchina (
    id_macchina BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codice_macchina VARCHAR(20) NOT NULL UNIQUE,
    modello VARCHAR(11) NOT NULL CHECK (modello IN ('ORIZZONTALE', 'VERTICALE')),
    reparto VARCHAR(30) NOT NULL
);

CREATE TABLE dim_stampo_anima (
    id_stampo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    numero_figure SMALLINT NOT NULL CHECK (numero_figure BETWEEN 1 AND 2),
    tempo_ciclo_ideale_sec NUMERIC(6,2) NOT NULL CHECK (tempo_ciclo_ideale_sec > 0)
);

CREATE TABLE dim_operatore (
    id_operatore BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    matricola VARCHAR(10) NOT NULL UNIQUE,
    nome_operatore VARCHAR(100) NOT NULL,
    qualifica VARCHAR(30) NOT NULL
);

CREATE TABLE dim_contenitore (
    id_contenitore BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codice_contenitore VARCHAR(20) NOT NULL UNIQUE,
    tipo_contenitore VARCHAR(20) NOT NULL CHECK (tipo_contenitore IN ('bancale', 'cassone')),
    numero_scatole_nel_bancale SMALLINT NOT NULL CHECK (numero_scatole_nel_bancale BETWEEN 0 AND 8)
);

CREATE TABLE fatto_produzione_processo (
    id_ciclo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_lotto VARCHAR(30) NOT NULL, -- dimensione degenere: identifica il riempimento del contenitore
    id_data INTEGER NOT NULL REFERENCES dim_data(id_data),
    id_turno BIGINT NOT NULL REFERENCES dim_turno(id_turno),
    id_macchina BIGINT NOT NULL REFERENCES dim_macchina(id_macchina),
    id_stampo BIGINT NOT NULL REFERENCES dim_stampo_anima(id_stampo),
    id_operatore BIGINT NOT NULL REFERENCES dim_operatore(id_operatore),
    id_contenitore BIGINT NOT NULL REFERENCES dim_contenitore(id_contenitore),
    timestamp_inizio TIMESTAMPTZ NOT NULL,
    timestamp_fine TIMESTAMPTZ NOT NULL CHECK (timestamp_fine > timestamp_inizio),
    pezzi_prodotti SMALLINT NOT NULL CHECK (pezzi_prodotti >= 0),
    pezzi_scartati_plc SMALLINT NOT NULL CHECK (pezzi_scartati_plc <= pezzi_prodotti),
    temperatura_cassa_c NUMERIC(5,1) NOT NULL CHECK (temperatura_cassa_c BETWEEN 0 AND 400),
    pressione_soffiaggio_bar NUMERIC(4,2) NOT NULL CHECK (pressione_soffiaggio_bar BETWEEN 0 AND 10),
    tempo_ciclo_effettivo_sec NUMERIC(7,2) GENERATED ALWAYS AS (
        ROUND(EXTRACT(EPOCH FROM (timestamp_fine - timestamp_inizio))::numeric, 2)
    ) STORED,
    CONSTRAINT uq_macchina_inizio UNIQUE (id_macchina, timestamp_inizio)
);
CREATE TABLE fatto_consumi_risorse (
    id_consumo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_data INTEGER NOT NULL REFERENCES dim_data(id_data),
    id_turno BIGINT NOT NULL REFERENCES dim_turno(id_turno),
    id_macchina BIGINT NOT NULL REFERENCES dim_macchina(id_macchina),
    consumo_elettrico_kwh NUMERIC(10,2) NOT NULL CHECK (consumo_elettrico_kwh >= 0),
    consumo_sabbia_kg NUMERIC(10,2) NOT NULL CHECK (consumo_sabbia_kg >= 0),
    consumo_leganti_litri NUMERIC(10,2) NOT NULL CHECK (consumo_leganti_litri >= 0),
    CONSTRAINT uq_consumo_turno_macchina UNIQUE (id_data, id_turno, id_macchina)
);

CREATE TABLE fatto_manutenzione (
    id_manutenzione BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_data INTEGER NOT NULL REFERENCES dim_data(id_data),
    id_turno BIGINT NOT NULL REFERENCES dim_turno(id_turno),
    id_macchina BIGINT NOT NULL REFERENCES dim_macchina(id_macchina),
    id_operatore BIGINT NOT NULL REFERENCES dim_operatore(id_operatore),
    timestamp_inizio TIMESTAMPTZ NOT NULL,
    timestamp_fine TIMESTAMPTZ NOT NULL CHECK (timestamp_fine > timestamp_inizio),
    durata_fermo_minuti NUMERIC(7,2) GENERATED ALWAYS AS (
        ROUND((EXTRACT(EPOCH FROM (timestamp_fine - timestamp_inizio)) / 60.0)::numeric, 2)
    ) STORED,
    causa_guasto VARCHAR(100) NOT NULL
);

CREATE TABLE fatto_attrezzaggi (
    id_attrezzaggio BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_data INTEGER NOT NULL REFERENCES dim_data(id_data),
    id_turno BIGINT NOT NULL REFERENCES dim_turno(id_turno),
    id_macchina BIGINT NOT NULL REFERENCES dim_macchina(id_macchina),
    id_stampo BIGINT NOT NULL REFERENCES dim_stampo_anima(id_stampo),
    id_operatore BIGINT NOT NULL REFERENCES dim_operatore(id_operatore),
    timestamp_inizio TIMESTAMPTZ NOT NULL,
    timestamp_fine TIMESTAMPTZ NOT NULL CHECK (timestamp_fine > timestamp_inizio),
    durata_cambio_minuti NUMERIC(7,2) GENERATED ALWAYS AS (
        ROUND((EXTRACT(EPOCH FROM (timestamp_fine - timestamp_inizio)) / 60.0)::numeric, 2)
    ) STORED
);
CREATE TABLE fatto_qualita (
    id_controllo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_lotto VARCHAR(30) NOT NULL UNIQUE, -- un solo collaudo per lotto
    id_contenitore BIGINT NOT NULL REFERENCES dim_contenitore(id_contenitore),
    id_data INTEGER NOT NULL REFERENCES dim_data(id_data),
    id_operatore BIGINT NOT NULL REFERENCES dim_operatore(id_operatore),
    pezzi_controllati INTEGER NOT NULL CHECK (pezzi_controllati > 0),
    pezzi_scartati INTEGER NOT NULL CHECK (pezzi_scartati <= pezzi_controllati),
    codice_difetto VARCHAR(10) CHECK (
        (pezzi_scartati > 0 AND codice_difetto IS NOT NULL) OR 
        (pezzi_scartati = 0 AND codice_difetto IS NULL)
    ),
    motivo_scarto VARCHAR(100),
    timestamp_controllo TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_produzione_lotto ON fatto_produzione_processo (id_lotto);
