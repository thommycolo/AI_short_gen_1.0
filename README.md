# AI Short Generator (1.0)
### Desktop Application Standalone per Windows (`.exe`) — Zero WebApp
##### Pipeline di Generazione Video AI per TikTok, Instagram Reels e YouTube Shorts

Benvenuto nella documentazione ufficiale di **AI Short Generator 1.0**.

> [!IMPORTANT]
> **Applicazione Desktop Nativa Windows (`.exe`)**: Questo software è un programma desktop nativo a 64-bit distribuito con launcher eseguibile **`AI_Short_Generator.exe`** (< 50 MB, avvio < 1 secondo) tramite architettura portabile **PyInstaller `--onedir`** e installatore standard guidato **Inno Setup** (`AI_Short_Generator_Setup_v1.0.exe`).
> **Zero Bloat in %TEMP% & Zero Crash DLL**: Nessuna decompressione temporanea di 10 GB all'avvio. Le librerie PyTorch CUDA, i pesi dei modelli (scaricati al primo avvio tramite wizard guidato in `%LOCALAPPDATA%\AI_Short_Generator\models\`) e i binari FFmpeg risiedono stabilmente su disco.
> **La Matematica dei 4,0 GB**: Tetto massimo totale GPU di 4.000 MB. Sottratti 1.200 MB per Windows DWM, display e GUI Qt, l'applicazione rispetta un **budget netto rigoroso di 2.800 MB (2,8 GB)**, garantito da quantizzazione FP8, hard cap di memoria e isolamento subprocess.
> **NON è una WebApp**: non viene eseguito all'interno di un browser (Chrome/Edge/Firefox), non avvia web server (zero Flask/Streamlit/Gradio) e non utilizza framework web pesanti (zero Electron). Tutta la grafica è renderizzata nativamente via **PySide6 / Qt 6.7+** con accelerazione hardware diretta a 60 FPS.

---

## 📚 Documenti di Riferimento

Il progetto è dettagliato in due documenti esecutivi completi e allineati:

### 1. [PIANO_PROGETTO.md](file:///c:/Users/thomm/AI_short_gen_1.0/PIANO_PROGETTO.md) — *Piano Tecnico & Architetturale*
Contiene tutte le specifiche ingegneristiche e implementative con la risoluzione chirurgica di tutte le fallacie architetturali:

- **Sblocco Deadlock Script: Creazione Nuova Variante / Rigenera**:
  - Supera il blocco permanente dello stato `UTILIZZATO`: quando l'utente incolla o rielabora un testo già prodotto, il sistema espone l'opzione esplicita **"Crea Variante / Rigenera"** (`is_variant_of`, `variant_label`). Permette di rigenerare lo stesso testo con speaker, stile, font o velocità differenti senza essere respinto dalla deduplica.
- **Deduplica Multi-Index SimHash & Two-Phase Checking**:
  - Supera la vulnerabilità "Bag of Words": calcola l'impronta a 64 bit tramite **Character 3-grams Shingling + Word Bi-grams** pesati per frequenza (TF).
  - Memorizzazione esadecimale `simhash_hex TEXT(16)` per prevenire l'overflow signed int64 di SQLite, indicizzata su **6 blocchi unsigned da 10/11 bit** (`simhash_b1..b6`) con principio dei cassetti (Pigeonhole): lookup True $O(1)$ per distanze di Hamming $\le 5$.
  - Verifica a 2 fasi: Fase 1 bitwise unsigned int64 su hash in memoria; Fase 2 fetch di `raw_text` dal database SQLite WAL solo ed esclusivamente se Hamming $\le 5$, con validazione Jaccard $\ge 0.80$.
- **Normalizzazione Deterministica & Parser Sintattico `inflect`**:
  - Esecuzione locale sub-millisecondo (< 0.2ms) in memoria CPU (0 MB VRAM, zero demoni o server esterni).
  - Elaborazione esclusiva testi in **lingua inglese** (100% English inputs): espansione deterministica di 250+ lemmi slang e contrazioni (`schl` $\to$ `school`, `btw` $\to$ `by the way`, `idk` $\to$ `I do not know`, `rn` $\to$ `right now`, `w/` $\to$ `with`, `approx.` $\to$ `approximately`, `u` $\to$ `you`, ecc.) con regex boundary-protected contro falsi positivi (`_STRICT_LOWER_U`, `_STRICT_LOWER_R`, acronimi protetti `US`, `UK`, `AI`, `NASA`).
  - **Parser Sintattico Numeri e Valute con `inflect`**: Elimina le regex artigianali che corrompevano numeri grandi. Gestione impeccabile di valute composte (`$1,500` $\to$ `one thousand, five hundred dollars`, `$1` $\to$ `one dollar`, `$1.50` $\to$ `one dollar and fifty cents`), percentuali (`50%` $\to$ `fifty percent`) e numeri grandi formattati con virgole (`1,000,000` $\to$ `one million`).
