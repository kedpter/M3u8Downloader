### M3u8-dl

![alt text](https://img.shields.io/pypi/v/m3u8_dl.svg)
![alt text](https://img.shields.io/travis/kedpter/m3u8_dl.svg)
![alt text](https://readthedocs.org/projects/m3u8_dl/badge/?version=latest)

M3u8-dl is a simple command-line util which downloads m3u8 file.


### Install

```bash
pip install m3u8-dl
```

### Usage

Get the HLS Request infomation from web browser with `Developer Tools`.
Such As `Request URL` and `Referer`.

```bash
# HLS_URL -> Request URL
# OUTPUT -> such as example.ts
m3u8-dl HLS_URL OUTPUT
# code below may not work since the website server may reject an out-of-date request
m3u8-dl https://proxy-038.dc3.dailymotion.com/sec\(4pkX4jyJ09RyW9jaEyekktbBu55uix9cMXQu-o5e13EelVKd1csb9zYSD66hQl7PlA_V5ntIHivm_tuQqkANmQj8DbX33OMJ5Db-9n67_SQ\)/video/795/864/249468597_mp4_h264_aac.m3u8 example.ts -u https://proxy-038.dc3.dailymotion.com/sec\(4pkX4jyJ09RyW9jaEyekktbBu55uix9cMXQu-o5e13EelVKd1csb9zYSD66hQl7PlA_V5ntIHivm_tuQqkANmQj8DbX33OMJ5Db-9n67_SQ\)/video/795/864/ -r https://www.dailymotion.com/video/x44iz79

# restore last session if the task was interrupted
m3u8-dl --restore
```

If you are failed to download the stream, try it again with the options below:
- Specify the Referer with `-r` when you're blocked by the website (403 forbidden).
- Specify the base uri with `-u` when `#EXTINF hls-720p0.ts` has no base uri in `output.m3u8`.

You can even make it run faster by using `-t`, which means how many threads you want to start.

`--restore` will restore the last session.

For more details, check `--help`.
