import json
import logging
from typing import Dict, Any, List
import urllib.request
from app.config import config

logger = logging.getLogger(__name__)

class MSMARCODatasetInspector:
    """Inspects HuggingFace dataset ai4bharat/MSMARCO-XI schema and splits programmatically."""

    def __init__(self, dataset_name: str = None):
        self.dataset_name = dataset_name or config.DATASET_NAME

    def fetch_hf_metadata(self) -> Dict[str, Any]:
        url = f"https://huggingface.co/api/datasets/{self.dataset_name}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to fetch HF dataset metadata: {e}")
            return {"error": str(e)}

    def fetch_parquet_configs(self) -> Dict[str, Any]:
        url = f"https://huggingface.co/api/datasets/{self.dataset_name}/parquet"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to fetch HF parquet configs: {e}")
            return {"error": str(e)}

    def inspect_sample_schema(self) -> Dict[str, Any]:
        """Loads a small sample from parquet or datasets streaming to discover exact column names."""
        report = {
            "dataset_name": self.dataset_name,
            "hf_metadata": self.fetch_hf_metadata(),
            "parquet_configs": self.fetch_parquet_configs(),
            "detected_schema": None,
            "sample_record": None
        }

        try:
            from datasets import load_dataset
            logger.info("Streaming sample record from HuggingFace datasets...")
            dataset = load_dataset(self.dataset_name, config.DATASET_CONFIG, split=config.DATASET_SPLIT, streaming=True)
            for item in dataset:
                report["detected_schema"] = {k: type(v).__name__ for k, v in item.items()}
                report["sample_record"] = item
                break
        except Exception as e:
            logger.warning(f"Could not load via HuggingFace datasets streaming directly: {e}")
            # Fallback to pandas reading single parquet
            try:
                import pandas as pd
                parquet_info = report["parquet_configs"]
                if isinstance(parquet_info, dict) and "default" in parquet_info:
                    train_files = parquet_info["default"].get("train", [])
                    if train_files:
                        df_sample = pd.read_parquet(train_files[0])
                        first_row = df_sample.iloc[0].to_dict()
                        report["detected_schema"] = {k: str(v) for k, v in df_sample.dtypes.to_dict().items()}
                        report["sample_record"] = {k: (v.tolist() if hasattr(v, "tolist") else str(v)) for k, v in first_row.items()}
            except Exception as ex:
                logger.error(f"Fallback parquet inspect failed: {ex}")
                report["inspection_error"] = str(ex)

        return report

def inspect_and_save_report(output_path: str = "data/schema_report.json") -> Dict[str, Any]:
    inspector = MSMARCODatasetInspector()
    report = inspector.inspect_sample_schema()
    try:
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Saved dataset schema report to {output_path}")
    except Exception as e:
        logger.error(f"Could not save schema report: {e}")
    return report

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rep = inspect_and_save_report()
    print("Schema Keys:", rep.get("detected_schema"))
