"""AI Short Generator 1.0 - Discourse Coherence Chunker (<1ms CPU, 0 MB VRAM)"""

import re
from typing import List, Optional
from app.config import DEFAULT_WPS, TARGET_VIDEO_MAX_SEC, ALLOWED_CHUNKING_DELTA_SEC, PADDING_TOTAL_SEC


class DiscourseCoherenceChunker:
    """
    Gestisce l'enhancing prosodico, la segmentazione atomica (spaCy en_core_web_sm o regex)
    e la segmentazione per coerenza discorsiva deterministica su CPU (< 1ms, 0 MB VRAM)
    con tolleranza +-7s (38s - 45s).
    Padding totale: 2.0s (0.5s Intro + 1.5s Outro esteso).
    """

    DISCOURSE_CONNECTIVES = {
        "however", "therefore", "because", "although", "meanwhile", "moreover",
        "furthermore", "consequently", "but", "and", "thus", "hence", "otherwise",
        "nevertheless", "nonetheless", "besides", "instead", "yet"
    }

    ANAPHORIC_PRONOUNS = {
        "he", "she", "it", "they", "this", "that", "these", "those"
    }

    def __init__(self):
        self._nlp = None

    def _get_nlp(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
            except Exception:
                self._nlp = None
        return self._nlp

    def enhance_speech_text(self, text: str) -> str:
        """Applica le regole di formattazione ritmica per la narrazione di Qwen3-TTS."""
        text = re.sub(r'\s*;\s*', ', ', text)
        text = re.sub(r'\s*:\s*', '... ', text)
        text = re.sub(r'\s*[—–]\s*', ', ', text)
        return text

    def segment_atomic_sentences(self, text: str) -> List[str]:
        """Estrae le frasi atomiche sintatticamente inscindibili per testi in lingua inglese."""
        nlp = self._get_nlp()
        if nlp is not None:
            doc = nlp(text)
            sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 0]
            if sentences:
                return sentences

        # Fallback Deterministico Regex per lingua inglese
        protected = re.sub(r"([.!?]+)\s+(?=[A-Z0-9])", r"\1\n", text)
        sentences = [s.strip() for s in protected.split("\n") if s.strip()]
        return sentences

    def _is_question(self, sentence: str) -> bool:
        """Verifica se la frase è un'interrogativa."""
        return sentence.rstrip().endswith("?")

    def _starts_with_connective(self, sentence: str) -> bool:
        """Verifica se la frase inizia con un connettivo avversativo o causale."""
        first_word = re.findall(r"^[a-zA-Z]+", sentence.lower())
        return bool(first_word and first_word[0] in self.DISCOURSE_CONNECTIVES)

    def _starts_with_anaphora(self, sentence: str) -> bool:
        """Verifica se la frase inizia con un pronome anaforico dipendente dal contesto precedente."""
        first_word = re.findall(r"^[a-zA-Z]+", sentence.lower())
        return bool(first_word and first_word[0] in self.ANAPHORIC_PRONOUNS)

    def chunk_story_coherently(
        self,
        full_text: str,
        target_video_max: float = TARGET_VIDEO_MAX_SEC,      # Limite video 45.0s (Audio max 43.0s con 2.0s padding)
        allowed_delta_sec: float = ALLOWED_CHUNKING_DELTA_SEC,# Tolleranza +-7s: Reel consentiti tra 38.0s e 45.0s
        avg_wps: float = DEFAULT_WPS                         # Velocità standard unificata 2.50 WPS (150 WPM)
    ) -> List[str]:
        """
        Suddivide lo script preservando l'integrità logico-discorsiva del dialogo e della narrazione:
        - Mai spezzare una coppia domanda-risposta (frase dopo '?').
        - Mai iniziare un Reel con un connettivo (However, Therefore, Because, ecc.).
        - Preserva i legami anaforici.
        Finestra audio consentita: tra 36.0s e 43.0s (Reel video da 38.0s a 45.0s).
        """
        if not full_text.strip():
            return []

        # 1. Speech Enhancing
        enhanced = self.enhance_speech_text(full_text)

        # 2. Segmentazione Atomica
        sentences = self.segment_atomic_sentences(enhanced)
        if not sentences:
            return []

        # Durata stimata per singola frase
        sent_durations = [len(s.split()) / avg_wps for s in sentences]
        total_audio_dur = sum(sent_durations)

        total_padding = PADDING_TOTAL_SEC                             # 0.5s Intro + 1.5s Outro = 2.0s
        max_audio_dur = target_video_max - total_padding              # 43.0s (Video 45.0s)
        min_audio_dur = max_audio_dur - allowed_delta_sec             # 36.0s (Video 38.0s)

        # Se l'intera storia sta in un solo reel (<= 43.0s)
        if total_audio_dur <= max_audio_dur:
            return [" ".join(sentences)]

        chunks: List[str] = []
        curr_sentences: List[str] = []
        curr_dur: float = 0.0

        for idx, (sent, dur) in enumerate(zip(sentences, sent_durations)):
            # Se l'aggiunta della frase eccede il limite invalicabile di 43.0s:
            if curr_dur + dur > max_audio_dur and curr_sentences:
                chunks.append(" ".join(curr_sentences))
                curr_sentences = [sent]
                curr_dur = dur
                continue

            curr_sentences.append(sent)
            curr_dur += dur

            # Verifichiamo se possiamo chiudere il chunk nella finestra [36.0s, 43.0s]
            if curr_dur >= min_audio_dur and idx < len(sentences) - 1:
                next_sent = sentences[idx + 1]

                # REGOLA 1: Se la frase corrente è una domanda, la prossima è la risposta -> NON spezzare
                if self._is_question(sent):
                    continue

                # REGOLA 2: Se la frase successiva inizia con un connettivo, non può iniziare un Reel -> NON spezzare qui
                if self._starts_with_connective(next_sent):
                    continue

                # REGOLA 3: Se la frase successiva inizia con un pronome anaforico forte -> preferisci non spezzare se c'è spazio
                if self._starts_with_anaphora(next_sent) and (curr_dur + sent_durations[idx + 1] <= max_audio_dur):
                    continue

                # Punto di stacco ideale
                chunks.append(" ".join(curr_sentences))
                curr_sentences = []
                curr_dur = 0.0

        if curr_sentences:
            chunks.append(" ".join(curr_sentences))

        return chunks

