#!/usr/bin/python3
# -*- coding: utf-8 -*-
# 视频上传封装

import os
import time
from NetworkAttributes import ENCRYPT_ONE, ENCRYPT_TWO
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha1
from AliyunDrive import AliyunDrive

from Common import LOCK, DATA, print_success, get_running_path, qualify_path, print_error, print_warn, save_task, save_mv_id

task_template = {
        "filepath": None,
        "upload_time": 0,
        "drive_id": 0,
        "file_id": 0,
        "upload_id": 0,
        "part_number": 0,
        "chunk_size": 0,
    }


class Upload:

    def __init__(self, config, attributes, multithreading=True, max_workers=5):
        #  先读取本地的token，因为本地的token是有刷新过，比配置文件里的新
        self.token_path = get_running_path('/token.txt')
        self.multithreading = multithreading
        self.max_workers = max_workers
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as f:
                token = f.read().decode('utf-8')
                decrypt_token = attributes.decrypt(token)
                DATA['REFRESH_TOKEN'] = decrypt_token
        else:
            DATA['REFRESH_TOKEN'] = config.get('REFRESH_TOKEN')

        DATA['DRIVE_ID'] = config.get('DRIVE_ID')
        DATA['CHUNK_SIZE'] = config.get('CHUNK_SIZE')
        DATA['ROOT_PATH'] = qualify_path(config.get('ROOT_PATH'))
        # 启用多线程
        DATA['MULTITHREADING'] = bool(config.get('MULTITHREADING'))
        # 断点续传
        DATA['RESUME'] = bool(config.get('RESUME'))
        DATA['OVERWRITE'] = bool(config.get('OVERWRITE'))
        # 线程池最大线程数
        DATA['MAX_WORKERS'] = config.get('MAX_WORKERS')
        DATA['tasks'] = {}
        self.attributes = attributes
        #  上传完成后，删除原文件
        self.del_after_finish = True

    def save_token(self):
        """ 保存阿里云盘的最新token """
        LOCK.acquire()
        try:
            token = DATA['REFRESH_TOKEN']
            print('token:{}'.format(token))
            encrypt_token = self.attributes.encrypt(token)
            with open(self.token_path, 'w') as f:
                f.write(encrypt_token)
                f.flush()
        finally:
            LOCK.release()

    def upload_file(self, path, filepath, mvId):
        """ 上传视频到阿里云盘 """
        drive = AliyunDrive(DATA['DRIVE_ID'], mvId, DATA['ROOT_PATH'], DATA['CHUNK_SIZE'])
        # 刷新token
        drive.token_refresh()
        self.save_token()
        realpath = os.path.join(path, filepath)
        drive.load_file(filepath, realpath)
        # 创建目录
        LOCK.acquire()
        try:
            parent_folder_id = drive.get_parent_folder_id(filepath)
        finally:
            LOCK.release()
        # 断点续传
        if DATA['RESUME'] and drive.filepath_hash in DATA['tasks']:
            c_task = DATA['tasks'][drive.filepath_hash]
            if 0 not in (
                    c_task['drive_id'],
                    c_task['file_id'],
                    c_task['upload_id'],
                    c_task['part_number'],
                    c_task['chunk_size'],
            ):
                drive.drive_id = c_task['drive_id']
                drive.file_id = c_task['file_id']
                drive.upload_id = c_task['upload_id']
                drive.part_number = c_task['part_number']
                drive.chunk_size = c_task['chunk_size']
                # 获取上传地址
                drive.part_upload_url_list = drive.get_upload_url()
                # 上传
                drive.upload()
                # 提交
                if drive.complete():
                    return drive.filepath_hash
                return False

        # 创建上传
        create_post_json = drive.create(parent_folder_id)
        if 'rapid_upload' in create_post_json and create_post_json['rapid_upload']:
            print_success('【{filename}】秒传成功！消耗{s}秒'.format(filename=drive.filename, s=time.time() - drive.start_time))
            if self.del_after_finish:
                os.remove(drive.realpath)
            save_mv_id(drive.mv_id)
            return drive.filepath_hash
        # 上传
        drive.upload()
        # 提交
        if drive.complete():
            return drive.filepath_hash
        return False

    def upload(self, path, fileName, mvId):
        """ 上传文件，path：文件所在目录，fileName：文件名，mvId：视频id（格式：type_视频id) """
        if self.multithreading:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_list = []
                filepath_hash = sha1(fileName.encode('utf-8')).hexdigest()
                if filepath_hash not in DATA['tasks']:
                    DATA['tasks'][filepath_hash] = task_template.copy()
                DATA['tasks'][filepath_hash]['filepath'] = fileName
                if DATA['tasks'][filepath_hash]['upload_time'] > 0:
                    print_warn(os.path.basename(fileName) + ' 已上传，无需重复上传')
                    save_mv_id(mvId)
                else:
                    if DATA['tasks'][filepath_hash]['upload_time'] <= 0:
                        # 提交线程
                        future = executor.submit(self.upload_file, path, fileName, mvId)
                        future_list.append(future)

                for res in as_completed(future_list):
                    if res.result():
                        DATA['tasks'][res.result()]['upload_time'] = time.time()
                        save_task(DATA['tasks'])
                    else:
                        print_error(os.path.basename(fileName) + ' 上传失败')
        else:
            filepath_hash = sha1(fileName.encode('utf-8')).hexdigest()
            if filepath_hash not in DATA['tasks']:
                DATA['tasks'][filepath_hash] = task_template.copy()
            DATA['tasks'][filepath_hash]['filepath'] = fileName
            if DATA['tasks'][filepath_hash]['upload_time'] > 0:
                print_warn(os.path.basename(fileName) + ' 已上传，无需重复上传')
                save_mv_id(mvId)
            else:
                if DATA['tasks'][filepath_hash]['upload_time'] <= 0:
                    if self.upload_file(path, fileName, mvId):
                        DATA['tasks'][filepath_hash]['upload_time'] = time.time()
                        save_task(DATA['tasks'])
                    else:
                        print_error(os.path.basename(fileName) + ' 上传失败')
