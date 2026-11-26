# Synthetic inspected source; not a deployed artifact proof.
class FileLoader:
    def __init__(self):
        self.queued = []

    def enqueue(self, key):
        if key not in self.queued:
            self.queued.append(key)

    def process_one(self, parse):
        if self.queued:
            key = self.queued.pop(0)
            parse(key)
