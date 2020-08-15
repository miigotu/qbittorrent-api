from time import sleep

import pytest

from qbittorrentapi.rss import RSSitemsDictionary
from tests.conftest import is_version_less_than, check, get_func

folder_one = 'testFolderOne'
folder_two = 'testFolderTwo'

item_one = 'YTS1080p'
item_two = 'YTS1080pNew'
url = 'https://yts.mx/rss/'


@pytest.mark.parametrize('client_func', (('rss_add_folder', 'rss_remove_item', 'rss_items'),
                                         ('rss.add_folder', 'rss.remove_item', 'rss.items')))
def test_add_remove_folder(client, client_func):
    get_func(client, client_func[0])(folder_path=folder_one)  # rss_add_folder
    check(lambda: client.rss_items(), folder_one, reverse=True)
    get_func(client, client_func[1])(item_path=folder_one)  # rss_remove_item
    check(lambda: get_func(client, client_func[2])(), folder_one, reverse=True, negate=True)  # rss_items


@pytest.mark.parametrize('client_func',
                         (('rss_add_feed', 'rss_move_item', 'rss_refresh_item', 'rss_items', 'rss_mark_as_read', 'rss_remove_item'),
                          ('rss.add_feed', 'rss.move_item', 'rss.refresh_item', 'rss.items', 'rss.mark_as_read', 'rss.remove_item')))
def test_add_move_refresh_remove_feed(client, api_version, client_func):
    try:
        get_func(client, client_func[0])(item_path=item_one, url=url)  # rss_add_feed
        check(lambda: get_func(client, client_func[3])(), item_one, reverse=True)  # rss_items
        get_func(client, client_func[1])(orig_item_path=item_one, new_item_path=item_two)  # rss_move_item
        check(lambda: get_func(client, client_func[3])(), item_two, reverse=True)  # rss_items

        # update item_two
        if is_version_less_than(api_version, '2.2', lteq=False):
            with pytest.raises(NotImplementedError):
                get_func(client, client_func[2])(item_path=item_two)  # rss_refresh_item
        else:
            get_func(client, client_func[2])(item_path=item_two)  # rss_refresh_item
            # wait until the rss feed refresh is done
            check(lambda: client.rss_items(), item_two, reverse=True)
            check(lambda: client.rss_items(include_feed_data=True)[item_two], 'articles', reverse=True)
            check(lambda: bool(client.rss_items(include_feed_data=True)[item_two]['articles']), True)

        items = get_func(client, client_func[3])(include_feed_data=True)  # rss_items
        assert isinstance(items, RSSitemsDictionary)
        try:
            items = getattr(get_func(client, client_func[3]), 'without_data')  # rss_items
            assert isinstance(items, RSSitemsDictionary)
            items = getattr(get_func(client, client_func[3]), 'with_data')  # rss_items
            assert isinstance(items, RSSitemsDictionary)
        except AttributeError:
            pass

        if is_version_less_than(api_version, '2.5.1', lteq=False):
            with pytest.raises(NotImplementedError):
                get_func(client, client_func[4])()  # rss_mark_as_read
        else:
            items = client.rss_items(include_feed_data=True)  # rss_items
            # if items[item_two]['articles']:
            get_func(client, client_func[4])(item_path=item_two, article_id=items[item_two]['articles'][0])  # rss_mark_as_read
    finally:
        get_func(client, client_func[5])(item_path=item_two)  # rss_remove_item
        check(lambda: get_func(client, client_func[3])(), item_two, reverse=True, negate=True)  # rss_items


@pytest.mark.parametrize('client_func',
                         (('rss_add_feed', 'rss_set_rule', 'rss_rules', 'rss_rename_rule', 'rss_matching_articles', 'rss_remove_rule', 'rss_remove_item'),
                          ('rss.add_feed', 'rss.set_rule', 'rss.rules', 'rss.rename_rule', 'rss.matching_articles', 'rss.remove_rule', 'rss.remove_item')))
def test_rules(client, api_version, client_func):
    rule_name = item_one + 'Rule'
    rule_name_new = rule_name + 'New'
    rule_def = {'enabled': True,
                'affectedFeeds': url,
                'addPaused': True}
    try:
        get_func(client, client_func[0])(item_path=item_one, url=url)  # rss_add_feed
        if is_version_less_than(api_version, '2.2', lteq=False):
            with pytest.raises(NotImplementedError):
                client.rss.refresh_item(item_path=item_two)
        else:
            client.rss.refresh_item(item_path=item_two)
        get_func(client, client_func[1])(rule_name=rule_name, rule_def=rule_def)  # rss_set_rule
        try:
            get_func(client, client_func[2])()  # rss_rules
            check(lambda: get_func(client, client_func[2])(), rule_name, reverse=True)  # rss_rules
        except TypeError:
            check(lambda: get_func(client, client_func[2]), rule_name, reverse=True)  # rss_rules
        # rename is broken https://github.com/qbittorrent/qBittorrent/issues/12558
        # get_func(client, client_func[3])(orig_rule_name=rule_name, new_rule_name=rule_name_new)
        # check(get_func(client, client_func[2]), rule_name_new, reverse=True)
        if is_version_less_than(api_version, '2.5.1', lteq=False):
            with pytest.raises(NotImplementedError):
                get_func(client, client_func[4])(rule_name=rule_name)  # rss_matching_articles
        else:
            assert isinstance(get_func(client, client_func[4])(rule_name=rule_name), RSSitemsDictionary)  # rss_matching_articles
    finally:
        get_func(client, client_func[5])(rule_name=rule_name)  # rss_remove_rule
        check(lambda: client.rss_rules(), rule_name, reverse=True, negate=True)
        get_func(client, client_func[6])(item_path=item_one)  # rss_remove_item
        assert item_two not in client.rss_items()
        check(lambda: client.rss_items(), item_two, reverse=True, negate=True)
