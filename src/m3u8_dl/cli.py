# -*- coding: utf-8 -*-

"""Console script for M3u8Downloader."""
import click
from m3u8_dl import M3u8Downloader


def _show_progress_bar(downloaded, total):
    htlen = 33
    percent = downloaded / total * 100
    # 20 hashtag(#)
    hashtags = int(percent / 100 * htlen)
    print('|'
          + '#' * hashtags + ' ' * (htlen - hashtags) +
          '|' +
          '  {0}/{1} '.format(downloaded, total) +
          ' {:.1f}'.format(percent).ljust(5) + ' %', end='\r', flush=True) # noqa


# TODO:  restore
# ctrl + c => (save session)
# option --restore (restore session)
@click.command()
@click.option('-u', '--uri', default='', help='base uri for ts \
when downloading')
@click.option('-r', '--referer', default='',
              help='the Referer in request header')
@click.option('-t', '--threads', default=10,
              help='how many threads to start for download')
@click.argument('fileuri')
@click.argument('output')
def main(uri, referer, threads, fileuri, output):
    m = M3u8Downloader(fileuri, uri, referer, threads, output,
                       _show_progress_bar)

    click.echo('Downloading m3u8 ...')
    m.get_m3u8file()
    click.echo('Download Complete')
    click.echo('m3u8: Saving as ' + M3u8Downloader.m3u8_filename)

    click.echo('Parse m3u8 ...')
    m.parse_m3u8file()
    click.echo('Parse Complete')

    click.echo('Downloading ts...')
    m.get_tsfiles()

    click.echo('Merging all the ts ...')
    m.merge()
    click.echo('Merging Complete')

    click.echo('Clean up ...')
    m.cleanup()
    # downloader = M3u8Downloader(file, uri, referer, threads)


if __name__ == "__main__":
    main()
