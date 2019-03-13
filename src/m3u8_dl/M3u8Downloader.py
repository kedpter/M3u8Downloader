# -*- coding: utf-8 -*-

import m3u8
import click
import requests
from urllib.parse import urlparse, urljoin
import os
import shutil
from threading import Thread, Lock


class DownloadFileNotValidException(Exception):
    pass


class M3u8DownloaderNoStreamException(Exception):
    pass


def download_file(fileuri, headers, filename, check=None):
    with requests.get(fileuri, headers=headers, stream=True) as r:
        if check and not check(r):
            print('Not a valid ts file')
            print(r.content)
            raise DownloadFileNotValidException()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


class HttpFile(object):

    def get_file(self):
        raise NotImplementedError()


class M3u8File(HttpFile):

    def __init__(self, fileuri, headers, output_file):
        self.fileuri = fileuri
        self.headers = headers
        self.output_file = output_file

    def get_file(self):
        download_file(self.fileuri, self.headers, self.output_file)
        self._parse_file()

    def _parse_file(self):
        self.m3u8_obj = m3u8.load(self.output_file)
        return self.m3u8_obj

    def get_tssegments(self):
        return self.m3u8_obj.data['segments']

    @staticmethod
    def get_path_by_uri(uri, folder):
        return os.path.join(folder,
                            urlparse(uri).path.split('/')[-1])


class TsFile(HttpFile):
    def __init__(self, fileuri, headers, output_file, index):
        self.fileuri = fileuri
        self.headers = headers
        self.output_file = output_file
        self.index = index

    @staticmethod
    def check_valid(request):
        if request.headers['Content-Type'] == 'text/html':
            return False
        # print(request.headers['Content-Type'])
        # print(request.content)
        return True

    def get_file(self):
        download_file(self.fileuri, self.headers, self.output_file,
                      self.check_valid)


class M3u8Downloader:
    m3u8_filename = 'output.m3u8'
    ts_tmpfolder = '.tmpts'

    def __init__(self, fileuri, base_uri, referer, threads, output,
                 on_progress_callback=None):
        self.file = fileuri
        self.base_uri = base_uri if base_uri.endswith('/') else base_uri + '/'
        self.referer = referer
        self.threads = threads
        self.output_file = output

        self.fileuri = fileuri
        self.headers = {'Referer': referer}
        self.tsfiles = []

        self.on_progress = on_progress_callback

        if not os.path.isdir(M3u8Downloader.ts_tmpfolder):
            os.mkdir(M3u8Downloader.ts_tmpfolder)

    def get_m3u8file(self):
        self.m3u8file = M3u8File(self.fileuri, self.headers,
                                 M3u8Downloader.m3u8_filename)

        self.m3u8file.get_file()

    def parse_m3u8file(self):
        self.tssegments = self.m3u8file.get_tssegments()
        self.__all_tsseg_len = len(self.tssegments)
        if len(self.tssegments) == 0:
            click.echo(self.m3u8file.m3u8_obj.data)
            raise M3u8DownloaderNoStreamException()

    def get_tsfiles(self):
        self.ts_index = 0
        self.lock = Lock()

        self.thread_pool = []
        for i in range(self.threads):
            t = Thread(target=self._continue_download)
            self.thread_pool.append(t)
            t.daemon = True
            t.start()
        for i in range(self.threads):
            self.thread_pool[i].join()
        # for ts in tssegments:
        # self.download_ts(ts)
        pass

    def _continue_download(self, ):
        while True:
            try:
                with self.lock:
                    tsseg = self.tssegments.pop(0)
                    self.ts_index += 1
                    index = self.ts_index
            except IndexError:
                return
            self._download_ts(tsseg, index)

    def _download_ts(self, tsseg, index):
        try:
            outfile = M3u8File.get_path_by_uri(tsseg['uri'],
                                               M3u8Downloader.ts_tmpfolder)
            uri = urljoin(self.base_uri, tsseg['uri'])
            tsfile = TsFile(uri, self.headers, outfile, index)
            tsfile.get_file()
            self.tsfiles.append(tsfile)

            self.on_progress(len(self.tsfiles), self.__all_tsseg_len)
            # self._show_progress_bar(len(self.tsfiles), self.__all_tsseg_len)
            # print('append:' + tsfile.output_file)
        except DownloadFileNotValidException:
            self._download_ts(tsseg, index)
        except Exception as e:
            click.echo(e)
            click.echo('Exception occurred, ignore ...')
            self._download_ts(tsseg, index)

    def merge(self):
        # reorder
        self.tsfiles.sort(key=lambda x: x.index)
        with open(self.output_file, 'wb') as merged:
            for tsfile in self.tsfiles:
                print(tsfile.output_file)
                with open(tsfile.output_file, 'rb') as mergefile:
                    shutil.copyfileobj(mergefile, merged)
        #
        # with open(self.output_file, 'wb') as out:
        #     for tsfile in self.tsfiles:
        #         # tsfile = M3u8File.get_path_by_uri(tsseg['uri'],
        #         #                               M3u8Downloader.ts_tmpfolder)
        #         with open(tsfile.output_file, 'rb') as f:
        #             out.write(f.read())

    def cleanup(self):
        # clean
        shutil.rmtree(M3u8Downloader.ts_tmpfolder)
        os.unlink(M3u8Downloader.m3u8_filename)
