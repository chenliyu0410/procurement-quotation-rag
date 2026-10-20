import argparse

from app.db.session import build_session_factory
from app.ingestion.data_taipei import parse_csv
from app.ingestion.http import download
from app.ingestion.normalize import normalize_metro_tender, normalize_work_bureau
from app.ingestion.sync_cases import SourceConfig, sync_cases


SOURCES = {
    "work-bureau": ("臺北市政府工務局採購案件", normalize_work_bureau, False),
    "metro": ("臺北捷運公司採購案件預定招標時程", normalize_metro_tender, False),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Procurement data administration")
    commands = parser.add_subparsers(dest="command", required=True)
    sync = commands.add_parser("sync-cases")
    sync.add_argument("--source", required=True, choices=("work-bureau", "metro"))
    sync.add_argument("--resource-url", required=True)
    sync.add_argument("--period", required=True)
    args = parser.parse_args()
    name, normalizer, snapshot_mode = SOURCES[args.source]
    content, checksum = download(args.resource_url)
    records = parse_csv(content, normalizer, source_period=args.period, source_url=args.resource_url)
    resource_id = args.resource_url.rstrip("/").split("/")[-2] if "/resource/" in args.resource_url else checksum[:12]
    factory = build_session_factory()
    with factory() as session:
        summary = sync_cases(SourceConfig(args.source, name, args.resource_url, snapshot_mode, resource_id,
            args.period, records, checksum), session)
    print(f"同步完成: seen={summary.seen}, changed={summary.changed}, deactivated={summary.deactivated}")


if __name__ == "__main__":
    main()
