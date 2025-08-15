#!/usr/bin/env python3
import os.path
import pickle
import argparse
from collections import Counter
from operator import itemgetter

from lib import PAGES
from lib.chat import parse_chat
from lib.plot import plot

TIMELINE = os.path.join(os.path.dirname(__file__), "timeline.pickle")


def _load_timeline(paths):
    if os.path.exists(TIMELINE):
        with open(TIMELINE, "rb") as f:
            timeline = pickle.load(f)
    else:
        timeline = parse_chat(paths)
        with open(TIMELINE, "wb") as f:
            pickle.dump(timeline, f)

    return timeline


def _save_counts(timeline):
    _, _, counters = zip(*timeline)

    counter = Counter()
    for c in counters:
        counter.update(c)

    with open("words.tab", 'w') as f:
        for w, c in sorted(counter.items(), key=itemgetter(1), reverse=True):
            print(w, c, sep='\t', file=f)


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json", nargs="+")
    parser.add_argument("-n", "--normarize", action="store_true")
    parser.add_argument("-p", "--pages", type=int, nargs='*', default=range(1, 1 + PAGES))
    args = parser.parse_args()

    timeline = _load_timeline(args.json)
    _save_counts(timeline)

    plot(timeline, args.normarize, args.pages)


if __name__ == "__main__":
    _main()
