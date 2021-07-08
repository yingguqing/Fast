#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import json
import os
import time
from NetworkAttributes import NetworkAttributes, ENCRYPT_ONE, ENCRYPT_TWO
from concurrent.futures import ThreadPoolExecutor, as_completed
from Common import print_info, MVHISTORYCONT, MVUPLOADCOUNT
from Network import Network
from Upload import Upload
from Common import load_mv_ids

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
    #  文件名为空，表示下载失败，文件存在时，启动上传
    if file_name is not None:
        upload.upload(detailVideo.savePath, file_name, id)


if len(sys.argv) == 2:
    allConfig = json.loads(sys.argv[1])
    # 创建一号网络相关参数
    attOne = NetworkAttributes(allConfig.get('One'), ENCRYPT_ONE)
    # 创建一号网络
    one = Network(attOne)
    # 创建二号网络
    two = Network(NetworkAttributes(allConfig.get('Two'), ENCRYPT_TWO))
    # 创建上传
    upload = Upload(allConfig.get('Aliyun'), attOne)
    # 已下载的视频id
    ids = load_mv_ids()

    # 已经上传成功的mvId最大数，超过时就不再抓取
    existsMaxCount = 5

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_list = []
        for network in [one, two]:
            existsCount = 0
            while existsCount < existsMaxCount:
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
                            print_info('{}_相同数量已达到上限'.format(network.type))
                            break
                    else:
                        MVUPLOADCOUNT += 1
                        print_info('需要处理数：{}'.format(MVUPLOADCOUNT))
                        # 提交线程
                        future = executor.submit(download_upload, video, network, upload, id)
                        future_list.append(future)

        print_info('本次抓取需要处理视频数：{}'.format(MVUPLOADCOUNT))

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
