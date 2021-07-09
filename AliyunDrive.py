# -*- coding: utf-8 -*-
# +-------------------------------------------------------------------
# | 阿里云盘上传类
# +-------------------------------------------------------------------
# | Author: 李小恩 <i@abcyun.cc>
# +-------------------------------------------------------------------
import json
import math
import os
import sys
import time
import requests
from hashlib import sha1
from tqdm import tqdm
import Common
from Common import LOCK, DATA, print_info, get_running_path, print_error, print_success, print_warn, save_mv_id

requests.packages.urllib3.disable_warnings()


class AliyunDrive:
    def __init__(self, drive_id, mv_id, root_path, del_after_finish, chunk_size=10485760):
        self.start_time = time.time()
        self.drive_id = drive_id
        self.mv_id = mv_id
        self.root_path = root_path
        self.chunk_size = chunk_size
        self.filepath = None
        self.filepath_hash = None
        self.realpath = None
        self.filename = None
        self.hash = None
        self.part_info_list = []
        self.part_upload_url_list = []
        self.upload_id = 0
        self.file_id = 0
        self.part_number = 0
        self.filesize = 0
        self.headers = {}
        self.del_after_finish = del_after_finish

    def load_file(self, filepath, realpath):
        self.filepath = filepath
        self.filepath_hash = sha1(filepath.encode('utf-8')).hexdigest()
        self.realpath = realpath
        self.filename = os.path.basename(realpath)
        self.hash = Common.get_hash(self.realpath)
        self.filesize = os.path.getsize(self.realpath)
        # print_info('【{filename}】({filesize}M)正在校检文件中，耗时与文件大小有关'.format(filename=self.filename, filesize=round(self.filesize/float(1024 * 1024), 2)))

        self.part_info_list = []
        for i in range(0, math.ceil(self.filesize / self.chunk_size)):
            self.part_info_list.append({
                'part_number': i + 1
            })

        message = '''=================================================
        文件名：{filename}
        hash：{hash}
        文件大小：{filesize}M
        文件路径：{filepath}
=================================================
'''.format(filename=self.filename, hash=self.hash, filesize=round(self.filesize/float(1024 * 1024), 2), filepath=self.realpath)
        # print_info(message)

    def token_refresh(self):
        LOCK.acquire()
        try:
            data = {"refresh_token": DATA['REFRESH_TOKEN']}
            post = requests.post(
                'https://websv.aliyundrive.com/token/refresh',
                data=json.dumps(data),
                headers={
                    'content-type': 'application/json;charset=UTF-8'
                },
                verify=False
            )
            try:
                if post.content:
                    post_json = post.json()
                else:
                    return False
                # 刷新配置中的token
                # with open(get_running_path('/config.json'), 'rb') as f:
                #     config = json.loads(f.read().decode('utf-8'))
                # config['REFRESH_TOKEN'] = post_json['refresh_token']
                # with open(get_running_path('/config.json'), 'w') as f:
                #     f.write(json.dumps(config))
                #     f.flush()

            except Exception as e:
                print_warn('refresh_token已经失效')
                raise e

            access_token = post_json['access_token']
            self.headers = {
                'authorization': access_token,
                'content-type': 'application/json;charset=UTF-8'
            }
            DATA['REFRESH_TOKEN'] = post_json['refresh_token']
            return True
        finally:
            LOCK.release()

    def create(self, parent_file_id):
        create_data = {
            "drive_id": self.drive_id,
            "part_info_list": self.part_info_list,
            "parent_file_id": parent_file_id,
            "name": self.filename,
            "type": "file",
            "check_name_mode": "auto_rename",
            "size": self.filesize,
            "content_hash": self.hash,
            "content_hash_name": 'sha1'
        }
        # 覆盖已有文件
        # if DATA['OVERWRITE']:
        # 判断文件是否存在
        create_data['check_name_mode'] = 'refuse'
        request_post = requests.post(
            'https://api.aliyundrive.com/v2/file/create',
            data=json.dumps(create_data),
            headers=self.headers,
            verify=False
        )
        requests_post_json = request_post.json()
        self.check_auth(requests_post_json, lambda: self.create(parent_file_id))
        # 覆盖已有文件
        if DATA['OVERWRITE'] and requests_post_json.get('exist'):
            if self.recycle(requests_post_json.get('file_id')):
                print_info('【%s】原有文件回收成功' % self.filename)
                print_info('【%s】重新上传新文件中' % self.filename)
                return self.create(parent_file_id)

        self.part_upload_url_list = requests_post_json.get('part_info_list', [])
        self.file_id = requests_post_json.get('file_id')
        self.upload_id = requests_post_json.get('upload_id')
        return requests_post_json

    def get_upload_url(self):
        print_info('【%s】上传地址已失效正在获取新的上传地址' % self.filename)
        requests_data = {
            "drive_id": self.drive_id,
            "file_id": self.file_id,
            "part_info_list": self.part_info_list,
            "upload_id": self.upload_id,
        }
        requests_post = requests.post(
            'https://api.aliyundrive.com/v2/file/get_upload_url',
            data=json.dumps(requests_data),
            headers=self.headers,
            verify=False
        )
        requests_post_json = requests_post.json()
        self.check_auth(requests_post_json, self.get_upload_url)
        print_info('【%s】上传地址刷新成功' % self.filename)
        return requests_post_json.get('part_info_list')

    def upload(self):

        with open(self.realpath, "rb") as fs:
            # with tqdm.wrapattr(f, "read", desc='正在上传【%s】' % self.filename, miniters=1,
            #                    initial=self.part_number * self.chunk_size,
            #                    total=self.filesize,
            #                    ascii=True
            #                    ) as fs:

            while self.part_number < len(self.part_upload_url_list):
                upload_url = self.part_upload_url_list[self.part_number]['upload_url']
                total_size = min(self.chunk_size, self.filesize)
                fs.seek(self.part_number * total_size)
                res = requests.put(
                    url=upload_url,
                    data=Common.read_in_chunks(fs, 16 * 1024, total_size),
                    verify=False,
                    timeout=None
                )
                if 400 <= res.status_code < 600:
                    common_get_xml_value = Common.get_xml_tag_value(res.text, 'Message')
                    if common_get_xml_value == 'Request has expired.':
                        self.part_upload_url_list = self.get_upload_url()
                        continue
                    common_get_xml_value = Common.get_xml_tag_value(res.text, 'Code')
                    if common_get_xml_value == 'PartAlreadyExist':
                        pass
                    else:
                        print_error(res.text)
                        res.raise_for_status()
                self.part_number += 1
                DATA['tasks'][self.filepath_hash]['part_number'] = self.part_number
                DATA['tasks'][self.filepath_hash]['drive_id'] = self.drive_id
                DATA['tasks'][self.filepath_hash]['file_id'] = self.file_id
                DATA['tasks'][self.filepath_hash]['upload_id'] = self.upload_id
                DATA['tasks'][self.filepath_hash]['chunk_size'] = self.chunk_size
                Common.save_task(DATA['tasks'])

            print_info('【%s】上传完成' % self.filename)
            if self.del_after_finish:
                os.remove(self.realpath)

    def complete(self):
        complete_data = {
            "drive_id": self.drive_id,
            "file_id": self.file_id,
            "upload_id": self.upload_id
        }
        complete_post = requests.post(
            'https://api.aliyundrive.com/v2/file/complete', json.dumps(complete_data),
            headers=self.headers,
            verify=False
        )

        requests_post_json = complete_post.json()
        self.check_auth(requests_post_json, self.complete)
        # s = time.time() - self.start_time

        if 'file_id' in requests_post_json:
            # print_success('【{filename}】上传成功！消耗{s}秒'.format(filename=self.filename, s=s))
            save_mv_id(self.mv_id)
            return True
        else:
            s = time.time() - self.start_time
            print_warn('【{filename}】上传失败！消耗{s}秒'.format(filename=self.filename, s=s))
            return False

    def create_folder(self, folder_name, parent_folder_id):
        create_data = {
            "drive_id": self.drive_id,
            "parent_file_id": parent_folder_id,
            "name": folder_name,
            "check_name_mode": "refuse",
            "type": "folder"
        }
        create_post = requests.post(
            'https://api.aliyundrive.com/v2/file/create',
            data=json.dumps(create_data),
            headers=self.headers,
            verify=False
        )
        requests_post_json = create_post.json()
        self.check_auth(requests_post_json, lambda: self.create_folder(folder_name, parent_folder_id))
        return requests_post_json.get('file_id')

    def get_parent_folder_id(self, filepath):
        # print_info('检索目录中')
        filepath_split = (self.root_path + filepath.lstrip(os.sep)).split(os.sep)
        del filepath_split[len(filepath_split) - 1]
        path_name = os.sep.join(filepath_split)
        if path_name not in DATA['folder_id_dict']:
            parent_folder_id = 'root'
            parent_folder_name = os.sep
            if len(filepath_split) > 0:
                for folder in filepath_split:
                    if folder == '':
                        continue
                    parent_folder_id = self.create_folder(folder, parent_folder_id)
                    parent_folder_name = parent_folder_name.rstrip(os.sep) + os.sep + folder
                    DATA['folder_id_dict'][parent_folder_name] = parent_folder_id
        else:
            parent_folder_id = DATA['folder_id_dict'][path_name]
            print_info('已存在目录，无需创建')

        # print_info('目录id获取成功{parent_folder_id}'.format(parent_folder_id=parent_folder_id))
        return parent_folder_id

    def recycle(self, file_id):
        # https://api.aliyundrive.com/v2/batch
        requests_data = {
            "requests": [
                {
                    "body": {
                        "drive_id": self.drive_id,
                        "file_id": file_id
                    },
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "id": file_id,
                    "method": "POST",
                    "url": "/recyclebin/trash"
                }
            ],
            "resource": "file"
        }
        requests_post = requests.post(
            'https://api.aliyundrive.com/v2/batch',
            data=json.dumps(requests_data),
            headers=self.headers,
            verify=False
        )
        requests_post_json = requests_post.json()
        self.check_auth(requests_post_json, lambda: self.recycle(file_id))
        return True

    def check_auth(self, response_json, func):
        if response_json.get('code') == 'AccessTokenInvalid':
            print_info('AccessToken已失效，尝试刷新AccessToken中')
            if self.token_refresh():
                print_info('AccessToken刷新成功，返回创建上传任务')
                return func()
            print_error('无法刷新AccessToken，准备退出')
            sys.exit()
