#!/usr/bin/env python

import sys
import os
from google.cloud import storage
from itertools import chain
import datetime
import google.api_core.exceptions
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Sync error logs from google")
    parser.add_argument("bucket", type=str)
    parser.add_argument("--prefix", type=str, nargs="?",
                        help="Directory prefix inside the bucket")
    parser.add_argument("-v", dest="verbose", action="store_true", help="verbose")

    args = parser.parse_args()

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    search_fmt_string =  "{base:s}/{year:d}/{month:02d}/{day:02d}/"


    search_prefix = search_fmt_string.format(base=args.prefix,
                                             year=now.year,
                                             month=now.month,
                                             day=now.day)

    yesterday = now - datetime.timedelta(days=1)
    search_prefix_yesterday = search_fmt_string.format(base=args.prefix,
                                                       year=yesterday.year,
                                                       month=yesterday.month,
                                                       day=yesterday.day)

    storage_client = storage.Client.create_anonymous_client()

    bucket = storage_client.bucket(args.bucket)

    files_to_download = chain(bucket.list_blobs(prefix=search_prefix),
                              bucket.list_blobs(prefix=search_prefix_yesterday))

    for bucket_file in files_to_download:
        etag_filename = "{:s}/.etag_{:s}".format(os.path.dirname(bucket_file.name),
                                                 os.path.basename(bucket_file.name))
        if(args.verbose):
            print(bucket_file.name)

        os.makedirs(os.path.dirname(bucket_file.name), exist_ok=True)
        try:
            with open(etag_filename, "r") as f:
                etag_on_disk = f.readline()
        except FileNotFoundError:
            etag_on_disk = None

        try:
            bucket_file.download_to_filename(bucket_file.name, if_etag_not_match=etag_on_disk)
        except google.api_core.exceptions.NotModified:
            if(args.verbose):
                print("already up-to-date, not downloading.")

        with open(etag_filename, "w") as f:
            f.write(bucket_file.etag)




