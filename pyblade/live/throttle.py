"""Keeping one client from taking the live endpoints for itself.

Every live component answers on the same two endpoints, and a page only has to
be loaded once to hand a browser a snapshot it can send back as often as it
likes. Nothing about a live component stops a script doing exactly that, so
what is here does:

    - a client may only ask so often, per endpoint, per stretch of time;
    - a request may only be so big before it is read at all;
    - only so many streamed actions may run at once, each being a thread.

What it cannot do is stand in front of a distributed attack: by the time a
request reaches Django it has already cost a connection and a worker. That is
the business of whatever stands in front of the application -- a load balancer,
a CDN, a firewall. This is about the cheap abuse an application can see, and
about PyBlade not handing anyone a lever longer than the one they came with.

Everything is read from pyblade.toml, under [live.throttle], and can be
switched off there:

    [live.throttle]
    actions = "120/minute"
    uploads = "20/minute"

The counts are kept in Django's cache. The default one lives in the memory of
each process, so a project run on several workers counts per worker until it is
given a shared cache -- Redis or Memcached -- which is what a site that cares
about this has anyway.
"""

import re
import threading
import time
from functools import wraps

from pyblade.config import DEFAULTS as _SCHEMA
from pyblade.config import config

#: What a project gets without saying anything, kept with the rest of the schema
DEFAULTS = _SCHEMA["live_components"]["throttle"]

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_RATE = re.compile(r"^\s*(\d+)\s*/\s*(second|minute|hour|day)s?\s*$", re.IGNORECASE)

_SIZE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(b|kb|mb|gb)?\s*$", re.IGNORECASE)
_UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3}


def _now():
    """The time, asked for here so that a test can say what it is."""
    return time.time()


def option(name):
    """What the project says about one part of this, or what it gets without saying."""
    return config.live_components.throttle.get(name, DEFAULTS[name])


def parse_rate(rate):
    """A rate written the way people write one: '120/minute' -> (120, 60)."""
    match = _RATE.match(str(rate))
    if not match:
        raise ValueError(f"'{rate}' is not a rate. Write it as '120/minute', '5/second', '1000/hour'...")

    count, period = match.groups()

    return int(count), _PERIODS[period.lower()]


def parse_size(size):
    """A size written the way people write one: '1mb' -> 1048576."""
    if isinstance(size, int):
        return size

    match = _SIZE.match(str(size))
    if not match:
        raise ValueError(f"'{size}' is not a size. Write it as a number of bytes, or as '500kb', '1mb'...")

    amount, unit = match.groups()

    return int(float(amount) * _UNITS[(unit or "b").lower()])


def client_of(request):
    """Who is asking, as far as counting their requests goes.

    Someone signed in is counted as themselves, wherever they are asking from.
    Anyone else is counted by address -- the address the connection came from,
    unless the project says it sits behind a proxy it trusts, in which case the
    one the proxy says it forwarded. Trusting that header without a proxy that
    sets it would let every request name itself something new.
    """
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        return f"user:{user.pk}"

    if option("trust_forwarded"):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

    return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"


def hit(scope, request):
    """Count a request, and answer whether it is one too many.

    Answers how many seconds to wait before asking again, or None if the request
    may go ahead. The count is kept per stretch of time rather than as a sliding
    window: simple, the same on every cache there is, and a client right at the
    edge of one stretch gets at most twice the rate for a moment -- which is not
    what this is here to stop.
    """
    from django.core.cache import cache

    limit, period = parse_rate(option(scope))

    now = _now()
    stretch = int(now // period)
    key = f"pyblade:throttle:{scope}:{client_of(request)}:{stretch}"

    # add() only sets what is not there yet, so two requests arriving together
    # do not both start the count at zero
    cache.add(key, 0, timeout=period + 1)

    try:
        count = cache.incr(key)
    except ValueError:
        # The count ran out between the two lines above; this is the first again
        cache.set(key, 1, timeout=period + 1)
        count = 1

    if count <= limit:
        return None

    return max(1, int((stretch + 1) * period - now))


def too_big(request):
    """Whether a request says it is bigger than the project allows, before it is read.

    Taken from what the request says of itself rather than by reading it, so a
    body that is too big is never read into memory in the first place. Django
    refuses bodies over DATA_UPLOAD_MAX_MEMORY_SIZE on its own; this is the
    smaller limit an answer to a live component ever needs.
    """
    try:
        length = int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return True

    return length > parse_size(option("max_body"))


def throttled(scope, check_size=True):
    """Refuse a request to a live endpoint from a client asking too often.

        @throttled("actions")
        def update_component(request): ...

    A refused request is answered 429, with how long to wait in Retry-After, so
    that a client written to respect it -- PyBlade's own is -- stops asking.
    """

    def decorator(view):
        @wraps(view)
        def guarded(request, *args, **kwargs):
            from django.http import JsonResponse

            if not option("enabled"):
                return view(request, *args, **kwargs)

            if check_size and too_big(request):
                return JsonResponse({"error": "This request is too large."}, status=413)

            wait = hit(scope, request)
            if wait is not None:
                response = JsonResponse(
                    {"error": "Too many requests. Wait a moment before trying again."},
                    status=429,
                )
                response["Retry-After"] = str(wait)
                return response

            return view(request, *args, **kwargs)

        return guarded

    return decorator


class _StreamSlots:
    """How many streamed actions may run at once.

    A streamed action runs on a thread of its own, for as long as it runs. Left
    alone, each request for one would start another thread, and a client that
    asked for enough of them at once would run the server out of threads long
    before it ran out of anything else.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._running = 0

    def take(self):
        """Take a slot, or answer False if there is none free."""
        with self._lock:
            if self._running >= int(option("max_streams")):
                return False

            self._running += 1
            return True

    def give_back(self):
        with self._lock:
            self._running = max(0, self._running - 1)

    @property
    def running(self):
        return self._running


stream_slots = _StreamSlots()
