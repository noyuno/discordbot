from python:3-alpine

copy . $DEPLOY
run apk update && \
    apk add --virtual=deps git && \
    pip install git+https://github.com/Rapptz/discord.py.git@rewrite
cmd python3 discordbot.py

