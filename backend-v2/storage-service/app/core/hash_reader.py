import hashlib

class HashReader:
    def __init__(self, fobj):
        self._f = fobj
        self._hasher = hashlib.sha256()
        self.size = 0

    def read(self, n=-1):
        chunk = self._f.read(n)
        if chunk:
            # chunk may be str in some contexts; ensure bytes
            if isinstance(chunk, str):
                chunk = chunk.encode()
            self._hasher.update(chunk)
            self.size += len(chunk)
        return chunk

    def hexdigest(self):
        return self._hasher.hexdigest()

    def seek(self, *args, **kwargs):
        return getattr(self._f, "seek")(*args, **kwargs)

    def tell(self):
        return getattr(self._f, "tell")()
