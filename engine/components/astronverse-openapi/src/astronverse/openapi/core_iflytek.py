import base64
import hashlib
import hmac
import json
import os
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import requests
from astronverse.actionlib.atomic import atomicMg
from astronverse.openapi.error import *

# 配置文件中设置信息读取
cfg = atomicMg.cfg_from_file(key="OpenApi")
APPId = cfg.get("APP_ID", "")
APISecret = cfg.get("API_SECRET", "")
APIKey = cfg.get("API_KEY", "")

# ---------------------------------------------------------------------------
# Local OCR engine (PaddleOCR) – lazy-loaded singleton
# ---------------------------------------------------------------------------
_ocr_engine = None


def _get_ocr_engine():
    """Return a cached PaddleOCR instance, creating it on first call."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR  # noqa: F811
        except ImportError:
            raise BaseException(
                AI_SERVER_ERROR,
                "PaddleOCR 未安装，请运行: pip install paddleocr paddlepaddle",
            )
        _ocr_engine = PaddleOCR(lang="ch", use_textline_orientation=True)
    return _ocr_engine


class OcrRequests:
    """OCR请求封装"""

    @staticmethod
    def __parse_url__(url: str):
        """解析url"""

        st = url.index("://")
        host = url[st + 3 :]
        schema = url[: st + 3]
        ed = host.index("/")
        if ed <= 0:
            raise Exception("invalid request url:" + url)
        path = host[ed:]
        host = host[:ed]
        return host, path, schema

    @staticmethod
    def __assemble_ws_auth_url__(url: str, method="POST", api_key="", api_secret=""):
        """加密token"""

        host, path, schema = OcrRequests.__parse_url__(url)

        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(host, date, method, path)
        signature_sha = hmac.new(
            api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")
        authorization_origin = 'api_key="%s", algorithm="%s", headers="%s", signature="%s"' % (
            api_key,
            "hmac-sha256",
            "host date request-line",
            signature_sha,
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(encoding="utf-8")
        values = {"host": host, "date": date, "authorization": authorization}
        return url + "?" + urlencode(values)

    @staticmethod
    def request(method, url, **kwargs):
        """请求"""
        request_url = OcrRequests.__assemble_ws_auth_url__(url, "POST", APIKey, APISecret)
        return requests.request(method, request_url, **kwargs)


class OpenapiIflytek:
    """iflytek开放平台"""

    @staticmethod
    def template_ocr(header_dict: dict, files: list, type_code: str, url: str, key_name: str) -> list:
        results = []
        for image in files:
            with open(image, "rb") as f:
                image_bytes = f.read()
                image_info = base64.b64encode(image_bytes)
            suffix = os.path.splitext(image)[1].lstrip(".").lower()
            # 请求数据准备
            body = {
                "header": {"app_id": APPId, "status": 3},
                "parameter": {
                    key_name: {
                        "result": {
                            "encoding": "utf8",
                            "compress": "raw",
                            "format": "json",
                        },
                        "template_list": type_code,
                    }
                },
                "payload": {
                    f"{key_name}_data_1": {
                        "encoding": suffix,
                        "image": str(image_info, "UTF-8"),
                        "status": 3,
                    }
                },
            }
            headers = {
                "content-type": "application/json",
                "host": "api.xf-yun.com",
                "app_id": APPId,
            }
            # 发起请求
            ret = OcrRequests.request("POST", url, data=json.dumps(body), headers=headers)

            # 请求结果处理
            if ret.status_code != 200:
                raise BaseException(AI_SERVER_ERROR, "ai服务器无响应或错误 {}".format(ret))
            text = (
                base64.b64decode(ret.json()["payload"]["result"]["text"])
                .decode()
                .replace(" ", "")
                .replace("\n", "")
                .replace("\t", "")
                .strip()
            )
            if not text.endswith("}"):
                reverse_text = text[::-1]
                ind = reverse_text.find("}")
                real_ind = len(text) - ind
                text = text[:real_ind]
            ret_dict = json.loads(text)
            if ret_dict["error_code"] != 0:
                raise BaseException(
                    AI_REQ_ERROR_FORMAT.format(ret_dict["error_msg"]),
                    "ai服务请求异常 {}".format(ret_dict["error_msg"]),
                )
            if ret_dict["object_list"][0]["error_code"] != 0:
                raise BaseException(
                    AI_REQ_ERROR_FORMAT.format(ret_dict["object_list"][0]["error_msg"]),
                    "ai服务请求异常 {}".format(ret_dict["object_list"][0]["error_msg"]),
                )
            result_info = {}
            for region in ret_dict["object_list"][0]["region_list"]:
                key = region["text_block_list"][0]["key"]
                if not header_dict.get(key):
                    continue
                if region["text_block_list"][0]["value"]:
                    result_info[header_dict[key]] = region["text_block_list"][0]["value"]
            results.append(result_info)
        return results

    @staticmethod
    def common_ocr(header_dict: dict, files: list) -> list:
        """
        本地通用文字识别（基于PaddleOCR），无需联网即可完成图片文字识别。

        参数:
            header_dict: 字段映射字典，如 {"Context": "图文识别结果"}
            files: 待识别的图片文件路径列表

        返回:
            list[dict]: 每张图片的识别结果
        """
        ocr = _get_ocr_engine()
        from PIL import Image as _PILImage
        import numpy as _np
        results: list[dict] = []
        for image in files:
            _img = _PILImage.open(image).convert("RGB")
            ocr_result = ocr.ocr(_np.array(_img))
            content = OpenapiIflytek.__analyse_ocr_result__(ocr_result)
            ocr_dict = {"Context": content}
            json_result = {}
            for k, v in ocr_dict.items():
                if not header_dict.get(k):
                    continue
                json_result[header_dict[k]] = v
            results.append(json_result)
        return results

    @staticmethod
    def __analyse_ocr_result__(data: list | None) -> str:
        """
        解析PaddleOCR返回的数据，将检测到的文字按行重组为纯文本。

        PaddleOCR 3.x 返回格式（传入numpy数组时）:
            [OCRResult]  — paddlex.inference.pipelines.ocr.result.OCRResult 对象
            OCRResult 属性:
              - rec_texts: list[str]  识别文字列表
              - dt_polys:  list[list] 检测框多边形坐标
              - rec_scores: list[float] 置信度

        Y坐标差值小于10像素的文本框视为同一行，否则插入换行符。
        """
        if data is None or len(data) == 0:
            return ""
        result = data[0]
        # OCRResult 是 dict 子类，统一用 .get()
        rec_texts = list(result.get("rec_texts", []) or [])
        dt_polys = list(result.get("dt_polys", []) or [])

        if len(rec_texts) == 0:
            return ""

        # 将 (文字, Y坐标) 配对并按 Y 排序
        items = []
        for i, text in enumerate(rec_texts):
            poly = dt_polys[i] if i < len(dt_polys) else None
            if poly is not None and len(poly) > 0:
                y = poly[0][1]
            else:
                y = 0
            items.append((y, text))
        items.sort(key=lambda x: x[0])

        content = ""
        y = 0
        first = True
        for current_y, text in items:
            if not first and not (y - 10 < current_y < y + 10):
                content += "\n"
            content += text
            first = False
            y = current_y
        return content
