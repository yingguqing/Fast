#!/usr/bin/python3
# -*- coding: utf-8 -*-
# 网络解密等参数封装

from Crypto.Cipher import AES
import base64
import json
import hashlib
from urllib import parse

# 旧快猫
ENCRYPT_ONE = 1
# 新快猫
ENCRYPT_TWO = 2


class NetworkAttributes:

    def __init__(self, jsonValue, type):
        self.host = jsonValue["Host"]
        self.successCode = int(jsonValue["SuccessCode"])
        self.messageKey = jsonValue["MessageKey"]
        self.key = jsonValue["Key"]
        self.iv = jsonValue["IV"]
        self.salt = jsonValue["Salt"]
        self.account = jsonValue["Account"]
        self.password = jsonValue["Password"]
        self.type = type
        API = jsonValue["API"]
        self.login_api = API["Login"]
        self.hot_api = API["HotList"]
        self.detail_api = API["VideoDetail"]
        self.apiToken = ""

    def postParams(self, params):
        """ 请求参数拼装和加密 """
        if self.type == ENCRYPT_ONE:
            if type(params) is str:
                jsonString = str(params)
            else:
                jsonString = json.dumps(params).replace(' ', '')
            # 参数转成json字符串，再加密
            encryptString = self.encrypt(jsonString)
            sig = "data={}{}".format(encryptString, self.salt)
            sig = hashlib.md5(sig.encode(encoding='UTF-8')).hexdigest()
            return {"data": encryptString, "sig": sig}
        elif self.type == ENCRYPT_TWO:
            apiToken = ""
            # 判断是否需要加上用户的token
            if bool(params.get('FastNeedUserTokenKey')):
                apiToken = self.apiToken

            newParams = params
            if params.get('FastNeedUserTokenKey') is not None:
                newParams.pop('FastNeedUserTokenKey')

            # 对参数的key进行升序排序
            sortValue = []
            for key in sorted(newParams):
                if newParams.get(key) is None:
                    continue
                value = str(newParams.get(key))
                string = str(parse.quote(key)) + "=" + str(parse.quote(value))
                sortValue.append(string)
            # 使用&拼接
            sortString = '&'.join(sortValue)
            signString = sortString + self.salt
            sign = hashlib.md5(signString.encode(encoding='UTF-8')).hexdigest().upper()
            newParams["signature"] = sign
            jsonString = json.dumps(newParams)
            # 参数转成json字符串，再加密
            encryptString = self.encrypt(jsonString)
            result = {
                "data": encryptString,
                "device_version": "h5",
                "device_type": "iPhone",
                "version_code": "1.0",
                "device": "h5",
                "api_token": apiToken
            }
            return result

    def encrypt(self, content):
        """ AES加密, 输出Base16进制字符串 """
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        x = AES.block_size - (len(content) % AES.block_size)
        if x != 0:
            content = content + chr(x)*x
        msg = cipher.encrypt(content)
        # 重新编码
        msg = str(base64.b16encode(msg), encoding='utf-8').upper()
        return msg

    def decrypt(self, enStr):
        """ Base16字符串，AES解密 """
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decryptByts = base64.b16decode(enStr)
        msg = cipher.decrypt(decryptByts).decode('utf-8')
        paddingLen = ord(msg[len(msg)-1])
        return msg[0:-paddingLen]
