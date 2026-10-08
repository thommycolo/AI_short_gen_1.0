# Design System & GUI Architecture: AI Short Generator (1.0)
### Specifica di Design dell'Interfaccia, UX/UI, Wireframe e Sistema Cromatico
*Versione Specifica 1.0 — Documento di Design Esecutivo*

---

## 1. Filosofia di Design & Principi Guida

L'applicazione **AI Short Generator 1.0** è concepita secondo i principi del **Design Professionale Silenzioso** (*Quiet & Focused Workflow*). La sua interfaccia deve offrire un'esperienza fluida sia all'utente che desidera completare un video in due clic, sia al creatore esperto che esige il pieno controllo su ogni micro-parametro.

### I Tre Pilastri Fondamentali

1. **Atmosfera Cromatica Morbida & Anti-Affaticamento**:
   - **Toni scuri, ma rigorosamente non neri**: Il nero assoluto (`#000000`) crea contrasti eccessivi e affaticamento visivo. L'interfaccia adotta sfumature profonde di grafite, ardesia e cenere fredda.
   - **Divieto categorico di colori fluo o ad alto contrasto**: Nessun verde acido (`#00FF00`), rosa shocking, giallo evidenziatore o ciano saturato. Tutti i colori funzionali e di accento utilizzano toni polverosi (*dusty*), desaturati, caldi e omogenei.
2. **Architettura a Spazio Ottimizzato (Nessun Ingombro Inutile)**:
   - Anziché occupare gran parte della schermata con una mastodontica casella di testo, la gestione degli script è demandata a una **barra di selezione compatta** collegata a **finestre modali dedicate**.
   - L'utente può popolare in anticipo un archivio di testi (repository di idee) tramite una finestra dedicata. Il backend valida ogni inserimento contro lo storico, salvandolo solo se inedito con un **nome di contesto semantico (non casuale)**.
   - Uno script utilizzato per generare video short viene marcato permanentemente come `UTILIZZATO` e **bloccato per il futuro**, ma mai dimenticato dallo storico.
3. **Controllo Vocale & Visivo Avanzato (Qwen3-TTS Suite & Live Safe Zones)**:
   - Integrazione completa di **Qwen3-TTS**: Voci Predefinite con istruzioni emotive (`instruct`), **Zero-Shot Voice Cloning** con pre-caching dei profili vocali, **Voice Design** (creazione di voci artificiali da prompt testuale) e streaming audio sub-100ms.
   - Un player video interattivo 9:16 posizionato sul lato destro mostra sempre l'anteprima del risultato, con la possibilità di attivare le maschere delle aree sicure (*Safe Zones*) di TikTok, Instagram Reels e YouTube Shorts per garantire che i sottotitoli non siano mai coperti dai pulsanti social.

### Architettura Desktop Nativa Windows (.exe) — NO WebApp
- **Applicazione Desktop Nativa Autoportante**: Il software viene distribuito con un **file eseguibile launcher nativo Windows 64-bit** (`AI_Short_Generator.exe`, ad avvio istantaneo < 1 secondo) impacchettato con architettura portabile **PyInstaller `--onedir`** e installatore standard Windows guidato via **Inno Setup** (`AI_Short_Generator_Setup_v1.0.exe`).
- **Nessuna Decompressione Bloat in %TEMP%**: Evita l'approccio `--onefile` che scompatta 10 GB a ogni avvio congelando lo schermo; le DLL CUDA e i pesi vengono letti direttamente e istantaneamente dalla directory di installazione locale.
- **Divieto Assoluto di WebApp o Browser**: L'applicazione **NON è una WebApp**, non si apre all'interno di un browser web (Chrome, Edge o Firefox) e **non utilizza framework web** (zero Flask, zero FastAPI, zero Streamlit, zero Gradio) né wrapper web pesanti (zero Electron, zero Chromium Embedded Framework).
- **GUI Qt/PySide6 con Rendering Hardware Diretto**: L'interfaccia grafica opera direttamente sulle API grafiche native di Windows (DirectX/OpenGL) a 60 FPS con bassissimo consumo di memoria RAM.
- **Finestre e Controlli Nativi**: Barra del titolo personalizzata con styling dark, dialoghi modali e drawer fluidi, integrazione nativa con la barra delle applicazioni di Windows (icona `.ico` 256x256 e splash screen di avvio).

---

## 2. Palette Cromatica & Token di Design

Tutta l'interfaccia fa riferimento a un insieme unificato di token cromatici a bassa saturazione.

