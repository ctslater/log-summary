#!/usr/bin/env python

from __future__ import print_function

import sys
import os
import json
from collections import defaultdict
from textdistance import levenshtein

import jinja2

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))

def find_matching_messages(new_message, message_list):

    similarity_cut = 5

    # Lots of errors report specific numbers, which are not important
    # in finding matching messages.
    substitutions = {ord("%d" % x): "" for x in range(0, 10)}
    new_msg_filtered = new_message.translate(substitutions)

    for test_message in message_list:
        test_msg_filtered = test_message.translate(substitutions)
        if(levenshtein.distance(new_msg_filtered, test_msg_filtered) < similarity_cut):
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
        messages = defaultdict(list)
        for log in logs:
            message = log["jsonPayload"]["message"]
            label = log["jsonPayload"]["MDC"]["LABEL"]
            msg_key = find_matching_messages(message, messages.keys())
            if(msg_key is None):
                msg_key = message

            messages[msg_key].append(label)

        output = {"run_name": run_name,
                  "messages": messages}

        output_by_run.append(output)

    return output_by_run


def format_html(summary):

    template = jinja_env.get_template("day.html")
    return template.render(summary=summary)

if __name__ == '__main__':

    if(len(sys.argv) != 2):
        print("Must supply json filename")
        exit(0)

    with open(sys.argv[1]) as f:
        logs = json.load(f)

    summary = parse_logs_into_summary(logs)

    output_filename = "test_out.html"
    with open(output_filename, "w") as f:
        f.write(format_html(summary))






