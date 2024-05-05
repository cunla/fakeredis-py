import json
from random import shuffle


class TDigest(object):
    def __init__(self, delta=0.01, compression=20):
        self.delta = float(delta)
        self.compression = compression
        self.tdc = TDigestCore(self.delta)

    def push(self, x, w):
        self.tdc.push(x, w)
        if len(self) > self.compression / self.delta:
            self.compress()

    def compress(self):
        aux_tdc = TDigestCore(self.delta)
        centroid_list = self.tdc.centroid_list
        shuffle(centroid_list)
        for c in centroid_list:
            aux_tdc.push(c.mean, c.count)
        self.tdc = aux_tdc

    def quantile(self, x):
        return self.tdc.quantile(x)

    def serialize(self):
        centroids = [[c.mean, c.count] for c in self.tdc.centroid_list]
        return json.dumps(centroids)

    def __len__(self):
        return len(self.tdc)

    def __repr__(self):
        return str(self.tdc)


class Centroid(object):
    def __init__(self, x, w, id):
        self.mean = float(x)
        self.count = float(w)
        self.id = id

    def push(self, x, w):
        self.count += w
        self.mean += w * (x - self.mean) / self.count

    def equals(self, c):
        if c.id == self.id:
            return True
        else:
            return False

    def distance(self, x):
        return abs(self.mean - x)

    def __repr__(self):
        return "Centroid{mean=%.1f, count=%d}" % (self.mean, self.count)


class TDigestCore(object):
    def __init__(self, delta):
        self.delta = delta
        self.centroid_list = []
        self.n = 0
        self.id_counter = 0

    def push(self, x, w):
        self.n += 1

        if self.centroid_list:
            S = self._closest_centroids(x)
            shuffle(S)
            for c in S:
                if w == 0:
                    break
                q = self._centroid_quantile(c)
                delta_w = min(4 * self.n * self.delta * q * (1 - q) - c.count, w)
                c.push(x, delta_w)
                w -= delta_w

        if w > 0:
            self.centroid_list.append(Centroid(x, w, self.id_counter))
            self.centroid_list.sort(key=lambda c: c.mean)
            self.id_counter += 1

    def quantile(self, x):
        if len(self.centroid_list) < 3:
            return 0.0
        total_weight = sum([centroid.count for centroid in self.centroid_list])
        q = x * total_weight
        m = len(self.centroid_list)
        cumulated_weight = 0
        for nr in range(m):
            current_weight = self.centroid_list[nr].count
            if cumulated_weight + current_weight > q:
                if nr == 0:
                    delta = (
                            self.centroid_list[nr + 1].mean - self.centroid_list[nr].mean
                    )
                elif nr == m - 1:
                    delta = (
                            self.centroid_list[nr].mean - self.centroid_list[nr - 1].mean
                    )
                else:
                    delta = (
                                    self.centroid_list[nr + 1].mean
                                    - self.centroid_list[nr - 1].mean
                            ) / 2
                return (
                        self.centroid_list[nr].mean
                        + ((q - cumulated_weight) / (current_weight) - 0.5) * delta
                )
            cumulated_weight += current_weight
        return self.centroid_list[nr].mean

    def _closest_centroids(self, x):
        S = []
        z = None
        for centroid in self.centroid_list:
            d = centroid.distance(x)
            if z is None:
                z = d
                S.append(centroid)
            elif z == d:
                S.append(centroid)
            elif z > d:
                S = [centroid]
                z = d
            elif x > centroid.mean:
                break
        T = []
        for centroid in S:
            q = self._centroid_quantile(centroid)
            if centroid.count + 1 <= 4 * self.n * self.delta * q * (1 - q):
                T.append(centroid)
        return T

    def _centroid_quantile(self, c):
        q = 0
        for centroid in self.centroid_list:
            if centroid.equals(c):
                q += c.count / 2
                break
            else:
                q += centroid.count
        return q / sum([centroid.count for centroid in self.centroid_list])

    def __len__(self):
        return len(self.centroid_list)

    def __repr__(self):
        return "[ %s ]" % ", ".join([str(c) for c in self.centroid_list])

