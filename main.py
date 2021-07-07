#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import json
import os
import time
from NetworkAttributes import NetworkAttributes, ENCRYPT_ONE, ENCRYPT_TWO
from concurrent.futures import ThreadPoolExecutor, as_completed
from Common import print_info, MVHISTORYCONT
from Network import Network
from Upload import Upload
from Common import load_mv_ids, save_mv_id

if __name__ != '__main__':
    sys.exit()


#  视频下载与上传
def download_upload(video, network, upload, id):
    # 获取视频的详细数据，主要是获取下载地址
    detailVideo = network.detail(video)
    if detailVideo is None:
        return
    #  下载视频，返回文件名
    file_name = detailVideo.download()
    #  启动上传
    upload.upload(detailVideo.savePath, file_name, id)


if len(sys.argv) == 2:
    allConfig = json.loads(sys.argv[1])
    attOne = NetworkAttributes(allConfig.get('One'), ENCRYPT_ONE)
    one = Network(attOne)
    upload = Upload(allConfig.get('Aliyun'), attOne)
    two = Network(NetworkAttributes(allConfig.get('Two'), ENCRYPT_TWO))
    ids = load_mv_ids()

    # 已经上传成功的mvId最大数，超过时就不再抓取
    existsMaxCount = 15

    for network in [one, two]:
        existsCount = 0
        while True:
            # 获取热门视频列表
            videoList = network.hotList(network.page)
            if videoList is None:
                break
            for video in videoList:
                # 生成固定格式的mvId
                id = '{}_{}'.format(video.type, video.mvId)
                if id in ids:
                    existsCount += 1
                    if existsCount >= existsMaxCount:
                        break
                    else:
                        print_info('{} 已经上传成功'.format(id))
                        continue

                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_list = []
                    # 提交线程
                    future = executor.submit(download_upload, video, network, upload, id)
                    future_list.append(future)

    # 计算本次更新视频数
    history = MVHISTORYCONT
    load_mv_ids()
    newCount = MVHISTORYCONT - history
    # 更新ReadMe，记录本次更新视频数量
    fold = os.path.abspath('.')
    readMePath = os.path.join(fold, "README.md")
    with open(readMePath, 'a+') as f:
        f.seek(0)
        loc_time = time.strftime("%Y-%m-%d", time.localtime())
        f.write('\n')
        f.write(loc_time)
        f.write('\n')
        f.write('更新视频数：{}'.format(newCount))
        f.flush()
