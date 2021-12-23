import requests
import io

# from @codeskyblue : https://stackoverflow.com/a/62424471/3278496

class MjpegReader:
    def __init__(self, url: str):
        self._url = url

    def iter_content(self):
        """
        Raises:
            RuntimeError
        """
        r = requests.get(self._url, stream=True)

        # parse boundary
        content_type = r.headers['content-type']
        index = content_type.rfind("boundary=")
        assert index != 1
        boundary = content_type[index+len("boundary="):] + "\r\n"
        boundary = boundary.encode('utf-8')

        rd = io.BufferedReader(r.raw)
        while True:
            length = self._parse_length(rd)
            yield rd.read(length)
            self._skip_to_boundary(rd, boundary)

    @staticmethod
    def _parse_length(rd) -> int:
        length = 0
        while True:
            line = rd.readline()
            if line == b'\r\n':
                return length
            if line.startswith(b"Content-Length"):
                length = int(line.decode('utf-8').split(": ")[1])
                assert length > 0

    @staticmethod
    def _skip_to_boundary(rd, boundary: bytes):
        for _ in range(1000):
            line = rd.readline()
            if boundary in line:
                break
        else:
            raise RuntimeError("Boundary not detected:", boundary)