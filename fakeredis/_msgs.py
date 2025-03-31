INVALID_EXPIRE_MSG = "ERR invalid expire time in {}"
WRONGTYPE_MSG = "WRONGTYPE Operation against a key holding the wrong kind of value"
SYNTAX_ERROR_MSG = "ERR syntax error"
SYNTAX_ERROR_LIMIT_ONLY_WITH_MSG = (
    "ERR syntax error, LIMIT is only supported in combination with either BYSCORE or BYLEX"
)
INVALID_HASH_MSG = "ERR hash value is not an integer"
INVALID_INT_MSG = "ERR value is not an integer or out of range"
INVALID_FLOAT_MSG = "ERR value is not a valid float"
INVALID_WEIGHT_MSG = "ERR weight value is not a float"
INVALID_OFFSET_MSG = "ERR offset is out of range"
INVALID_BIT_OFFSET_MSG = "ERR bit offset is not an integer or out of range"
INVALID_BIT_VALUE_MSG = "ERR bit is not an integer or out of range"
BITOP_NOT_ONE_KEY_ONLY = "ERR BITOP NOT must be called with a single source key"
INVALID_DB_MSG = "ERR DB index is out of range"
INVALID_MIN_MAX_FLOAT_MSG = "ERR min or max is not a float"
INVALID_MIN_MAX_STR_MSG = "ERR min or max not a valid string range item"
STRING_OVERFLOW_MSG = "ERR string exceeds maximum allowed size (proto-max-bulk-len)"
OVERFLOW_MSG = "ERR increment or decrement would overflow"
NONFINITE_MSG = "ERR increment would produce NaN or Infinity"
SCORE_NAN_MSG = "ERR resulting score is not a number (NaN)"
INVALID_SORT_FLOAT_MSG = "ERR One or more scores can't be converted into double"
SRC_DST_SAME_MSG = "ERR source and destination objects are the same"
NO_KEY_MSG = "ERR no such key"
INDEX_ERROR_MSG = "ERR index out of range"
INDEX_NEGATIVE_ERROR_MSG = "ERR value is out of range, must be positive"
# ZADD_NX_XX_ERROR_MSG6 = "ERR ZADD allows either 'nx' or 'xx', not both"
ZADD_NX_XX_ERROR_MSG = "ERR XX and NX options at the same time are not compatible"
ZADD_INCR_LEN_ERROR_MSG = "ERR INCR option supports a single increment-element pair"
ZADD_NX_GT_LT_ERROR_MSG = "ERR GT, LT, and/or NX options at the same time are not compatible"
NX_XX_GT_LT_ERROR_MSG = "ERR NX and XX, GT or LT options at the same time are not compatible"
EXPIRE_UNSUPPORTED_OPTION = "ERR Unsupported option {}"
ZUNIONSTORE_KEYS_MSG = "ERR at least 1 input key is needed for {}"
WRONG_ARGS_MSG7 = "ERR Wrong number of args calling Redis command from script"
WRONG_ARGS_MSG6 = "ERR wrong number of arguments for '{}' command"
UNKNOWN_COMMAND_MSG = "ERR unknown command `{}`, with args beginning with: "
EXECABORT_MSG = "EXECABORT Transaction discarded because of previous errors."
MULTI_NESTED_MSG = "ERR MULTI calls can not be nested"
WITHOUT_MULTI_MSG = "ERR {0} without MULTI"
WATCH_INSIDE_MULTI_MSG = "ERR WATCH inside MULTI is not allowed"
NEGATIVE_KEYS_MSG = "ERR Number of keys can't be negative"
TOO_MANY_KEYS_MSG = "ERR Number of keys can't be greater than number of args"
TIMEOUT_NEGATIVE_MSG = "ERR timeout is negative"
NO_MATCHING_SCRIPT_MSG = "NOSCRIPT No matching script. Please use EVAL."
GLOBAL_VARIABLE_MSG = "ERR Script attempted to set global variables: {}"
COMMAND_IN_SCRIPT_MSG = "ERR This Redis command is not allowed from scripts"
BAD_SUBCOMMAND_MSG = "ERR Unknown {} subcommand or wrong # of args."
BAD_COMMAND_IN_PUBSUB_MSG = "ERR only (P)SUBSCRIBE / (P)UNSUBSCRIBE / PING / QUIT allowed in this context"
CONNECTION_ERROR_MSG = "FakeRedis is emulating a connection error."
REQUIRES_MORE_ARGS_MSG = "ERR {} requires {} arguments or more."
LOG_INVALID_DEBUG_LEVEL_MSG = "ERR Invalid debug level."
LUA_COMMAND_ARG_MSG6 = "ERR Lua redis() command arguments must be strings or integers"
LUA_COMMAND_ARG_MSG = "ERR Lua redis lib command arguments must be strings or integers"
VALKEY_LUA_COMMAND_ARG_MSG = "Command arguments must be strings or integers script: {}"
LUA_WRONG_NUMBER_ARGS_MSG = "ERR wrong number or type of arguments"
SCRIPT_ERROR_MSG = "ERR Error running script (call to f_{}): @user_script:?: {}"
RESTORE_KEY_EXISTS = "BUSYKEY Target key name already exists."
RESTORE_INVALID_CHECKSUM_MSG = "ERR DUMP payload version or checksum are wrong"

