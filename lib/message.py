import re
from datetime import datetime, timezone
from copy import copy

from sudachipy import tokenizer, dictionary
import jaconv

from . import STOP_WORDS, PNS, PN_PATTERNS


class Message:
    _tokenizer = dictionary.Dictionary().create()
    _mode = tokenizer.Tokenizer.SplitMode.C

    pns = PNS
    pn_patterns = PN_PATTERNS
    stop_words = STOP_WORDS

    @classmethod
    def _tokenize(cls, text):
        return cls._tokenizer.tokenize(text, cls._mode)

    def _init_items(self, raw):
        raise NotImplementedError
        self.id
        self.datetime
        self.message
        self.emotes

    def __init__(self, raw):
        self._init_items(raw)

        self.msg = set()

        message = self.message
        for emote in self.emotes:
            message = message.replace(emote, "")
        for stop in self.stop_words:
            message = message.replace(stop, "")
        message = re.sub(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", "", message)

        #
        for pattern, replace in self.pn_patterns:
            match = pattern.findall(message)
            if match:
                self.msg.add(replace)
                if pattern.pattern.startswith('^') and pattern.pattern.endswith('$'):
                    message = ''
                else:
                    for m in match:
                        message = message.replace(m, "")

        #
        for pn in self.pns:
            if pn in message:
                self.msg.add(pn)
                message = message.replace(pn, "")

        #
        message = jaconv.h2z(message)

        # (名詞 or 動詞) (+助動詞)を取り出す
        parts = []
        currentpart = None
        for m in self._tokenize(message):
            part = m.part_of_speech()[0]

            if currentpart:
                if part == "助動詞":
                    parts.append(m.surface())
                else:
                    self.msg.add(''.join(parts))
                    parts = []
                    if part in ("名詞", "動詞"):
                        currentpart = part
                        parts.append(m.surface())
                    else:
                        currentpart = None
            else:
                if part in ("名詞", "動詞"):
                    currentpart = part
                    parts.append(m.surface())

        if parts:
            self.msg.add(''.join(parts))

        #
        kusa = False
        for word in copy(self.msg):
            if set(word) & set(('w', 'ｗ')):
                kusa = True
                self.msg.remove(word)
        if kusa:
            self.msg.add("ｗｗｗ")

        message = message.strip()
        if not self.msg and message:
            self.msg.add(message)

        if 'rtaClap r' in self.msg:
            raise KeyError

    def __len__(self):
        return len(self.msg)

    @property
    def words(self):
        return self.msg | self.emotes


class ChatDownloaderMessage(Message):
    def _init_items(self, raw):
        self.id = raw["message_id"]
        # self.name = raw["author"]["name"]
        self.message = raw["message"]

        if "emotes" in raw:
            self.emotes = set(e["name"] for e in raw["emotes"]
                              if e["name"] not in self.stop_words)
        else:
            self.emotes = set()

        self.datetime = datetime.fromtimestamp(int(raw["timestamp"]) // 1000000).replace(tzinfo=timezone.utc)
        # self.datetime = datetime.fromtimestamp(int(raw["timestamp"]) // 1000000)


class TwitchVODMessage(Message):
    def _init_items(self, raw):
        self.id = raw["_id"]
        # self.name = raw["commenter"]["name"]
        self.message = raw["message"]["body"]

        self.emotes = set()
        if raw["message"]["emoticons"]:
            for emote in raw["message"]["emoticons"]:
                self.emotes.add(self.message[(emote["begin"]):(emote["end"])].strip())

        self.datetime = datetime.fromisoformat(raw["created_at"]).astimezone(timezone.utc)
        # self.datetime = self.datetime.astimezone(timezone.utc).replace(tzinfo=None)
