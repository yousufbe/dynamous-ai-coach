"""CLI wrapper to compare baseline vs fine-tuned embeddings."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from src.rag_pipeline.embeddings.eval import (
    EvaluationRequest,
    run_evaluation,
    write_report,
)
from src.shared.logging import get_logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(description="Run embedding evaluation.")
    parser.add_argument("--validation-path", required=True, help="Path to validation pairs JSONL.")
    parser.add_argument("--base-model", required=True, help="Base model name or path.")
    parser.add_argument("--tuned-model", required=True, help="Fine-tuned model path.")
    parser.add_argument("--top-k", type=int, default=5, help="Recall@k threshold (default: 5).")
    parser.add_argument(
        "--output",
        type=str,
        help="Optional path to write the evaluation report JSON.",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for the evaluation runner.

    Parses arguments, runs evaluation, prints the report, and optionally writes
    it to disk.
    """
    args = parse_args()
    request = EvaluationRequest(
        validation_path=Path(args.validation_path),
        base_model_path=args.base_model,
        tuned_model_path=args.tuned_model,
        top_k=args.top_k,
    )
    logger = get_logger(__name__)
    report = run_evaluation(request, logger=logger)
    print(json.dumps(asdict(report), indent=2))
    if args.output:
        write_report(report, Path(args.output))
        logger.info("embedding_evaluation_report_written", output=args.output)


if __name__ == "__main__":
    main()
