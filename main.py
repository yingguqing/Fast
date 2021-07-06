#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os

if len(sys.argv) == 2:
    print(sys.argv[1])
    try:
        fold = os.path.abspath('.')  # 表示当前所处的文件夹的绝对路径

        path = os.path.join(fold, "test.log")
        with open(path, 'w') as f:
            f.write(sys.argv[1])
            f.flush()
    finally:
        print("")
else:
    print("111222")