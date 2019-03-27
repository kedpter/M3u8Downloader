
M3u8-dl
^^^^^^^


.. image:: https://img.shields.io/pypi/v/m3u8_dl.svg
   :target: https://img.shields.io/pypi/v/m3u8_dl.svg
   :alt: alt text


.. image:: https://img.shields.io/travis/kedpter/m3u8_dl.svg
   :target: https://img.shields.io/travis/kedpter/m3u8_dl.svg
   :alt: alt text


.. image:: https://readthedocs.org/projects/m3u8_dl/badge/?version=latest
   :target: https://readthedocs.org/projects/m3u8_dl/badge/?version=latest
   :alt: alt text


M3u8-dl is a simple command-line util which downloads m3u8 file.

Install
^^^^^^^

.. code-block:: bash

   pip install m3u8-dl

Usage
^^^^^

Get the HLS Request infomation from web browser with ``Developer Tools``.
Such As ``Request URL`` and ``Referer``.

.. code-block:: bash

   # HLS_URL -> Request URL
   # OUTPUT -> such as example.ts
   m3u8-dl HLS_URL OUTPUT
   # restore last session if the task was interrupted
   m3u8-dl --restore

If you are failed to download the stream, try it again with the options below:


* Specify the Referer with ``-r`` when you're blocked by the website (403 forbidden).
* Specify the base uri with ``-u`` when ``#EXTINF hls-720p0.ts`` has no base uri in ``output.m3u8``.

You can even make it run faster by using ``-t``\ , which means how many threads you want to start.

``--restore`` will restore the last session.

For more details, check ``--help``.
