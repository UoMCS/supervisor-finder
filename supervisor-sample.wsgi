import sys
import logging

sys.path.insert(0, '/path/to/supervisor-finder')
logging.basicConfig(stream=sys.stderr)

from supervisor import app as application
