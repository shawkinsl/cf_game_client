#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, r'/var/www/falcon/pnw_stats_finder/servlet/')
from wsgi import app as application
application.secret_key = 'SUPER SECRET WAHAHA'
