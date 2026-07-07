"""Make `custom_components/mycoolman/protocol.py` importable as `protocol`
without going through the package's `__init__.py` (which pulls in Home
Assistant imports protocol.py itself doesn't need).

Note: this deliberately does NOT add `custom_components/mycoolman/` to
`sys.path` - that directory also contains a `select.py` (the HA `select`
platform), which would shadow Python's stdlib `select` module and break
anything importing it (asyncio, pdb, ...). Loading protocol.py directly by
file path avoids that collision entirely.
"""

import importlib.util
import sys
from pathlib import Path

_protocol_path = (
    Path(__file__).parent.parent / "custom_components" / "mycoolman" / "protocol.py"
)
_spec = importlib.util.spec_from_file_location("protocol", _protocol_path)
_protocol = importlib.util.module_from_spec(_spec)
sys.modules["protocol"] = _protocol
_spec.loader.exec_module(_protocol)
