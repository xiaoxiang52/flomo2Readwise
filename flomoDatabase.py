from time import time, sleep
from notion_client import Client
from datetime import datetime, timedelta, datetime
from tenacity import retry, wait_exponential, stop_after_attempt

import os
import requests
import hashlib
import re
from typing import Any, List, Tuple
from functools import wraps

api_key = "flomo_web"
app_version = "2.0"
webp = 1
# 逆向来自 _getSign 方法, 它是一个常量
flomo_web_key = "dbbc3dd73364b4084c3a69346e0ce2b2"

match_memo_id_reg = r".*=(\S+)"


def md5value(key) -> str:
    input_name = hashlib.md5()
    input_name.update(key.encode("utf-8"))
    # create_sign 方法需要 md5 加密为 32位小写
    result = (input_name.hexdigest()).lower()
    return result

# 传递时间戳


def createSimpleObj(seed: str) -> str:
    # api_key=flomo_web&app_version=2.0&timestamp=1691246824&webp=1&
    return "api_key={}&app_version={}&timestamp={}&webp={}".format(api_key, app_version, seed, webp)

# 传递时间戳
# 逆向 _getSign 得出
# 结果需要: md5(api_key) ||| 32位小写


def createParAndSign(seed: str) -> str:
    par = createSimpleObj(seed)
    result = "{}{}".format(par, flomo_web_key)
    output = md5value(result)
    return output

# 获取 flomo 原始文章
# token 的获取方式参考: codelight.js 中的 getToken


def fetch_raw_flomo_memo_images(id: str, token: str) -> List[str]:
    # 1. 生成接口地址
    timestamp = int(time())  # 时间戳
    parBody = createSimpleObj(timestamp)
    sign = createParAndSign(timestamp)
    req_url = "https://flomoapp.com/api/v1/memo/{}?timestamp={}&api_key=flomo_web&app_version=2.0&webp=1&sign={}".format(
        id, timestamp, sign)
    auth = 'Bearer {}'.format(token)
    headers = {
        'authority': 'flomoapp.com',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://v.flomoapp.com',
        'referer': 'https://v.flomoapp.com/',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'authorization': auth,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    }
    # 2. 请求该接口
    resp = requests.get(req_url, headers=headers)
    # 3. 返回内容中有一个 files 字段, 如果有附件的话(只要拿图片的可以过滤一下只要 type == image)则拿到所有附件的 url
    # 接口类型参考: https://note.ms/python2
    rawResp = resp.json()
    files: List[dict] = rawResp["data"]["files"]
    result: List[str] = []
    if (len(files) >= 1):
        # TODO: 过滤一下只要 type == image 的
        for item in files:
            # item['type'] == 'image'
            real_image = item['url']
            result.append(real_image)
    return result

# 将图片链接转为图片Markdown标记


def image_to_markdown(images: List[str]):
    result: str = ""
    for item in images:
        result += "![]({})\n".format(item)
    return result

# 自动将附件添加到内容后面
# 需要传递 id, sign, token


def easy_append_images_to_memo(content: str, id: str, token: str) -> Tuple[str, List[str], int]:
    images = fetch_raw_flomo_memo_images(id, token)
    _len = len(images)
    if _len <= 0:
        return content, [], 0
    append_content = image_to_markdown(images)
    result = "{}\n{}".format(content, append_content)
    return result, images, _len

# if __name__ == "__main__":
#     content = "hello world\n balbala"
#     pull_data, _, _ = easy_append_images_to_memo("demo hello ", "Nzc2NjY1NTQ", "2468903|EkSoszB0ItF3DJjunaobwaoYdRMQHKDE9FnOAZ6x")
#     print(pull_data)

# copy by https://gist.github.com/ChrisTM/5834503?permalink_comment_id=2005466#gistcomment-2005466
# def throttle(seconds=0, minutes=0, hours=0):
#     throttle_period = timedelta(seconds=seconds, minutes=minutes, hours=hours)
#     def throttle_decorator(fn):
#         time_of_last_call = datetime.min
#         @wraps(fn)
#         def wrapper(*args, **kwargs):
#             now = datetime.now()
#             if now - time_of_last_call > throttle_period:
#                 nonlocal time_of_last_call
#                 time_of_last_call = now
#                 return fn(*args, **kwargs)
#         return wrapper
#     return throttle_decorator


