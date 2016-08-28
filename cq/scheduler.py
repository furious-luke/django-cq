import time
from datetime import timedelta
import logging

from django_redis import get_redis_connection
from django.utils import timezone
from django.db.utils import ProgrammingError
from django.core.cache import cache

from .models import RepeatingTask


logger = logging.getLogger('cq')


def perform_scheduling():
    with cache.lock('cq:scheduler:lock'):
        logger.debug('Checking for scheduled tasks.')
        now = timezone.now()
        try:
            rtasks = RepeatingTask.objects.filter(next_run__lte=now)
            for rt in rtasks:
                rt.submit()
        except ProgrammingError:
            logger.warning('CQ scheduler not running, DB is out of date.')


def scheduler(*args, **kwargs):
    while 1:
        conn = get_redis_connection()
        if conn.setnx('cq:scheduler', 'dummy'):
            conn.expire('cq:scheduler', 30)
            perform_scheduling()
        now = timezone.now()
        delay = ((now + timedelta(minutes=1)).replace(second=0, microsecond=0) - now).total_seconds()
        logger.debug('Waiting {} seconds for next schedule attempt.'.format(delay))
        time.sleep(delay)