from pathlib import Path
from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.cli import demo
ROOT=Path(__file__).parents[1]
demo(load_runtime(ROOT),trace=False)
