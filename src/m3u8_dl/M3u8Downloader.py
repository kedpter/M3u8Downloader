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


def download_file(fileuri, headers, filename, check=None, verify=True):
    with requests.get(fileuri, headers=headers, stream=True, verify=verify) as r:  # noqa
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


class M3u8File:

    def __init__(self, fileuri, headers, output_file, sslverify, finished=False):  # noqa
        self.fileuri = fileuri
        self.headers = headers
        self.output_file = output_file
        self.finished = finished
        self.sslverify = sslverify

    def get_file(self):
        # check scheme (http or local)
        parsed_uri = urlparse(self.fileuri)
        if parsed_uri.scheme == "http" or parsed_uri.scheme == "https":
            if not self.finished:
                download_file(self.fileuri, self.headers,
                              self.output_file, verify=self.sslverify)
        elif parsed_uri.scheme == "file":
            shutil.copy(parsed_uri.path, self.output_file)
        else:
            raise Exception("Unspported url scheme")

    def parse_file(self):
        self.m3u8_obj = m3u8.load(self.output_file)
        return self.m3u8_obj

    def get_tssegments(self):
        return self.m3u8_obj.data['segments']

    @staticmethod
    def get_path_by_uri(uri, folder):
        return os.path.join(folder,
                            urlparse(uri).path.split('/')[-1])


class TsFile(HttpFile):
    def __init__(self, fileuri, headers, output_file, index, sslverify):
        super(HttpFile, self).__init__()
        self.fileuri = fileuri
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
        download_file(self.fileuri, self.headers, self.output_file,
                      self.check_valid, self.sslverify)
        self.finished = True


class M3u8Downloader:
    m3u8_filename = 'output.m3u8'
    ts_tmpfolder = '.tmpts'
    max_try = 10

    def __init__(self, restore_obj, on_progress_callback=None):
        self.restore_obj = restore_obj
        self.is_task_success = False

        user_options = self.restore_obj['user_options']

        self.fileuri = user_options['file_uri']
        self.base_uri = user_options['base_uri'] if user_options['base_uri'].endswith('/') else user_options['base_uri'] + '/'  # noqa
        self.referer = user_options['referer']
        self.threads = user_options['threads']
        self.output_file = user_options['output_file']
        self.sslverify = user_options['sslverify']

        self.headers = {'Referer': self.referer}
        self.tsfiles = []

        self.ts_index = 0
        self.lock = Lock()

        self.on_progress = on_progress_callback

        if not os.path.isdir(M3u8Downloader.ts_tmpfolder):
            os.mkdir(M3u8Downloader.ts_tmpfolder)

    @monitor_proc('download m3u8 file')
    def get_m3u8file(self):
        finished = self.restore_obj['processes']['get_m3u8file']['finished']
        self.m3u8file = M3u8File(self.fileuri, self.headers,
                                 M3u8Downloader.m3u8_filename, self.sslverify,
                                 finished)
        self.m3u8file.get_file()
        finished = True

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
                self.restore_obj['downloaded_ts'], ))
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
        if trycnt > M3u8Downloader.max_try:
            raise M3u8DownloaderMaxTryException
        try:
            outfile = M3u8File.get_path_by_uri(tsseg['uri'],
                                               M3u8Downloader.ts_tmpfolder)
            uri = urljoin(self.base_uri, tsseg['uri'])
            tsfile = TsFile(uri, self.headers, outfile, index, self.sslverify)

            if not tsseg['uri'] in dd_ts:
                tsfile.get_file()
                dd_ts.append(tsseg['uri'])
            self.tsfiles.append(tsfile)

            self.on_progress(len(self.tsfiles), self.__all_tsseg_len)
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
            for tsfile in self.tsfiles:
                print(tsfile.output_file)
                with open(tsfile.output_file, 'rb') as mergefile:
                    shutil.copyfileobj(mergefile, merged)

    @monitor_proc('clean up')
    def cleanup(self):
        # clean
        shutil.rmtree(M3u8Downloader.ts_tmpfolder)
        os.unlink(M3u8Downloader.m3u8_filename)
