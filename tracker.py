import requests
import settings


TIMEOUT = 2  # seconds


def send_location(username, lat, long):
    if not settings.TRACKER:
        raise RuntimeError('Tracking server not configured')

    data = dict(
        username=username,
        lat='{:.6f}'.format(lat),
        lon='{:.6f}'.format(long)
    )

    url = '{base_url}/api/set'.format(
        base_url=settings.TRACKER
    )

    with requests.post(url, json=data, timeout=TIMEOUT) as r:
        code = r.status_code
        if code != 200:
            raise RuntimeError('Wrong HTTP code from tracking server: {}'.format(code))
        data = r.json()
        if not data.get('error', False):
            return True
        else:
            raise RuntimeError('Got error from tracking server: {}'.format(data))
