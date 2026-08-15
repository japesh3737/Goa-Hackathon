import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.dataset_loader import MSMARCODatasetLoader

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a small development sample from MSMARCO-XI dataset.")
    parser.add_argument("--limit", type=int, default=500, help="Number of records to extract (default: 500)")
    parser.add_argument("--output", type=str, default=None, help="Output parquet filepath")
    args = parser.parse_args()

    print(f"=== Creating MSMARCO-XI Sample Dataset (Limit={args.limit}) ===")
    loader = MSMARCODatasetLoader()
    output_path = loader.create_sample_file(limit=args.limit, output_path=args.output)
    print(f"Sample creation complete! Saved to {output_path}")
