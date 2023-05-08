#!/bin/sh

##########################################################################
#
#   Generate uptime summary JSON file 
#
#   Run a SQL query to generate summary data in JSON format. 
#
#   2023-05-05  Todd Valentic
#               Initial implementation
#
##########################################################################

set -o errexit  # abort on nonzero exitstatus
set -o nounset  # abort on unbound variable
set -o pipefail # do not hide errors within pipes

VESION=1.0.0
PROJECT=uptime-json

BASEDIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null 2>&1 && pwd )"
SQLDIR=$(realpath $BASEDIR/../lib/sql)
VARDIR=$(realpath $BASEDIR/../var)

SQLQUERY=$SQLDIR/totaldays_json.sql

#-------------------------------------------------------------------------
# Usage function
#-------------------------------------------------------------------------

function usage()
{
    cat << HEREDOC

    Usage: $progname [options]

    Optional arguments:
      -h, --help            show this help message and exit
      -V, --version         $progname vesion
      -v, --verbose         increase the verbosity (can be applied multiple times)
      -s, --server          SQL database server host (default: localhost) 
      -p, --port            SQL database server port (default: 5432)
      -u, --user            SQL database user (default: transport)
      -d, --database        SQL database (default: mango)
      -o, --output          Output filename (default: stdout) 

HEREDOC
}

#-------------------------------------------------------------------------
# Initialize variables 
#-------------------------------------------------------------------------

progname=$(basename $0)
verbose=0
OUTPUT=
HOST=localhost
PORT=15432
USER=transport
DB=mango

SQLOPTS="-h $HOST -p $PORT -U $USER $DB"

#-------------------------------------------------------------------------
# Parse command line
#-------------------------------------------------------------------------

OPTS=$(getopt \
    -o "hVvs:p:u:d:o:" \
    --long "help,version,verbose,server:,port:,user:,database:,output:" \
    -n "$progname" -- "$@")
if [ $? != 0 ] ; then echo "Error in command line arguments." >&2 ; usage; exit 1 ; fi
eval set -- "$OPTS"

while true; do
    # uncomment the next line to see how shift is working
    #echo "\$1:\"$1\" \$2:\"$2\""
    case "$1" in
      -h | --help )         usage; exit; ;;
      -V | --version )      echo $VERSION; exit ;;
      -v | --verbose )      verbose=$((verbose + 1)); shift; ;;
      -s | --server )       HOST="$2"; shift; shift; ;;
      -p | --port )         PORT="$2"; shift; shift; ;;
      -u | --user )         USER="$2"; shift; shift; ;;
      -d | --database )     DB="$2"; shift; shift; ;;
      -o | --output )       OUTPUT="-o $2"; shift; shift ;;
      -- )                  shift; break ;;
      * )                   break ;;
    esac
done

#if [ $# -eq 0 ]; then
#    usage
#    exit 1
#fi

SQLOPTS="-h $HOST -p $PORT -U $USER $DB"

if (( $verbose > 0 )); then

    cat << EOM
verbose=$verbose
OUTPUT=$OUTPUT
TMPDIR=$TMPDIR
BASEDIR=$BASEDIR
SQLDIR=$SQLDIR
SQLOPTS=$SQLOPTS
SQLQUERY=$SQLQUERY
PLOTTER=$PLOTTER
EOM
fi

#=========================================================================
# Main Application
#=========================================================================

psql $SQLOPTS -f $SQLQUERY -t -A $OUTPUT


