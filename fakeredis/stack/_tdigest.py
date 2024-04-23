import sortedcontainers

class Centroid(object):

    def __init__(self, mean, n, cumn):
        # cumn: cumulative count
        self.mean = float(mean)
        self.n = n
        self.cumn = cumn


class Tdigest(object):

    def __init__(self, delta=0.01, K=25, CX=1.1):
        self.delta = delta
        self.K = K
        self.CX = CX
        self.centroids = RBTree()
        self.nreset = 0
        self.reset()

    def reset(self):
        self.centroids.clear()
        self.n = 0
        self.nreset += 1
        self.last_cumulate = 0
        self.compressing = False

    def push(self, x, n=1):
        if not isinstance(x, list):
            x = [x]
        for item in x:
            self._digest(item, n)

    def percentile(self, p):
        if self.size() == 0:
            return None
        self._cumulate(True)
        cumn = self.n * p
        lower = self.centroids.min_item()[1]
        upper = self.centroids.max_item()[1]
        for c in self.centroids.values():
            if c.cumn <= cumn:
                lower = c
            else:
                upper = c
                break
        if lower == upper:
            return lower.mean
        return lower.mean + (cumn - lower.cumn) * (upper.mean - lower.mean) / (upper.cumn - lower.cumn)

    def serialize(self):
        result = '%s~%s~%s~' % (self.delta, self.K, self.size())
        if self.size() == 0:
            return result
        self._cumulate(True)
        means = []
        counts = []
        for c in self.centroids.values():
            means.append(str(c.mean))
            counts.append(str(c.n))
        return '%s%s~%s' % (result, '~'.join(means), '~'.join(counts))

    def simpleSerialize(self):
        if self.size() == 0:
            return ''
        self._cumulate(True)
        result = []
        for c in self.centroids.values():
            result.append(str(c.mean))
            result.append(str(c.n))
        return '~'.join(result)

    @classmethod
    def deserialize(cls, serialized_str):
        if not isinstance(serialized_str, str):
            raise Exception(u'serialized_str must be str')
        data = serialized_str.split('~')
        t = Tdigest(delta=float(data[0]), K=int(data[1]))
        size = int(data[2])
        for i in range(size):
            t.push(float(data[i + 3]), int(data[size + i + 3]))
        t._cumulate(True)
        return t

    def _digest(self, x, n):
        if self.size() == 0:
            self._new_centroid(x, n, 0)
        else:
            _min = self.centroids.min_item()[1]
            _max = self.centroids.max_item()[1]
            nearest = self.find_nearest(x)
            if nearest and nearest.mean == x:
                self._addweight(nearest, x, n)
            elif nearest == _min:
                self._new_centroid(x, n, 0)
            elif nearest == _max:
                self._new_centroid(x, n, self.n)
            else:
                p = (nearest.cumn + nearest.n / 2.0) / self.n
                max_n = int(4 * self.n * self.delta * p * (1 - p))
                if max_n >= nearest.n + n:
                    self._addweight(nearest, x, n)
                else:
                    self._new_centroid(x, n, nearest.cumn)
        self._cumulate(False)
        if self.K and self.size() > self.K / self.delta:
            self.compress()

    def find_nearest(self, x):
        if self.size() == 0:
            return None
        try:
            lower = self.centroids.ceiling_item(x)[1]
        except KeyError:
            lower = None

        if lower and lower.mean == x:
            return lower

        try:
            prev = self.centroids.floor_item(x)[1]
        except KeyError:
            prev = None

        if not lower:
            return prev
        if not prev:
            return lower
        if abs(prev.mean - x) < abs(lower.mean - x):
            return prev
        else:
            return lower

    def size(self):
        return len(self.centroids)

    def compress(self):
        if self.compressing:
            return
        points = self.toList()
        self.reset()
        self.compressing = True
        for point in sorted(points, key=lambda x: random()):
            self.push(point['mean'], point['n'])
        self._cumulate(True)
        self.compressing = False

    def _cumulate(self, exact):
        if self.n == self.last_cumulate:
            return
        if not exact and self.CX and self.last_cumulate and \
                self.CX > (self.n / self.last_cumulate):
            return
        cumn = 0
        for c in self.centroids.values():
            cumn = c.cumn = cumn + c.n
        self.n = self.last_cumulate = cumn

    def toList(self):
        return [dict(mean=c.mean, n=c.n, cumn=c.cumn) for
                c in self.centroids.values()]

    def _addweight(self, nearest, x, n):
        if x != nearest.mean:
            nearest.mean += n * (x - nearest.mean) / (nearest.n + n)
        nearest.cumn += n
        nearest.n += n
        self.n += n

    def _new_centroid(self, x, n, cumn):
        c = Centroid(x, n, cumn)
        self.centroids.insert(x, c)
        self.n += n
        return c


if __name__ == '__main__':
    from random import random

    t = Tdigest(K=25)
    for i in range(1000):
        t.push(random())
    print('P0 = ', t.percentile(0))
    print('P10 = ', t.percentile(0.1))
    print('P50 = ', t.percentile(0.5))
    print('P90 = ', t.percentile(0.9))
    print('P100 = ', t.percentile(1.0))

    t1 = Tdigest(K=25)
    t1.push(100)
    t1.push(200)
    t1.push(300)
    t1.push(400)
    print('serialize = ', t1.serialize())
    print('simpleSerialize = ', t1.simpleSerialize())
