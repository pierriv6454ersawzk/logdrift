"""Command-line entry point for logdrift."""

from __future__ import annotations

import argparse
import sys

from logdrift.anomaly_detector import AnomalyDetector
from logdrift.formatter import FormatOptions, LogFormatter
from logdrift.log_source import FileLogSource
from logdrift.output_sink import FileSink, MultiSink, StreamSink
from logdrift.pipeline import Pipeline


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logdrift",
        description="Tail a log file and highlight anomalies in real-time.",
    )
    parser.add_argument("file", help="Path to the log file to tail.")
    parser.add_argument(
        "--window",
        type=float,
        default=10.0,
        metavar="SECONDS",
        help="Sliding window size for rate calculation (default: 10s).",
    )
    parser.add_argument(
        "--baseline",
        type=int,
        default=60,
        metavar="SAMPLES",
        help="Number of samples required before anomaly detection activates (default: 60).",
    )
    parser.add_argument(
        "--spike-threshold",
        type=float,
        default=2.0,
        metavar="MULTIPLIER",
        help="Score multiplier above which a spike label is shown (default: 2.0).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color codes in output.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Also write output to this file (in addition to stdout).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    source = FileLogSource(args.file)
    detector = AnomalyDetector(
        window_seconds=args.window,
        min_baseline_samples=args.baseline,
    )
    fmt_options = FormatOptions(
        use_color=not args.no_color,
        spike_threshold=args.spike_threshold,
    )
    formatter = LogFormatter(fmt_options)

    stdout_sink: StreamSink = StreamSink(sys.stdout)
    if args.output:
        sink = MultiSink(stdout_sink, FileSink(args.output))
    else:
        sink = MultiSink(stdout_sink)  # type: ignore[assignment]

    pipeline = Pipeline(source=source, detector=detector, formatter=formatter, sink=sink)

    try:
        pipeline.run()
    except KeyboardInterrupt:
        pipeline.stop()
    finally:
        sink.close()

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
