# -*- coding: utf-8 -*-

"""Console script for M3u8Downloader."""
from m3u8_dl import M3u8Downloader
from m3u8_dl.faker import Faker
import json
import signal
import sys
import os
import argparse
from m3u8_dl import M3u8Context
import pickle
from m3u8_dl import PickleContextRestore



def execute(restore, context):
    """
    download ts file by restore object (dict)
    """
    m = M3u8Downloader(context, on_progress_callback=M3u8Downloader._show_progress_bar)

    def signal_handler(sig, frame):
        print('\nCaptured Ctrl + C ! Saving Current Session ...')
        restore.dump(context)
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)

    m.get_m3u8file()
    print('m3u8: Saving as ' + M3u8Downloader.m3u8_filename)

    m.parse_m3u8file()
    m.get_tsfiles()
    if m.is_task_success:
        m.merge()

    # clean everything Downloader generates
    m.cleanup()
    # clean restore
    restore.cleanup()

    if not m.is_task_success:
        print('Download Failed')
        print('Try it again with options --refer and --url')


def main():
    """
    deal with the console
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", default='',
                        help="[0]base url for ts when downloading")
    parser.add_argument("-r", "--referer", default='',
                        help="[0]the Referer in request header")
    parser.add_argument("-t", "--threads", type=int, default=10,
                        help="[0]how many threads to start for download")
    parser.add_argument("--insecure", action="store_true",
                        help="[0]ignore verifying the SSL certificate")
    parser.add_argument("--certfile", default='',
                        help="[0]do not ignore SSL certificate, verify it with a file or directory with CAs")  # noqa
    parser.add_argument("fileurl", nargs="?",
                        help="[0]url [e.g.:http://example.com/xx.m3u8]")
    parser.add_argument("output", nargs="?", help="[0]file for saving [e.g.: example.ts]")  # noqa
    parser.add_argument("--restore", action="store_true",
                        help="[1]restore from last session")
    parser.add_argument("-f", "--fake", help="[2]fake a m3u8 file")
    parser.add_argument("--range", help="[2]ts range")
    parser.add_argument("--ts", help="[2]ts link")

    args = parser.parse_args()

    restore = PickleContextRestore()

    if args.fake:
        range = args.range.split(',')
        faker = Faker()
        faker.create_file(args.fake, args.ts, int(range[0]), int(range[1])+1)

    else:
        if args.restore:
            context = restore.load()
        else:
            if not args.fileurl or not args.output:
                print('error: [fileurl] and [output] are necessary if not in restore\n')  # noqa
                parser.print_help()
                sys.exit(0)

            context = M3u8Context(file_url=args.fileurl, referer=args.referer,
                                  threads=args.threads, output_file=args.output,
                                  get_m3u8file_complete=False, downloaded_ts_urls=[])
            context["base_url"] = args.url \
                if args.url .endswith('/') else args.url + '/'  # noqa
            if args.insecure:
                context['sslverify'] = False
            if not args.insecure:
                if args.certfile == '':
                    context['sslverify'] = True
                else:
                    context['sslverify'] = args.certfile
        execute(restore, context)


if __name__ == "__main__":
    main()
