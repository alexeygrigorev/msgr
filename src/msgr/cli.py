"""msgr command line interface."""

import argparse
import sys

from . import __version__, adb, store

PREVIEW_LEN = 60


def _preview(body, length=PREVIEW_LEN):
    flat = " ".join(body.split())
    if len(flat) > length:
        return flat[: length - 1] + "…"
    return flat


def _print_row(row):
    print(f"{row['android_id']:<6} {store.fmt_ts(row['date_ms']):<17} "
          f"{row['address']:<20} {_preview(row['body'])}")


def _print_list(rows, title):
    print(f"{title} ({len(rows)}):")
    if not rows:
        print("  (none)")
        return
    print(f"{'id':<6} {'received':<17} {'from':<20} preview")
    for row in rows:
        _print_row(row)


def _sync(con, args):
    serial, messages = adb.fetch_inbox(args.serial)
    new = store.upsert(con, serial, messages)
    print(f"synced from {serial}: {len(messages)} on phone, {new} new.")
    return new


def cmd_list(con, args):
    if not getattr(args, "no_sync", False):
        try:
            _sync(con, args)
        except RuntimeError as exc:
            print(f"warning: sync failed ({exc}); showing stored messages.",
                  file=sys.stderr)
    rows = store.list_messages(con, "new")
    _print_list(rows, "unarchived messages")
    if rows:
        print("\nread one with: msgr read <id>")


def cmd_read(con, args):
    row = store.get_message(con, args.id)
    if row is None:
        sys.exit(f"error: no message with id {args.id} (try: msgr list / msgr archived)")
    print(f"From:    {row['address']}")
    print(f"Date:    {store.fmt_ts(row['date_ms'])}")
    print()
    print(row["body"])
    print()
    if args.keep:
        print("(shown with --keep, not archived)")
        return
    store.mark_read(con, row)
    print("(archived — read it again later via: msgr archived, or: "
          f"msgr read {row['android_id']} --keep)")


def cmd_archived(con, args):
    rows = store.list_messages(con, "archived")
    _print_list(rows, "archived messages")
    if rows:
        print("\nreread one with: msgr read <id> --keep  (never re-archives)")


def cmd_sync(con, args):
    _sync(con, args)


def cmd_unarchive(con, args):
    row = store.get_message(con, args.id)
    if row is None:
        sys.exit(f"error: no message with id {args.id}")
    store.set_state(con, row["android_id"], "new")
    print(f"message {row['android_id']} moved back to unarchived.")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="msgr",
        description="Read SMS from a connected Android phone (ADB) as a local "
        "inbox; reading a message archives it.",
    )
    parser.add_argument("--serial", help="adb device serial (default: the only "
                        "connected device; env MSGR_SERIAL)")
    parser.add_argument("--db", help="archive database path "
                        "(default ~/.msgr/messages.db; env MSGR_DB)")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list", help="sync, then list unarchived messages")
    p_list.add_argument("--no-sync", action="store_true",
                        help="list from the local archive only")
    p_list.set_defaults(func=cmd_list)

    p_read = sub.add_parser("read", help="show a message and archive it")
    p_read.add_argument("id", type=int, help="message id from msgr list")
    p_read.add_argument("--keep", action="store_true",
                        help="show without archiving")
    p_read.set_defaults(func=cmd_read)

    sub.add_parser("archived", help="list archived messages").set_defaults(
        func=cmd_archived)
    sub.add_parser("sync", help="pull new messages from the phone only").set_defaults(
        func=cmd_sync)
    p_un = sub.add_parser("unarchive", help="move a message back to unarchived")
    p_un.add_argument("id", type=int)
    p_un.set_defaults(func=cmd_unarchive)

    args = parser.parse_args(argv)
    if args.cmd is None:
        args.func = cmd_list
        args.no_sync = False
    con = store.connect(args.db)
    try:
        args.func(con, args)
    finally:
        con.close()


if __name__ == "__main__":
    main()
