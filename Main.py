#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import json
import os
import time
from NetworkAttributes import NetworkAttributes, ENCRYPT_ONE, ENCRYPT_TWO
from concurrent.futures import ThreadPoolExecutor, as_completed
from Network import Network
from Upload import Upload
from Common import print_info, print_error, load_mv_ids, set_ready_count, get_running_path, get_all_file_relative, save_count, MVHISTORYCONT

if __name__ != '__main__':
    sys.exit()


# 上传本地视频
def upload_local_files(upload):
    ids = load_mv_ids()
    # 一共两个目录下有视频
    paths = [get_running_path('/FastVideo/One'), get_running_path('/FastVideo/Two')]

    type = 0
    total_count = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_list = []
        for path in paths:
            type += 1
            file_list = get_all_file_relative(path)
            total_count += len(file_list)
            for file in file_list:
                star = file.rfind(':')
                end = file.rfind('.')
                id = '{}_{}'.format(type, file[star+1:end])
                if id in ids:
                    real_path = os.path.join(path, file)
                    os.remove(real_path)
                else:
                    # 提交线程
                    future = executor.submit(upload.upload, path, file, id)
                    future_list.append(future)

        set_ready_count(total_count)

        for res in as_completed(future_list):
            if res.result():
                print_error(os.path.basename(file) + ' 上传成功')


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


if len(sys.argv) >= 2:

    allConfig = json.loads(sys.argv[1])
    # 创建一号网络相关参数
    attOne = NetworkAttributes(allConfig.get('One'), ENCRYPT_ONE)
    # 创建一号网络
    one = Network(attOne)
    networks = [one]

    # 暂时不抓取二号的视频，后期看情况
    # 创建二号网络
    two = Network(NetworkAttributes(allConfig.get('Two'), ENCRYPT_TWO))
    networks.append(two)

    # 创建上传
    upload = Upload(allConfig.get('Aliyun'), attOne)

    # 已下载的视频id
    ids = load_mv_ids()

    # 三个参数时，上传本地存在的视频
    if len(sys.argv) >= 3:
        upload_local_files(upload)
        sys.exit()

    # 需要处理视频数
    readyCount = 0
    # 最大处理视频数
    readyMaxCount = 400

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_list = []
        print_info('正在获取视频列表。。。')
        for network in networks:
            while readyCount <= readyMaxCount:
                # 获取热门视频列表
                videoList = network.hotList(network.page)
                if videoList is None:
                    break
                for video in videoList:
                    # 生成固定格式的mvId
                    id = '{}_{}'.format(video.type, video.mvId)
                    if id not in ids:
                        if readyCount > readyMaxCount:
                            break

                        readyCount += 1
                        # 提交线程
                        future = executor.submit(download_upload, video, network, upload, id)
                        future_list.append(future)
            if readyCount > readyMaxCount:
                break
        set_ready_count(readyCount)

    # 把本地视频再检查一下，如果存在就不上传
    print_info('准备处理本地没有上传成功的视频')
    upload_local_files(upload)
    fold = os.path.abspath('.')
    # 保存成功处理的视频数量
    count = save_count()
    # 将视频数做为文件名，也上传到阿里云盘
    if count is not None and count > 0:
        name = '#视频数：%d.txt' % count
        path = os.path.join(fold, name)
        with open(path, 'a+') as f:
            f.write('\n')
            f.flush()
        upload.upload(fold, name, '')
