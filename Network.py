#!/usr/bin/python3
# -*- coding: utf-8 -*-
# 网络请求封装

from Video import Video
import requests
import json
from NetworkAttributes import ENCRYPT_ONE, ENCRYPT_TWO
from urllib.parse import urljoin, urlencode, urlparse
from Common import print_info, print_error


class Network:

    def __init__(self, attributes):
        #  页码
        self.page = 1
        #  最大加载页码数
        self.maxPage = 15
        #  每页个数
        self.perPage = 4
        self.attributes = attributes
        self.host = attributes.host
        self.type = attributes.type
        if self.type == ENCRYPT_ONE:
            # 热门数据列表中的下载链接的host
            self.oldDownloadHost = ''
            # 获取详细信息后的下载链接的host（替换列表中的链接，减少请求）
            self.newDownloadHost = ''
            self.maxPage = 10

    def post(self, api, params, keyPath=None):
        url = urljoin(self.host, api)
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        paramsString = urlencode(self.attributes.postParams(params))
        res = requests.post(url=url, data=paramsString, headers=headers)
        d = self.attributes.decrypt(res.text)
        jsonValue = json.loads(d)

        # 返回值为空
        if jsonValue is None:
            print_error('返回数据为空：url:{},params:{}'.format(url, params))
            return None

        # 返回值不是json类型
        if type(jsonValue) is not dict:
            print_error('返回数据类型不是json：url:{},params:{},value:{}'.format(url, params, jsonValue))
            return None

        # 返回值没有code字段
        if 'code' not in jsonValue.keys():
            print_error('返回数据没有code字段：url:{},params:{},value:{}'.format(url, params, jsonValue))
            return None

        code = int(jsonValue.get('code'))

        if code != self.attributes.successCode:
            msg = '失败'
            if self.attributes.messageKey in jsonValue.keys():
                msg = jsonValue.get(self.attributes.messageKey)
            print_error('请求结果失败：{}:url:{},params:{},value:{}'.format(msg, url, params, jsonValue))
            return None

        if keyPath is not None:
            keys = keyPath.split(".")
            for key in keys:
                jsonValue = jsonValue.get(key)
        return jsonValue

    def hotList(self, page):
        """ 热门 """
        if self.page > self.maxPage:
            return None

        api = self.attributes.hot_api
        if self.type == ENCRYPT_ONE:
            params = {
                "page": int(page),
                "perPage": self.perPage
            }
            keyPath = "data.list"
        elif self.type == ENCRYPT_TWO:
            params = {
                "page": int(page),
                "perPage": self.perPage,
                "type": 1
            }
            keyPath = "data.video_list"
        else:
            return None
        jsonArray = self.post(api, params, keyPath)

        if jsonArray is None:
            return None
        #  解析所有视频数据
        videos = []
        for value in jsonArray:
            video = Video(value, self.type)
            # 过滤广告和收费视频
            if video.isCatAds or video.gold > 0:
                continue
            videos.append(video)
        print_info('{} 第{}页: {}条获取成功'.format(self.type, self.page, len(videos)))
        self.page += 1
        return videos

    def detail(self, video):
        """ 视频详细数据 """
        if video is None or video.mvId is None:
            return None

        # 第一种类型的视频下载地址有规律，所以只要拿了第一个的详细下载地址，就能提取相应的host进行替换
        if self.type == ENCRYPT_ONE and len(self.oldDownloadHost) > 0 and len(self.newDownloadHost) > 0:
            video.downloadURL = video.downloadURL.replace(self.oldDownloadHost, self.newDownloadHost)
            return video

        api = self.attributes.detail_api
        if self.type == ENCRYPT_ONE:
            params = {
                "uId": "60364099",
                "mvId": str(video.mvId),
                "type": 0
            }
            keyPath = "data"
        elif self.type == ENCRYPT_TWO:
            params = {
                "video_id": int(video.mvId)
            }
            keyPath = "data.video_info"
        else:
            return None
        jsonValue = self.post(api, params, keyPath)

        if jsonValue is None or type(jsonValue) is not dict:
            print_error('{}_{} 下载链接获取失败'.format(video.type, video.mvId))
            return None

        video_temp = Video(jsonValue, self.type)
        if video_temp.downloadURL is not None:
            if self.type == ENCRYPT_ONE:
                # 提取host和scheme，用于其他视频下载地址的替换
                parsed = urlparse(video.downloadURL)
                self.oldDownloadHost = '{probuf.scheme}://{uri.netloc}'.format(uri=parsed, probuf=parsed)
                parsed = urlparse(video_temp.downloadURL)
                self.newDownloadHost = '{probuf.scheme}://{uri.netloc}'.format(uri=parsed, probuf=parsed)

            video.downloadURL = video_temp.downloadURL
        else:
            video.downloadURL = None
            print_error('{}_{} 下载链接为空'.format(video.type, video.mvId))

        return video