class FastFetchRawMemoDatabase:
    def __init__(self):
        self.dict = set()
        self.filename = "raw_memo.txt"
        # TODO: 写入太频繁
        # self.saveFn = throttle(seconds=2)

    def fetch_KV_with_local(self) -> List[str]:
        try:
            name = self.filename
            if not os.path.exists(name):
                return []
            with open(name, 'r') as f:
                pipe: List[str] = f.read().split("\n")
                return pipe
        except Exception:
            print("本地文件 raw_memo 不存在")
            return []

    # TODO: 实现初始化方法
    # 1. 通过 \n 读取本地的 raw_memo.txt 文件
    # 2. 将数组添加到存储缓存里
    def init(self):
        text = self.fetch_KV_with_local()
        _len = len(text)
        if len(text) >= 1:
            for item in text:
                result = item.strip()
                if len(result) >= 1:
                    self.dict.add(item)
        print("从缓存取出(raw_memo.txt): {}".format(_len))

    def has(self, id: str) -> bool:
        return self.dict.__contains__(id)

    def save(self) -> bool:
        print("try to be save(local): {}".format(int(time())))
        if len(self.dict) <= 0:
            return False
        result = '\n'.join(list(self.dict))
        if len(result) <= 0:
            return False
        with open(self.filename, 'w') as f:
            f.write(result)
        return True

    def add(self, id: str) -> str:
        self.dict.add(id)
        self.save()
        return id


