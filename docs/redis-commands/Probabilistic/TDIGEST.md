# `tdigest` commands (14/14 implemented)

## [TDIGEST.CREATE](https://redis.io/commands/tdigest.create/)

Allocates memory and initializes a new t-digest sketch

## [TDIGEST.RESET](https://redis.io/commands/tdigest.reset/)

Resets a t-digest sketch: empty the sketch and re-initializes it.

## [TDIGEST.ADD](https://redis.io/commands/tdigest.add/)

Adds one or more observations to a t-digest sketch

## [TDIGEST.MERGE](https://redis.io/commands/tdigest.merge/)

Merges multiple t-digest sketches into a single sketch

## [TDIGEST.MIN](https://redis.io/commands/tdigest.min/)

Returns the minimum observation value from a t-digest sketch

## [TDIGEST.MAX](https://redis.io/commands/tdigest.max/)

Returns the maximum observation value from a t-digest sketch

## [TDIGEST.QUANTILE](https://redis.io/commands/tdigest.quantile/)

Returns, for each input fraction, an estimation of the value (floating point) that is smaller than the given fraction of observations

## [TDIGEST.CDF](https://redis.io/commands/tdigest.cdf/)

Returns, for each input value, an estimation of the fraction (floating-point) of (observations smaller than the given value + half the observations equal to the given value)

## [TDIGEST.TRIMMED_MEAN](https://redis.io/commands/tdigest.trimmed_mean/)

Returns an estimation of the mean value from the sketch, excluding observation values outside the low and high cutoff quantiles

## [TDIGEST.RANK](https://redis.io/commands/tdigest.rank/)

Returns, for each input value (floating-point), the estimated rank of the value (the number of observations in the sketch that are smaller than the value + half the number of observations that are equal to the value)

## [TDIGEST.REVRANK](https://redis.io/commands/tdigest.revrank/)

Returns, for each input value (floating-point), the estimated reverse rank of the value (the number of observations in the sketch that are larger than the value + half the number of observations that are equal to the value)

## [TDIGEST.BYRANK](https://redis.io/commands/tdigest.byrank/)

Returns, for each input rank, an estimation of the value (floating-point) with that rank

## [TDIGEST.BYREVRANK](https://redis.io/commands/tdigest.byrevrank/)

Returns, for each input reverse rank, an estimation of the value (floating-point) with that reverse rank

## [TDIGEST.INFO](https://redis.io/commands/tdigest.info/)

Returns information and statistics about a t-digest sketch



