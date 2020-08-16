from os import environ
from os import path
from time import sleep

import pytest
import six

from qbittorrentapi import APIConnectionError
from qbittorrentapi import Client
from qbittorrentapi.request import Request

qbt_version = 'v' + environ['QBT_VER']

api_version_map = {
    'v4.1.0': '2.0',
    'v4.1.1': '2.0.1',
    'v4.1.2': '2.0.2',
    'v4.1.3': '2.1',
    'v4.1.4': '2.1.1',
    'v4.1.5': '2.2',
    'v4.1.6': '2.2',
    'v4.1.7': '2.2',
    'v4.1.8': '2.2',
    'v4.1.9': '2.2.1',
    'v4.1.9.1': '2.2.1',
    'v4.2.0': '2.3',
    'v4.2.1': '2.4',
    'v4.2.2': '2.4.1',
    'v4.2.3': '2.4.1',
    'v4.2.4': '2.5',
    'v4.2.5': '2.5.1',
}

_check_limit = 10

_orig_torrent_url = 'http://cdimage.ubuntu.com/xubuntu/releases/18.04/release/xubuntu-18.04.1-desktop-amd64.iso.torrent'
_orig_torrent_hash = '635cbf8317ef942e8ba21ececdc7526a41b7e4b2'

torrent1_url = 'https://releases.ubuntu.com/18.04/ubuntu-18.04.5-desktop-amd64.iso.torrent'
torrent1_filename = torrent1_url.split('/')[-1]
torrent1_hash = '94a315e2cf8015b2f635d79aab592e6db557d5ea'

torrent2_url = 'https://releases.ubuntu.com/20.04/ubuntu-20.04.1-desktop-amd64.iso.torrent'
torrent2_filename = torrent2_url.split('/')[-1]
torrent2_hash = 'd1101a2b9d202811a05e8c57c557a20bf974dc8a'

is_version_less_than = Request._is_version_less_than
suppress_context = Request._suppress_context


def get_func(client, func_str):
    func = client
    for attr in func_str.split('.'):
        func = getattr(func, attr)
    return func


def check(check_func, value, reverse=False, negate=False, any=False):
    """
    Compare the return value of an arbitrary function to expected value with retries.
    Since some requests take some time to take affect in qBittorrent, the retries every second for 10 seconds.

    :param check_func: callable to generate values to check
    :param value: str, int, or iterator of values to look for
    :param reverse: False: look for check_func return in value; True: look for value in check_func return
    :param negate: False: value must be found; True: value must not be found
    :param any: False: all values must be (not) found; True: any value must be (not) found
    """
    def _do_check(_check_func_val, _v, _negate, _reverse):
        if _negate:
            if _reverse:
                assert _v not in _check_func_val
            else:
                assert _check_func_val not in (_v,)
        else:
            if _reverse:
                assert _v in _check_func_val
            else:
                assert _check_func_val in (_v,)

    if isinstance(value, (six.string_types, int)):
        value = (value,)

    try:
        for i in range(_check_limit):
            try:
                exp = None
                for v in value:
                    if any:  # clear any previous exceptions
                        exp = None

                    try:
                        check_val = check_func()  # get here so pytest includes value in failures
                        _do_check(check_val, v, negate, reverse)
                    except AssertionError as e:
                        exp = e

                    if not any and exp:  # fail the test on first failure any=False
                        break
                    if any and not exp:  # this value passed so test succeeded with any=True
                        break

                if exp:  # raise caught inner exception for handling
                    raise exp

                break  # test succeeded!!!!

            except AssertionError:
                if i >= _check_limit - 1:
                    raise
                sleep(1)
    except APIConnectionError:
        raise suppress_context(AssertionError('qBittrorrent crashed...'))


@pytest.fixture(autouse=True)
def abort_if_qbittorrent_crashes(client):
    """Abort tests if qbittorrent disappears during testing"""
    try:
        _ = client.app.version
        yield
    except APIConnectionError:
        pytest.exit('qBittorrent crashed :(')


@pytest.fixture(autouse=True)
def abort_if_qbittorrent_crashes(client):
    """Abort tests if qbittorrent disappears during testing"""
    try:
        _ = client.app.version
    except APIConnectionError:
        pytest.exit('qBittorrent crashed :(')


@pytest.fixture(scope='session')
def client():
    """qBittorrent Client for testing session"""
    try:
        client = Client(RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=True, VERBOSE_RESPONSE_LOGGING=True)
        client.auth_log_in()
        # add orig_torrent to qBittorrent
        client.torrents_add(urls=_orig_torrent_url, upload_limit=10, download_limit=10)
        return client
    except APIConnectionError:
        pytest.exit('qBittorrent was not running when tests started')


@pytest.fixture(scope='session')
def orig_torrent_hash():
    """Torrent hash for the Xubuntu torrent loaded for testing"""
    return _orig_torrent_hash


@pytest.fixture(scope='function')
def orig_torrent(client, orig_torrent_hash):
    """Torrent to remain in qBittorrent for entirety of session"""
    try:
        check(lambda: len([t for t in client.torrents_info() if t.hash == orig_torrent_hash]), value=1)
        return [t for t in client.torrents_info() if t.hash == orig_torrent_hash][0]
    except APIConnectionError:
        pytest.exit('Failed to find "orig_torrent"')


@pytest.fixture
def new_torrent(client):
    """Torrent that is added on demand to qBittorrent and then removed"""
    def add_test_torrent(client):
        client.torrents.add(urls=torrent1_url,
                            save_path=path.expanduser('~/test_download/'),
                            category='test_category', is_paused=True,
                            upload_limit=1024, download_limit=2048,
                            is_sequential_download=True, is_first_last_piece_priority=True)
        for attempt in range(_check_limit):
            try:
                # not all versions of torrents_info() support passing a hash
                return list(filter(lambda t: t.hash == torrent1_hash, client.torrents_info()))[0]
            except:
                if attempt >= _check_limit - 1:
                    raise
                sleep(1)

    def delete_test_torrent(torrent):
        torrent.delete(delete_files=True)
        check(lambda: [t.hash for t in torrent._client.torrents_info()], torrent.hash, reverse=True, negate=True)

    try:
        torrent = add_test_torrent(client)
    except APIConnectionError:
        yield None  # if qBittorrent crashed, it'll get caught in abort fixture
    else:
        yield torrent
        try:
            delete_test_torrent(torrent)
        except APIConnectionError:
            pass  # if qBittorrent crashed, it'll get caught in abort fixture


@pytest.fixture(scope='session')
def app_version():
    """qBittorrent App Version being used for testing"""
    return qbt_version


@pytest.fixture(scope='session')
def api_version():
    """qBittorrent App API Version being used for testing"""
    return api_version_map[qbt_version]


def pytest_sessionfinish(session, exitstatus):
    try:
        if 'TRAVIS' not in environ:
            client = Client()
            # remove all torrents
            for torrent in client.torrents_info():
                client.torrents_delete(delete_files=True, torrent_hashes=torrent.hash)
    except:
        pass
