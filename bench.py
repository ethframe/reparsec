from json import dumps

import pyperf

from reparsec.json import parse
from reparsec.json_scannerless import parse as sl_parse

DATA = dumps({"key_" + str(n): list(range(100)) for n in range(1000)})


runner = pyperf.Runner()
runner.bench_func("json_parser", lambda: parse(DATA))
runner.bench_func("json_sl_parser", lambda: sl_parse(DATA))
