import datetime
import json
import time
import os
import pytz
import requests
from bs4 import BeautifulSoup as bs
import sys

FETCH_LOG = "tweet.log"
FETCH_SAVE_LOG = "tweet_fetch.log"

def print_log(msg_str):
  y4m2d2, hms = get_now(date_slicer="-", time_slicer=":")
  with open(FETCH_LOG, "a+") as f:
    msg_str = "[{} {}] {}".format(y4m2d2, hms, msg_str)
    print(msg_str)
    print(msg_str, file=f)
  f.close()

def get_now(tz="Etc/GMT", date_slicer="", time_slicer=":"):
  now = datetime.datetime.now(pytz.timezone(tz))
  y4m2d2 = str(int(now.year * 10000 + now.month * 100 + now.day))
  y4m2d2 = "{1}{0}{2}{0}{3}".format(date_slicer, y4m2d2[:4], y4m2d2[4:6], y4m2d2[6:])
  hhmmss = "{0:0=2d}{1:0=2d}{2:0=2d}".format(now.hour, now.minute, now.second)
  hhmmss = "{1}{0}{2}{0}{3}".format(time_slicer, hhmmss[:2], hhmmss[2:4], hhmmss[4:])
  return y4m2d2, hhmmss

def ts2dt(ts):
  return datetime.datetime.fromtimestamp(float(ts))

def get_sys_gmt():
  t0 = datetime.datetime.now(tz=pytz.UTC)
  sys_t = datetime.datetime.now()
  h_delta = sys_t.hour - t0.hour
  day_offset = 0 if t0.day == sys_t.day else 24 if sys_t.day > t0.day else -24
  gmt = h_delta + day_offset
  return gmt