RESTORE_INVALID_TTL_MSG = "ERR Invalid TTL value, must be >= 0"
JSON_WRONG_REDIS_TYPE = "ERR Existing key has wrong Redis type"
JSON_KEY_NOT_FOUND = "ERR could not perform this operation on a key that doesn't exist"
JSON_PATH_NOT_FOUND_OR_NOT_STRING = "ERR Path '{}' does not exist or not a string"
JSON_PATH_DOES_NOT_EXIST = "ERR Path '{}' does not exist"
LCS_CANT_HAVE_BOTH_LEN_AND_IDX = "ERR If you want both the length and indexes, please just use IDX."
BIT_ARG_MUST_BE_ZERO_OR_ONE = "ERR The bit argument must be 1 or 0."
XADD_ID_LOWER_THAN_LAST = "ERR The ID specified in XADD is equal or smaller than the target stream top item"
XADD_INVALID_ID = "ERR Invalid stream ID specified as stream command argument"
XGROUP_BUSYGROUP = "ERR BUSYGROUP Consumer Group name already exists"
XREADGROUP_KEY_OR_GROUP_NOT_FOUND_MSG = (
    "NOGROUP No such key '{0}' or consumer group '{1}' in XREADGROUP with GROUP option"
)
XGROUP_GROUP_NOT_FOUND_MSG = "NOGROUP No such consumer group '{0}' for key name '{1}'"
XGROUP_KEY_NOT_FOUND_MSG = (
    "ERR The XGROUP subcommand requires the key to exist."
    " Note that for CREATE you may want to use the MKSTREAM option to create an empty stream automatically."
)
GEO_UNSUPPORTED_UNIT = "unsupported unit provided. please use M, KM, FT, MI"
LPOS_RANK_CAN_NOT_BE_ZERO = (
    "RANK can't be zero: use 1 to start from the first match, 2 from the second ... "
    "or use negative to start from the end of the list"
)
NUMKEYS_GREATER_THAN_ZERO_MSG = "numkeys should be greater than 0"
FILTER_FULL_MSG = ""
NONSCALING_FILTERS_CANNOT_EXPAND_MSG = "Nonscaling filters cannot expand"
ITEM_EXISTS_MSG = "item exists"
NOT_FOUND_MSG = "not found"
INVALID_BITFIELD_TYPE = (
    "ERR Invalid bitfield type. Use something like i16 u8. Note that u64 is not supported but i64 is."
)
INVALID_OVERFLOW_TYPE = "ERR Invalid OVERFLOW type specified"

# ACL specific errors
AUTH_FAILURE = "WRONGPASS invalid username-password pair or user is disabled."

# TDigest error messages
TDIGEST_KEY_EXISTS = "T-Digest: key already exists"
TDIGEST_KEY_NOT_EXISTS = "T-Digest: key does not exist"
TDIGEST_ERROR_PARSING_VALUE = "T-Digest: error parsing val parameter"
TDIGEST_BAD_QUANTILE = "T-Digest: quantile should be in [0,1]"
TDIGEST_BAD_RANK = "T-Digest: rank needs to be non negative"

# TimeSeries error messages
TIMESERIES_KEY_EXISTS = "TSDB: key already exists"
TIMESERIES_INVALID_DUPLICATE_POLICY = "TSDB: Unknown DUPLICATE_POLICY"
TIMESERIES_KEY_DOES_NOT_EXIST = "TSDB: the key does not exist"
TIMESERIES_RULE_DOES_NOT_EXIST = "TSDB: compaction rule does not exist"
TIMESERIES_RULE_EXISTS = "TSDB: the destination key already has a src rule"
TIMESERIES_BAD_AGGREGATION_TYPE = "TSDB: Unknown aggregation type"
TIMESERIES_INVALID_TIMESTAMP = "TSDB: invalid timestamp"
TIMESERIES_BAD_TIMESTAMP = "TSDB: Couldn't parse alignTimestamp"
TIMESERIES_TIMESTAMP_OLDER_THAN_RETENTION = "TSDB: Timestamp is older than retention"
TIMESERIES_TIMESTAMP_LOWER_THAN_MAX_V7 = (
    "TSDB: timestamp must be equal to or higher than the maximum existing timestamp"
)
TIMESERIES_TIMESTAMP_LOWER_THAN_MAX_V6 = "TSDB: for incrby/decrby, timestamp should be newer than the lastest one"
TIMESERIES_BAD_CHUNK_SIZE = "TSDB: CHUNK_SIZE value must be a multiple of 8 in the range [48 .. 1048576]"
TIMESERIES_DUPLICATE_POLICY_BLOCK = (
    "TSDB: Error at upsert, update is not supported when DUPLICATE_POLICY is set to BLOCK mode"
)
TIMESERIES_BAD_FILTER_EXPRESSION = "TSDB: failed parsing labels"
HEXPIRE_NUMFIELDS_DIFFERENT = "The `numfields` parameter must match the number of arguments"

MISSING_ACLFILE_CONFIG = "ERR This Redis instance is not configured to use an ACL file. You may want to specify users via the ACL SETUSER command and then issue a CONFIG REWRITE (assuming you have a Redis configuration file set) in order to store users in the Redis configuration."

NO_PERMISSION_ERROR = "NOPERM User {} has no permissions to run the '{}' command"
NO_PERMISSION_KEY_ERROR = "NOPERM No permissions to access a key"
NO_PERMISSION_CHANNEL_ERROR = "NOPERM No permissions to access a channel"

# Command flags
FLAG_NO_SCRIPT = "s"  # Command not allowed in scripts
FLAG_LEAVE_EMPTY_VAL = "v"
FLAG_TRANSACTION = "t"
FLAG_DO_NOT_CREATE = "i"
