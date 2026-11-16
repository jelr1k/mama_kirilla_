from collections import deque


class StatisticsService:
    def __init__(self, max_history: int = 500):
        self.history = deque(maxlen=max_history)
        self.whisper_history = deque(maxlen=max_history)

    def add(self, stats):
        self.history.append(stats)

    @property
    def latest(self):
        return self.history[-1] if self.history else None

    def add_whisper(self, stats):
        if stats is None:
            return
        self.whisper_history.append(stats)

    @property
    def latest_whisper(self):
        return self.whisper_history[-1] if self.whisper_history else None