class TweetSearchAdvanced:
  def __init__(self, fetch_max_position=None):
    self._header = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:54.0) Gecko/20100101 Firefox/54.0",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US;q=0.3",
                    "Upgrade-Insecure-Requests": "1"}
    self._url_host = "https://twitter.com/search"

    self.contain_all_of_these_words_in_list = list()
    self.contain_this_exact_phrase = ""
    self.contain_any_of_these_word_in_list = list()
    self.contain_any_of_these_tags_in_list = list()
    self.none_of_these_words_in_list = list()
    self.sent_from_any_of_these_accounts_in_list = list()
    self.sent_to_any_of_these_accounts_in_list = list()
    self.mentioning_any_of_these_accounts_in_list = list()
    self.near_this_location = ""
    self.from_date = ""
    self.to_date = ""
    self.language = ""

    self.fetch_max_position = fetch_max_position
    self.get_tweet_num = 0

  def set_lang(self, lang):
    self.language = lang  # type(lang) is str

  def set_contain_exact_phrase(self, phrase):
    self.contain_this_exact_phrase = phrase  # type(phrase) is str

  def set_near_location(self, location_str, distance=15):
    self.near_this_location = 'near:"{}" within:{}mi'.format(location_str, distance)

  def set_from_date(self, yyyymmdd):
    # e.g. yyyymmdd = "20170720"
    self.from_date = "since:{}-{}-{}".format(yyyymmdd[:4], yyyymmdd[4:6], yyyymmdd[6:])

  def set_to_date(self, yyyymmdd):
    # e.g. yyyymmdd = "20170720"
    self.to_date = "until:{}-{}-{}".format(yyyymmdd[:4], yyyymmdd[4:6], yyyymmdd[6:])

  def add_word_to_contain_all(self, word):
    self.contain_all_of_these_words_in_list.append(word)

  def add_word_to_contain_any(self, word):
    self.contain_any_of_these_word_in_list.append(word)

  def add_word_to_contain_tag(self, word):
    self.contain_any_of_these_tags_in_list.append(word)

  def add_word_to_exclude(self, word):
    self.none_of_these_words_in_list.append(word)

  def add_to_from_accounts(self, account):
    self.sent_from_any_of_these_accounts_in_list.append(account)

  def add_to_to_accounts(self, account):
    self.sent_to_any_of_these_accounts_in_list.append(account)

  def add_to_mentioning_accounts(self, account):
    self.mentioning_any_of_these_accounts_in_list.append(account)

  def _get_query_list(self):
    query_list = list()
    if len(self.contain_all_of_these_words_in_list) > 0:
      query_list.append(" ".join(self.contain_all_of_these_words_in_list))

    if len(self.contain_this_exact_phrase) > 0:
      query_list.append('"{}"'.format(self.contain_this_exact_phrase))

    if len(self.contain_any_of_these_word_in_list) > 0:
      query_list.append(" OR ".join(self.contain_any_of_these_word_in_list))

    if len(self.none_of_these_words_in_list) > 0:
      query_list.append(" ".join(["-{}".format(i) for i in self.none_of_these_words_in_list]))

    if len(self.contain_any_of_these_tags_in_list) > 0:
      query_list.append(" OR ".join(["#{}".format(i) for i in self.contain_any_of_these_tags_in_list]))

    if len(self.sent_from_any_of_these_accounts_in_list) > 0:
      query_list.append(" OR ".join(["from:{}".format(i) for i in self.sent_from_any_of_these_accounts_in_list]))

    if len(self.sent_to_any_of_these_accounts_in_list) > 0:
      query_list.append(" OR ".join(["to:{}".format(i) for i in self.sent_to_any_of_these_accounts_in_list]))

    if len(self.mentioning_any_of_these_accounts_in_list) > 0:
      query_list.append(" OR ".join(["@{}".format(i) for i in self.sent_to_any_of_these_accounts_in_list]))

    if len(self.near_this_location) > 0:
      query_list.append(self.near_this_location)

    if len(self.from_date) > 0:
      query_list.append(self.from_date)

    if len(self.to_date) > 0:
      query_list.append(self.to_date)
    return query_list

  def _get_url(self):
    url_query = "q={}".format(" ".join(self._get_query_list()))
    if self.fetch_max_position is None:
      url_host = "https://twitter.com/search?"
      url = url_host + url_query
    else:
      url_host = "https://twitter.com/i/search/timeline?"
      sys_params = "vertical=default&include_available_features=1&include_entities=1"
      url = url_host+sys_params+"&{}&max_position={}".format(url_query, self.fetch_max_position)
    if len(self.language) > 0:
         url += "&l={}".format(self.language)
    return url

  def fetch_tweets(self):
    if self.fetch_max_position is None:
      gmt0_dt, content_list = self._first_fetch_tweet()
    else:
      gmt0_dt, content_list = self._fetch_next()
    return gmt0_dt, content_list

  def _first_fetch_tweet(self):
    gmt0_dt, content_list = None, list()
    try:
      url, header = self._get_url(), self._header
      resp_cont = requests.get(url, headers=header).content
      print_log("Will Req [{}]".format(url))
      soup = bs(resp_cont, "html.parser")
      div = soup.find(attrs={"id": "timeline"}).find(attrs={"class": "stream-container"})
      self.fetch_max_position = div.get("data-max-position")
      for li in soup.find_all("li", attrs={"class": "stream-item"}):
        tweet_div = li.find("div", attrs={"class": "tweet"})
        self.get_tweet_num += 1
        gmt0_dt, content = parse_tweet_div(tweet_div)
        content_list.append(content)
    except Exception as e:
      print_log("First Request Error. {}".format(e))
    return gmt0_dt, content_list

  def _fetch_next(self):
    gmt0_dt, content_list = None, list()
    try:
      url, header = self._get_url(), self._header
      print_log("Will Req [{}]".format(url))
      resp_cont = requests.get(url, headers=header).text
      res_dict = json.loads(resp_cont)
      self.fetch_max_position = res_dict["min_position"]
      soup = bs(res_dict["items_html"], "html.parser")
      for li in soup.find_all("li", attrs={"class": "stream-item"}):
        tweet_div = li.find("div", attrs={"class": "tweet"})
        self.get_tweet_num += 1
        gmt0_dt, content = parse_tweet_div(tweet_div)
        content_list.append(content)
    except Exception as e:
      print_log("First Request Error. {}".format(e))
    return gmt0_dt, content_list

