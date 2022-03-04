from json import dumps

import pyperf

from tests.parsers.json import loads
from tests.parsers.json_scannerless import loads as sl_loads

DATA = dumps({"key_" + str(n): list(range(100)) for n in range(1000)})


runner = pyperf.Runner()
runner.bench_func("json_parser", lambda: loads(DATA))
runner.bench_func("json_sl_parser", lambda: sl_loads(DATA))
