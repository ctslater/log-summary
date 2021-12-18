#!/usr/bin/env python

import argparse
import datetime
import json
import os
import sys
from collections import defaultdict

import google.api_core.exceptions
import jinja2
from google.cloud import storage
from textdistance import levenshtein

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))


def find_matching_messages(new_message, message_list):

    similarity_cut = 5

    # Lots of errors report specific numbers, which are not important
    # in finding matching messages.
    substitutions = {ord("%d" % x): "" for x in range(0, 10)}
    new_msg_filtered = new_message.translate(substitutions)

    for test_message in message_list:
        test_msg_filtered = test_message.translate(substitutions)
        if levenshtein.distance(new_msg_filtered, test_msg_filtered) < similarity_cut:
            return test_message

    return None


def parse_logs_into_summary(logs):

    runs = defaultdict(list)
    for log in logs:
        try:
            run = log["jsonPayload"]["MDC"]["RUN"]
        except KeyError:
            continue
        runs[run].append(log)

    output_by_run = []
    for run_name, logs in runs.items():
        messages = defaultdict(set)
        for log in logs:
            message = log["jsonPayload"]["message"]
            label = log["jsonPayload"]["MDC"]["LABEL"]
            msg_key = find_matching_messages(message, messages.keys())
            if msg_key is None:
                msg_key = message

            messages[msg_key].add(label)

        output = {"run_name": run_name, "messages": messages}

        output_by_run.append(output)

    return output_by_run


def download_logs(bucket, prefix, year, month, day):

    search_fmt_string = "{base:s}/{year:d}/{month:02d}/{day:02d}/"

    search_prefix = search_fmt_string.format(
        base=prefix, year=year, month=month, day=day
    )

    storage_client = storage.Client.create_anonymous_client()

    bucket = storage_client.bucket(args.bucket)

    files_to_download = bucket.list_blobs(prefix=search_prefix)

    logs = []

    for bucket_file in files_to_download:
        json_string = bucket_file.download_as_string()

        for line in json_string.decode().split("\n"):
            if len(line) == 0:
                continue
            json_value = json.loads(line)
            logs.append(json_value)

    return logs


def format_html(summary):

    template = jinja_env.get_template("day.html")
    return template.render(summary=summary)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--today",
        action="store_true",
        help="Download and summarize logs for today (UTC)",
    )
    parser.add_argument(
        "--yesterday",
        action="store_true",
        help="Download and summarize logs for yesterday (UTC)",
    )
    parser.add_argument(
        "--filenames", nargs="+", help="Summarize logs from json files."
    )
    parser.add_argument("--bucket", nargs="?", help="Google Cloud Storage bucket name.")
    parser.add_argument("--prefix", nargs="?", help="Directory prefix inside bucket.")
    parser.add_argument(
        "--output-dir", nargs="?", help="Destination directory for html files."
    )

    args = parser.parse_args()

    supplied_args = (
        1 * (args.today) + 1 * (args.yesterday) + 1 * (args.filenames is not None)
    )
    if supplied_args != 1:
        print("Must specify one of --today, --yesterday, or --filenames")
        sys.exit(1)

    if (args.today or args.yesterday) and (args.bucket is None or args.prefix is None):
        print("Must supply --bucket and --prefix when downloading logs")
        sys.exit(1)

    search_time = datetime.datetime.now(tz=datetime.timezone.utc)

    if args.today or args.yesterday:

        if args.yesterday:
            search_time -= datetime.timedelta(days=1)

        logs = download_logs(
            args.bucket,
            args.prefix,
            search_time.year,
            search_time.month,
            search_time.day,
        )

    else:
        logs = []
        for filename in args.filenames:
            with open() as f:
                logs.extend(json.load(f))

    summary = parse_logs_into_summary(logs)

    output_filename = "errors_{:04d}_{:02d}_{:02d}.html".format(
        search_time.year, search_time.month, search_time.day
    )
    if args.output_dir:
        output_filename = os.path.join(args.output_dir, output_filename)

    with open(output_filename, "w") as f:
        f.write(format_html(summary))
