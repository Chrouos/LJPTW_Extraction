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

def chinese_to_int(text):

    num_dict = {
        # '零': '0', 
        '０': '零',
        '壹': '1', '一': '1', '１': '1',
        '貳': '2', '二': '2', '２': '2',
        '參': '3', '三': '3', '叁': '3', '参': '3', '３': '3',
        '肆': '4', '四': '4', '４': '4',
        '伍': '5', '五': '5', '５': '5',
        '陸': '6', '六': '6', '６': '6',
        '柒': '7', '七': '7', '７': '7',
        '捌': '8', '八': '8', '８': '8',
        '玖': '9', '九': '9', '９': '9',
        
    }
    
    process_text = ''
    for char_index in text:
        if char_index in num_dict:
            process_text += str(num_dict[char_index])
        else:
            process_text += char_index
    
    return process_text