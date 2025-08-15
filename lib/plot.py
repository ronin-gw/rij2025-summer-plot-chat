from collections import Counter
from bisect import bisect_left

import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.image as mpimg
from matplotlib.ticker import MultipleLocator, PercentFormatter
from matplotlib.font_manager import FontProperties

from adjustText import adjust_text

from emoji import EMOJI_DATA

from . import (
    TIMEZONE,
    EVENT_NAME,
    RTA_EMOTES,
    VOCABULARY,
    GAMES,
    AVR_WINDOW,
    PER_SECONDS,
    FIND_WINDOW,
    DOMINATION_RATE,
    COUNT_THRESHOLD,
    DPI,
    ROW,
    PAGES,
    YMAX,
    WIDTH,
    HEIGHT,
    FONT_COLOR,
    FRAME_COLOR,
    BACKGROUND_COLOR,
    FACE_COLOR,
    ARROW_COLOR,
    MESSAGE_FILL_COLOR,
    MESSAGE_EDGE_COLOR,
    ALPHA,
    BACKGROUND
)


matplotlib.use("module://mplcairo.macosx")

matplotlib.rcParams["font.sans-serif"] = [
    "Hiragino Maru Gothic Pro", "Yu Gothic", "Meirio", "Takao",
    "IPAexGothic", "IPAPGothic", "VL PGothic", "Noto Sans CJK JP"
]
emoji_prop = FontProperties(fname="/System/Library/Fonts/Apple Color Emoji.ttc")

UNICODE_EMOJI = EMOJI_DATA.keys()

plt.rcParams['axes.facecolor'] = FACE_COLOR
plt.rcParams['savefig.facecolor'] = FACE_COLOR


def plot(timeline, normarize, pages):
    scales = False
    if normarize:
        x, totals, _ = tuple(zip(*timeline))

        breaks = [game.startat for game in GAMES]
        breaks = [bisect_left(x, b) for b in breaks]
        breaks = [0] + breaks + [len(x)]

        scales = np.array([])
        totals = moving_average(totals) * PER_SECONDS
        for begin, end in zip(breaks, breaks[1:]):
            max_msgs = max(totals[begin:end])
            scales = np.concatenate((scales, np.ones(end - begin) / max_msgs))

    for npage in range(1, 1 + PAGES):
        if npage not in pages:
            continue

        chunklen = int(len(timeline) / PAGES / ROW)

        fig = plt.figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        plt.rcParams["savefig.facecolor"] = BACKGROUND_COLOR
        ax = fig.add_axes((0, 0, 1, 1))
        background_image = mpimg.imread(BACKGROUND)
        ax.imshow(background_image)

        plt.subplots_adjust(left=0.07, bottom=0.05, top=0.92)

        for i in range(1, 1 + ROW):
            nrow = i + ROW * (npage - 1)
            f, t = chunklen * (nrow - 1), chunklen * nrow
            x, c, y = zip(*timeline[f:t])
            # _x = tuple(t.replace(tzinfo=None) for t in x)

            ax = fig.add_subplot(ROW, 1, i)
            scale = False if scales is False else scales[f:t]

            _plot_row(ax, x, y, c, i == 1, i == ROW, scale)

        fig.suptitle(f"{EVENT_NAME} チャット頻出スタンプ・単語 ({npage}/{PAGES})",
                     color=FONT_COLOR, size="x-large")

        desc = "" if scales is False else ", ゲームタイトルごとの最大値=100%"
        ytitle = f"単語 / 分 （同一メッセージ内の重複は除外{desc}）"
        fig.text(0.03, 0.5, ytitle,
                 ha="center", va="center", rotation="vertical", color=FONT_COLOR, size="large")
        fig.savefig(f"{npage}.png", dpi=DPI, transparent=True)
        plt.close()
        print(npage)


def moving_average(x, w=AVR_WINDOW):
    _x = np.convolve(x, np.ones(w), "same") / w
    return _x[:len(x)]


