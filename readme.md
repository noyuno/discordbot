# discordbot

## How to use API

~~~bash
curl -XPOST -d '{"message":"hello, discordbot"}' http://discordbot/ >/dev/null
~~~

helper function
~~~bash
message () {
    echo "$1"
    curl -XPOST -sd '{"message": "'"$CONTAINER_NAME"': '"$1"'"}' http://discordbot >/dev/null
    if [ $? -ne 0 ]; then
        echo "$CONTAINER_NAME: failed to send message to discordbot"
    fi
}

message "operation finished"
~~~

## Environment variables example

put below variables to `.env`

~~~
DISCORD_TOKEN=
DISCORD_CHANNEL_NAME=general
GOOGLE_MAPS_API_KEY=
DARK_SKY_API_KEY=
LOCATION=Tokyo
XRAIN_LON=
XRAIN_LAT=
XRAIN_ZOOM=8
~~~

## Commands

### weather|天気

show weather forecast and XRAIN map

![weather](https://raw.githubusercontent.com/noyuno/discordbot/master/weather.png)

### ps

show status of docker containers

### help

show available commands

### hi

just return 'hi'

