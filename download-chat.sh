#!/bin/bash

OUTDIR=chat

mkdir -p $OUTDIR

for i in 2535211874 2536749176 2538262613 2539971906 2540611863; do
    json=$OUTDIR/${i}.json
    if [ ! -f "$json.gz" ]; then
        chat_downloader -o $json https://www.twitch.tv/videos/${i} > /dev/null &
    fi
done
wait
pigz -p 4 $OUTDIR/*.json
