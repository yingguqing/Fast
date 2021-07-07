#!/usr/bin/python3
# -*- coding: utf-8 -*-
# 用户信息封装


from NetworkAttributes import ENCRYPT_ONE, ENCRYPT_TWO


class User:

    def __init__(self, jsonValue, type):
        self.type = type
        if type == ENCRYPT_ONE:
            self.uId = str(jsonValue.get("mu_id"))
            self.avatar = str(jsonValue.get("mu_avatar"))
            self.token = str(jsonValue.get("mu_token"))
            self.nickName = str(jsonValue.get("mu_name"))
            self.isAttention = bool(jsonValue.get("is_attention"))
        elif type == ENCRYPT_TWO:
            self.uId = str(jsonValue.get("user_id"))
            self.avatar = str(jsonValue.get("avatar"))
            self.token = str(jsonValue.get("api_token"))
            self.nickName = str(jsonValue.get("nickname"))
            relation = jsonValue.get('relation')
            if relation is not None:
                self.isAttention = int(relation) == 1
            else:
                self.isAttention = False
        else:
            pass
