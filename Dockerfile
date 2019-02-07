from python:3-alpine

copy . $DEPLOY
run apk update && \
    apk add --virtual=deps git && \
    pip install git+https://github.com/Rapptz/discord.py.git@rewrite schedule selenium
cmd python3 -u discordbot.py

