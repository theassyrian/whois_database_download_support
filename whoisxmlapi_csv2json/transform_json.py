#!/usr/bin/env python

from argparse import ArgumentParser
import csv
import multiprocessing
import json
import sys
import os
from platform import system

VERSION = "0.0.2"
MYNAME = sys.argv[0].replace('./', '')

# Preparing arguments
argparser = ArgumentParser(description='Convert CSV to JSON format')
argparser.add_argument('--version',
                       help='Print version information and exit.',
                       action='version',
                       version=MYNAME + ' ver. ' + VERSION + '\n(c) WhoisXML API LLC.')
argparser.add_argument('-i', '--path',
                       help='input directory with uncompressed CSVs or single CSV file',
                       type=str, required=True)
argparser.add_argument('--key', help='primary key field for records, default "domainName"',
                       type=str, default='domainName')
argparser.add_argument('--threads',
                       help='number of threads, default 1',
                       type=int, default=1)
argparser.add_argument('--force', help='overwrite existent files', action='store_true')
argparser.add_argument('--human-readable',
                       help='generate human readable output',
                       action='store_true')
args = argparser.parse_args()

# increase max size of the field
if system() == 'Windows':
    csv.field_size_limit(2147483647)
else:
    from sys import maxsize as csv_maxsize
    csv.field_size_limit(csv_maxsize)


def convert_json(csv_queue):
    while not csv_queue.empty():
        csv_file = csv_queue.get()
        json_file = os.path.join(
            os.path.dirname(csv_file),
            os.path.basename(csv_file).replace('.csv', '.json'))
        if args.force or not os.path.isfile(json_file):
            out_data = dict()
            with open(csv_file, 'rt') as infile:
                infile_csv = csv.DictReader(infile)
                for in_row in infile_csv:
                    out_data.update({in_row[args.key]: {}})
                    for field in infile_csv.fieldnames:
                        if field != args.key and in_row[field] != '':
                            out_data[in_row[args.key]].update({field: in_row[field]})
            with open(json_file, 'wt') as json_file_obj:
                if args.human_readable:
                    json_file_obj.write(json.dumps(out_data, indent=4))
                else:
                    json_file_obj.write(json.dumps(out_data))
            del out_data


if __name__ == '__main__':
    # populating queue
    csvQueue = multiprocessing.Queue()

    if os.path.isdir(args.path):
        for csv_f in os.listdir(args.path):
            if csv_f.endswith('.csv'):
                csvQueue.put(os.path.join(args.path, csv_f))
    elif os.path.isfile(args.path) and args.path.endswith('.csv'):
        csvQueue.put(args.path)
    else:
        exit(1)

    threads = []
    for t in range(0, args.threads):
        convert_thread = multiprocessing.Process(target=convert_json, args=(csvQueue, ))
        convert_thread.start()
        threads.append(convert_thread)
    for convert_thread in threads:
        convert_thread.join()
