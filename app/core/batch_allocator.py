"""AI Short Generator 1.0 - Batch Allocator & Feasibility Solver with Category Continuity"""

import itertools
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from app.config import PURGE_THRESHOLD_MAX


@dataclass
class StoryRequirement:
    script_id: int
    context_title: str
    num_parts: int
    base_duration_sec: float     # A velocità nominale 1.00x
    speed_rate: float            # Velocità scelta nello slider (es. 1.15x)
    category: str = "General"    # Categoria tematica richiesta
    text: str = ""
    voice_config: Optional[dict] = None
    subtitle_config: Optional[dict] = None
    bgm_config: Optional[dict] = None

    @property
    def estimated_video_seconds(self) -> float:
        """Calcola i secondi video continui richiesti alla velocità impostata (+2.0s padding per short)."""
        rate = max(0.5, self.speed_rate)
        audio_dur = self.base_duration_sec / rate
        return audio_dur + (self.num_parts * 2.0)


@dataclass
class VideoSourceCandidate:
    source_id: int
    title: str
    category: str
    available_duration_sec: float
    current_playhead_sec: float
    file_path: str = ""


@dataclass
class AllocationPlanItem:
    story: StoryRequirement
    assigned_source_id: int
    source_title: str
    category: str
    start_time_sec: float
    end_time_sec: float
    allocated_seconds: float
    leftover_after: float
    is_purged_after: bool


@dataclass
class FeasibilityReport:
    is_feasible: bool
    total_stories: int
    total_seconds_needed: float
    total_seconds_available: float
    plans: List[AllocationPlanItem]
    deficit_seconds: float
    unassigned_stories: List[StoryRequirement]
    projected_pool_summary: List[dict]


@dataclass
class SubQueueSuggestion:
    selected_stories: List[StoryRequirement]
    excluded_stories: List[StoryRequirement]
    feasibility_report: FeasibilityReport
    wasted_seconds_purged: float  # Secondi che cadono nella soglia <= 1m 50s ed eliminati
    utilized_seconds: float       # Secondi video montati utilmente


class ContinuousBatchFeasibilitySolver:
    PURGE_THRESHOLD_MAX = PURGE_THRESHOLD_MAX # 110.0s (1m 50s)

    @classmethod
    def solve(cls, stories: List[StoryRequirement], pool: List[VideoSourceCandidate]) -> FeasibilityReport:
        """
        Risolutore di allocazione continua con Continuità Tematica per Categoria:
        Assegna intervalli temporali da sorgenti compatibili per categoria,
        minimizzando gli scarti e verificando la fattibilità globale.
        """
        virtual_pool = {
            v.source_id: {
                "title": v.title,
                "category": v.category,
                "available": v.available_duration_sec,
                "playhead": v.current_playhead_sec,
                "file_path": v.file_path
            } for v in pool
        }

        total_needed = sum(s.estimated_video_seconds for s in stories)
        total_avail = sum(v["available"] for v in virtual_pool.values())

        plans: List[AllocationPlanItem] = []
        unassigned: List[StoryRequirement] = []

        for story in stories:
            req_sec = story.estimated_video_seconds
            best_source_id = None
            min_waste = float("inf")

            # 1. Ricerca candidati con categoria coincidente (o General)
            candidates = {
                sid: data for sid, data in virtual_pool.items()
                if (data["category"] == story.category or story.category == "General" or data["category"] == "General")
                and data["available"] >= req_sec
            }

            # 2. Tightest-Fit con minimizzazione scarti
            for sid, state in candidates.items():
                leftover = state["available"] - req_sec
                waste = leftover if (leftover <= cls.PURGE_THRESHOLD_MAX) else 0.0
                if waste < min_waste:
                    min_waste = waste
                    best_source_id = sid

            if best_source_id is None:
                unassigned.append(story)
                continue

            state = virtual_pool[best_source_id]
            start_t = state["playhead"]
            end_t = start_t + req_sec
            leftover = state["available"] - req_sec

            will_be_purged = (leftover <= cls.PURGE_THRESHOLD_MAX)
            state["available"] = 0.0 if will_be_purged else leftover
            state["playhead"] = end_t

            plans.append(AllocationPlanItem(
                story=story,
                assigned_source_id=best_source_id,
                source_title=state["title"],
                category=state["category"],
                start_time_sec=start_t,
                end_time_sec=end_t,
                allocated_seconds=req_sec,
                leftover_after=leftover,
                is_purged_after=will_be_purged
            ))

        is_feasible = (len(unassigned) == 0)
        deficit = sum(s.estimated_video_seconds for s in unassigned)

        projected_summary = [
            {
                "source_id": sid,
                "title": data["title"],
                "category": data["category"],
                "final_available": data["available"],
                "status": "EPURATO" if data["available"] == 0.0 else "PARZIALMENTE_USATO"
            } for sid, data in virtual_pool.items()
        ]

        return FeasibilityReport(
            is_feasible=is_feasible,
            total_stories=len(stories),
            total_seconds_needed=total_needed,
            total_seconds_available=total_avail,
            plans=plans,
            deficit_seconds=deficit,
            unassigned_stories=unassigned,
            projected_pool_summary=projected_summary
        )

    @classmethod
    def suggest_optimal_subqueue(
        cls,
        requested_stories: List[StoryRequirement],
        pool: List[VideoSourceCandidate]
    ) -> List[SubQueueSuggestion]:
        """
        In caso di materiale insufficiente, trova e raccomanda la sotto-coda
        che minimizza i secondi di video eliminati nella finestra di scarto <= 1m 50s.
        """
        m = len(requested_stories)
        valid_suggestions: List[SubQueueSuggestion] = []

        for target_k in range(m - 1, 0, -1):
            for subset in itertools.combinations(requested_stories, target_k):
                subset_list = list(subset)
                report = cls.solve(subset_list, pool)

                if report.is_feasible:
                    wasted_sec = sum(
                        p.leftover_after for p in report.plans if p.is_purged_after
                    )
                    used_sec = sum(s.estimated_video_seconds for s in subset_list)
                    excluded = [s for s in requested_stories if s not in subset_list]

                    valid_suggestions.append(SubQueueSuggestion(
                        selected_stories=subset_list,
                        excluded_stories=excluded,
                        feasibility_report=report,
                        wasted_seconds_purged=wasted_sec,
                        utilized_seconds=used_sec
                    ))

            if valid_suggestions:
                break

        # Ordina: 1. Minimizza scarti buttati, 2. Massimizza secondi usati
        valid_suggestions.sort(key=lambda s: (s.wasted_seconds_purged, -s.utilized_seconds))
        return valid_suggestions

