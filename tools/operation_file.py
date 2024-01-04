from os import listdir, path, mkdir, remove
from datetime import datetime
import json
import re
import io
import sys
import random
from collections import defaultdict, Counter
import shutil
import random
import pandas as pd

sys.path.append('./tools')

# ----- 清空指定目錄中的所有檔案
def clear_directory(directory):
    if path.exists(directory):
        for file in listdir(directory):
            file_path = path.join(directory, file)
            if path.isfile(file_path):
                remove(file_path)
                
    return True
                
                
# ----- 全形轉成半形
def convert_fullwidth_to_halfwidth(text):
    result = []
    for char in text:
        code = ord(char)
        if code == 0x3000:  # 全形空格直接轉換
            code = 0x0020
        elif 0xFF01 <= code <= 0xFF5E:  # 全形字符（除空格）轉換成半形字符
            code -= 0xFEE0
        result.append(chr(code))
        
    return ''.join(result)
