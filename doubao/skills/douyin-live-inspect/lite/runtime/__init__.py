"""Content-only live inspection runtime."""
from pathlib import Path
import sys
import types
__path__.append(str(Path(__file__).resolve().parents[2] / 'telemetry' / 'python'))
from . import bridge, transaction
for _name in ('telemetry','telemetry_context','telemetry_transport','telemetry_keys','asr_observability','diagnostic_transport','diagnostic_outbox'):
    sys.modules[__name__+'.'+_name]=bridge
    globals()[_name]=bridge
for _name in ('task_telemetry','telemetry_rules','telemetry_funnel','telemetry_batch','telemetry_cloud','telemetry_transaction'):
    sys.modules[__name__+'.'+_name]=transaction
    globals()[_name]=transaction
telemetry_stop=types.ModuleType(__name__+'.telemetry_stop')
telemetry_stop.safe=bridge.stop_safe
telemetry_stop.observations=bridge.stop_observations
sys.modules[telemetry_stop.__name__]=telemetry_stop
