import logging

class MovingAverage:

    def __init__(self, n):
        self.n = round(n) if n > 0 else 1
        self.denominator = self.n * (self.n + 1) / 2
        self.queue = []

    def add(self, x):

        if len(self.queue) == 0:
            self.queue = [x] * self.n
            self.total = sum(self.queue)
            self.numerator = x * self.denominator

        self.numerator += self.n * x - self.total

        self.total += x - self.queue[0]

        self.queue.append(x)
        self.queue = self.queue[-self.n:]

        return self.numerator / self.denominator

