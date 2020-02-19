import textwrap


class Faker:
    headers = textwrap.dedent("""
    #EXTM3U
    #EXT-X-TARGETDURATION:7
    #EXT-X-ALLOW-CACHE:YES
    #EXT-X-PLAYLIST-TYPE:VOD
    #EXT-X-VERSION:3
    #EXT-X-MEDIA-SEQUENCE:1""")

    def create_file(self, file, blink, rs, re):
        content = Faker.headers
        for i in range(rs, re):
            link = blink.replace("@NUMBER", str(i), 1)
            extinf = textwrap.dedent("""
            #EXTINF:3.003,
            {0}
            """.format(link))
            content = content + extinf

        with open(file, 'w') as f:
            f.write(content)
