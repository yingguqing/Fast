#!/usr/bin/python3
# -*- coding: utf-8 -*-
# 视频信息封装

import json
from NetworkAttributes import ENCRYPT_ONE, ENCRYPT_TWO
from User import User
import os
import requests
from Common import print_info


class Video(User):

    def __init__(self, jsonValue, type):
        super().__init__(jsonValue, type)
        self.gold = 0
        self.retime = 3
        if type == ENCRYPT_ONE:
            self.mvId = str(jsonValue.get("mv_id"))
            self.title = str(jsonValue.get("mv_title")).replace(" ", "")
            self.imgURL = str(jsonValue.get("mv_img_url"))
            self.playURL = str(jsonValue.get("mv_play_url"))
            self.downloadURL = str(jsonValue.get("mv_play_url"))
            self.playWidth = str(jsonValue.get("mv_play_width"))
            self.playHeight = str(jsonValue.get("mv_play_height"))
            self.like = str(jsonValue.get("mv_like"))
            self.isCatAds = bool(jsonValue.get("is_cat_ads"))
            self.isCollect = str(jsonValue.get("is_collect"))
        elif type == ENCRYPT_TWO:
            self.mvId = str(jsonValue.get("id"))
            self.title = str(jsonValue.get("title")).replace(" ", "")
            self.imgURL = str(jsonValue.get("cover"))
            self.playURL = str(jsonValue.get("normal_url"))
            self.downloadURL = str(jsonValue.get("normal_url"))
            self.playWidth = str(jsonValue.get("width"))
            self.playHeight = str(jsonValue.get("height"))
            self.like = str(jsonValue.get("praise_num"))
            self.isCatAds = False
            self.isCollect = str(jsonValue.get("is_collect"))
            if 'type' in jsonValue.keys():
                videoType = int(jsonValue.get('type'))
                self.isCatAds = videoType == 2
            else:
                self.isCatAds = False

            if "gold" in jsonValue.keys():
                self.gold = int(jsonValue.get("gold"))
        else:
            pass
        self.createSavePath()

    def createSavePath(self):
        """ 创建下载目录 """
        if self.type == ENCRYPT_ONE:
            child = "One"
        elif self.type == ENCRYPT_TWO:
            child = "Two"
        else:
            child = "Other"
        fold = os.path.abspath('.')
        self.savePath = os.path.join(fold, "FastVideo", child)
        if not os.path.exists(self.savePath):
            os.makedirs(self.savePath)

    def download(self):
        """ 下载视频,返回文件名 """
        url = self.downloadURL
        if url is None:
            print_info('{}_{} 下载链接为空'.format(self.type, self.mvId))
            return None
        res = requests.get(url)
        name = '{}_u:{}v:{}{}'.format(self.title, self.uId, self.mvId, os.path.splitext(url)[-1])

        path = os.path.join(self.savePath, name)
        if os.path.exists(path):
            print_info('{}_{} 文件存在，不用下载'.format(self.type, self.mvId))
            return name

        print_info('开始下载：{}_{}'.format(self.type, self.mvId))
        with open(path, 'wb') as f:
            try:
                f.write(res.content)
                # 文件小于1M不上传
                if self.get_FileSize(path) < 1:
                    return None
                print_info('{}_{} 下载成功'.format(self.type, self.mvId))
                return name
            finally:
                f.close

    def get_FileSize(self, filePath):
        fsize = os.path.getsize(filePath)
        fsize = fsize/float(1024 * 1024)
        return round(fsize, 2)