- **Segmentazione Narrativa Deterministica (`DiscourseCoherenceChunker`)**:
  - Sostituito il pesante modello transformer `all-MiniLM-L6-v2` con un motore deterministico basato su regole di coerenza discorsiva su CPU (< 1ms, 0 MB VRAM).
  - Divieto assoluto di separare coppie domanda-risposta (se una frase termina con `?`, la successiva rimane nello stesso Reel).
  - Penalizzazione connettivi narrativi a inizio Reel (*However, Furthermore, Therefore, Consequently, But, And*).
  - Preservazione del legame anaforico (pronomi di terza persona ancorati al loro antecedente).
- **La Matematica dei 4,0 GB & Subprocess Isolation (Netto < 2.8 GB)**:
  - Budget Netto Applicazione: **2.800 MB (2,8 GB Netto)** (Tetto massimo 4.000 MB - 1.200 MB per DWM e PySide6).
  - **Qwen3-TTS 1.7B in Quantizzazione FP8 / INT8**: Pesi compressi a 1.7 GB, runtime totale 2.5 GB (ben sotto il budget di 2.8 GB netti). Fedeltà vocale intatta al 99.9%.
  - **Isolamento Worker Subprocess Python (`multiprocessing` context `spawn`)**: Quando il worker TTS termina la generazione, il processo muore e il kernel WDDM di Windows è forzato a bonificare istantaneamente il 100% della VRAM, azzerando la frammentazione e i leak tra batch.
  - Hard cap hardware: `torch.cuda.set_per_process_memory_fraction(0.35)` e `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
- **Allineamento Fonetico Millimetrico: Whisper `large-v3-turbo` (INT8 CUDA)**:
  - Superato il paradosso della CPU e del modello base: Faster-Whisper esegue `large-v3-turbo` in INT8 su CUDA consumando appena **1.1 GB di VRAM** (a GPU libera dopo l'uscita del worker TTS).
  - Trascrizione in **0.3s** (contro 2-3s su CPU) con jitter $< 20\text{ ms}$, garantendo un effetto karaoke word-by-word impeccabile a 60 FPS.
- **Risoluzione del Deadlock Cronometrico: Ground Truth Audio Reale**:
  - Superata la riserva video stimata a priori: l'audio generato da Qwen3-TTS e rifinito con Silero VAD rappresenta la **Ground Truth temporale assoluta** misurata al millisecondo sul file WAV salvato.
  - La riserva del segmento video (`reserve_segment_for_story`) avviene solo a valle, richiedendo la durata esatta $T_{\text{video}} = T_{\text{audio}} + 2.0\text{ s}$.
- **Continuità Tematica per Categoria & Grafo di Normalizzazione Hardware FFmpeg**:
  - Gli Short possono combinare spezzoni da file master differenti della stessa categoria (`Minecraft`, `Subway Surfers`, `GTA V`, `Satisfying`, `Drone/Nature`, `General`).
  - Il grafo filtri FFmpeg impone una **normalizzazione hardware preventiva** (`fps=60,setsar=1,format=nv12,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920`) a ciascun flusso prima della concatenazione (`concat`), prevenendo qualsiasi crash o desync con l'encoder NVENC.
  - **Bounded Right Edge Snapping**: snap ai tagli di scena vincolato al margine destro dello slot libero (`end_time_sec = min(snapped_end, slot_right_boundary)`).
- **Tipografia ASS: Bounding Box Geometrico in Pixel ($\le 880\text{ px}$)**:
  - Superata la regola empirica delle 3 parole: calcolo geometrico reale con `ImageFont.getlength()` (Pillow) sul font renderizzato (es. Montserrat Black 68pt). A capo automatico (`\N`) appena la riga supera gli $880\text{ px}$ di Safe Zone utile, con massimo 2 righe per evento visivo.
- **Trimming Vocale Fonetico Avanzato (`SileroVADSilenceTrimmer`)**:
  - Silero VAD v5 (ONNX su CPU < 2 MB): rilevamento esatto dell'attacco fonetico al millisecondo con 30ms di pre-roll, eliminando l'amputazione di consonanti occlusive o sibilanti (*Think, Summer, Hello*).
- **Timing & Padding Sincronizzato (+2.0s Totale) & Banner Centrati**:
  - Con `adelay=500|500` ($+0.5\text{ s}$ lead-in) e outro video a $+1.5\text{ s}$ ($T_{\text{video}} = T_{\text{audio}} + 2.0\text{ s}$), il parlato parte a $0.500\text{ s}$ e stacca a $1.500\text{ s}$ prima del termine.
  - **Intro Title Banner ($0.0\text{ s} \to 1.5\text{ s}$)**: centrato a schermo (`Alignment 5`), `"[nome del testo] part.[numero clip]"`.
  - **Outro CTA Banner ($T_{\text{video}} - 1.0\text{ s} \to T_{\text{video}}$)**: centrato a schermo (`Alignment 5`), `"Subscribe for part.[i+1]"` o `"Subscribe for more!"`.
- **Thumbnail Coordinate di Serie (Same-Frame Series Branding)**:
  - Copertina verticale 9:16 (`.jpg` 1080x1920) per ciascun Short riutilizzando lo stesso identico fotogramma master campionato a $0.600\text{ s}$ con testo a 2 righe outline.
- **Audio Mix Professionale & True Peak Limiter a -1.0 dB**:
  - Rimosso `volume=2` su `amix` e impostato `normalize=0`. True Peak Limiter a -1.0 dB a fine catena per azzerare distorsioni su smartphone.

---

### 2. [DESIGN_APP.md](file:///c:/Users/thomm/AI_short_gen_1.0/DESIGN_APP.md) — *Design System, UI/UX & Wireframe*
Contiene la progettazione visiva ed esperienziale della GUI:
- **Filosofia Visiva**: Toni scuri morbidi (vietato il nero puro `#000000`), palette cromatica non-fluo omogenea e delicata.
- **Layout Compatto & Monitor Multi-Task**: Sostituzione del campo di testo ingombrante con card snelle e inserimento del box persistente `MONITOR ATTIVITÀ MULTI-TASK CONCORRENTI` (tracciamento VRAM netta $< 2.8\text{ GB}$, totale $< 4.0\text{ GB}$).
- **Finestra Modale Inserimento Script (`ScriptInputModal`)**:
  - Interfaccia ottimizzata per testi 100% English. Normalizzazione deterministica con parser sintattico `inflect`, deduplica Shingling SimHash True $O(1)$ e opzione "Crea Nuova Variante" per sblocco duplicati.