```
+-----------------------------------------------------------------------------------------+
|                                    SISTEMA DEI COLORI                                   |
+-----------------------------------------------------------------------------------------+
| TOKEN                | CODICE HEX  | DESCRIZIONE & UTILIZZO                             |
+----------------------+-------------+----------------------------------------------------+
| bg-base              | #181A20     | Sfondo primario della finestra (Ardesia Profonda)  |
| bg-surface           | #21242C     | Sfondo delle card e dei pannelli di lavoro         |
| bg-surface-elevated  | #2A2E38     | Drawer secondari a scomparsa, finestre modali      |
| bg-interactive-hover | #333845     | Stato hover di bottoni, liste e selettori          |
| border-subtle        | #343946     | Linee divisorie e bordi non invasivi               |
| border-focus         | #4C5466     | Bordo per campi di testo e controlli attivi        |
| text-primary         | #DCE0EA     | Testo principale ad alta leggibilità (Perla Chiaro)|
| text-secondary       | #949CAE     | Etichette descrittive, unità di misura, metadati   |
| text-muted           | #666E7F     | Testo disabilitato, placeholder, watermark         |
| accent-indigo        | #6B82A6     | Accento principale elegante (Indaco Polveroso)     |
| accent-indigo-hover  | #7E95BC     | Hover dell'accento principale                      |
| accent-warm-sand     | #BFA175     | Evidenziazione sottotitoli attiva (Sabbia Calda)   |
| status-available     | #729B84     | Script disponibile per la produzione (Salvia)      |
| status-locked-used   | #5A6273     | Script utilizzato / bloccato per il futuro (Ardesia)|
| status-warning       | #C4A36B     | Avviso duplicato o testo vicino al limite (Ambra)  |
| status-error         | #AA7373     | Errore o duplicato bloccato (Rosa Antico)          |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Tipografia e Ritmo Visivo

- **Carattere di Sistema GUI**: `Inter`, `Segoe UI Variable` o `Roboto` (Linee pulite, eccellente leggibilità a dimensioni ridotte).
- **Carattere di Rendering Sottotitoli**: Caratteri ad alto impatto con supporto ai pesi Bold ed ExtraBold:
  - `Montserrat Black` (Moderno e impattante)
  - `Anton` (Stile tipico dei video virali)
  - `The Bold Font` (Solido, geometrico)
  - `Poppins SemiBold` (Morbido e contemporaneo)

---

## 4. Architettura della Schermata Principale (Layout Ottimizzato)

Grazie alla barra compattata per la gestione degli script e alla card multimediale per la Voice Suite, l'interfaccia offre una visione d'insieme chiara e priva di scroll orizzontali:

```
+----------------------------------------------------------------------------------------------------+
|  [Logo] AI SHORT GENERATOR 1.0     | Preset: [ Reddit Stories v ] | [ 📋 Coda Batch (Audit) ] [ Esporta ]|
+----------------------------------------------------------------------------------------------------+
|  COLONNA DI SINISTRA: WORKSPACE DI CONFIGURAZIONE (58%) | COLONNA DI DESTRA: MONITOR 9:16 & BATCH (42%)|
|                                                         |                                              |
|  +-- 1. SCRIPT ATTIVO & REPOSITORY -------------------+ |  +-- MONITOR DI ANTEPRIMA (1080x1920) -----+ |
|  | [ ➕ Nuovo Script ]   [ 📂 Scegli dall'Archivio ]    | |  |                                         | |
|  | -------------------------------------------------- | |  |    +-------------------------------+    | |
|  | SCRIPT ATTIVO:                                     | |  |    |  [ Safe-Zone Overlay: ON ]    |    | |
|  | Titolo: "Cosmos_BlackHoles_Singularity"             | |  |    |                               |    | |
|  | Dati  : 96 Words | Stima: ~37.4 s | 1 Clip Short    | |  |    |  [ INTRO BANNER 0.0s-1.5s ]   |    | |
|  | Stato : [ 🟢 DISPONIBILE ]         [ ✕ Cambia ]     | |  |    |     "Cosmos_BlackHoles part.1"|    | |
|  +----------------------------------------------------+ |  |    |       (Centro Schermo)        |    | |
|                                                         | |  |    |                               |    | |
|  +-- 2. SUITE VOCE QWEN3-TTS (en-US) -----------------+ |  |    |      SOTTOTITOLI ATTIVI       |    | |
|  | Speaker: [ 👤 Ryan (American Warm Male)         v ] | |  |    |    (Safe-Zone Word-by-word)   |    | |
|  | Lingua : [ 🇺🇸 English (US) v ] | Stile: [ Viral Hook v]| |  |    +-------------------------------+    | |
|  | [▶ Ascolta Live ~97ms]    [⚙️ Studio Voce Completo]| |  |                                         | |
|  +----------------------------------------------------+ |  |  [▶ Play] [ 00:00.6 / 00:39.4 ]   [Vol] | |
|                                                         |  +-----------------------------------------+ |
|  +-- 3. BACKGROUND VIDEO POOL (Continuo / Locale & YT)+ |                                              |
|  | [ 📁 Importa Locale ] [ ⬇️ Scarica YT ] [ 📂 Pool ]| |  +-- GESTIONE BATCH CLIP GENERATE ---------+ |
|  | Categoria  : [ Minecraft                     v ]   | |  | [ Clip 01: 39.4s ] (Pronta)             | |
|  | Assegnazione: [ 🤖 Auto (Thematic Category Solver)v]| |  | [ Clip 02: 42.0s ] (In elaborazione...) | |
|  | Video      : "Minecraft_Parkour_4K" (ID: #003)     | |  | [ Clip 03: 37.8s ] (In coda)            | |
|  | Durata     : 06m 45s disponibili (Frontiera: 00:00)| |  +-----------------------------------------+ |
|  | Continuità : [ Multiversale per Categoria 🎮 ]      | |                                              |
|  | Snapping   : [ Confini Scena Bounded Right (±1.5s)]| |  +-- CRONOLOGIA AZIONI & LOG DI SISTEMA --+ |
|  | Ingestion  : [ Zero-Recode Ingestion (Master RAW) ]| |  | [22:15] Script verificato True O(1)     | |
|  | Stato      : [ 🟢 Idoneo (Pool Minecraft: 14m 20s) ]| |  | [22:16] Qwen3-TTS generato in 3.8s      | |
|  | [⚙️ Impostazioni Video & Ritaglio On-Demand]       | |  | [22:16] Silero VAD Trim applicato       | |
|                                                         |  | [22:16] Padding +2.0s (0.5s/1.5s) ok   | |
|  +-- 4. SOTTOTITOLI & SINCRONIZZAZIONE ---------------+ |  | [22:16] Peak Limiter audio -1.0 dB     | |
|  | Preset Stile: [ Viral Pop (Sabbia Calda)     v ]   | |  +-----------------------------------------+ |
|  | Auto-Wrap   : [ Bounding Box <= 880px, 2 righe max ]| |                                              |
|  | Timing: +0.5s pre / +1.5s outro (CTA a -1.0s)       | |  +-- MONITOR ATTIVITÀ MULTI-TASK CONCORRENTI |
|  | [⚙️ Tipografia & Personalizzazione Avanzata]        | |  | 🚀 VRAM Phase 1/3 (TTS): [====o     ] 45%  | |
|  +----------------------------------------------------+ |  |    (VRAM Net: 2.5 GB / Limite Tot: 4.0 GB)| |
|                                                         |  | ⬇️ Zero-Recode Ingestion: 1 video (2s)   | |
|                                                         |  | 📝 Script Ingestion    : Pronto (<0.2ms) | |
|                                                         |  +-----------------------------------------+ |
|                                                                                                        |
|  [================ GENERAZIONE FINALE VIDEO SHORT (Ctrl+Enter) =====================================] |
+--------------------------------------------------------------------------------------------------------+
```

---

### 4.2. Esecuzione Multi-Task Contemporanea & VRAM Lifecycle Isolato

La GUI è progettata per consentire all'utente di operare in modo completamente parallelo, senza che nessuna operazione "congeli" o impedisca le altre:

1. **Inserimento Continuo di Script durante il Rendering**:
   - Mentre il worker GPU sta processando le fasi di sintesi e montaggio di una coda di Short, l'utente può cliccare su `[ ➕ Nuovo Script ]`, aprire la modale, digitare o incollare decine di nuovi testi e salvarli nell'archivio. Il controllo deduplica True $O(1)$ (B-Tree + Pigeonhole SimHash 16-bit) e la normalizzazione deterministica con parser sintattico `inflect` (< 0.2ms) operano in memoria CPU e su SQLite WAL senza intaccare minimamente la VRAM o il render in corso.
2. **Zero-Recode Ingestion & Download YT in Background**:
   - L'utente può trascinare file MP4/MKV direttamente nella finestra o incollare link YouTube con supporto cookie anti-bot. L'ingestion lascia il file master intatto registrando metadati in 2-3 secondi; l'analisi scene detect e la catalogazione per categoria (`Minecraft`, `Subway Surfers`, ecc.) proseguono in background su thread I/O e CPU dedicati senza bloccare l'interfaccia.
3. **GPU VRAM Lifecycle Orchestrator (Budget Netto 2.800 MB, Tetto Totale 4.0 GB)**:
   - La produzione di clip finite impiega la GPU in modo rigorosamente serializzato attraverso **Worker Subprocess Python isolati (`multiprocessing` con context `spawn`)**:
     - Fase TTS (Qwen3-TTS quantizzato FP8/INT8): consumo netto bloccato a **$2,5\text{ GB}$**. Alla conclusione, il processo esce forzando Windows WDDM a bonificare istantaneamente il 100% della memoria video.
     - Fase Allineamento (Faster-Whisper `large-v3-turbo` in INT8 su CUDA): allocato a GPU pulita, consuma solo **$1,1\text{ GB}$** per $0,3\text{ s}$, azzerando il jitter (< 20ms).
     - Il consumo totale della GPU (inclusi 1.200 MB per DWM e PySide6) non supera mai i **$3.800\text{ MB}$**, ampiamente entro il tetto massimo invalicabile di **$4.0\text{ GB}$**.
4. **Monitor di Stato Asincrono & Notifiche Toast**:
   - Nella colonna destra della schermata principale, il box `MONITOR ATTIVITÀ MULTI-TASK CONCORRENTI` mostra in tempo reale l'avanzamento separato di:
     - Pipeline GPU Serializzata (con indicatore VRAM netta attiva in tempo reale, picco $< 2.8\text{ GB}$, totale scheda $< 4.0\text{ GB}$)
     - Zero-Recode Ingestion Video Locale / yt-dlp con fallback cookie multi-browser
     - Script Manager / Ingestion (< 0.2ms con sblocco varianti)
   - Al termine di ogni elaborazione, una discreta notifica toast non-fluo informa l'utente senza sottrarre il focus dalla scrittura o dai menu aperti.

---

---

## 5. Finestre Modali Dedicate (Modals) & Menu Secondari (Drawers)

### 5.1. Finestra Modale 1: Inserimento Nuovo Script (`ScriptInputModal`)
*Questa finestra può essere aperta in qualunque momento per inserire e memorizzare testi nell'archivio, anche in stock preventivi di 10 o 20 storie.*

```
+--------------------------------------------------------------------------------------+
| [X] CHIUDI          INSERIMENTO NUOVO SCRIPT & VERIFICA STORICO   [ Fast Norm: ON 🟢 ] |
+--------------------------------------------------------------------------------------+
| Incolla o digita il testo dello Short (100% English):                                |
| +----------------------------------------------------------------------------------+ |
| | Black holes are among the most mysterious entities in the universe. When a      | |
| | massive star collapses at the end of its life cycle, gravity becomes so intense  | |
| | that nothing, not even light, can escape beyond the event horizon. If you were   | |
| | to fall into a black hole, you would undergo a process known as spaghettification| |
| +----------------------------------------------------------------------------------+ |
| METRICHE TESTO IN TEMPO REALE (DEFAULT_WPS = 2.50 / 150 WPM)                         |
| Parole: 74  |  Caratteri: 468  |  Stima Durata Voce: ~29.6 s (Limite Max: 43.0 s)    |
|                                                                                      |
| CATALOGAZIONE SEMANTICA (NON CASUALE)                                                |
| Nome di Contesto Proposto: [ Space_BlackHoles_EventHorizon                        ]   |
| (Calcolato automaticamente sui concetti chiave. Modificabile a piacere)              |
|                                                                                      |
| PIPELINE AUTOMATICA DETERMINISTICA AL SALVATAGGIO (< 0.2ms):                         |
| [*] 1. Espansione Slang Deterministica: FastDeterministicNormalizer (250+ lemmi EN)  |
|        (schl->school, idk->I don't know, btw->by the way, rn->right now, w/->with)   |
|        (Esecuzione locale in CPU sub-millisecondo, 0 MB VRAM, zero demoni esterni)   |
| [*] 2. Sanitizzazione RegEx: Strip Markdown, emoji, caratteri di intonazione sporchi |
| [*] 3. Deduplica Shingling SimHash: Trigrammi + Bigrammi TF, Hex TEXT(16), 6 Blocchi |
| [*] 4. Auto-Clearing: Pulisce il testo e rimette il focus a riga 1 per nuovo input   |
|                                                                                      |
| [ Annulla / Chiudi ]                               [ Salva & Pulisci per Prossimo ]  |
+--------------------------------------------------------------------------------------+
```

#### Pipeline Esecutiva al Salvataggio: Normalizzazione Deterministica, Sanitizzazione & Pulizia
Non appena l'utente clicca `[ Salva & Pulisci per Prossimo ]` (oppure preme la scorciatoia `Ctrl+Enter`):

1. **Normalizzazione Deterministica Slang Inglese (`FastDeterministicNormalizer`)**:
   - **Esecuzione Sub-Millisecondo (< 0.2ms)**: Senza attendere chiamate LLM esterne e senza avviare server di terze parti, il motore espande istantaneamente le forme gergali e le abbreviazioni della lingua inglese (250+ lemmi: `schl` $\to$ `school`, `u` $\to$ `you`, `btw` $\to$ `by the way`, `idk` $\to$ `I do not know`, `approx.` $\to$ `approximately`, `w/` $\to$ `with`, `rn` $\to$ `right now`, `imo` $\to$ `in my opinion`).
   - **Zero Allucinazioni & Zero VRAM**: L'operazione è deterministica al 100%, non consuma memoria GPU ed è sempre disponibile su qualunque PC.
2. **Sanitizzatore Deterministico RegEx per Speech di Alta Qualità**:
   - Subito dopo l'espansione, il testo viene filtrato attraverso espressioni regolari precompilate:
     - **Rimozione Markdown Accidentale**: Eliminazione di formattazioni web come grassetto (`**testo**`), corsivo (`*testo*`), intestazioni (`#`, `##`), elenchi puntati (`-`, `*`), link (`[testo](url)`), blocchi di codice (`` ` ``, ```` ``` ````) e separatori tabelle (`|`).
     - **Pulizia Caratteri Non-Speech & Intonazione Sporca**: Rimozione di emoji, simboli tecnici decorativi (`~`, `^`, `\`, `@`, `$`, `%`, `*`, `_`), parentesi descrittive irrilevanti e punteggiatura anomala ripetuta (`????` $\to$ `?`, `....` $\to$ `.`).
     - **Normalizzazione Spazi e Punteggiatura**: Rimozione di doppi spazi e formattazione pulita di punti e virgole per scandire le pause respiratorie ideali per il motore TTS.
3. **Verifica Deduplica Multi-Index SimHash (Shingling & Trigrammi)**:
   - Supera i limiti delle "Bag of Words": calcola il SimHash 64-bit su Character 3-grams Shingling e Word Bi-grams pesati per frequenza (TF).
   - Memorizzato come stringa esadecimale `simhash_hex TEXT(16)` per prevenire l'overflow signed int64 di SQLite, ed indicizzato su 6 blocchi unsigned da 10/11-bit (`simhash_b1..b6`) garantendo complessità True $O(1)$ con principio dei cassetti (Pigeonhole) per distanza di Hamming $\le 5$ e validazione Jaccard $\ge 0.80$.
4. **Auto-Clearing Immediato & Focus a Riga 1**:
   - L'area di testo viene ripulita istantaneamente (`QTextEdit.clear()`).
   - Il cursore viene riposizionato all'inizio del campo (`QTextEdit.setFocus()`), permettendo all'utente di continuare a incollare decine di testi in successione fluida.
5. **Banner di Notifica Sobrio Non-Fluo**:
   - Compare nella parte inferiore della modale in Verde Salvia / Ardesia (`#2D4C3C` / `#729B84`):

```
+--------------------------------------------------------------------------------------+
|  ✓ SCRIPT CORRETTO, SANITIZZATO E SALVATO (ID: #043)                                 |
|  Titolo Assegnato: "Space_BlackHoles_EventHorizon" [ English en-US ]                 |
|  Correzioni: 2 abbreviazioni espanse, markdown rimosso. Pronto per il prossimo testo. |
+--------------------------------------------------------------------------------------+
```

#### Feedback Visivo in Caso di Testo Duplicato & Creazione Variante (Sblocco Deadlock)
Se l'utente inserisce un testo già memorizzato o già usato, il form espone un box informativo di sicurezza color Rosa Antico / Ambra Morbido (`#AA7373` / `#C4A36B`). Se lo script rilevato è in stato `UTILIZZATO`, il sistema non blocca l'utente in un vicolo cieco, ma offre l'opzione esplicita **"Crea Nuova Variante"** per produrre il testo con voce, font o velocità differenti:

```
+--------------------------------------------------------------------------------------+
|  ⚠ ATTENZIONE: TESTO GIÀ PRESENTE NELLO STORICO                                      |
|  Questo scritto è identico o quasi-duplicato (>80% similarità) a uno script nel DB:  |
|  - ID Storico   : #042                                                               |
|  - Titolo       : "Space_BlackHoles_Singularity"                                     |
|  - Stato        : UTILIZZATO (Video prodotto il 14/09/2026 alle 18:22)               |
|                                                                                      |
|  Testo già prodotto in passato: vuoi creare una nuova variante con stile differente? |
|                                                                                      |
|  [ 🔄 Crea Nuova Variante (Nuovo Stile) ]                    [ Annulla / Modifica ]  |
+--------------------------------------------------------------------------------------+
```
- Cliccando su `[ 🔄 Crea Nuova Variante (Nuovo Stile) ]`, il testo viene salvato come nuovo script in stato `DISPONIBILE` con riferimento padre `is_variant_of = 42`, permettendo all'utente di selezionarlo immediatamente per un nuovo montaggio.

#### Salvataggio Automatico alla Chiusura (Auto-Save on Close)
Se l'utente chiude la finestra (`[X]`, tasto `Esc` o clic all'esterno) con un testo digitato non ancora salvato, il sistema non perde il lavoro svolto: avvia in background la pipeline di normalizzazione, sanitizzazione e archiviazione prima di congedare la finestra.

---

### 5.2. Finestra Modale 2: Selettore Script & Archivio Storico (`ScriptLibraryModal`)
*Permette di consultare la biblioteca degli script e scegliere quale utilizzare per la generazione.*

```
+--------------------------------------------------------------------------------------+
| [X] CHIUDI          ARCHIVIO SCRIPT & STORICO UTILIZZO                               |
+--------------------------------------------------------------------------------------+
| Cerca per titolo o parole chiave: [ buchi neri                             ] [Filtra]|
|                                                                                      |
| [ TAB: DISPONIBILI (3 Script Pronti) ]     [ TAB: UTILIZZATI / STORICO (14 Passati) ]|
| ------------------------------------------------------------------------------------ |
|                                                                                      |
| ELENCO SCRIPT DISPONIBILI:                                                           |
| +----------------------------------------------------------------------------------+ |
| | TITOLO: Space_BlackHoles_EventHorizon                          [ SELEZIONA QUESTO ]| |
| | Data Creazione: Today, 22:15  |  Parole: 74  |  Stima Voce: ~29.6 s (1 Clip)      | |
| | Anteprima: "Black holes are among the most mysterious entities in the universe..."| |
| +----------------------------------------------------------------------------------+ |
| | TITOLO: History_Rome_JuliusCaesar_Rubicon                      [ SELEZIONA QUESTO ]| |
| | Data Creazione: Yesterday, 19:40 | Parole: 88  | Stima Voce: ~35.2 s (1 Clip)     | |
| | Anteprima: "In 49 BC, Julius Caesar made a monumental decision that changed..."   | |
| +----------------------------------------------------------------------------------+ |
| | TITOLO: DeepSea_MarianaTrench_Pressure                         [ SELEZIONA QUESTO ]| |
| | Data Creazione: 02/10/2026   |  Parole: 82  |  Stima Voce: ~32.8 s (1 Clip)      | |
| | Anteprima: "At the deepest point on Earth, the atmospheric pressure is 1000x..."  | |
| +----------------------------------------------------------------------------------+ |
+--------------------------------------------------------------------------------------+
```

#### Visualizzazione della Scheda "UTILIZZATI / STORICO"
Nella seconda scheda sono raccolti i testi già trasformati in video short. Ciascun elemento presenta il badge `🔒 UTILIZZATO` e il pulsante dedicato `[ 🔄 Crea Variante / Rigenera ]`, che crea una nuova istanza modificabile nello stato `DISPONIBILE`:

```
+--------------------------------------------------------------------------------------+
| SCRIPT UTILIZZATI (STORICO COMPLETO & FUNZIONE DI RIGENERAZIONE):                    |
| +----------------------------------------------------------------------------------+ |
| | TITOLO: Science_JamesWebb_Galaxies          [ 🔒 UTILIZZATO ] [ 🔄 Crea Variante ]| |
| | Prodotto il: 28/09/2026 alle 15:30  |  Parole: 91  |  Durata Video: 41.2 s        | |
| | Video Prodotti: "Short_Webb_01.mp4", "Short_Webb_02.mp4"                          | |
| | Anteprima: "The first deep field image sent by the James Webb Space Telescope..."  | |
| +----------------------------------------------------------------------------------+ |
+--------------------------------------------------------------------------------------+
```

---

### 5.3. Finestra Modale 3: Download & Accodamento Multi-Video YouTube (`VideoDownloadModal`)
*Consente di incollare e scaricare più video YouTube o importare video locali a Ricodifica Zero (< 3s per video), classificandoli automaticamente per categoria tematica.*

```
+--------------------------------------------------------------------------------------+
| [X] CHIUDI          DOWNLOAD MULTI-VIDEO YOUTUBE & CREAZIONE POOL CONTINUO           |
+--------------------------------------------------------------------------------------+
| AUTENTICAZIONE ANTI-BOT YOUTUBE (Bypass Chrome 127+ App-Bound Encryption):           |
| Sorgente Cookie: [ 🦊 Firefox (Consigliato) v ]   [ 📁 Importa cookies.txt ] [ OK 🟢 ]|
|                                                                                      |
| Incolla uno o più link di YouTube (uno per riga):                                    |
| +----------------------------------------------------------------------------------+ |
| | https://www.youtube.com/watch?v=dQw4w9WgXcQ                                      | |
| | https://www.youtube.com/watch?v=abc123xyz89                                      | |
| +----------------------------------------------------------------------------------+ |
| Categoria Video Rilevata / Forzata: [ 🎮 Minecraft (Auto-Rilevata)               v ] |
| [ + Aggiungi alla Coda di Download ]                                                 |
|                                                                                      |
| STATO CODA DI DOWNLOAD & INGESTION A RICODIFICA ZERO IN TEMPO REALE:                 |
| +----------------------------------------------------------------------------------+ |
| | 1. "Minecraft_Parkour_Speedrun_4K"                                [ COMPLETATO 🟢] | |
| |    Azione: Ingestion a Ricodifica Zero (3s) -> Master Intatto 09m 00s [ Minecraft ]| |
| +----------------------------------------------------------------------------------+ |
| | 2. "GTA_V_MegaRamp_Cinematic_60FPS"                               [ ELABORAZIONE ⏳] | |
| |    Progresso: Download stream video HD in corso (64%)...                           | |
| +----------------------------------------------------------------------------------+ |
| * Regole di Elaborazione Efficienza Estrema (Zero-Recode Ingestion):                 |
| - Nessuna ricodifica all'ingestion: il master rimane integro e l'import impiega < 3s.|
| - Rimozione audio (-an) e conform 9:16 avvengono nel SINGOLO passaggio finale NVENC!|
| - Continuità Tematica per Categoria: spezzoni della stessa storia associabili a più   |
|   video della stessa categoria (Minecraft, Subway Surfers, Satisfying, GTA V, ecc.). |
| - Micro-snapping sui tagli visivi entro +-0.200s (200ms assorbiti nel padding).       |
|                                                                                      |
| [ Chiudi Finestra (Elaborazione continua in background) ]                            |
+--------------------------------------------------------------------------------------+
```

---

### 5.4. Finestra Modale 4: Libreria Video Background & Pool a Flusso Continuo (`VideoLibraryModal`)
*Permette di consultare lo stato del Video Pool con categorie tematiche. **Di default l'assegnazione è 100% Automatica**, ma consente l'override manuale o il cambio categoria.*

```
+----------------------------------------------------------------------------------------------------+
| [X] CHIUDI          LIBRERIA VIDEO BACKGROUND & POOL CONTINUO                      [ Auto-Save: ON ]|
+----------------------------------------------------------------------------------------------------+
| MODALITÀ DI ASSEGNAZIONE VIDEO ATTIVA:                                                             |
| [ (•) 🤖 SELEZIONE AUTOMATICA OTTIMALE (Default - Continuità per Categoria Tematica)               ] |
|       * Il solver abbina da solo video continui della stessa categoria minimizzando scarti e tagli.|
| [ ( ) 👤 PREFERENZA MANUALE SPECIFICA (Override dell'utente su un determinato video continuo)      ] |
|                                                                                                    |
| STATO STORIA ATTIVA: Richiede 3 Short Vocali (Fabbisogno Video: ~02m 04s | Categoria: Minecraft)   |
| Video Attualmente Assegnato: "Minecraft_Parkour_Speedrun_4K" (ID: #001) [ 🤖 Scelto in Automatico ]|
| -------------------------------------------------------------------------------------------------- |
|                                                                                                    |
| VIDEO CONTINUI DISPONIBILI NEL POOL:                                                               |
| +------------------------------------------------------------------------------------------------+ |
| | [Miniatura] "Minecraft_Parkour_Speedrun_4K" (ID: #001) [ Cat: Minecraft ]   [ SELEZIONA QUESTO ]| |
| | Durata Totale: 09m 00s  |  Disponibili: 06m 00s continui (Playhead a 03m 00s)                  | |
| | Compatibilità: [ 🟢 IDONEO: Ha 06m 00s liberi, copre integralmente i 02m 04s richiesti ]        | |
| +------------------------------------------------------------------------------------------------+ |
| | [Miniatura] "Subway_Surfers_Gameplay_HD" (ID: #002) [ Cat: Subway Surfers ]  [ ALTRA CATEGORIA ] | |
| | Durata Totale: 06m 00s  |  Disponibili: 01m 20s continui (Playhead a 04m 40s)                  | |
| | Compatibilità: [ 🟡 CATEGORIA DIFFERENTE: Riservato per storie a tema Subway Surfers ]          | |
| +------------------------------------------------------------------------------------------------+ |
| | [Miniatura] "Minecraft_Bedwars_Highlights" (ID: #003) [ Cat: Minecraft ]     [ SELEZIONA QUESTO ]| |
| | Durata Totale: 07m 30s  |  Disponibili: 07m 30s continui (Nuovo master intero)                  | |
| | Compatibilità: [ 🟢 IDONEO: Stessa categoria Minecraft, utilizzabile anche per concatenazione ] | |
| +------------------------------------------------------------------------------------------------+ |
|                                                                                                    |
| [ 🤖 Ripristina Selezione Automatica ]                            [ Chiudi & Applica Modifiche ]   |
+----------------------------------------------------------------------------------------------------+
```

---

### 5.5. Dialog di Avviso: Risoluzione Continuità Tematica per Categoria/Gioco
*Viene mostrato se l'utente tenta di produrre una storia in una categoria priva di materiale continuativo sufficiente.*

```
+--------------------------------------------------------------------------------------+
|  ⚠ ATTENZIONE: MATERIALE INSUFFICIENTE NELLA CATEGORIA SELEZIONATA                  |
|                                                                                      |
|  La storia richiede ~02m 04s di girato continuo nella categoria "Minecraft",         |
|  ma nel pool sono presenti solo 01m 20s continui per questa specifica categoria.    |
|                                                                                      |
|  REGOLA DI CONTINUITÀ TEMATICA:                                                      |
|  I video di una storia possono provenire da più file purché condividano la STESSA    |
|  categoria tematica (es. due gameplay di Minecraft).                                 |
|                                                                                      |
|  OPZIONI DISPONIBILI:                                                                |
|  1. Aggiungi un nuovo video alla categoria "Minecraft" (Drag & Drop o YouTube).       |
|  2. Assegna la storia a una categoria differente (es. "Subway Surfers" o "General"). |
|                                                                                      |
|  [ Cambia Categoria Storia ]    [ Importa Locale ]    [ Scarica da YouTube ]         |
+--------------------------------------------------------------------------------------+
```

---

### 5.6. Finestra Modale 5: Coda di Produzione Multi-Storia, Personalizzazione per Script & Audit Preventivo (`BatchQueueManagerModal`)
*Consente di comporre una coda di lavoro con storie multiple, personalizzare voce e font in modo indipendente per ciascun testo, propagare le impostazioni a tutta la coda con un clic, e verificare preventivamente la fattibilità dell'intera produzione contro il Video Pool.*

```
+--------------------------------------------------------------------------------------------------------------------------------+
| [X] CHIUDI          CODA DI PRODUZIONE BATCH & AUDIT PREVENTIVO DI FATTIBILITÀ                         [ Auto-Save on Close: ON 🟢 ] |
+--------------------------------------------------------------------------------------------------------------------------------+
| STRUMENTI RAPIDI CODA:                                                                                                         |
| Preset Coda: [ 📂 Viral Batch Standard v ] [ 💾 Salva Preset ]  |  [ 🔗 Applica Voce a Tutte le Storie ] [ 🔗 Applica Font a Tutte ]  |
| ------------------------------------------------------------------------------------------------------------------------------ |
| SELEZIONA LE STORIE DALL'ARCHIVIO DA INCLUDERE NELLA CODA:                                                                     |
| [X] 1. "Cosmos_BlackHoles_Singularity"   (96 Words | 1.15x Speed -> Stima Video: ~33.5s | Fabbisogno: 1 Short Continuo)            |
| [X] 2. "RomanEmpire_JuliusCaesar_Rubicon" (148 Words| 1.00x Speed -> Stima Video: ~01m 08s | Fabbisogno: 2 Short Continui)         |
| [ ] 3. "DeepSea_MarianaTrench_Pressure"   (84 Words | 1.00x Speed -> Stima Video: ~37.8s  | Fabbisogno: 1 Short Continuo)          |
|                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------ |
| TABELLA DETTAGLIATA CODA: PREVISIONE DINAMICA (WPM / SPEED), STILI INDIPENDENTI & ASSEGNAZIONE CONTINUA:                       |
| +----------------------------------------------------------------------------------------------------------------------------+ |
| | # | STORIA IN CODA       | VOCE & SPEED (Clicca per edit)     | STILE FONT / SOTTOTITOLI (Clicca)   | SECONDI    | INTERVALLO VIDEO | STATO    | |
| +---+----------------------+------------------------------------+-------------------------------------+------------+------------------+----------+ |
| | 1 | Cosmos_BlackHoles    | [ 🎙️ Ryan (US) - Speed 1.15x ✏️]   | [ 🔤 Montserrat Black (68pt, Oro) ✏️ ]| 33.5s      | Video B: [00:00-33.5s] [ OK 🟢 ] | |
| | 2 | RomanEmpire_Caesar   | [ 🎙️ Vivian (US) - Speed 1.00x ✏️ ]| [ 🔤 Anton Bold (72pt, Perla) ✏️ ]    | 01m 08s    | Video A: [00:00-01m08s][ OK 🟢 ] | |
| +----------------------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                                |
| * FUNZIONALITÀ INTERATTIVE DI RIGA & REATTIVITÀ SPEED RATE:                                                                    |
| - Cliccando sulla cella [ 🎙️ Voce & Speed ]: Si apre lo Studio Voce scoped sullo script (con slider Speed 0.8x-1.5x e Demo 5s).|
| - Muovendo lo slider di velocità (Speed Rate), i secondi stimati e l'audit sul Video Pool si ricalcolano ISTANTANEAMENTE.      |
| - Cliccando [ 🔗 Applica Voce / Font a Tutte ]: Replica istantaneamente la configurazione della riga selezionata su tutte.    |
|                                                                                                                                |
| * CONTINUITÀ CINEMATOGRAFICA GARANTITA:                                                                                        |
|   La Storia 2 (divisa in 2 Short) consuma un intervallo temporale contiguo dal Video A: tra la Parte 1 e la Parte 2 non vi è  |
|   alcun salto visivo. Il video prosegue fluido al millisecondo senza frame sprecati.                                           |
|                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------ |
| RESPONSO DI AUDIT DI FATTIBILITÀ PREVENTIVA:                                                                                   |
| +----------------------------------------------------------------------------------------------------------------------------+ |
| | 🟢 CODA 100% FATTIBILE - MATERIALE CONTINUO COMPLETO                                                                       | |
| | - Totale Storie in Coda   : 2 Storie distinte con configurazioni audio/grafiche personalizzate                                | |
| | - Totale Short Generati   : 3 Video Short (1080x1920 @ 60fps)                                                             | |
| | - Tempo Continuo Richiesto: 01m 41.5s totali (Coperti integralmente da spezzoni monosorgente continui)                       | |
| | - Proiezione Finale Pool  : Video A conserverà 04m 12s liberi; Video B conserverà 06m 20s liberi.                             | |
| +----------------------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                                |
| (QUANDO IL MATERIALE È INSUFFICIENTE, COMPARE IL BOX DI SUGGERIMENTO INTELLIGENTE "ZERO SPRECHI"):                             |
| +----------------------------------------------------------------------------------------------------------------------------+ |
| | 🟡 AUDIT: MATERIALE ATTUALMENTE INSUFFICIENTE PER TUTTE LE 4 STORIE SELEZIONATE (Mancano 48 secondi continui conformi)      | |
| |                                                                                                                            | |
| | 💡 SUGGERIMENTO OTTIMIZZATORE "ZERO SPRECHI" (Consigliato):                                                                | |
| | Rimuovendo 1 testo ed eseguendo la produzione con 3 storie (#1, #2, #4), la coda diventa 100% FATTIBILE con ZERO SPRECHI:  | |
| | - Storie in produzione : #1 Cosmos (33.5s) + #2 Caesar (01m 08s) + #4 Pompeii (41.0s)                                       | |
| | - Storia esclusa       : #3 Mariana Trench (55.0s) -> Resta custodita nell'archivio come [ DISPONIBILE ]                    | |
| | - Allocazione Pool     : Video A satura esattamente il residuo; Video B conserva 05m 10s liberi riutilizzabili.              | |
| | - Scarti da Regola GC  : 0 SECONDI BUTTATI VIA! (Nessun residuo cade nella fascia di scarto <= 1m 50s).                     | |
| |                                                                                                                            | |
| | * MOTIVAZIONE COMPARATIVA DELL'ALGORITMO (Regola 1m 30s +20s/-inf):                                                        | |
| |   Con l'altra combinazione teorica (#2, #3, #4), rimarrebbe 1m 15s residuo nel Video B che verrebbe buttato ed eliminato    | |
| |   dal Garbage Collector (poiché <= 1m 50s). La combinazione (#1, #2, #4) viene raccomandata perché AZZERA GLI SCARTI!      | |
| |                                                                                                                            | |
| | [ 💡 APPLICA SUGGERIMENTO OTTIMALE (3 Storie, 0 Scarti) ]    [ ➕ Scarica Nuovo Video YT ]    [ Modifica Selezione Manuale ] | |
| +----------------------------------------------------------------------------------------------------------------------------+ |
|                                                                                                                                |
| [ Annulla / Chiudi (Auto-Saved) ]                                              [ 🚀 AVVIA PRODUZIONE BATCH (Ctrl+Shift+Enter) ]|
+--------------------------------------------------------------------------------------------------------------------------------+
```

#### Dettaglio delle Funzionalità della Coda Batch (Soluzione B)
1. **Configurazione Multi-Stile & Ricalcolo Dinamico Speed Rate**:
   - Ogni riga della tabella consente di definire una combinazione unica di Speaker/Voce (`Qwen3-TTS`), Stile Sottotitoli (`Font`, animazione, colori) e soprattutto **Velocità dello Speech (`speed_rate`)**.
   - Spostando lo slider da 0.8x a 1.5x, la durata stimata della storia e la sua barra di fabbisogno video si ricalcolano **in tempo reale (< 1ms)** senza attendere il render vocale.
2. **Propagazione Universale "Applica a Tutte le Storie in Coda"**:
   - I pulsanti toolbar `[ 🔗 Applica Voce a Tutte le Storie ]` e `[ 🔗 Applica Font a Tutte ]` propagano all'istante voce, velocità e preset grafici a tutta la coda con un clic.
3. **Audit Preventivo su Flussi Video Continui**:
   - Il solver CSP valuta in tempo reale la compatibilità temporale continua: verifica che i secondi richiesti siano inferiori o uguali ai secondi continui residui del video master ($D_{\text{residua}}$), preservando il vincolo monosorgente.
4. **Algoritmo di Suggerimento Intelligente della Sotto-Coda (Zero-Waste Heuristic)**:
   - Se l'utente compone una coda sovradimensionata, il motore calcola le combinazioni ammissibili ed **esegue una comparazione di spreco sui secondi residui che cadrebbero nella fascia di scarto $\le 1\text{m } 50\text{s}$ (e verrebbero distrutti dal Garbage Collector)**.
   - **Criterio di Predilezione Assoluta**: Se una combinazione lascia $1\text{m } 15\text{s}$ orfani (che verrebbero buttati via), mentre un'altra combinazione lascia $0\text{s}$ o un blocco $> 1\text{m } 50\text{s}$ riutilizzabile, il sistema **predilige e raccomanda la combinazione a zero sprechi**.
   - Cliccando su `[ 💡 APPLICA SUGGERIMENTO OTTIMALE ]`, la GUI aggiorna istantaneamente le selezioni dei checkbox ed esclude la storia eccedente conservandola intatta in archivio.
5. **Salvataggio Automatico alla Chiusura**:
   - Qualsiasi modifica effettuata nella tabella viene persistita all'istante alla chiusura della finestra (`closeEvent`).

---

### 5.7. Gestione della Garbage Collection Automatica dei Residui (1m 30s con tolleranza +20s / -inf)
Quando una sessione di generazione consuma secondi da un video master continuo:
1. **Soglia Minima Reel**: Nessuno Short può durare meno di **$38.0\text{ secondi}$**.
2. **Finestra di Scarto Residuo**:
   - Baseline di scarto: **$1\text{m } 30\text{s}$** ($90.0\text{ s}$).
   - Tolleranza superiore $+20\text{ s}$ $\implies$ Soglia massima di eliminazione residuo: **$\le 1\text{m } 50\text{s}$** ($110.0\text{ s}$).
   - Tolleranza inferiore $-\infty$ (Permesso di eccedere la soglia per produrre una clip):
     Se per completare una clip il video deve scendere sotto la soglia lasciando ad esempio $1\text{m } 10\text{s}$ ($70\text{ s}$), il sistema **utilizza regolarmente quello spezzone per il video finale**, e poi **cancella dal disco il restante minuto e 10 secondi**, liberando spazio.
3. Se al termine delle produzioni i secondi residui del video master scendono a $\le 1\text{m } 50\text{s}$, il file master residuo viene **automaticamente eliminato dal disco** e lo stato passa a `[ EPURATO (Residuo <= 1m 50s eliminato) ]`.
4. Notifica executive nella console di log non-fluo:
   `[Garbage Collector] Video #002 epurato: il residuo di 01m 12s (<= 1m 50s) è stato eliminato dal disco per liberare spazio.`

---

### 5.8. Drawer 1: Studio Voce Avanzato & Voice Intelligence (Qwen3-TTS en-US)
*Accessibile dal Modulo 2 tramite il pulsante `[⚙️ Studio Voce Completo]` o cliccando sul badge della voce in qualsiasi riga della Coda Batch. Ottimizzato nativamente per la lingua **Inglese Americano (`en-US`)** con supporto per **Demo Audio (Max 5s)**, **Preset Persistenti**, **Propagazione alla Coda** e **Auto-Salvataggio alla Chiusura**.*

```
+----------------------------------------------------------------------------------------------------+
| [X] CHIUDI          VOICE STUDIO & INTELLIGENZA VOCALE (Qwen3-TTS en-US)     [ Auto-Save on Close: ON 🟢 ]|
+----------------------------------------------------------------------------------------------------+
| AMBITO ATTIVO: Configurazione per Script #001 ("Cosmos_BlackHoles_Singularity")                     |
|                                                                                                    |
| GESTIONE PRESET & PROPAGAZIONE IN CODA:                                                            |
| Preset Voce Attivo : [ 📂 US_ViralHook_Ryan (American Male, 150 WPM)   v ] [ 💾 Salva Nuovo Preset ]|
| Azione Rapida Coda : [ 🔗 Applica Questa Voce a Tutte le Storie in Coda ]                          |
| -------------------------------------------------------------------------------------------------- |
| [ TAB 1: PRESET VOCI US ] [ TAB 2: VOICE CLONE ] [ TAB 3: VOICE DESIGN ] [ LIBRERIA PROFILI ]     |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
| === SEZIONE ATTIVA: TAB 1 - VOCI PREDEFINITE & INSTRUCTION GUIDATA (en-US) ===                     |
|                                                                                                    |
| Speaker Ufficiale Americano : [ Ryan (Natural Warm Male - American Accent)                     v ] |
| (Disponibili anche: Aiden [Dynamic Young US], Vivian [Warm Female], Emma [Expressive Narrator])    |
| Lingua di Sintesi Primaria  : [ 🇺🇸 English (United States) - en-US                            v ] |
|                                                                                                    |
| PRESET DI GUIDA EMOTIVA & PROSODIA PER SHORT VIRALI (`instruct`):                                  |
| [ Preset: Viral Hook (High energy, punchy pace, emphasizes keywords)                            v ]|
| [ Preset: Dark Mystery & Crime (Deep tone, suspenseful micro-pauses)                              ]|
| [ Preset: Tech & Science Facts (Fast-paced, crystal clear American diction)                       ]|
| [ Preset: Inspiring Motivational (Passionate, confident, cinematic)                               ]|
|                                                                                                    |
| Prompt Libero Istruzione:                                                                          |
| [ "Speak with an engaging, fast-paced American creator voice, building tension toward climax"    ] |
|                                                                                                    |
| REGOLAZIONI FINI AUDIZIONE:                                                                        |
| Speaking Rate (Velocità WPM) : [======o======] 1.00x (~150 WPM American Standard)                  |
| Pitch / Vocal Timbre         : [====o========] Neutral                                             |
| Sampling Temperature         : [=======o=====] 0.70                                                |
| Pausa su Punto Fermo (.)     : [====o========] 350 ms   | Pausa su Virgola (,): [==o====] 150 ms   |
|                                                                                                    |
| -------------------------------------------------------------------------------------------------- |
| 🎧 ANTEPRIMA RAPIDA VOCE (DEMO AUDIO RIGOROSAMENTE LIMITATA A MAX 5.0 SECONDI):                    |
| Frase di Test: "Black holes are among the most mysterious cosmic titans in the entire universe..." |
| [ ▶ Ascolta Demo Audio (Max 5.0s) ]   [ ■ Stop ]    Progresso: [======o      ] 00:02.8 / 00:05.0   |
| * Nota di Efficienza: Il motore genera solo i primi 5 secondi con micro-fadeout di 50ms,           |
|   garantendo un riscontro sonoro ultra-veloce senza generare l'intero audio dello Short.           |
| -------------------------------------------------------------------------------------------------- |
|                                                                                                    |
| === SEZIONE ATTIVA: TAB 2 - CLONAZIONE VOCALE AVANZATA (ZERO-SHOT CLONING) ===                     |
|                                                                                                    |
| 1. AUDIO DI RIFERIMENTO (Da 3 a 15 secondi di voce chiara):                                        |
|    [ Sfoglia File (.wav, .mp3, .m4a) ]  oppure  [ 🎙️ Registra Microfono ]                          |
|    File Caricato: "reference_voice_sample.wav" (Durata: 6.2s | Frequenza: 44.1kHz)                 |
|                                                                                                    |
| 2. TRASCRIZIONE AUDIO DI RIFERIMENTO (Necessaria per condizionamento acustico):                    |
|    [ Welcome back to another video, today we are exploring...                                    ] |
|    [ ✨ Auto-Trascrivi con Faster-Whisper (en) ]  <-- Compilazione automatica a zero sforzo         |
|                                                                                                    |
| 3. PROFILAZIONE PERSISTENTE & CACHING:                                                             |
|    Nome Profilo Vocale : [ Ryan_Creator_Clone                                                    ] |
|    [ 💾 Estrai & Salva Profilo Vocale (.qvoice) ]                                                  |
|    * Nota: Il profilo calcola i pesi una sola volta. Nei montaggi successivi la voce               |
|      partirà all'istante senza ricalcolare l'audio sorgente!                                        |
|                                                                                                    |
| 4. CONDIZIONAMENTO VOCALE (en-US):                                                                 |
|    Lingua di Sintesi: 🇺🇸 English (US) nativo garantito                                            |
|    Accento Target: General American Accent (Integrazione Qwen3-TTS Base 1.7B)                      |
|                                                                                                    |
| -------------------------------------------------------------------------------------------------- |
|                                                                                                    |
| === SEZIONE ATTIVA: TAB 3 - VOICE DESIGN (CREA VOCI DA DESCRIZIONE TESTUALE) ===                  |
|                                                                                                    |
| Descrivi in linguaggio naturale la voce ideale che desideri creare (in inglese):                   |
| +------------------------------------------------------------------------------------------------+ |
| | "Male American voice, 35-40 years old, deep warm baritone tone, confident and                  | |
| | engaging pacing, perfect for thrilling science and mystery YouTube Shorts"                     | |
| +------------------------------------------------------------------------------------------------+ |
| Preset Rapidi da un Clic:                                                                          |
| [ US Docu Baritone ]  [ US Dynamic Creator 22y ]  [ Movie Trailer ]  [ Chill Podcast ]             |
| [ ▶ Demo 5s Voice Design ]                      [ 💾 Salva come Avatar Esclusivo del Canale ]      |
|                                                                                                    |
| [ Ripristina Valori ]   [ 🔗 Applica a Tutte in Coda ]   [ Salva & Chiudi (Auto-Saved on Close) ]  |
+----------------------------------------------------------------------------------------------------+
```

#### Caratteristiche Salienti dello Studio Voce
1. **Lazy Swapping & Garanzia VRAM < 4.2 GB**:
   - Nella memoria video GPU viene caricato sempre e solo **un singolo modello vocale alla volta** (CustomVoice, Base o VoiceDesign). All'atto del cambio scheda o tipologia di voce, il modello precedente viene scaricato esplicitamente (`_unload_active_model()`) con pulizia completa della cache CUDA e garbage collection.
2. **Audizione Sicura Multi-Task (Fallback CPU se Batch Attivo)**:
   - Se l'utente ascolta un provino audio rapido mentre in background è attivo il rendering di un batch di video sulla GPU, il sistema instrada automaticamente l'audizione su CPU (`device="cpu"`), prevenendo qualsiasi contesa di risorse hardware o rischio di CUDA OOM.
3. **Demo Audio Rigorosamente Clamped a Max 5.0 Secondi**:
   - Per evitare di attendere la sintesi dell'intera narrazione durante la taratura della voce, il motore esegue il chunking della sola prima frase e applica un taglio hardware a $5.00\text{ s}$ con inviluppo esponenziale fadeout di $50\text{ ms}$.
4. **Preset Vocali Persistenti (`voice_presets`)**:
   - È possibile salvare qualsiasi combinazione di speaker (Ryan en-US, clone `.qvoice` o avatar sintetico), istruzione emotiva, velocità WPM e pause in un preset riutilizzabile e ricaricabile in qualsiasi momento.
5. **Pulsante "Applica Questa Voce a Tutte le Storie in Coda"**:
   - Propaga all'istante l'intera identità vocale selezionata a tutti gli altri elementi presenti nella Coda Batch aperta.
6. **Salvataggio Automatico alla Chiusura (Auto-Save on Close)**:
   - Ogni modifica viene salvata in modo asincrono nel database non appena l'utente chiude la finestra.

---

### 5.9. Drawer 2: Studio Video, Conform 9:16 & Taglio On-Demand
*Accessibile dal Modulo 3 tramite il pulsante `[⚙️ Impostazioni Video]`:*

```
+----------------------------------------------------------------------+
| [X] CHIUDI      OPZIONI VIDEO & FLUSSO CONTINUO   [ Auto-Save: ON 🟢]|
+----------------------------------------------------------------------+
| GESTIONE FLUSSO VIDEO CONTINUO & TAGLI ON-DEMAND (SOLUZIONE B)       |
| Conform 9:16 su Ingestion       : [ 1080x1920 @ 60fps (Automatico)  v]|
| Modalità di Taglio Video        : [ Just-In-Time su Durata Audio    v]|
| Scene Boundary Snapping         : [ Micro-snapping (±0.200s)       v]|
| Soglia Minima Accettabile Reel  : [ 38.0 secondi                     ]|
| Finestra Garbage Collector      : [ 1m 30s (+20s / -inf) -> <= 110s  ]|
| Riutilizzo Spazi da Rollback    : [ Temporal Free-List (Best-Fit) ON ]|
|                                                                      |
| FORMATO & INQUADRATURA VERTICALE (9:16)                              |
| Modalità di Adattamento Ingestion: [ Ritaglio Intelligente al Centro]|
|                                   [ Sfocatura Sfondo (Letterbox)   ] |
|                                   [ Scala e Centra (Aspect Ratio)  ] |
| Risoluzione Master Ingestion    : [ 1080 x 1920 (Full HD Vertical) v ]|
| Frame Rate Target               : [ 60 FPS                         v]|
| SINCRONIZZAZIONE & PADDING AUDIO-VIDEO (LEAD-IN 0.5s & OUTRO 1.5s)   |
| Lead-in Video (Anticipo Inizio) : [=====o======] 0.50 secondi        |
| Lead-out Video (Coda Post-Voce) : [========o==] 1.50 secondi        |
| * Stacco Speech a -1.5s; CTA Banner a -1.0s fino a fine video        |
| * Durata Totale Short: T_video = (Durata Voce + 2.00 s)              |
|                                                                      |
| GESTIONE RISORSE HARDWARE                                            |
| Encoder Video Utilizzato        : [ h264_nvenc (Accelerazione GPU) v]|
| Preset di Codifica              : [ Qualità Elevata (-cq 18 / p5)  v]|
|                                                                      |
| [ Ripristina Valori Predefiniti ]        [ Salva & Chiudi (Auto-Save)]|
+----------------------------------------------------------------------+
```

---

### 5.10. Drawer 3: Subtitle Designer, Anteprima Visiva Live (9:16) & Preset Tipografici
*Accessibile dal Modulo 4 tramite il pulsante `[⚙️ Tipografia & Personalizzazione]` o cliccando sul badge del font/stile in qualsiasi riga della Coda Batch. Include **Anteprima Visiva Live 9:16**, **Salvataggio/Caricamento Preset Font**, **Propagazione Universale alla Coda** e **Auto-Salvataggio alla Chiusura**.*

```
+----------------------------------------------------------------------------------------------------+
| [X] CHIUDI          DESIGNER SOTTOTITOLI & SAFE-ZONE STUDIO                  [ Auto-Save on Close: ON 🟢 ] |
+----------------------------------------------------------------------------------------------------+
| AMBITO ATTIVO: Configurazione Sottotitoli per Script #001 ("Cosmos_BlackHoles_Singularity")        |
|                                                                                                    |
| GESTIONE PRESET TIPOGRAFICI & CODA:                                                                |
| Preset Font Attivo : [ 📂 Viral_Gold_Pop (Montserrat Black, Oro & Perla) v ] [ 💾 Salva Nuovo Preset] |
| Azione Rapida Coda : [ 🔗 Applica Questo Font a Tutte le Storie in Coda ]                          |
| -------------------------------------------------------------------------------------------------- |
|                                                                                                    |
| COLONNA SINISTRA: IMPOSTAZIONI GRAFICHE              | COLONNA DESTRA: ANTEPRIMA VISIVA LIVE (9:16)|
|                                                      |                                             |
| STILE ANIMAZIONE DINAMICA:                           | SELEZIONE SFONDO VIDEO REALE (1-Frame Foto):|
| [ (•) Word Pop (Parola per parola sincronizzata)   ] | Clip Assegnata: [ 🎬 Clip #01 (Minecraft) v]|
| [ ( ) Karaoke Lineare (Evidenziazione su riga)     ] | Scrub Fotogramma: [====o=======] 00:02.5s   |
| [ ( ) Due Parole a Rimbalzo (Bounce Chunk)         ] |                                             |
|                                                      | +----------- SMARTPHONE 9:16 ------------+  |
| TIPOGRAFIA & FONT:                                   | |  [ Top Safe-Zone: Libero da testo ]    |  |
| Famiglia Font      : [ Montserrat Black           v ]| |                                        |  |
| (Disponibili: Anton, The Bold Font, Poppins)         | |  +----------------------------------+  |  |
| Dimensione Testo   : [======o======] 68 pt           | |  | 🖼️ FOTOGRAMMA REALE ESTRATTO      |  |  |
| Stile Lettere      : [ TUTTO MAIUSCOLO (All Caps) v ]| |  |    DALLA CLIP VIDEO ASSEGNATA    |  |  |
| Spaziatura Lettere : [==o==========] 1.5 px          | |  |    (Immagine esatta a t=02.5s)   |  |  |
|                                                      | |  +----------------------------------+  |  |
| PALETTE COLORI (Strictly Non-Fluo):                  | |                                        |  |
| Colore Testo Base  : [ #DCE0EA ] (Perla Morbido)     | |        +-- BOX SOTTOTITOLI LIVE --+    |  |
| Colore Evidenziato : [ #BFA175 ] (Sabbia Dorata)     | |        |                          |    |  |
| Colore Contorno    : [ #181A20 ] (Ardesia Scura)     | |        |     BLACK HOLES ARE      |    |  |
| Spessore Bordo     : [===o=========] 5 px            | |        |   [ MOST MYSTERIOUS ]    |    |  |
| Ombra Morbida      : [====o========] Raggio: 3 px    | |        |        OBJECTS...        |    |  |
|                                                      | |        +--------------------------+    |  |
| POSIZIONAMENTO & SAFE ZONES SOCIAL:                  | |   * Contrasto visivo verificato sopra  |  |
| Margine Y Fondo    : [=======o=====] 440 px (Safe)   | |     le immagini reali del video!       |  |
| Maschere Overlay   : [X] TikTok  [X] Reels  [ ] Short| |                                        |  |
|                                                      | |  [ Bottom Safe-Zone: Icone Social ]    |  |
|                                                      | +----------------------------------------+  |
|                                                      | [ ▶ Play Demo Animazione ] [ 📸 Altro Frame]|
| -------------------------------------------------------------------------------------------------- |
| [ Ripristina Valori ]    [ 🔗 Applica a Tutte in Coda ]    [ Salva & Chiudi (Auto-Saved on Close) ]|
+----------------------------------------------------------------------------------------------------+
```

#### Caratteristiche Salienti del Subtitle Designer
1. **Anteprima Visiva Live su Singolo Frame Reale del Video (1-Frame Real Video Preview)**:
   - Non viene utilizzato un anonimo sfondo grigio o nero: il sistema estrae istantaneamente **1 fotogramma JPEG ad alta risoluzione (1080x1920)** dallo specifico intervallo temporale continuo assegnato alla storia dal master video (tramite comando FFmpeg sub-secondo `-ss [start_sec + offset] -i master.mp4 -vframes 1`).
   - L'immagine estratta viene renderizzata direttamente come sfondo del monitor smartphone 9:16.
   - L'utente può così valutare a colpo d'occhio la leggibilità del font, il contrasto della parola attiva in evidenza (oro morbido `#BFA175`) e l'efficacia del bordo scuro e dell'ombra sopra le immagini reali del filmato (scene chiare, scure o ricche di dettagli).
   - È possibile navigare tra le diverse parti assegnate alla storia (`Parte 1`, `Parte 2`, ecc.) e regolare il timestamp tramite cursore di scrubbing per verificare il sottotitolo su fotogrammi differenti.
2. **Auto-Impaginazione Rigorosa & Anti-Overflow Schermo (1080px)**:
   - Per impedire che parole con font grandi (68-72 pt) escano dai bordi laterali dello schermo 9:16, il generatore impone:
     - Massimo **3 parole per riga**.
     - Massimo **2 righe per evento a schermo** (tetto massimo 6 parole visibili contemporaneamente).
     - Ritorno a capo naturale `\N` calcolato prima del rendering per preservare il perfetto baricentro orizzontale.
3. **Preset Tipografici Persistenti (`subtitle_presets`)**:
   - Consente di salvare template completi di stile (es. *Viral Gold Pop*, *Slate Crime Thriller*, *Clean White Sans*) pronti per essere applicati con un solo clic.
4. **Pulsante "Applica Questo Font a Tutte le Storie in Coda"**:
   - Uniforma all'istante l'intera coda di lavoro sullo stile grafico configurato.
5. **Salvataggio Automatico alla Chiusura (Auto-Save on Close)**:
   - Tutte le proprietà grafiche dello script attivo o del preset vengono salvate nel database alla chiusura della finestra.

---

### 5.11. Drawer 4: Audio Mixing, Background Music (BGM), Mastering & True Peak Limiter
*Accessibile dal controllo volume/audio o tramite il pulsante `[🎵 Musica di Sottofondo]`. Consente di incollare direttamente **link YouTube** per le tracce audio in background o utilizzare la libreria Safe CC0 integrata.*

```
+----------------------------------------------------------------------------------------------------+
| [X] CHIUDI          MIXING AUDIO, BGM & YOUTUBE INGESTION                  [ Auto-Save on Close: ON 🟢 ] |
+----------------------------------------------------------------------------------------------------+
| AMBITO ATTIVO: Configurazione Audio per Script #001 ("Cosmos_BlackHoles_Singularity")               |
|                                                                                                    |
| SEZIONE 1: SCARICA & CONVERTI BGM DA LINK YOUTUBE (Elaborazione Automatica)                         |
| Incolla uno o più link di YouTube (uno per riga) per le musiche di sottofondo:                      |
| +------------------------------------------------------------------------------------------------+ |
| | https://www.youtube.com/watch?v=5qap5aO4i9A  (Lofi Chill Study Beats)                          | |
| | https://www.youtube.com/watch?v=jfKfPfyJRdk  (Dark Ambient Tension & Mystery)                  | |
| +------------------------------------------------------------------------------------------------+ |
| [ ⬇️ Scarica & Converti Audio da YouTube (Estrazione Stream + Normalizzazione -24 LUFS) ]          |
|                                                                                                    |
| STATO ELABORAZIONE AUDIO IN TEMPO REALE:                                                           |
| +------------------------------------------------------------------------------------------------+ |
| | 🟢 "Lofi_Chill_Study_Beats" (Durata: 2m 45s | Canale: LofiGirl)                                  | |
| |    Azione: Solo stream audio scaricato -> Silenzi tagliati -> Normalizzato a -24.0 LUFS -> Pronto| |
| +------------------------------------------------------------------------------------------------+ |
|                                                                                                    |
| -------------------------------------------------------------------------------------------------- |
| SEZIONE 2: LIBRERIA BGM LOCALE (TRACCE YOUTUBE & SAFE CC0 PRONTE ALL'USO)                          |
| +------------------------------------------------------------------------------------------------+ |
| | [▶ Play] "Lofi_Chill_Study_Beats" (2m 45s | -24 LUFS)              [ ASSEGNATA A QUESTA STORIA 🟢]| |
| | [▶ Play] "Dark_Ambient_Tension" (1m 58s | -24 LUFS)                [ Scegli per Questa Storia ]  | |
| | [▶ Play] "Cinematic_SciFi_Pad" (3m 12s | -24 LUFS)                 [ Scegli per Questa Storia ]  | |
| +------------------------------------------------------------------------------------------------+ |
| [X] Ruota casualmente le tracce musicali della libreria tra le diverse storie in Coda Batch         |
|                                                                                                    |
| -------------------------------------------------------------------------------------------------- |
| SEZIONE 3: AUTO-DUCKING DINAMICO SENZA POP/CLIC                                                    |
| [X] Attiva Auto-Ducking Morbido (Curve continue senza gradini impulsivi)                            |
| Volume Musica durante il Parlato (Voice Active) : [===o=========] -22.0 dB                         |
| Volume Musica durante Intro (0.5s) ed Outro (1.5s) : [=====o======] -14.0 dB (Swell + CTA a -1.0s)  |
| Tempo di Transizione / Rilascio Ducking         : [==o==========] 180 ms                           |
|                                                                                                    |
| -------------------------------------------------------------------------------------------------- |
| SEZIONE 4: ADATTAMENTO DURATA & MASTERING BROADCAST (TRUE PEAK LIMITER)                            |
| Gestione Durata Traccia BGM    : [ Seamless Loop con Crossfade se più corta del video            v ]|
|                                  [ Trim Automatico con Fade-out a fine video                     v ]|
| Mixaggio Flussi Audio          : [ amix con normalize=0 (Eliminato volume=2, zero clipping)      v ]|
| Limiter Anti-Clipping Finale   : [ True Peak Limiter a -1.0 dB (alimiter=limit=-1.0dB:attack=5)  v ]|
|                                                                                                    |
| [ Ripristina Valori ]    [ 🔗 Applica BGM a Tutte in Coda ]    [ Salva & Chiudi (Auto-Saved on Close)]|
+----------------------------------------------------------------------------------------------------+
```

#### Dettaglio del Flusso di Gestione BGM & Mastering
1. **Zero Attrito: Ingestion Diretta da URL**:
   - L'utente copia e incolla semplicemente il link YouTube del brano musicale desiderato.
   - Non serve alcun convertitore esterno né il download manuale di file MP3.
2. **Download Intelligente del Solo Flusso Audio**:
   - Il backend sfrutta `yt-dlp` richiedendo unicamente lo stream audio (`-x --audio-format mp3`). Non viene scaricato il video, risparmiando il 90% del tempo e dello spazio su disco.
3. **Condizionamento e Normalizzazione Automatica**:
   - **Taglio Silenzi (`silenceremove`)**: Elimina code o pause iniziali e finali.
   - **Target -24 LUFS (`loudnorm`)**: Riduce la dinamica della musica portandola esattamente al livello di riferimento internazionale per le colonne sonore di sottofondo, garantendo che non copra mai la voce generata da Qwen3-TTS.
4. **Protezione Assoluta contro il Clipping su Smartphone**:
   - Invece di usare `volume=2` su `amix` (che causava saturazione severa e distorsione sui piccoli altoparlanti mobili), il motore usa `normalize=0` ed applica a fine catena un **True Peak Limiter a -1.0 dB** (`alimiter=limit=-1.0dB:attack=5:release=50:asc=1`), assicurando volume elevato e zero distorsioni.
5. **Archiviazione Locale Riutilizzabile**:
   - Ogni brano scaricato da YouTube viene memorizzato nella cartella `app_data/bgm_library/` e catalogato nella tabella `bgm_tracks`. È accessibile per sempre per tutti i video futuri senza dover effettuare ulteriori download.

---

### 5.12. Architettura dei Preset Persistenti & Salvataggio Automatico Globale (Auto-Save on Close)

Per garantire un'esperienza utente priva di attriti e prevenire qualsiasi perdita di dati o impostazioni:

#### 1. Principio dell'Auto-Salvataggio Sistematico alla Chiusura (`closeEvent`)
In tutta l'applicazione (Finestra Principale, Finestre Modali 1-5, Drawer 1-4), ogni interfaccia eredita da una classe base `AutoSaveDialog` / `AutoSaveDrawer` collegata al ciclo di vita Qt:
- **Evento di Chiusura Intercettato**: Cliccare sul pulsante `[X]`, premere il tasto `Esc` o chiudere il cassetto laterale non scarta mai le modifiche, ma scatena automaticamente la persistenza asincrona dello stato nel database SQLite (`settings`, `queue_items`, `script_drafts`).
- **Nessun Modale Modale di Conferma Intrusivo**: Non compare alcun pop-up che chiede *"Vuoi salvare prima di uscire?"*. L'app salva silenziosamente e conferma l'azione con una leggera micro-animazione dell'indicatore `[ Auto-Save on Close: ON 🟢 ]`.

#### 2. Sistema di Salvataggio e Caricamento Preset (Voci e Font)
- **Preset Voce**: Memorizzati nella tabella `voice_presets`, archiviano speaker americano (`Ryan`, `Aiden`), profilo di clonazione (`.qvoice`), parametri emotivi di recitazione `instruct`, velocità WPM (con limite $\le 44.0\text{ s}$) e pause di punteggiatura.
- **Preset Sottotitoli**: Memorizzati nella tabella `subtitle_presets`, archiviano famiglia font (`Montserrat Black`, `Anton`), dimensione in pt, palette non-fluo (base e parola attiva), spessore contorno in px, raggio d'ombra e margine verticale Y Safe-Area.
- **Caricamento Istantaneo**: Da qualsiasi schermata o riga della Coda Batch, l'utente seleziona il preset da un menu a tendina e tutti i controlli visivi/sonori si aggiornano all'istante, pronti per l'audizione demo (Max 5s) o per l'anteprima 9:16.


---

### 5.13. Finestra Modale di Riepilogo Pre-Render & Ispezione Frame 0.6s (PreProductionReviewModal)

La finestra modale **`PreProductionReviewModal`** rappresenta l'ultimo checkpoint visivo e analitico prima di avviare il processo di rendering irreversibile. Si apre automaticamente quando l'utente clicca su `[ 🚀 PROCEDI ALLA CREAZIONE DEI CONTENUTI ]` (dalla schermata principale per una singola storia) oppure su `[ 🚀 AVVIA PRODUZIONE BATCH ]` (dalla Coda di Produzione Multi-Storia).

#### 1. Obiettivi e Filosofia UX del Checkpoint
1. **Verifica "Uno a Uno" Sequenziale**: Per ogni storia inclusa nella sessione di creazione (singola o batch multi-storia), l'utente naviga attraverso un carosello ordinato `[ ◀ Precedente ] Storia X di N [ Successiva ▶ ]`.
2. **Riepilogo Sintetico Esecutivo**: Presenta in una vista compatta tutte le scelte effettuate per quella specifica storia (testo, durata prevista, voce, vincoli di clip sequenziale monosorgente, traccia BGM e stile grafico).
3. **Ispezione Reale del Primo Frame a 0.60 Secondi ($t = 0.60\text{ s}$) con Intro Title Banner**:
   - **Razionale Matematico del Frame a 0.6s**: Poiché il video inizia con un anticipo di $0.50\text{ s}$ rispetto alla voce ($t = 0.0\text{ s} \to 0.50\text{ s}$ è puro video d'aggancio in cui è attivo il banner del titolo al centro), la voce e i sottotitoli dinamici si attivano esattamente a $t = 0.50\text{ s}$. Di conseguenza, il fotogramma a **$t = 0.60\text{ s}$** ($100\text{ ms}$ dopo l'inizio della prima parola) è il **primo istante esatto in cui compaiono a video simultaneamente**:
     - **Al centro dello schermo**: l'**Intro Title Banner** `"[nome del testo] part.[clip_num]"` renderizzato con il font scelto per lo Short.
     - **In basso nella Safe Zone**: la **prima parola parlata attiva** illuminata con il colore di highlight configurato (`#BFA175` Sabbia Dorata).
   - Il motore FFmpeg genera al volo l'immagine composita reale (`review_frame_0_6s.jpg`): fotogramma reale della clip video assegnata con impressi sopra il banner centrale e i sottotitoli ASS con font, colori, contorni e margini Safe-Zone configurati.
   - L'utente può verificare prima del rendering definitivo sia il titolo al centro sia la leggibilità dei sottotitoli e il contrasto sui colori del video di background all'interno delle Safe Zones di TikTok, Reels e Shorts.
4. **Protezione dalle Modifiche Irreversibili**: Fino a quando l'utente non preme `[ 🚀 CONFERMA & AVVIA CREAZIONE DEFINITIVA ]`, le clip video nel Video Pool **non vengono scalate** e lo script **non viene marcato come `UTILIZZATO`**. Se qualcosa non convince, l'utente clicca su `[ ✏️ Modifica / Torna Indietro ]` per ritoccare le impostazioni senza alcun impatto sullo stato del sistema.

---

#### 2. Wireframe ASCII della Finestra Modale di Riepilogo Pre-Render (`PreProductionReviewModal`)

```
+--------------------------------------------------------------------------------------------------------------------+
| [X]  RIEPILOGO PRE-PRODUZIONE & ISPEZIONE VISIVA PRIMO FRAME (0.6s)                               [ Auto-Save: ON 🟢 ]|
|--------------------------------------------------------------------------------------------------------------------|
|  NAVIGAZIONE CODA:  [ ◀ STORIA PRECEDENTE ]        STORIA 1 DI 4: Space_BlackHoles_EventHorizon       [ STORIA SUCCESSIVA ▶ ] |
|--------------------------------------------------------------------------------------------------------------------|
|                                                          |                                                         |
|  COLONNA SINISTRA: RIEPILOGO SINTETICO IMPOSTAZIONI       |  COLONNA DESTRA: ISPEZIONE PRIMO FRAME SOTTOTITOLI      |
|                                                          |  (Fotogramma Esatto a t = 0.60s sul Video Assegnato)    |
|  +----------------------------------------------------+  |                                                         |
|  | 📝 SCRIPT & METRICHE DURATA                         |  |  [ Monitor Smartphone 9:16 - Frame a 00:00:00.600 ]     |
|  |  • Titolo Contesto: Space_BlackHoles_EventHorizon    |  |  +---------------------------------------------------+  |
|  |  • Parole: 104  |  Caratteri: 582                   |  |  | [   Area Superiore Safe Zone (Ricerca)   ]        |  |
|  |  • Durata Voce Prevista: 36.4 s (Max: 43.0s)  ✅    |  |  |                                                   |  |
|  |  • Durata Video Totale: 38.4 s (+2.0s Padding)  ✅ |  |  |           [ INTRO TITLE BANNER ]               |  |
|  |    (0.5s Intro + 1.5s Outro esteso)                 |  |  |       "Space_BlackHoles part.1"               |  |
|  +----------------------------------------------------+  |  |       (Centro Schermo - Stesso Font)          |  |
|                                                          |  |                                                   |  |
|  +----------------------------------------------------+  |  |                  [ IMMAGINE REALE                 |  |
|  | 🎙️ CONFIGURAZIONE VOCE & RECITAZIONE               |  |  |                   DELLA CLIP VIDEO                |  |
|  |  • Profilo Vocale: Ryan (American English Male)    |  |  |                     ASSEGNATA                     |  |
|  |  • Modalità: Custom Voice en-US                    |  |  |                 Minecraft_Parkour_01]             |  |
|  |  • Guida Emotiva (Instruct): "Viral Hook & Mystery"|  |  |                                                   |  |
|  |  • Cadenza / Velocità: 1.05x  |  Pitch: +0.0        |  |  |                                                   |  |
|  +----------------------------------------------------+  |  |         ---------------------------------         |  |
|                                                          |  |         |  [ DISCOVER ] THIS STORY      |  <--    |  |
|  +----------------------------------------------------+  |  |         ---------------------------------         |  |
|  | 🎬 VIDEO ASSEGNATO & ALLOCAZIONE REGISTRY          |  |  |          Parola Attiva: #BFA175 (Sabbia Dorata)   |  |
|  |  • File Sorgente: Minecraft_Parkour_01.mp4         |  |  |          Testo Base:    #DCE0EA (Perla Morbido)   |  |
|  |  • Segmento Video: 00:00.0 -> 00:38.4 (Snapping)   |  |  |          Bordo/Ombra:   #181A20 (Bordo 5px)       |  |
|  |  • Vincolo Sequenziale: Monosorgente Garantito ✅   |  |  |                                                   |  |
|  +----------------------------------------------------+  |  |  | Area Profilo, Like, Commenti TikTok (Coperta) |  |  |
|                                                          |  |  +---------------------------------------------------+  |
|  +----------------------------------------------------+  |  |  CTA FINALE CONFIGURATA (a t = 37.4s -> 38.4s):       |  |
|  | 🏷️ BANNER INTRO & OUTRO CTA (STESSO FONT)          |  |  |  "Subscribe for part.2" (Centro Schermo)             |  |
|  |  • Intro (0.0s-1.5s): "Space_BlackHoles part.1"    |  |  +---------------------------------------------------+  |
|  |  • Outro CTA (-1.0s): "Subscribe for part.2"       |  |                                                         |
|  |  • Stacco Voce: a -1.5s dalla fine del video       |  |  CONTROLLI DI VERIFICA GRAFICA:                         |
|  +----------------------------------------------------+  |  [X] Mostra Overlay Safe Zones Social (TikTok/IG/Shorts)|
|                                                          |  Timestamp Esatto: 00:00:00.600 (+0.10s su inizio voce) |
|  +----------------------------------------------------+  |                                                         |
|  | 🎵 COLONNA SONORA (BGM) DA YOUTUBE                 |  |  STATO AUDIT FATTIBILITÀ:                               |
|  |  • Brano: Lofi_Chill_Atmosphere_Night (YouTube)    |  |  Materiale Video Disponibile:  COMPLETO (100%) 🟢       |
|  |  • Target Loudness: -24.0 LUFS (EBU R128)          |  |  Conflitti Monosorgente:       NESSUNO ✅               |
|  |  • Auto-Ducking: Attivo (-22 dB voce, -14 dB outro)|  |  Allocazione Coda:             4 Storie / 4 Clip        |
|  +----------------------------------------------------+  |                                                         |
|                                                          |                                                         |
|  +----------------------------------------------------+  |                                                         |
|  | ✍️ TIPOGRAFIA SOTTOTITOLI & BANNER                  |  |                                                         |
|  |  • Font: Montserrat Black (68 pt, TUTTO MAIUSCOLO)  |  |                                                         |
|  |  • Colori: Base #DCE0EA | Parola Attiva #BFA175    |  |                                                         |
|  |  • Effetto: Word Pop Dinamico | Margine Y: 440 px  |  |                                                         |
|  +----------------------------------------------------+  |                                                         |
|--------------------------------------------------------------------------------------------------------------------|
|  [ ✏️ Modifica / Torna Indietro ]                          |   [ 🚀 CONFERMA & AVVIA CREAZIONE DEFINITIVA (4 SHORT) ]|
|  (Riapre la coda per modifiche senza consumare clip)      |   (Avvia GPU & Pipeline Multi-Thread, Blocca a UTILIZZATO)|
+--------------------------------------------------------------------------------------------------------------------+
```

---

#### 3. Specifiche dei Componenti UI della Finestra di Riepilogo

##### A. Header di Paginazione Sequenziale
- **Titolo Finestra**: Stile soft dark con badge di stato e indicatore di auto-save.
- **Pulsanti di Scorrimento (`[ ◀ Precedente ]` e `[ Successiva ▶ ]`)**:
  - Permettono di passare fluidamente da una storia all'altra della coda.
  - Al cambio di pagina, sia la colonna di sinistra (metadati e configurazioni) che il monitor 9:16 di destra (frame a 0.6s) si aggiornano istantaneamente ($< 50\text{ ms}$).
  - Nel caso di produzione a storia singola, la barra di navigazione mostra l'etichetta `STORIA SINGOLA: [Titolo]` con i pulsanti di navigazione disabilitati con eleganza visiva.

##### B. Colonna Sinistra: Moduli di Riepilogo Sintetico
Organizzata in card compatte con contorno delicato `#343946` e sfondo `#21242C`:
1. **Card 1: Script & Metriche Temporali**:
   - Titolo semantico dello script e prime due righe di testo in anteprima.
   - Conteggio parole e verifica conformità della durata ($T_{\text{audio}} \le 43.0\text{ s}$, $T_{\text{video}} = T_{\text{audio}} + 2.0\text{ s}$).
2. **Card 2: Voce Qwen3-TTS & Recitazione**:
   - Profilo vocale (`Ryan`, `Aiden`, clone vocale `.qvoice` o avatar `Voice Design`).
   - Prompt `instruct` emotivo, fattore di velocità WPM, intonazione e assenza di pause anomale.
3. **Card 3: Video Monosorgente & Serie di Clip**:
   - Titolo del video sorgente e coordinate temporali assegnate dal Segment Registry.
   - Verifica di integrità del vincolo monosorgente sequenziale (nessuna contaminazione tra video differenti).
4. **Card 4: Banner Intro & Outro CTA (Stesso Font dello Short)**:
   - Visualizzazione del testo iniziale: `"[Titolo] part.[N]"` (attivo $0.0\text{s} \to 1.5\text{s}$ a centro schermo).
   - Visualizzazione della Call-to-Action finale: `"Subscribe for part.[N+1]"` (o `"Subscribe for more!"` se ultima clip), attiva da $-1.0\text{s}$ fino a fine video con stacco vocale a $-1.5\text{s}$.
5. **Card 5: Colonna Sonora BGM**:
   - Titolo brano convertito da YouTube, normalizzazione sonora EBU R128 a $-24\text{ LUFS}$ e parametri di ducking audio tri-fase (con volume a $-14\text{ dB}$ sull'outro esteso di $1.5\text{ s}$).
6. **Card 6: Tipografia Sottotitoli & Banner**:
   - Famiglia di font ereditata sia per i sottotitoli che per entrambi i banner centrati, dimensione in pt, stile di animazione (*Word Pop* o *Karaoke*), contorno protettivo e posizionamento Y.
7. **Card 7: Thumbnail Seriale Coordinata (Same-Frame Branding)**:
   - **Sfondo Identico per l'Intera Serie**: utilizza lo stesso fotogramma master campionato a $0.60\text{ s}$ per tutte le parti della storia.
   - **Titolazione a Due Righe**: Riga 1 `"[titolo storia]"` e Riga 2 `"part.[numero clip]"` con font uniforme.
   - File generato: `app_data/renders/[titolo]_part[N]_thumb.jpg` (1080x1920 nativo).

##### C. Colonna Destra: Monitor 9:16 & Toggle Ispezione [ Frame 0.60s | Thumbnail Serie ]
- **Monitor Formato 9:16**: Rapporto d'aspetto nativo smartphone (1080x1920 scalato proporzionalmente a 270x480 nella GUI).
- **Selettore Tab di Ispezione**: `[ 📺 Video Frame 0.60s ]`  |  `[ 🖼️ Thumbnail Short ]`:
  1. **Vista Video Frame ($t = 0.60\text{ s}$)**:
     - Mostra il fotogramma campionato dalla clip con impresso sia l'**Intro Title Banner centrato** sia la prima parola parlata attiva in basso con colore di evidenziazione (`#BFA175` Sabbia Dorata).
  2. **Vista Thumbnail Serie**:
     - Visualizza in tempo reale la copertina ufficiale ad alta risoluzione:
       - Sfondo: **lo stesso fotogramma master per tutte le parti della storia**.
       - Testo al centro: Riga 1 `"[titolo storia]"` a capo Riga 2 `"part.[N]"` con font identico, contorno 8px e ombra soft.
- **Toggle Overlay Safe Zones Social**:
  - Checkbox interattiva che proietta le guide per:
    - **Safe Zone 9:16**: Margini video da controlli TikTok, Reels e Shorts.
    - **Safe Zone 1:1 & 3:4 Thumbnail**: Verifica immediata che il titolo su due righe sia centrato e mai tagliato nelle griglie profilo di Instagram (1:1) o nelle tab Shorts di YouTube (3:4).

##### D. Barra di Azione Inferiore (Footer)
- **`[ ✏️ Modifica / Torna Indietro ]` (Pulsante Secondario, Sfondo `#2D323E`, Bordo `#4C5568`)**:
  - Chiude la modale di riepilogo e riporta l'utente alla schermata di configurazione o alla Coda di Produzione.
  - Nessuna transazione viene eseguita nel database: le clip non vengono consumate e lo script rimane con stato `DISPONIBILE`.
- **`[ 🚀 CONFERMA & AVVIA CREAZIONE DEFINITIVA ]` (Pulsante Primario Soft, Sfondo `#6B82A6`, Testo `#FFFFFF`)**:
  - Esegue la validazione finale atomica.
  - Scala definitivamente le clip video dal Video Pool registrando la transazione.
  - Invia i job di montaggio alla coda GPU asincrona multi-thread (`AsyncExecutionCoordinator`).
  - Esegue la transizione di stato dello script da `DISPONIBILE` a `UTILIZZATO` con marcatura oraria irreversibile.
  - Chiude la modale e porta il focus sul `MONITOR ATTIVITÀ MULTI-TASK CONCORRENTI` della Finestra Principale per seguire l'avanzamento del render al 60 FPS senza bloccare la GUI.


---

### 5.14. Finestra di Avanzamento Lavori Professionale & Gestione Annullamento Atomico (ProductionProgressDialog)

Quando l'utente conferma la produzione (singola o batch multi-storia) nella finestra di riepilogo pre-render, l'applicazione visualizza la finestra di avanzamento **`ProductionProgressDialog`**.

A differenza dei tradizionali applicativi che mostrano una console nera con scritte da terminale (output grezzo di FFmpeg o log tecnici illeggibili), questa finestra adotta un'interfaccia **visiva, intuitiva ed executive**, pensata per dare all'utente il massimo controllo in tempo reale mantenendo l'estetica soft dark curata del sistema.

Inoltre, offre una duplice modalità di cancellazione atomica e selettiva:
1. **Annullamento Mirato di Singoli Testi (`Per-Story Cancellation`)**: L'utente può rimuovere uno specifico testo dalla coda in qualsiasi momento (sia se è ancora in attesa, sia se è quello attualmente in elaborazione), senza dover interrompere l'intero batch.
2. **Interruzione Globale della Coda (`Batch Abort`)**: L'utente può arrestare tutta la produzione residua con un solo clic.

In entrambi i casi viene applicata la **Regola Fondamentale di Atomicità a Livello di Intero Testo**:
- **Salvataggio Esclusivo per Testi Completati al 100%**: Un testo narrativo può generare più clip Short sequenziali ($\text{Parte } 1, 2, \dots, M$). Vengono mantenuti salvati **SOLO E SOLTANTO gli Short appartenenti a testi i cui Short sono stati TUTTI generati al 100%**.
- **Cancellazione degli Short di Testi Incompleti**: Se un testo è in lavorazione ed è solo parzialmente prodotto (ad esempio: il Testo 3 richiede 5 Short e l'utente annulla al $3^\circ$ Short), **i 3 Short già creati per quel testo vengono IMMEDIATAMENTE ELIMINATI da disco** per non lasciare sui canali social parti monche o incomplete.
- **Ripristino Totale del Testo e delle Clip**: Il testo incompleto torna nello stato **`🟢 DISPONIBILE`** nell'archivio, e **tutte le sue clip video** (sia quelle dei 3 Short eliminati, sia quelle dei 2 non ancora avviati) **tornano usabili nel Video Pool nella loro sequenza originaria intatta**.

---

#### 1. Wireframe ASCII della Finestra di Avanzamento Lavori (`ProductionProgressDialog`)

```
+--------------------------------------------------------------------------------------------------------------------+
| [X]  AVANZAMENTO PRODUZIONE VIDEO SHORT                                                    [ ● GPU CUDA ATTIVA ⚡ ]|
|--------------------------------------------------------------------------------------------------------------------|
|  STATO GLOBALE BATCH:   2 DI 3 TESTI COMPLETATI AL 100% (6 Short Salvati su 11 Totali)                             |
|  [====================================================----------------------------]  55% COMPLETAMENTO GLOBALE     |
|  Tempo Trascorso: 02m 45s  |  Tempo Rimanente Stimato (ETA): ~02m 10s  |  Velocità Media: 40s per Short            |
|--------------------------------------------------------------------------------------------------------------------|
|                                                                                                                    |
|  TESTO CORRENTE IN LAVORAZIONE (Testo 3 di 3):                                                                     |
|  +--------------------------------------------------------------------------------------------------------------+  |
|  |  📝 Titolo Script: Mystery_Atlantis_DeepSea (Richiede 5 Short Totali: Parti 1, 2, 3, 4, 5)                    |  |
|  |  🎬 Parte Corrente: Parte 3 di 5 (Clip 5 di 10 - Video_A) | 🎙️ Ryan (en-US) • 🎵 Lofi Chill (-24 LUFS)       |  |
|  |--------------------------------------------------------------------------------------------------------------|  |
|  |  PIPELINE A FASI DELLA PARTE 3:                                                                              |  |
|  |                                                                                                              |  |
|  |   [ 1. SINTESI VOCALE ]    -->   [ 2. SOTTOTITOLI ]     -->   [ 3. DUCKING AUDIO ]    -->   [ 4. RENDER 9:16 ]   |  |
|  |      Qwen3-TTS en-US               Faster-Whisper               BGM & Voce Mix            NVENC + ASS Burn       |  |
|  |      [ ✅ COMPLETATO ]            [ ⚡ IN CORSO: 82% ]          [ ⏳ IN ATTESA ]           [ ⏳ IN ATTESA ]      |  |
|  |                                                                                                              |  |
|  |  Avanzamento Parte 3 (Whisper): [====================================================------]  82%            |  |
|  +--------------------------------------------------------------------------------------------------------------+  |
|                                                                                                                    |
|  DETTAGLIO DEI TESTI IN CODA & STATO DEI RISPETTIVI SHORT:                                                         |
|  +--------------------------------------------------------------------------------------------------------------+  |
|  |  #   TESTO NARRATIVO              SHORT RICHIESTI   STATO DI COMPLETAMENTO          AZIONI DISPONIBILI       |  |
|  |--------------------------------------------------------------------------------------------------------------|  |
|  | [1]  Space_BlackHoles_EventHorizon 2 Short (Parti 1-2) ✅ TESTO COMPLETATO (2/2 Short) [ 📂 Apri Cartella MP4 ]|  |
|  | [2]  Science_Brain_Neurons         4 Short (Parti 1-4) ✅ TESTO COMPLETATO (4/4 Short) [ 📂 Apri Cartella MP4 ]|  |
|  | [3]  Mystery_Atlantis_DeepSea      5 Short (Parti 1-5) ⚡ IN CORSO (3 di 5 creati)      [ ⏹️ Salta / Annulla ]  |  |
|  | [4]  Curiosity_Oceans_Abyss        3 Short (Parti 1-3) ⏳ IN CODA (0 di 3 avviati)     [ ✕ Rimuovi dalla Coda ]|  |
|  +--------------------------------------------------------------------------------------------------------------+  |
|                                                                                                                    |
|--------------------------------------------------------------------------------------------------------------------|
|  ℹ️ Regola di Salvataggio: Restano salvati solo gli Short di testi finiti al 100%. Gli Short incompleti si eliminano. |
|                                                                                                                    |
|  [ ⚙️ Riduci a Icona in Background ]                                       [ 🛑 INTERROMPI TUTTA LA CODA RIMANENTE ]|
+--------------------------------------------------------------------------------------------------------------------+
```

---

#### 2. Wireframe ASCII dei Modali di Conferma Interruzione

##### A. Modale di Annullamento Singolo Testo in Lavorazione (`CancelActiveStoryModal`)
Si apre quando l'utente clicca su `[ ⏹️ Salta / Annulla ]` su un testo che ha già prodotto una parte dei suoi Short (es. Testo 3 con 3 Short generati su 5):

```
+--------------------------------------------------------------------------------------------+
| ⚠️  CONFERMA ANNULLAMENTO TESTO INCOMPLETO                                                 |
|--------------------------------------------------------------------------------------------|
|                                                                                            |
|  Stai interrompendo la produzione del Testo 3:                                             |
|  📌 "Mystery_Atlantis_DeepSea" (Richiede 5 Short - Attualmente creati: 3 su 5).            |
|                                                                                            |
|  COSA SUCCEDE CONFERMANDO L'ANNULLAMENTO:                                                  |
|  1. ELIMINAZIONE SHORT PARZIALI: I 3 Short già creati per il Testo 3 VERRANNO ELIMINATI    |
|     immediatamente dal disco (non rimarranno spezzoni orfani o storie incomplete).         |
|  2. TESTO RIUTILIZZABILE: Lo script del Testo 3 tornerà DISPONIBILE nell'archivio.         |
|  3. RIPRISTINO DELLE CLIP VIDEO: Tutte le 5 clip video assegnate al Testo 3 (sia le 3      |
|     usate per gli Short eliminati, sia le 2 non ancora usate) TORNANO USABILI nel          |
|     Video Pool NELLA SEQUENZA ORIGINARIA INTATTA (zero clip sprecate).                     |
|  4. I Testi 1 e 2 già completati al 100% RIMANGONO REGOLARMENTE SALVATI.                  |
|                                                                                            |
|--------------------------------------------------------------------------------------------|
|  [ ↩️ Continua Creazione Testo 3 ]                     [ 🛑 Elimina i 3 Short & Annulla ]  |
+--------------------------------------------------------------------------------------------+
```

##### B. Modale di Interruzione Globale dell'Intera Coda (`CancelBatchModal`)
Si apre quando l'utente preme il pulsante primario `[ 🛑 INTERROMPI TUTTA LA CODA RIMANENTE ]`:

```
+--------------------------------------------------------------------------------------------+
| ⚠️  CONFERMA INTERRUZIONE GLOBALE PRODUZIONE                                                |
|--------------------------------------------------------------------------------------------|
|                                                                                            |
|  Sei sicuro di voler interrompere la produzione dell'intera coda?                          |
|                                                                                            |
|  RIEPILOGO ATOMICO SALVATAGGI & ROLLBACK:                                                  |
|  • TESTI COMPLETATI AL 100% (Testo 1 e Testo 2):                                           |
|    --> RIMARRANNO SALVATI TUTTI GLI SHORT (2 Short del Testo 1 e 4 Short del Testo 2).     |
|    --> I relativi 2 testi restano archiviati come UTILIZZATI.                              |
|                                                                                            |
|  • TESTO INCOMPLETO CORRENTE (Testo 3 - 3 Short su 5 creati):                              |
|    --> I 3 SHORT GIA' CREATI DEL TESTO 3 VERRANNO ELIMINATI DAL DISCO.                     |
|    --> Il Testo 3 tornerà DISPONIBILE nell'archivio.                                       |
|    --> TUTTE LE 5 CLIP VIDEO DEL TESTO 3 TORNANO USABILI NELLA LORO SEQUENZA ORIGINARIA.   |
|                                                                                            |
|  • TESTI NON ANCORA AVVIATI (Testo 4):                                                     |
|    --> Il Testo 4 resta DISPONIBILE e le sue clip video restano usabili nel pool.          |
|                                                                                            |
|--------------------------------------------------------------------------------------------|
|  [ ↩️ Continua la Creazione ]                         [ 🛑 CONFERMA ED INTERROMPI TUTTO ]   |
+--------------------------------------------------------------------------------------------+
```

---

#### 3. Logica Dettagliata di Rollback & Ripristino Integrità

##### A. Testi Interamente Completati al 100% (Preservazione Rigorosa)
- Un testo è "Completato al 100%" **solo se tutti i suoi $M$ Short sono stati interamente esportati** in `app_data/renders/`.
- Tutti gli Short MP4 appartenenti a testi completati (es. i 2 Short del Testo 1 e i 4 Short del Testo 2) rimangono intatti e salvati.
- I corrispondenti script nel database SQLite conservano lo stato definitivo `🔒 UTILIZZATO`.
- I segmenti video continui del video sorgente consumati per questi testi restano marcati come `COMMITTED` e non riutilizzabili.

##### B. Testo Incompleto al Momento dell'Annullamento (es. Testo 3 con 3 su 5 Short Creati)
1. **Eliminazione di Tutti gli Short Già Creati del Testo**:
   - Vengono cancellati dal disco i file MP4 completati delle parti già renderizzate per quel testo (es. `Short_Testo3_Parte1.mp4`, `Short_Testo3_Parte2.mp4`, `Short_Testo3_Parte3.mp4`).
   - Vengono cancellati tutti i file provvisori (`temp_audio.wav`, `temp_subtitles.ass`, `temp_output.part.mp4`) tramite `safe_delete_file_with_retry` per prevenire il blocco `WinError 32` di Windows.
   - Nessun video orfano, monco o incompleto rimane su disco.
2. **Ripristino dello Script a `DISPONIBILE`**:
   - Lo script del testo incompleto viene reimpostato a `🟢 DISPONIBILE` con `used_at = NULL`. Torna immediatamente selezionabile per essere prodotto per intero in futuro.
3. **Ripristino Totale dei Segmenti Video via Segment Registry & Temporal Free-List**:
   - **Tutti i secondi e gli intervalli video assegnati a quel testo tornano integralmente utilizzabili**:
     - I segmenti `video_timeline_segments` della storia annullata vengono eliminati chirurgicamente dal database.
     - **Prevenzione Ghost Gap**: L'intervallo temporale liberato `[start_sec, end_sec]` viene immediatamente registrato nella **Temporal Free-List (Best-Fit)** (`find_free_interval_in_pool`), consentendo alle storie future di riutilizzare il video vuoto senza creare frammentazioni o salti.
     - Se la storia annullata si trovava in testa alla frontiera (`frontier_playhead_sec`), la frontiera viene retrocessa al massimo `end_time_sec` dei segmenti rimasti `COMMITTED`.
     - Nessun secondo viene sprecato e non si verificano scarti prematuri del Garbage Collector ($1\text{m } 30\text{s} +20\text{s}/-\infty$, ovvero $\le 110\text{ s}$).

##### C. Testi in Coda Non Ancora Iniziati
- Vengono rimossi dalla coda di lavorazione.
- Gli script rimangono invariati con stato `🟢 DISPONIBILE`.
- I secondi video prenotati tornano disponibili per nuove allocazioni nel pool.

---

---

---

## 6. Mappa delle Safe Zones per Social Network (9:16)


```
+---------------------------------------------+  ^
|  [   Area Superiore: Barra di Ricerca   ]   |  | 140 px (Non inserire testi chiave)
|---------------------------------------------|  v
|                                             |
|                                             |
|               AREA CENTRALE                 |
|                                             |
|             SICURA AL 100% PER              |
|                                             |
|           TITOLI E VIDEO PRINCIPALE         |
|                                             |
|                                             |
|---------------------------------------------|
|          AREA OTTIMALE SOTTOTITOLI          |  <-- Margine Y: tra 1200px e 1450px
|            [ DISCOVER THIS STORY ]          |      (Visibile su TikTok, IG e Shorts)
|---------------------------------------------|  ^
|                        | Avatar Autore [o]  |  |
|  Area Descrizione      | Like          [♥]  |  |
|  Profilo e Suono       | Commenti      [💬] |  | 360 px (Coperta da UI nativa)
|  TikTok / Instagram    | Condividi     [➜]  |  |
+---------------------------------------------+  v
```

---

## 7. Foglio di Stile Completo QSS (PySide6 Theme Implementation)

```css
/* ====================================================================
   AI SHORT GENERATOR 1.0 - THEME STYLESHEET (PySide6 / Qt)
   Palette scura riposante, zero nero puro (#000000), zero colori fluo
   ==================================================================== */

QWidget {
    background-color: #181A20;
    color: #DCE0EA;
    font-family: "Segoe UI Variable", "Inter", sans-serif;
    font-size: 13px;
    selection-background-color: #6B82A6;
    selection-color: #FFFFFF;
    border: none;
}

/* CARD SUPERFICIALI */
QFrame#CardSurface {
    background-color: #21242C;
    border: 1px solid #343946;
    border-radius: 8px;
    padding: 12px;
}

/* FINESTRE MODALI & CASSETTI */
QDialog#ModalWindow, QFrame#SideDrawer {
    background-color: #252933;
    border: 1px solid #3C4252;
    border-radius: 10px;
}

/* ETICHETTE */
QLabel#SectionHeader {
    font-size: 14px;
    font-weight: 600;
    color: #E2E6EF;
}

QLabel#HelperText {
    font-size: 11px;
    color: #949CAE;
}

/* BADGE DI STATO DEGLI SCRIPT */
QLabel#BadgeAvailable {
    background-color: #22382D;
    color: #729B84;
    border: 1px solid #2D4C3C;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#BadgeUsedLock {
    background-color: #282C37;
    color: #8C94A6;
    border: 1px solid #383E4E;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

/* CAMPI INPUT E TEXT EDIT */
QTextEdit, QLineEdit {
    background-color: #1A1C22;
    color: #DCE0EA;
    border: 1px solid #343946;
    border-radius: 6px;
    padding: 8px;
}

QTextEdit:focus, QLineEdit:focus {
    border: 1px solid #6B82A6;
    background-color: #1D2027;
}

/* PULSANTI */
QPushButton {
    background-color: #2B303C;
    color: #DCE0EA;
    border: 1px solid #3A4150;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #353B4A;
    border-color: #4C5568;
}

QPushButton:disabled {
    background-color: #22252D;
    color: #5A6273;
    border-color: #2D323E;
}

QPushButton#PrimaryButton {
    background-color: #4B5E7D;
    color: #FFFFFF;
    border: 1px solid #5C7296;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #566C8F;
    border-color: #6B84AE;
}

/* TAB BAR (PER ARCHIVIO E VOICE STUDIO) */
QTabBar::tab {
    background-color: #1E2129;
    color: #949CAE;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #2A2E38;
    color: #DCE0EA;
    border-bottom: 2px solid #6B82A6;
}

/* SLIDERS E PROGRESS BAR */
QSlider::groove:horizontal {
    height: 4px;
    background: #2D323E;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #6B82A6;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #B4BCCB;
    border: 1px solid #4C5568;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QProgressBar {
    background-color: #1E2128;
    border: 1px solid #343946;
    border-radius: 4px;
    text-align: center;
    color: #DCE0EA;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #6B82A6;
    border-radius: 3px;
}
```

---

## 8. Ciclo di Vita Utente & Transizione di Stato Post-Creazione

1. **Popolamento Preventivo (Opzionale)**:
   - L'utente apre la modale *"➕ Nuovo Script"*, incolla una storia e clicca *"Salva nell'Archivio"*.
   - Il sistema convalida che non sia un duplicato tramite l'algoritmo $O(1)$, genera il nome di contesto semantico (es. `Space_BlackHoles_EventHorizon`) e la memorizza come `DISPONIBILE`. L'operazione può essere ripetuta per decine di storie.
2. **Selezione Script per il Video**:
   - Dalla finestra principale, l'utente clicca *"📂 Scegli dall'Archivio"* e seleziona lo script desiderato.
   - Lo script viene caricato nel Modulo 1 mostrando il titolo di contesto e le metriche di durata stimata.
3. **Configurazione Voce (Custom, Clone o Voice Design)**:
   - L'utente seleziona un profilo vocale già memorizzato (es. la propria voce clonata `.qvoice` o un avatar sintetico disegnato a parole) oppure seleziona uno speaker predefinito.
   - Sceglie l'istruzione emotiva `instruct` (*Viral Hook*, *Mistero*, ecc.) e testa la resa in streaming sub-100ms.
4. **Selezione o Download Video Background (Flusso Continuo & Monosorgente)**:
   - L'utente seleziona un video dal Video Pool (oppure apre `[ ➕ Scarica Video YT ]` per accodare più link YouTube in successione con conform 9:16 e autenticazione Firefox / `cookies.txt`).
   - **Verifica Vincolo Monosorgente Continuo**: Il solver verifica che il video selezionato possieda una durata continua contigua sufficiente a coprire l'intero fabbisogno della storia ($T_{\text{storia}}$). Tutti gli Short della storia devono provenire dallo stesso identico video master in sequenza continua.
   - **Caso di Durata Continua Insufficiente**: Il sistema blocca il mix di video diversi e alloca un nuovo video master continuo. La storia partirà dal secondo `00:00.0` del nuovo video. I secondi residui del video precedente **non vengono buttati via subito**: restano nel pool per future storie brevi compatibili (o vengono riutilizzati tramite la Free-List).
   - **Garbage Collection Automatica ($1\text{m } 30\text{s} +20\text{s}/-\infty \implies \le 110.0\text{ s}$)**: Se al termine delle produzioni il residuo finale di un master scende a $\le 1\text{m } 50\text{s}$ ($110\text{ s}$), il file master viene eliminato automaticamente da disco liberando spazio e marcato come epurato.
   - La voce viene sintetizzata con Qwen3-TTS ($\le 43.0\text{ s}$).
5. **Configurazione Musica di Sottofondo (BGM) & Sottotitoli**:
   - Ingestion automatica della traccia YouTube o selezione da libreria Safe CC0 / Royalty-Free (o modalità raccomandata `Nessuna Musica` per trend social) con normalizzazione a $-24.0\text{ LUFS}$ e ducking con rampe morbide ($150\text{ms}$ attack, $300\text{ms}$ release, $-22\text{ dB}$ voce, $-14\text{ dB}$ intro/outro).
   - Scelta del preset font, animazione parola per parola, Intro Title Banner centrato a $0.0\text{s} \to 1.5\text{s}$, Outro CTA Banner centrato da $-1.0\text{s}$ a fine video con stacco voce a $-1.5\text{s}$, e allineamento Safe Zones.
6. **Finestra Modale di Riepilogo Pre-Render & Ispezione Visiva Frame 0.6s (`PreProductionReviewModal`)**:
   - Al clic su `[ 🚀 PROCEDI ALLA CREAZIONE DEI CONTENUTI ]` (o `[ 🚀 AVVIA PRODUZIONE BATCH ]`), il rendering **non parte alla cieca**.
   - Si apre la finestra di riepilogo in cui l'utente ispeziona **uno a uno** ogni video da produrre tramite carosello `[ ◀ Precedente ] Storia X di N [ Successiva ▶ ]`.
   - Vengono mostrati: riepilogo sintetico di script, durata, voce, segmento video continuo assegnato monosorgente, BGM e font.
   - **Ispezione Visiva Frame 0.6s**: Viene mostrato il primo fotogramma esatto in cui compaiono i sottotitoli a video ($t = 0.60\text{ s}$, corrispondente a $+0.10\text{ s}$ dall'inizio della voce) con il Title Banner centrato e la prima parola karaoke attiva impressa sopra il video reale di background, per verificare a colpo d'occhio leggibilità, contrasto cromatico e posizionamento Safe-Area.
   - **Thumbnail Coordinata Serie**: Ispezione della copertina ufficiale generata con lo stesso frame di sfondo per tutte le parti della storia, titolazione su due righe e font coordinato.
   - L'utente può cliccare `[ ✏️ Modifica / Torna Indietro ]` per cambiare qualsiasi parametro a costo zero, oppure dare il via definitivo con `[ 🚀 CONFERMA & AVVIA CREAZIONE DEFINITIVA ]`.
7. **Avanzamento Lavori Professionale (`ProductionProgressDialog`) & Gestione Annullamento in Qualsiasi Momento**:
   - Al via libera definitivo, si apre la finestra di avanzamento executive con stepper visivo delle 4 fasi per ogni storia, indicatori percentuali chiari ed ETA.
   - **Possibilità di Cancellazione Istantanea**: In qualsiasi momento, l'utente può premere `[ 🛑 INTERROMPI CREAZIONE ]` o rimuovere singoli testi con `[ ✕ Rimuovi dalla Coda ]` / `[ ⏹️ Salta / Annulla ]`.
   - **Rollback Atomico & Integrità delle Risorse (Regola per Intero Testo)**:
     - **Vengono mantenuti salvati SOLO gli Short di testi completati al 100%** (tutti i loro Short esportati, es. Testi 1 e 2) e contrassegnati come `🔒 UTILIZZATO`.
     - **Per i testi rimasti incompleti (es. Testo 3 con 3 su 5 Short creati)**: i 3 Short già creati vengono **immediatamente eliminati da disco** (cancellazione protetta da retry contro `WinError 32` per i file MP4 parziali, `.wav` e `.ass`), lo script del Testo 3 torna nello stato `🟢 DISPONIBILE` nell'archivio.
     - **Segment Free-List Registry**: Tutti i segmenti temporali assegnati al testo incompleto tornano disponibili nella Free-List per essere riutilizzati da storie successive (Best-Fit), oppure la frontiera `frontier_playhead_sec` retrocede se il testo era in cima alla sequenza. Zero secondi sprecati e zero buchi orfani.
     - I testi in coda non avviati rimangono `🟢 DISPONIBILE`.
   - A processo completato al 100% per un testo, i segmenti video utilizzati vengono consolidati definitivamente come `COMMITTED` e lo script passa irreversibilmente da `🟢 DISPONIBILE` a `🔒 UTILIZZATO (Completato)`.


