from m3u8_dl import M3u8Context
import pickle
import os


class PickleContextRestore:
    restore_file = 'm3u8_dl.restore'

    def __init__(self):
        pass

    def dump(self, context):
        with open(self.restore_file, 'wb') as f:
            pickle.dump(context, f)

    def load(self):
        with open(self.restore_file, 'rb') as f:
            return pickle.load(f)

    def cleanup(self):
        if os.path.isfile(self.restore_file):
            os.unlink(self.restore_file)