def parse_tweet_div(tweet_div):
  tweet_url = "https://twitter.com/" + tweet_div.get("data-permalink-path")
  tweet_id = tweet_div.get("data-tweet-id")
  author_show_name = tweet_div.get("data-name")
  author_page_url = "https://twitter.com/" + tweet_div.get("data-screen-name")

  # tweet send 2 time-information, post_local_dt = post's location time. post_system_time_ts = post_local_dt convert to fetch machine time.
  time_a = tweet_div.find(attrs={"class": "tweet-timestamp"})
  # post_local_dt = datetime.datetime.strptime(time_a.get("title"), "%I:%M %p - %d %b %Y")

  post_system_time_ts = int(time_a.find("span").get("data-time"))
  gmt0_ts = post_system_time_ts - get_sys_gmt() * 3600
  gmt0_dt = ts2dt(ts=gmt0_ts)

  # post_local_time_str = post_local_dt.strftime("%Y-%m-%d %H:%M")
  gmt0_time_str = gmt0_dt.strftime("%Y-%m-%d %H:%M+00:00")

  tweet_content = tweet_div.find("p", attrs={"class": "tweet-text"}).text
  reply_num = tweet_div.find(attrs={"class", "ProfileTweet-action--reply"}).find(attrs={"class": "ProfileTweet-actionCount"}).get("data-tweet-stat-count", 0)
  like_num = tweet_div.find(attrs={"class", "ProfileTweet-action--favorite"}).find(attrs={"class": "ProfileTweet-actionCount"}).get("data-tweet-stat-count", 0)

  hash_tag_list = tweet_div.find_all("a", attrs={"class": "twitter-hashtag"})
  hash_tags = "" if len(hash_tag_list) == 0 else ",".join([tag_a.text.replace("#", "") for tag_a in hash_tag_list])
  content_dict = dict()

  content_dict["id"] = "tweet_{}".format(tweet_id)
  content_dict["author"] = author_show_name
  content_dict["link"] = tweet_url
  content_dict["timestamp"] = gmt0_time_str  # gmt0 timezone, "%Y-%m-%d %H:%M%z"
  content_dict["ts"] = int(gmt0_ts)          # gmt0 timezone
  content_dict["ts_tz"] = "Etc/GMT"
  content_dict["title"] = tweet_content
  content_dict["body"] = tweet_content

  # additional
  content_dict["like_num"] = int(like_num)
  content_dict["reply_num"] = int(reply_num)
  content_dict["author_link"] = author_page_url
  content_dict["tags"] = hash_tags  # "tag1,tag2,tag3"
  return gmt0_dt, content_dict


def main(from_date, to_date):
  fetch_max_position = None
  if os.path.exists(FETCH_SAVE_LOG):
    with open(FETCH_SAVE_LOG, "r") as f:
      fetch_max_position = f.readlines()[0]
  tsa = TweetSearchAdvanced(fetch_max_position=fetch_max_position)

  # add some key word
  tsa.add_word_to_contain_any("iphone")
  tsa.add_word_to_contain_any("ipad")
  tsa.set_lang("en")
  tsa.set_from_date(from_date)
  tsa.set_to_date(to_date)

  # start to fetch
  stop_fetch = False
  while not stop_fetch:
    last_dt, tweet_list = tsa.fetch_tweets()
    print_log("{}".format(last_dt))
    for tweet in tweet_list:
      print(tweet["body"])
    stop_fetch = len(tweet_list) == 0  # no more tweet.
    with open(FETCH_SAVE_LOG, "w+") as f:
      f.write(tsa.fetch_max_position)
    time.sleep(0.5)

if __name__ == '__main__':
  assert len(sys.argv) == 3, "python advanced_fetcher.py 20170101 20170120"
  s_y4m2d2, e_y4m2d2 = sys.argv[1], sys.argv[2]
  main(s_y4m2d2, e_y4m2d2)
