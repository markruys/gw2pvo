import logging

class MovingAverage:

    def __init__(self, n):
        self.n = round(n) if n > 0 else 1
        self.denominator = self.n * (self.n + 1) / 2
        self.fifo = []

    def add(self, x):

        if len(self.fifo) == 0:
            print(x, self.n)
            self.fifo = [x] * self.n
            self.total = sum(self.fifo)
            self.numerator = x * self.denominator

        self.numerator += self.n * x - self.total

        self.total += x - self.fifo[0]

        self.fifo.append(x)
        self.fifo = self.fifo[-self.n:]

        return self.numerator / self.denominator

