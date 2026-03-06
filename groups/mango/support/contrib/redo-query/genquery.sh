#!/usr/bin/sh

URL=${MANGO_DATABASE_URI:="postgresql://transport@localhost:15432/mango"}

echo $URL

QUERYFILE=query.sql
OPTS="$URL -f $QUERYFILE"

STARTDATE=2026-01-30
ENDDATE=now
DATES="-v startdate=$STARTDATE -v enddate=$ENDDATE"

PSQL="psql $OPTS $DATES"

imagers=(
    "cfs greenline"
)

for stationinstrument in "${imagers[@]}"; do
    set -- $stationinstrument
    echo $1 $2
    $PSQL -v station=$1 -v instrument=$2 > $1-$2.list
done


