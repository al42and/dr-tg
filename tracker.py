import urllib.parse
import urllib.request
import settings


def send_location(username, lat, long, silent=True):
    if not settings.TRACKER:
        if silent:
            return False
        else:
            raise RuntimeError('Tracking server not configured')

    query = dict(
        username=username,
        lat='{:.6f}'.format(lat),
        lon='{:.6f}'.format(long)
    )

    # Not /set?, but /set/
    url = '{base_url}/set/?{query}'.format(
        base_url=settings.TRACKER,
        query=urllib.parse.urlencode(query)
    )

    with urllib.request.urlopen(url, timeout=2) as r:
        code = r.getcode()
        if code != 200:
            if silent:
                return False
            else:
                raise RuntimeError('Wrong HTTP code from tracking server: {}'.format(code))
        data = r.read()
        if data.strip() == 'ok':
            return True
        else:
            if silent:
                return False
            else:
                raise RuntimeError('Wrong data from tracking server: {}'.format(data))