class FlomoDatabase:
    def __init__(self, api_key, database_id, logger, update_tags=True, skip_tags=['', 'welcome']):
        self.notion = Client(auth=api_key)
        self.database_id = database_id
        self.logger = logger
        self.update_tags = update_tags
        self.skip_tags = skip_tags
        # 这里暂时直接从环境变量拿吧
        self.memo_token = os.getenv(
            'MEMO_TOKEN', '2495049|a3xCeTtKHBYC7gjLnMzsl2IIibcymClyPdGkbaaE')
        self.fastKV = FastFetchRawMemoDatabase()
        self.fastKV.init()

    def fetch_flomo_memos(self, callback, last_sync_time=None):
        start_time = time()
        all_memos = []
        # get 100 pages at a time
        result_list: Any = self.notion.databases.query(self.database_id)
        while result_list:
            # save content of each page
            for page in result_list['results']:
                flomo_memo = self.fetch_flomo_memo(
                    page, last_sync_time=last_sync_time)
                if flomo_memo:
                    all_memos.append(flomo_memo)
                    if len(all_memos) % 10 == 0:
                        print("进行中")
            while len(all_memos) > 0:
                # 打印列表的前20个元素
                data_len = len(all_memos) if len(all_memos) < 20 else 20
                callback(all_memos[:data_len])
                del all_memos[:data_len]
                print("使用时间:", time()-start_time)
            # get next 100 pages, until no more pages
            if "next_cursor" in result_list and result_list["next_cursor"]:
                result_list = self.notion.databases.query(
                    self.database_id, start_cursor=result_list["next_cursor"])
            else:
                break
        return all_memos

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(5))
    def fetch_flomo_memo(self, page, last_sync_time=None):
        # Skip pages edited before last_sync_time
        # format: '2023-04-17T00:00:00.000Z' and it's UTC time
        last_edit_time_str = page['last_edited_time']
        last_edit_time = datetime.strptime(
            last_edit_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        if last_sync_time and last_edit_time < last_sync_time:
            return None

        # Get tags, which are separated by slash in flomo
        tags = self.fetch_and_seperate_tags(page)
        for skip_tag in self.skip_tags:
            if skip_tag == '' and len(tags) == 0:
                return None
            if skip_tag in tags:
                return None

        # Store seperated tags as a new Multi-select property in Notion
        if self.update_tags:
            self.update_seperated_tags(page, tags)

        # Get content text, flomo memo has only one block
        page_blocks = self.notion.blocks.children.list(page['id'])
        text_content = page_blocks['results'][0]['paragraph']['rich_text'][0]['plain_text']

        raw_url: str = page['properties']['Link']['url']

        flomo_memo = {
            'tags':			tags,
            'flomo_url':	raw_url,
            'edit_time':	last_edit_time_str,
            'text':			text_content
        }

        if "得到" in tags:
            memo = self.parse_dedao_content(tags, text_content)
            flomo_memo.update(memo)

        memo_id: str = re.search(match_memo_id_reg, raw_url).group(1)
        if not self.fastKV.has(memo_id):
            try:
                apply_raw_memo_content, context_image, has_image = easy_append_images_to_memo(
                    flomo_memo['text'], memo_id, self.memo_token)
                if has_image:
                    print("从原memo提取附件成功: {}".format(memo_id))
                    flomo_memo['text'] = apply_raw_memo_content
                else:
                    print("原memo不存在附件: {}".format(memo_id))
                self.fastKV.add(memo_id)
            except Exception:
                # FIXME: 可能是 token 过期了, 或者接口返回太频繁了
                print("从原memo提取附件失败: {}".format(memo_id))
                sleep(3)

        if flomo_memo['text'] == '':
            return None

        return flomo_memo

    """ Tools """

    def test_connection(self):
        # Need 'Read user information' permission in Notion Integration
        list_users_response = self.notion.users.list()
        self.logger.log(list_users_response)

    def fetch_and_seperate_tags(self, page):
        # Get tags, which are separated by slash in flomo
        tags_property = page['properties']['Tags']['multi_select']
        if len(tags_property) == 0:
            return []
        tags_slashs = [tag['name'] for tag in tags_property]
        tags = []
        for tags_slash in tags_slashs:
            tags += tags_slash.split('/')
        return tags

    def update_seperated_tags(self, page, tags):
        # add new property to the database if not exist
        if 'Seperated Tags' not in page['properties']:
            self.add_multi_select_property('Seperated Tags')
        # update property if not match
        st = page['properties']['Seperated Tags']['multi_select']
        if len(st) != len(tags) or not all([st[i]['name'] == tags[i] for i in range(len(tags))]):
            self.notion.pages.update(page['id'], properties={
                'Seperated Tags': {
                    'multi_select': [{'name': tag} for tag in tags]
                }
            })

    def add_multi_select_property(self, property_name, options=[]):
        # Get the database schema
        database = self.notion.databases.retrieve(self.database_id)
        properties = database['properties']
        # Check if the property already exists
        if property_name in properties:
            return
        # Add the property
        properties[property_name] = {
            'type': 'multi_select',
            'multi_select': {
                    'options': options
            }
        }
        # Update the database schema
        self.notion.databases.update(self.database_id, properties=properties)

    def parse_dedao_content(self, tags, text):
        all_tags = '_'.join(tags)
        # category
        category = None
        if '电子书' in all_tags:
            category = 'books'
        elif '课程' in all_tags:
            category = 'podcasts'
        elif '其他' in all_tags:
            category = 'podcasts'
        elif '城邦' in all_tags:
            category = 'tweets'
        # author
        author = None
        author_list = ['万维钢', '卓克', '刘擎', '刘嘉', '何帆', '吴军', '刘润',
                       '薛兆丰', '林楚方', '徐弃郁', '施展', '王立铭', '薄世宁',
                       '王煜全', '香帅', '冯雪', '贾宁', '李筠', '梁宁', '刘苏里']
        if category == 'podcasts':
            for author_name in author_list:
                if author_name in all_tags:
                    author = author_name
                    break
        # text
        # remove the first line, which is tags
        # remove the last two lines, which is "来源：https://dedao.cn"
        text = text.split('\n')
        title = text[0].split('/')[-1]
        text = text[1:-2]
        text = '\n'.join(text)
        # return as a dict
        return {
            'text': text,
            'title': title,
            'author': author,
            'category': category
        }