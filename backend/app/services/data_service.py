import json
import logging
from pathlib import Path
from app.core.paths import SEED_DIR
from app.schemas.provenance import DataProvenance, MetricWithProvenance

logger = logging.getLogger(__name__)


class DataService:
    """Reads the bundled seed fixtures from `backend/data/seed/`.

    Previously this globbed `backend/app/data`, which does not exist, so
    `self.datasets` was always empty and every lookup returned `[]`. Callers that
    depend on an empty result were reading an empty directory, not an empty
    dataset.
    """

    def __init__(self):
        self.datasets: dict[str, list | dict] = {}
        self.missing: list[str] = []
        self.load_all()

    def load_all(self):
        self.missing = []
        for file in sorted(SEED_DIR.glob("*.json")):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.datasets[file.stem] = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("Could not load seed dataset %s: %s", file, exc)
                self.missing.append(file.stem)
        if self.missing:
            logger.error("Seed datasets unavailable: %s", ", ".join(self.missing))
        return self.datasets

    def get_dataset(self, name: str) -> list | dict:
        return self.datasets.get(name, [])

    def has_dataset(self, name: str) -> bool:
        return name in self.datasets
        
    def get_provenance_for_dataset(self, dataset_name: str, fallback_confidence: str = "medium") -> DataProvenance:
        sources = self.datasets.get("data_sources", [])
        for src in sources:
            if src.get("dataset") == dataset_name:
                return DataProvenance(
                    source_type=src.get("type", "open_data"),
                    source_name=src.get("name", "Unknown Source"),
                    dataset_name=dataset_name,
                    last_updated=src.get("last_updated"),
                    confidence=src.get("confidence", fallback_confidence)
                )
        # Fallback if not defined
        return DataProvenance(
            source_type="demo_data",
            source_name="Fallback Local Dataset",
            dataset_name=dataset_name,
            confidence=fallback_confidence,
            methodology="Loaded from local static files without strict source tracking."
        )

    def get_metric_with_provenance(self, value, dataset_name: str) -> MetricWithProvenance:
        return MetricWithProvenance(
            value=value,
            provenance=self.get_provenance_for_dataset(dataset_name)
        )

data_service = DataService()
