# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | 公共函数类
# +-------------------------------------------------------------------
# | Author: 李小恩 <i@abcyun.cc>
# +-------------------------------------------------------------------
import hashlib
import json
import os
import random
import sys
import threading
import time
from xml.dom.minidom import parseString

LOCK = threading.Lock()
DATA = {
    'config': {},
    'folder_id_dict': {},
    'tasks': {}
}
# 历史上传视频成功数
MVHISTORYCONT = 0
# 本次抓取视频需要上传数量
MVUPLOADCOUNT = 0


# 处理路径
def qualify_path(path):
    if not path:
        return ''
    return path.replace('/', os.sep).replace('\\\\', os.sep).rstrip(os.sep) + os.sep


# 获取运行目录
def get_running_path(path=''):
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable) + path
    elif __file__:
        return os.path.dirname(__file__) + path


def get_hash(filepath, block_size=2 * 1024 * 1024):
    with open(filepath, 'rb') as f:
        sha1 = hashlib.sha1()
        while True:
            data = f.read(block_size)
            if not data:
                break
            sha1.update(data)
        return sha1.hexdigest()


def get_all_file(path):
    result = []
    get_dir = os.listdir(path)
    for i in get_dir:
        sub_dir = os.path.join(path, i)
        if os.path.isdir(sub_dir):
            result.extend(get_all_file(sub_dir))
        else:
            result.append(sub_dir)
    return result


def get_all_file_relative(path):
    result = []
    get_dir = os.listdir(path)
    for i in get_dir:
        sub_dir = os.path.join(path, i)
        if os.path.isdir(sub_dir):
            all_file = get_all_file_relative(sub_dir)
            all_file = map(lambda x: i + os.sep + x, all_file)
            result.extend(all_file)
        else:
            result.append(i)
    return result


def print_info(message):
    i = random.randint(34, 37)
    log(message)
    print('\033[7;30;{i}m{message}\033[0m'.format(message=message, i=i))


def print_warn(message):
    log(message)
    print('\033[7;30;33m{message}\033[0m'.format(message=message))


def print_error(message):
    log(message)
    print('\033[7;30;31m{message}\033[0m'.format(message=message))


def print_success(message):
    log(message)
    print('\033[7;30;32m{message}\033[0m'.format(message=message))


def date(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def log(message):
    file = get_running_path('/log/' + time.strftime("%Y-%m-%d", time.localtime()) + '.log')
    if not os.path.exists(os.path.dirname(file)):
        os.mkdir(os.path.dirname(file))
    with open(file, 'a') as f:
        f.write('【{date}】{message}\n'.format(date=date(time.time()), message=message))


def get_xml_tag_value(xml_string, tag_name):
    DOMTree = parseString(xml_string)
    DOMTree = DOMTree.documentElement
    tag = DOMTree.getElementsByTagName(tag_name)
    if len(tag) > 0:
        for node in tag[0].childNodes:
            if node.nodeType == node.TEXT_NODE:
                return node.data
    return False


def load_task():
    LOCK.acquire()
    try:
        with open(get_running_path('/tasks.json'), 'rb') as f:
            task = f.read().decode('utf-8')
            return json.loads(task)
    except Exception:
        return {}
    finally:
        LOCK.release()


def save_task(task):
    LOCK.acquire()
    try:
        with open(get_running_path('/tasks.json'), 'w') as f:
            f.write(json.dumps(task))
            f.flush()
    finally:
        LOCK.release()


def load_mv_ids():
    """ 读取保存视频id """
    LOCK.acquire()
    try:
        upload_ids_path = get_running_path('/upload_ids.txt')
        ids = []
        if os.path.exists(upload_ids_path):
            with open(upload_ids_path, 'rb') as f:
                values = f.read().decode('utf-8')
                values = values.replace('\n', '')
                values = values.replace(' ', '')
                ids = values.split(",")
        global MVHISTORYCONT
        MVHISTORYCONT = len(ids)
        return ids
    finally:
        LOCK.release()


def save_mv_id(mv_id):
    """ 保存视频id，用于上传成功记录 """
    LOCK.acquire()
    try:
        upload_ids_path = get_running_path('/upload_ids.txt')
        ids = []
        if os.path.exists(upload_ids_path):
            with open(upload_ids_path, 'rb') as f:
                ids = f.read().decode('utf-8').split(",")
        ids.insert(0, mv_id)
        with open(upload_ids_path, 'w') as f:
            f.write(','.join(ids))
            f.flush()

        global MVHISTORYCONT
        global MVUPLOADCOUNT
        print_info('{}/{}: {}上传成功.'.format((len(ids) - MVHISTORYCONT), MVUPLOADCOUNT, mv_id))
    finally:
        LOCK.release()


def read_in_chunks(file_object, chunk_size=16 * 1024, total_size=10 * 1024 * 1024):
    load_size = 0
    while True:
        if load_size >= total_size:
            break
        data = file_object.read(chunk_size)
        if not data:
            break
        load_size += 16 * 1024
        yield data
