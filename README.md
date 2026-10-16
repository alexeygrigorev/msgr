# msgr

Read the text messages of a connected Android phone from your computer's
command line. Messages are pulled over ADB into a local archive; reading one
archives it, and archived messages stay readable forever.

No cloud, no companion app — the phone is only touched while it is plugged in.

## Requirements

- Python 3.9+
- [`adb`](https://developer.android.com/tools/adb) on your `PATH` (Android
  platform-tools)
- An Android phone with USB debugging enabled, connected via USB
  (the phone must allow the computer; accept the prompt on the phone once)

## Install

```sh
pip install git+https://github.com/<owner>/msgr.git
```

or from a clone:

```sh
pip install .
```

## Usage

```sh
msgr                  # sync + list unarchived messages
msgr read 42          # show message 42, then archive it
msgr archived         # list everything already read
msgr read 42 --keep   # reread an archived message without changing it
msgr unarchive 42     # put a message back on the unread list
msgr sync             # pull new messages only
```

Typical session:

```
$ msgr
synced from ZY32MN9V2K: 9 on phone, 3 new.
unarchived messages (3):
id     received          from                 preview
8      2026-10-16 09:41  Finom                DO NOT SHARE. Your sign-in code is 480178…
9      2026-10-16 09:42  Telegram             Telegram code: 45458…

read one with: msgr read <id>

$ msgr read 9
From:    Telegram
Date:    2026-10-16 09:42

Telegram code: 45458
...

(archived — read it again later via: msgr archived, or: msgr read 9 --keep)
```

## Where things live

- Archive database: `~/.msgr/messages.db` (override: `--db` or `MSGR_DB`)
- adb binary: `adb` on `PATH` (override: `MSGR_ADB`)
- Device selection: the only connected device, or `--serial` / `MSGR_SERIAL`

## How it works

`msgr` queries the phone's SMS inbox with
`adb exec-out content query --uri content://sms/inbox`, so nothing is
installed on the phone. Every pull is deduplicated by the phone's own message
id, and messages stay in the archive even after they are deleted from the
phone.

## Limitations

- Received SMS (inbox) only — no MMS, no sent messages.
- Requires the phone to expose `content://sms` to the shell user (works on
  stock and near-stock Android; some heavily customized ROMs block it).
- Message ids come from the phone; after a factory reset they can repeat.

## Development

```sh
pip install -e .
python -m unittest discover -s tests -v
```

## License

MIT
