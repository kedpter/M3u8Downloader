# -*- coding: utf-8 -*-

import m3u8
import requests
from urllib.parse import urlparse, urljoin
import os
import shutil
from threading import Thread, Lock
import urllib3
# to surpress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def monitor_proc(proc_name):
    def monitor(func):
        def wrapper(*args, **kwargs):
            print('Executing: {} ...'.format(proc_name))
            func(*args, **kwargs)
            print('Finished: {} '.format(proc_name))
        return wrapper
    return monitor


class DownloadFileNotValidException(Exception):
    pass


class M3u8DownloaderNoStreamException(Exception):
    pass


class M3u8DownloaderMaxTryException(Exception):
    pass


def download_file(fileurl, headers, filename, check=None, verify=True):
    with requests.get(fileurl, headers=headers, stream=True, verify=verify) as r:  # noqa
        if check and not check(r):
            print('Not a valid ts file')
            print(r.content)
            raise DownloadFileNotValidException()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


class M3u8File:

    def __init__(self, fileurl, headers, output_file, sslverify, finished=False):  # noqa
        self.fileurl = fileurl
        self.headers = headers
        self.output_file = output_file
        self.finished = finished
        self.sslverify = sslverify

    def get_file(self):
        # check scheme (http or local)
        parsed_url = urlparse(self.fileurl)
        if parsed_url.scheme == "http" or parsed_url.scheme == "https":
            if not self.finished:
                download_file(self.fileurl, self.headers,
                              self.output_file, verify=self.sslverify)
        elif parsed_url.scheme == "file":
            shutil.copy(parsed_url.path, self.output_file)
        else:
            raise Exception("Unspported url scheme")

    def parse_file(self):
        self.m3u8_obj = m3u8.load(self.output_file)
        return self.m3u8_obj

    def get_tssegments(self):
        return self.m3u8_obj.data['segments']

    @staticmethod
    def get_path_by_url(url, folder):
        return os.path.join(folder,
                            urlparse(url).path.split('/')[-1])


class TsFile():
    def __init__(self, fileurl, headers, output_file, index, sslverify):
        self.fileurl = fileurl
        self.headers = headers
        self.output_file = output_file
        self.index = index
        self.finished = False
        self.sslverify = sslverify

    @staticmethod
    def check_valid(request):
        if request.headers['Content-Type'] == 'text/html':
            return False
        # print(request.headers['Content-Type'])
        # print(request.content)
        return True

    def get_file(self):
        download_file(self.fileurl, self.headers, self.output_file,
                      self.check_valid, self.sslverify)
        self.finished = True


class M3u8Context(object):
    rendering_attrs = ['file_url', 'base_url', 'referer', 'threads', 'output_file', 'sslverify',
                       'get_m3u8file_complete', 'downloaded_ts_urls']

    def __init__(self, **kwargs):
        self._container = {}
        for key, value in kwargs.items():
            self._container.setdefault(key, value)

    def __getitem__(self, item):
        return self._container[item]

    def __setitem__(self, key, value):
        self._container[key] = value

    def __iter__(self):
        return iter(self._container.items())

    def __getstate__(self):
        obj_dict = {}
        for attr in self.rendering_attrs:
            if attr in self._container:
                obj_dict[attr] = self._container[attr]
        return obj_dict

    def __setstate__(self, obj):
        self._container = obj


class M3u8Downloader:
    m3u8_filename = 'output.m3u8'
    ts_tmpfolder = '.tmpts'
    max_try = 10

    def __init__(self, context, on_progress_callback=None):
        self.context = context
        self.is_task_success = False

        self.fileurl = context['file_url']
        self.base_url = context['base_url']
        self.referer = context['referer']
        self.threads = context['threads']
        self.output_file = context['output_file']
        self.sslverify = context['sslverify']

        self.headers = {'Referer': self.referer}
        self.tsfiles = []

        self.ts_index = 0
        self.lock = Lock()

        self.on_progress = on_progress_callback

        if not os.path.isdir(self.ts_tmpfolder):
            os.mkdir(self.ts_tmpfolder)

    @monitor_proc('download m3u8 file')
    def get_m3u8file(self):
        self.m3u8file = M3u8File(self.fileurl, self.headers,
                                 self.m3u8_filename, self.sslverify,
                                 self.context['get_m3u8file_complete'])
        self.m3u8file.get_file()
        self.context['get_m3u8file_complete'] = True

    @monitor_proc('parse m3u8 file')
    def parse_m3u8file(self):
        self.m3u8file.parse_file()
        self.tssegments = self.m3u8file.get_tssegments()
        self.__all_tsseg_len = len(self.tssegments)
        if len(self.tssegments) == 0:
            print(self.m3u8file.m3u8_obj.data)
            raise M3u8DownloaderNoStreamException()

    @monitor_proc('download ts files')
    def get_tsfiles(self):
        """
        start multiple threads to download ts files,
        threads will fetch links from the pool (ts segments)
        """
        self.thread_pool = []
        for i in range(self.threads):
            t = Thread(target=self._keep_download, args=(
                self.context['downloaded_ts_urls'], ))
            self.thread_pool.append(t)
            t.daemon = True
            t.start()
        for i in range(self.threads):
            self.thread_pool[i].join()
        pass

    def _keep_download(self, dd_ts):
        trycnt = 0
        while True:
            try:
                with self.lock:
                    tsseg = self.tssegments.pop(0)
                    self.ts_index += 1
                    index = self.ts_index
                    trycnt = 0
            except IndexError:
                self.is_task_success = True
                return
            try:
                self._download_ts(tsseg, index, dd_ts, trycnt)
            except M3u8DownloaderMaxTryException:
                break

    def _download_ts(self, tsseg, index, dd_ts, trycnt):
        uri = tsseg['uri']
        if trycnt > self.max_try:
            raise M3u8DownloaderMaxTryException
        try:
            outfile = M3u8File.get_path_by_url(uri,
                                               self.ts_tmpfolder)
            url = urljoin(self.base_url, uri)
            tsfile = TsFile(url, self.headers, outfile, index, self.sslverify)

            if not uri in dd_ts:
                tsfile.get_file()
                dd_ts.append(uri)
            self.tsfiles.append(tsfile)

            self.on_progress(self, len(self.tsfiles), self.__all_tsseg_len)
        except DownloadFileNotValidException:
            trycnt = trycnt + 1
            self._download_ts(tsseg, index, dd_ts, trycnt)
        except Exception as e:
            print(e)
            print('Exception occurred, ignore ...')
            trycnt = trycnt + 1
            self._download_ts(tsseg, index, dd_ts, trycnt)

    @monitor_proc('merging ts files')
    def merge(self):
        # reorder
        self.tsfiles.sort(key=lambda x: x.index)
        with open(self.output_file, 'wb') as merged:
            for tsfile in range(len(self.tsfiles)):
                self._show_progress_bar(tsfile + 1, len(self.tsfiles))
                with open(self.tsfiles[tsfile].output_file, 'rb') as mergefile:
                    shutil.copyfileobj(mergefile, merged)

    @monitor_proc('clean up')
    def cleanup(self):
        # clean
        shutil.rmtree(self.ts_tmpfolder)
        os.unlink(self.m3u8_filename)

    def _show_progress_bar(self, downloaded, total):
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