- **Finestra Modale Archivio & Storico (`ScriptLibraryModal`)**: Tab per testi `DISPONIBILI` e `UTILIZZATI` (con pulsante `[ 🔄 Crea Variante / Rigenera ]`).
- **Finestre Modali Video Pool (`VideoDownloadModal` & `VideoLibraryModal`)**:
  - Selezione e auto-classificazione per Categoria (`Minecraft`, `Subway Surfers`, `GTA V`, ecc.), badge Zero-Recode Ingestion (< 3s import).
- **Studio Voce Avanzato & Voice Intelligence (Qwen3-TTS en-US)**:
  - Voci americane (`Ryan`, `Vivian`, `Aiden`), quantizzazione FP8, isolamento subprocess worker con scaricamento totale WDDM.
- **Subtitle Designer & Safe-Zone Studio**:
  - Bounding box geometrico in pixel ($\le 880\text{ px}$), anteprima 9:16 live sul video effettivo.
- **Finestra Modale Pre-Render Review (`PreProductionReviewModal`)**:
  - Ispezione sequenziale carosello 1-a-1 con anteprima del fotogramma composito a $0.600\text{ s}$ e della Thumbnail di serie.
- **Finestra Avanzamento Lavori (`ProductionProgressDialog`)**: Stepper a 4 fasi con rollback atomico su crash o cancellazione.
