# -*- coding: utf-8 -*-

"""Console script for M3u8Downloader."""
from m3u8_dl import M3u8Downloader
import json
import signal
import sys
import os
import argparse


restore_file = 'm3u8_dl.restore'


def _show_progress_bar(downloaded, total):
    """
    progress bar for command line
    """
    htlen = 33
    percent = downloaded / total * 100
    # 20 hashtag(#)
    hashtags = int(percent / 100 * htlen)
    print('|'
          + '#' * hashtags + ' ' * (htlen - hashtags) +
          '|' +
          '  {0}/{1} '.format(downloaded, total) +
          ' {:.1f}'.format(percent).ljust(5) + ' %', end='\r', flush=True)  # noqa


def restore_from_file():
    """
    restore init from the previous backup file
    """
    restore_obj = {}
    with open(restore_file, 'r') as f:
        restore_obj = json.load(f)
    return restore_obj


def restore_init(uri, referer, threads, fileuri, output):
    """
    restore default init
    """
    restore_obj = {}
    user_options = {}
    user_options['file_uri'] = fileuri
    user_options['base_uri'] = uri
    user_options['referer'] = referer
    user_options['threads'] = threads
    user_options['output_file'] = output

    restore_obj.setdefault('processes',
                           {'get_m3u8file': {'finished': False}})

    restore_obj.setdefault('user_options', user_options)
    restore_obj.setdefault('downloaded_ts', [])
    return restore_obj


def execute(restore_obj):
    """
    download ts file by restore object (dict)
    """
    m = M3u8Downloader(restore_obj, on_progress_callback=_show_progress_bar)

    def signal_handler(sig, frame):
        print('\nCaptured Ctrl + C ! Saving Current Session ...')
        with open(restore_file, 'w') as out:
            json.dump(restore_obj, out)
        sys.exit(0)

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
    if os.path.isfile(restore_file):
        os.unlink(restore_file)

    if not m.is_task_success:
        print('Download Failed')
        print('Try it again with options --refer and --uri')


def main():
    """
    deal with the console
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--uri", default='',
                        help="base uri for ts when downloading")
    parser.add_argument("-r", "--referer", default='',
                        help="the Referer in request header")
    parser.add_argument("-t", "--threads", type=int, default=10,
                        help="how many threads to start for download")
    parser.add_argument("fileuri", nargs="?",
                        help="url [e.g.:http://example.com/xx.m3u8]")
    parser.add_argument("output", nargs="?", help="file for saving [e.g.: example.ts]")  # noqa
    parser.add_argument("--restore", action="store_true",
                        help="restore from last session")
    args = parser.parse_args()

    restore_obj = {}

    if args.restore:
        restore_obj = restore_from_file()
    else:
        if not args.fileuri or not args.output:
            print('error: [fileuri] and [output] are necessary if not in restore\n')  # noqa
            parser.print_help()
            sys.exit(0)
        restore_obj = restore_init(args.uri, args.referer,
                                   args.threads, args.fileuri,
                                   args.output)
    execute(restore_obj)


if __name__ == "__main__":
    main()
