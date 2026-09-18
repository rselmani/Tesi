# Data Warehouse ed ETL per il monitoraggio KPI in un reparto di animisteria
Codice della tesi di laurea triennale in Ingegneria Informatica
*"Sviluppo di un'Architettura Data Warehouse ed ETL per il Monitoraggio KPI e la Gestione
Logistica in un Reparto Industriale di Animisteria"* — Università degli Studi di Bergamo,
anno accademico 2025/2026.

Il repository contiene tutto ciò che serve a ricostruire da zero il Data Warehouse descritto
nella tesi: lo schema del database, il generatore dei dati grezzi e lo script di caricamento.

## Contenuto

| File | Descrizione |
| --- | --- |
| `Codice_Creazione_DB.sql` | Schema del Data Warehouse: 8 dimensioni e 6 tabelle dei fatti, con vincoli e colonne generate |
| `ETL.py` | Estrazione, pulizia e caricamento dei file CSV nel Data Warehouse |

## Prerequisiti

- PostgreSQL 12 o successivo (sviluppato su PostgreSQL 16)
- Python 3.9 o successivo (sviluppato su Python 3.14)
- Libreria `psycopg2`:

```bash
pip install psycopg2-binary
```

## Configurazione

I due script Python leggono i parametri di connessione dal dizionario `DB_CONFIG` in cima al
file. La password viene presa dalla variabile d'ambiente `PGPASSWORD`, così da non finire nel
repository:

```bash
export PGPASSWORD="la_tua_password"
```

Se il database, l'utente o la porta sono diversi da quelli predefiniti (`postgres`, `postgres`,
`5432`), modificali direttamente nel dizionario.

Il database deve interpretare gli orari privi di fuso come ora italiana:

```sql
ALTER DATABASE postgres SET timezone TO 'Europe/Rome';
```

## Esecuzione

L'ordine è obbligatorio: le tabelle devono esistere prima del caricamento, e i file CSV devono
essere stati generati prima di lanciare l'ETL.

```bash
# 1. creazione dello schema (cancella e ricrea tutte le tabelle)
psql -U postgres -d postgres -f CreazioneDatabase.sql

# 2. generazione dei dati grezzi nella cartella dati_grezzi_mese/
python3 GeneratoreDati.py

# 3. pulizia e caricamento nel Data Warehouse
python3 ETL.py
```

Entrambi gli script usano un percorso relativo per la cartella `dati_grezzi_mese`, quindi vanno
lanciati dalla directory del repository.

## Verifiche dopo il caricamento

```sql
-- collaudi senza i cicli corrispondenti (atteso: 0)
SELECT count(*) FROM fatto_qualita q
WHERE NOT EXISTS (SELECT 1 FROM fatto_produzione_processo p WHERE p.id_lotto = q.id_lotto);

-- lotti riempiti da più macchine o a cavallo di più turni (atteso: 0)
SELECT count(*) FROM (
  SELECT id_lotto FROM fatto_produzione_processo
  GROUP BY 1 HAVING count(DISTINCT (id_macchina, id_turno, id_data)) > 1) x;

-- lotti con pezzi prodotti diversi dai pezzi collaudati (atteso: 0)
SELECT count(*) FROM (
  SELECT p.id_lotto FROM fatto_produzione_processo p JOIN fatto_qualita q USING (id_lotto)
  GROUP BY 1, q.pezzi_controllati HAVING sum(p.pezzi_prodotti) <> q.pezzi_controllati) y;
```

## Visualizzazione

I cruscotti sono realizzati con Grafana 13.2.1, collegato a PostgreSQL tramite il connettore
nativo.

## Autore

Reda Selmani — Università degli Studi di Bergamo
