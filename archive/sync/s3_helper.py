#!/usr/local/bin/uv run 
# /// script
# requires-python = ">=3.11"
# dependencies = [ "requests" ]
# ///

# On newer systems that support env -S, the shebang line should be:
##!/usr/bin/env -S uv run --script

##########################################################################
#
#   Tool to interact with the simple HTTP API for AWS S3.
#
#   Requires:
#       Python 3.11+
#       requests
#
#   Designed to plug in to the existing data transport sync process group
#   and replace the SSH based tools.
#
#       s3_helper.py list -p mango_movies -f list
#       s3_helper.py download <key> -o <filename>
#
#   2025-05-30  Todd Valentic
#               Initial implementation
#
##########################################################################

import argparse
from datetime import datetime
import json
from pathlib import Path
import requests
import sys
import xml.etree.ElementTree as ET

VERSION="1.0"

class Pager:

    def __init__(self, url, ns=None, **params):
        self.url = url
        self.ns = ns
        self.params = params
        self.next_token = None
        self.finished = False

    def __iter__(self):
        return self

    def __next__(self):

        if self.finished:
            raise StopIteration

        params = { "list-type": "2", **self.params }

        if self.next_token:
            params["continuation-token"] = self.next_token

        response = requests.get(self.url, params=params)
        root = ET.fromstring(response.content)

        self.finished = root.find("s3:IsTruncated", self.ns).text == 'false'

        if not self.finished:
            self.next_token = root.find("s3:NextContinuationToken", self.ns).text

        return root 

class S3:

    def __init__(self, url):
        self.url = url 
        self.ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    def remove_ns(self, name):
        return name.split("}", 1)[-1]

    def list(self, limit=None, **params):

        records = []
        pager = Pager(self.url, ns=self.ns, **params)
        finished = False

        for page in pager:

            for contents in page.findall('s3:Contents', self.ns):
                record = {self.remove_ns(child.tag): child.text for child in contents}
                record["ETag"] = record["ETag"].replace('"', '') # strip quotes
                if not record["Key"].endswith("/"):
                    records.append(record)
            
                if limit and len(records) >= limit:
                    finished = True
                    break

            if finished: 
                break

        return sorted(records, key=lambda item: item["Key"])

    def download(self, key, output=None):

        response = requests.get(f"{self.url}/{key}")
        response.raise_for_status()

        if output is None:
            output = Path(Path(key).name)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.content)


class Application:
    """Command line application"""

    def __init__(self):
        self.args = self.parse_command_line()
        self.s3 = S3(self.args.url)

    def run(self):
        """Entry point"""
        return self.args.func(self.args) 

    def list_handler(self, args):
        """List bucket contents"""

        params = {
            "limit": args.limit,
            "prefix": args.prefix
        }

        records = self.s3.list(**params)

        if args.format == "json":
            result = json.dumps(records)
        elif args.format == "list":
            lines = []
            for record in records:
                dt = datetime.fromisoformat(record["LastModified"])
                timestamp = int(dt.timestamp())
                line = f"{timestamp} {record['Size']} {record['Key']}"
                lines.append(line)
            result = "\n".join(lines)
        else:
            result = str(results)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result)
        else:
            print(result)

        return 0 

    def download_handler(self, args):
        """Download file"""

        params = {
            "output": args.output
        }

        self.s3.download(args.key, **params)

        return 0
        
    def parse_command_line(self):
        """Parse command line options"""
        
        parser = argparse.ArgumentParser()
        subparser = parser.add_subparsers(dest="cmd")

        parser.add_argument(
            "-V", "--version",
            action="version",
            version=VERSION
        )

        parser.add_argument(
            "-u", "--url",
            help="Host URL",
            default="https://ncsa.osn.xsede.org/airglow"
        )

        parser_list = subparser.add_parser("list", help="List files")
        parser_list.set_defaults(func=self.list_handler)

        parser_list.add_argument(
            "-p", "--prefix",
            help="Only list keys starting with prefix"
        )

        parser_list.add_argument(
            "-n", "--limit", type=int,
            help="Limit output to this number of records"
        )

        parser_list.add_argument(
            "-o", "--output",
            type=Path,
            help="Output filename (default is stdout)"
        )

        parser_list.add_argument(
            "-f", "--format",
            choices=["json", "list"], 
            default="json",
            help="Output format (default is json)"
        )

        parser_download = subparser.add_parser("download", help="Download file")
        parser_download.set_defaults(func=self.download_handler)

        parser_download.add_argument(
            "key",
            help="Key to download"
        )

        parser_download.add_argument(
            "-o", "--output",
            type=Path,
            help="Output filename (default is key name)"
        )

        args = parser.parse_args()

        if args.cmd is None:
            parser.print_help()
            parser.exit()

        return args

if __name__ == "__main__":
    status_code = Application().run()
    sys.exit(status_code)