def _plot_row(ax, x, y, total_raw, add_upper_legend, add_lower_legend, scales):
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M", tz=TIMEZONE))
    ax.xaxis.set_major_locator(mdates.HourLocator())
    ax.xaxis.set_minor_locator(mdates.MinuteLocator(range(0, 60, 5)))

    if scales is not False:
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1))
        ax.yaxis.set_major_locator(MultipleLocator(0.5))
        ax.yaxis.set_minor_locator(MultipleLocator(0.1))
    else:
        ax.yaxis.set_minor_locator(MultipleLocator(50))

    ax.set_facecolor(FACE_COLOR)

    for axis in ("top", "bottom", "left", "right"):
        ax.spines[axis].set_color(FRAME_COLOR)

    ax.tick_params(colors=FONT_COLOR, which="both")
    ax.set_xlim(x[0], x[-1])
    if scales is not False:
        ax.set_ylim(0, 1)
    else:
        ax.set_ylim(0, YMAX)
    # ax.set_ylim(25, 800)
    # ax.set_yscale('log')

    ax.fill_between(x, 0, YMAX, color=BACKGROUND_COLOR, alpha=ALPHA)

    total = moving_average(total_raw) * PER_SECONDS
    if scales is not False:
        total *= scales
    total = ax.fill_between(x, 0, total, color=MESSAGE_FILL_COLOR,
                            edgecolor=MESSAGE_EDGE_COLOR, linewidth=0.5)

    text_spacing = (x[-1] - x[0]) / 250
    for i, game in enumerate(GAMES):
        annoat = YMAX if scales is False else 1
        if x[0] <= game.startat <= x[-1]:
            ax.axvline(x=game.startat, color=ARROW_COLOR, linestyle=":")
            # ax.annotate(game.name, xy=(game.startat, annoat), xytext=(game.startat, annoat * 0.85), verticalalignment="top",
            #             color=FONT_COLOR, arrowprops=dict(facecolor=ARROW_COLOR, shrink=0.05), ha=game.align)
            ax.text(game.startat, annoat * 0.98, '⭐', verticalalignment="top", horizontalalignment="center",
                    color=FONT_COLOR, fontproperties=emoji_prop)
            ax.text(game.startat + text_spacing * (1 if game.align == "left" else -1),
                    annoat * 0.9, game.name, verticalalignment="top", ha=game.align, color=FONT_COLOR)

    # ys = []
    # labels = []
    # colors = []
    for words, style, color in RTA_EMOTES:
        if isinstance(words, str):
            words = (words, )
        _y = np.fromiter((sum(c[w] for w in words) for c in y), int)
        if not sum(_y):
            continue
        _y = moving_average(_y) * PER_SECONDS
        if scales is not False:
            _y *= scales
        # ys.append(_y)
        # labels.append("\n".join(words))
        # colors.append(color if color else None)
        ax.plot(x, _y, label="\n".join(words), linestyle=style, color=(color if color else None))
    # ax.stackplot(x, ys, labels=labels, colors=colors)

    #
    avr_10min = moving_average(total_raw, FIND_WINDOW) * FIND_WINDOW
    words = Counter()
    for counter in y:
        words.update(counter)
    words = set(k for k, v in words.items() if v >= COUNT_THRESHOLD)
    words -= VOCABULARY

    annotations = []
    for word in words:
        at = []
        _ys = moving_average(np.fromiter((c[word] for c in y), int), FIND_WINDOW) * FIND_WINDOW
        for i, (_y, total_y) in enumerate(zip(_ys, avr_10min)):
            if _y >= total_y * DOMINATION_RATE and _y >= COUNT_THRESHOLD:
                ypoint = _y * PER_SECONDS / FIND_WINDOW * DOMINATION_RATE
                if scales is not False:
                    ypoint *= scales[i]
                at.append((i, ypoint))
        if at:
            at.sort(key=lambda x: x[1])
            at = at[-1]

            if any(c in UNICODE_EMOJI for c in word):
                text = ax.text(x[at[0]], at[1], word, color=FONT_COLOR, fontsize="xx-small", fontproperties=emoji_prop)
            else:
                text = ax.text(x[at[0]], at[1], word, color=FONT_COLOR, fontsize="xx-small")
            annotations.append(text)
    if annotations:
        adjust_text(annotations, only_move={"text": 'x'})

    if add_upper_legend:
        leg = ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left")
        _set_legend(leg)
        frame = leg.get_frame()
        frame.set_facecolor(MESSAGE_FILL_COLOR)
        frame.set_alpha(1)

    if add_lower_legend:
        leg = plt.legend([total], ["メッセージ / 分"], loc=(1.015, 0.4), framealpha=ALPHA)
        _set_legend(leg)
        msg = "図中の単語は{}秒間で{}%の\nメッセージに含まれていた単語\n({:.1f}メッセージ / 秒 以上のもの)".format(
            FIND_WINDOW, int(DOMINATION_RATE * 100), COUNT_THRESHOLD / FIND_WINDOW
        )
        plt.gcf().text(0.915, 0.06, msg, fontsize="x-small", color=FONT_COLOR)


def _set_legend(leg):
    frame = leg.get_frame()
    frame.set_facecolor(FACE_COLOR)
    frame.set_edgecolor(FRAME_COLOR)
    frame.set_alpha(ALPHA)

    for text in leg.get_texts():
        text.set_color(FONT_COLOR)
