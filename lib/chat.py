import json
import gzip
import sys
from collections import Counter
from itertools import chain
from multiprocessing import Pool

from . import EXCLUDE_MESSAGE_TERMS, WINDOW
from .message import ChatDownloaderMessage, TwitchVODMessage


def _make_td_message(raw_message):
    if "name" in raw_message["author"] and raw_message["author"]["name"] == "fossabot":
        return

    for term in EXCLUDE_MESSAGE_TERMS:
        if term in raw_message["message"]:
            return
    return ChatDownloaderMessage(raw_message)


def _make_tv_message(raw_message):
    if raw_message["commenter"]["name"] == "fossabot":
        return

    for term in EXCLUDE_MESSAGE_TERMS:
        if term in raw_message["message"]["body"]:
            return
    return TwitchVODMessage(raw_message)


def parse_chat(paths):
    messages = []
    loaded_ids = set()

    for p in paths:
        if p.endswith(".gz"):
            opener = gzip.open
        else:
            opener = open

        with opener(p) as f, Pool() as pool:
            if f.read(1) == b"[":
                jsontype = "ChatDownloader"
            else:
                jsontype = "TwitchVOD"
            f.seek(0)

            print(jsontype, p, file=sys.stderr)

            j = json.load(f)
            if jsontype == "ChatDownloader":
                poolres = pool.imap_unordered(_make_td_message, j, len(j) // pool._processes)
                msgs = [msg for msg in poolres
                        if msg is not None and msg.id not in loaded_ids]
            else:
                raw_messages = j["comments"]
                poolres = pool.imap_unordered(_make_tv_message, raw_messages, len(raw_messages) // pool._processes)
                msgs = [msg for msg in poolres
                        if msg is not None and msg.id not in loaded_ids]

            messages.extend(msgs)
            loaded_ids.update(msg.id for msg in msgs)

    messages.sort(key=lambda m: m.datetime)

    timeline = []
    currentwindow = messages[0].datetime.replace(microsecond=0) + WINDOW
    _messages = []
    for m in messages:
        if m.datetime <= currentwindow:
            _messages.append(m)
        else:
            timeline.append((currentwindow, *_make_timepoint(_messages)))
            while True:
                currentwindow += WINDOW
                if m.datetime <= currentwindow:
                    _messages = [m]
                    break
                else:
                    timeline.append((currentwindow, 0, Counter()))

    if _messages:
        timeline.append((currentwindow, *_make_timepoint(_messages)))

    return timeline


def _make_timepoint(messages):
    total = len(messages)
    counts = Counter(_ for _ in chain(*(m.words for m in messages)))

    return total, counts
