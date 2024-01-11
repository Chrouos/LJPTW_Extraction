import sys

import io
import json
import logging
import math
import random
import re
import shutil

import time
from collections import defaultdict, Counter
from datetime import datetime
from enum import Enum
from os import listdir, mkdir, path, remove
from os.path import isdir, join

import pandas as pd
from sklearn.model_selection import train_test_split
from tqdm import tqdm

import cn2an

sys.path.append('./tools')



class ProcessAILA:

    # -v- 初始化
    def __init__(   self, 
                    save_path, source_path, expect_folder=['test', 'problem_file', 'doing'], 
                    mode=0, limit_counts=None, isRandomData=False):
        
        # - 預設資料設定
        
        # @ 是否隨機資料 => 存擋打亂
        self.isRandomData = isRandomData
        
        # @ 資料路徑
        self.source_path = source_path
        self.save_path = save_path
        
        self.check_and_create_directories(self.save_path)   # = 路徑防呆
        self.initialize_logging(self.save_path) # = 初始化 logging
        
        # - 獲得所有 source 資料夾與之子之資料名稱
        source_folders = listdir(self.source_path)
        mode = Mode.from_string(mode)
        
        # # - 模式
        if mode == Mode.TEST:
            self.source_folderList = [folder for folder in source_folders if folder == 'test']
        elif mode == Mode.DOING:
            self.source_folderList = [folder for folder in source_folders if folder == 'doing']
        elif mode == Mode.FORMAL_EXPECT_PROBLEM:
            self.source_folderList = [folder for folder in source_folders if folder not in expect_folder]
        self.source_folderList = [folder for folder in self.source_folderList if isdir(join(self.source_path, folder))]
        self.limit_counts = -1 if limit_counts == None else round(int(limit_counts) / len(self.source_folderList)) # 預設要取多少
        print("Here is Running by {} mode".format(mode))
        
        # - 保存每個資料夾中的檔案名稱
        self.source_fileList= {} 
        for folder in self.source_folderList:
            files = listdir(self.source_path + folder)
            self.source_fileList[folder] = sorted(file for file in files)
                
    # -v- 計算總共數量
    def countLength_source(self):
        
        writeContent = []
        total_count = 0  # 起訴書的總數量        

        # @ 計算總共筆數和每個單位的資料量
        for folder_name in self.source_folderList:
            temp_fileList_indictment = self.source_fileList[folder_name]
            total_count += len(temp_fileList_indictment)
            writeContent.append(f"{folder_name}, {len(temp_fileList_indictment)}")
            
        # @ 輸出最後數量
        print(f"countLength_souce 總共 {total_count}" )
        writeContent.append(f"總共 {total_count}")

        # @ 儲存檔案
        save_file_path = f"{self.save_path}countLength_source.txt"
        self.save_to_file(save_file_path, "\n".join(writeContent))
        
        
    # -v- TWLJP
    def TWLJP_JSON(self):
        
        writeContent = []
        
        (accumulated_charge_dict, accumulated_article_dict, accumulated_criminals_dict, 
        accumulated_total_charges, accumulated_total_article, accumulated_total_mult_criminals) = self.initialize_accumulators()
        
        self.save_results(accumulated_criminals_dict, 'criminals', accumulated_total_mult_criminals)
        self.save_results(accumulated_charge_dict, 'charges', accumulated_total_charges)
        self.save_results(accumulated_article_dict, 'article', accumulated_total_article)
        
        # @ 計算時間
        folders_counts = len(self.source_folderList)
        folder_progress = tqdm(self.source_folderList, desc='Processing Folders', total=folders_counts)
        total_count = 0
            
        # - 進入資料夾
        for folder_name in folder_progress: # = outerLoop 資料夾名稱
            folder_progress.set_description(f"Processing {folder_name}")
            current_fileList = self.source_fileList[folder_name]
            
            # @ 是否限制筆數
            limit_count = min(len(current_fileList), self.limit_counts) if self.limit_counts != -1 else len(current_fileList)
            
            # @ 是否要隨機打亂檔案
            if self.isRandomData == True: limit_fileList = random.sample(current_fileList, limit_count)
            else: limit_fileList = current_fileList[:limit_count]  
            
            total_count += len(limit_fileList)
            logging.info(f"{folder_name} 取 {limit_count} 筆資料")
            
            # - 進入檔案
            for fileName in tqdm(limit_fileList, desc='Processing Files', leave=False):
                file_path = f"{self.source_path}{folder_name}/{fileName}"
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.readlines()
                    
                    # @ 獲取資料
                    separator = "------------------------------"
                    content_split = self.split_content_by_separator(content, separator) # = [0]第一段：起訴書, 簡易判決  |  [1]第二段：裁判書   
                
                # @ 變數
                original_article_list, article_list, total_article,  = self.re_article(content_split[0]) 
                original_article_list_judge, article_list_judge, total_article_judge,  = self.re_article(content_split[1]) 
                content_charge_indictment = self.re_charges(content_split[0]) 
                content_charge_judgment = self.re_charges(content_split[1], r'裁判案由：(.+)')
                criminals_list = self.re_criminals(content_split[0])
                main_text = self.re_main_text(content_split[1])
                amount_list, total_amount = self.re_amount(main_text)   
                imprisonment_list, total_imprisonment = self.re_imprisonment(main_text)
                imprisonment_count, amount_count = len(imprisonment_list), len(amount_list)
                
                reason = self.re_reason(main_text, amount_count, imprisonment_count)
                
                # @ 存擋格式
                content_dict = {
                    "file": fileName,
                    "fact": self.re_fact(content_split[0]), 
                    "meta": {
                        "relevant_articles": article_list,                  # law, article
                        "relevant_articles_org": original_article_list,     # law + article
                        "#_relevant_articles": total_article,               # article 的數量
                        
                        "relevant_articles_judge": article_list_judge,                  # law, article 下半部(裁判)
                        "relevant_articles_org_judge": original_article_list_judge,     # law + article 下半部(裁判)
                        "#_relevant_articles_judge": total_article_judge,               # article 的數量 下半部(裁判)
                        
                        "indictment_accusation": content_charge_indictment, # 起訴書案由
                        "judgment_accusation": content_charge_judgment,     # 裁判書案由
                        "criminals": criminals_list,                        # 犯罪者們
                        "#_criminals": len(criminals_list),                 # 犯罪者的數量
                        
                        "main_text": main_text,   # 判決主文
                        "term_of_imprisonment": {
                            "death_penalty": self.death_penalty(main_text),              # 死刑
                            "life_imprisonments": self.re_life_imprisonment(main_text),  # 無期徒刑 
                            
                            "imprisonments": imprisonment_list,             # 刑期 List 
                            "#_imprisonments": imprisonment_count,      # 刑期 數量  
                            "total_imprisonment_month": total_imprisonment, # 總共刑期時間 
                            
                            "amounts" : amount_list,                # 罰金 List
                            "#_amounts": amount_count,       # 罰金數量
                            "total_amount": total_amount,           # 罰金總額
                        }
                    },
                    
                    "reason": reason,       # 有罪、無罪、免刑、不受理
                    "penalty": self.re_penalty(amount_count, imprisonment_count),      # 刑期(#2)、罰金(#3)、無
                    "punishment": self.punishment(reason)     # 是(有罪)、否(無罪、免刑、不受理)
                    
                    # "ori_indictment_content": content_split[0],
                    # "ori_judgment_content": content_split[1]
                }
                
                # - 計數器
                # @ 多人犯罪者
                accumulated_criminals_dict[len(criminals_list)] += 1
                accumulated_total_mult_criminals += 1
                    
                self.save_results(accumulated_criminals_dict, 'criminals', accumulated_total_mult_criminals)
                
                # @ 起訴書、簡易判決處刑書： 擷取 charge
                if content_charge_indictment != "":
                    accumulated_total_charges += 1
                    accumulated_charge_dict[content_charge_indictment] += 1
                    
                self.save_results(accumulated_charge_dict, 'charges', accumulated_total_charges)
                    
                # @ 法條數量
                accumulated_total_article += total_article
                for key in original_article_list:
                    accumulated_article_dict[key] += 1
                    
                self.save_results(accumulated_article_dict, 'article', accumulated_total_article)
            
            # @ 存入 JSON
            writeContent.append(content_dict)
                
                
    # ---------------------------------------------------------------------------------------------------- 判決書細項目
    def split_content_by_separator(self, content, separator):
        
        # 尋找分隔符號的
        separator_index = None
        for i, line in enumerate(content):
            
            # 尋找分隔點
            if separator in line:
                separator_index = i
                break
            
        # 若沒有找到
        if separator_index is None:
            return content, []
        
        # 分割內容
        content_before_separator = content[ :separator_index]
        content_after_separator = content[separator_index + 1: ]

        return content_before_separator, content_after_separator
    
    def re_fact(self, content):
        
        is_fact = False # 是否是擷取位置
        result = ""     # 結果
        
        # 使用RE 「犯罪事實」及其變體
        start_pattern = re.compile(r'^\s*(犯\s*罪\s*事\s*實)\s*$')
        end_pattern = re.compile(r'(證\s*據|所\s*犯\s*法\s*條|證\s*據\s*並\s*所\s*犯\s*法\s*條)')
        
        for line in content:
            
            # @ 處理資料，若只是空白則跳過
            if line.strip() == '':
                continue
            
            text = line.replace(u'\u3000', u' ').replace(u'\xa0', u' ').strip()
            start_index = 0

            # STOP: 後文到了則停止
            if end_pattern.search(text):
                is_fact = False
            
            # START:
            if '犯罪事實：' in text:
                start_index = line.index('犯罪事實：') + len('犯罪事實：')
                is_fact = True
                
            # @ 擷取 extraction
            if is_fact:
                result += text[start_index: ]
                
            # START:
            if start_pattern.search(text):
                is_fact = True
            if '犯罪事實' in text and '如下' in text:
                is_fact = True
                
        return result 
    
    def re_article(self, content):
        
        '''
            return example
                Counter({'刑法第30條': 1, '刑法第339條': 1})
        '''
        
        original_article_list = []
        case_reason_list = []
        total_article = 0
        
        is_article_line = False
        for line in content:
            
            # @ 處理資料，若只是空白則跳過
            if line.strip() == '':
                continue
            
            _, _, total_article, is_article_line = self.find_article_extraction(original_article_list, case_reason_list, total_article, line, is_article_line)
            
        return original_article_list, case_reason_list, total_article
    
    def find_article_extraction(self, original_article_list, case_reason_list, total_article, line, is_article_line):
        '''
        
            step1, 2 找到前後文
            step3 根據前後文找到要擷取的範圍後把所有可能性擷取起來
            
            return 
                case_reason_dict => ['刑法第30條', '刑法第339條']
                case_reason_list => [['刑法', '第30條'], ['刑法', '第339條']]
                total_article => 2
                is_article_line  => True / False (下一次是否要擷取)
        '''
        
        default_law_article = [ '刑法', '毒品危害防制條例', '槍砲彈藥刀械管制條例', '藥事法', '著作權法', \
                                '廢棄物清理法', '性騷擾防治法', '公職人員選舉罷免法', '建築法', '家庭暴力防治法', \
                                '就業服務法', '入出國及移民法', '性侵害犯罪防治法', '公司法', '商業會計法', '稅捐稽徵法',\
                                '洗錢防制法', '兒童及少年性剝削防制條例', '區域計畫法', '醫療法', '水土保持法',
                                '組織犯罪防制條例', '妨害兵役治罪條例', '銀行法', '電子遊戲場業管理條例', '醫師法', \
                                '政府採購法', '個人資料保護法', '森林法', '野生動物保育法', '水污染防治法', '臺灣地區與大陸地區人民關係條例', \
                                '動物保護法', '貪污治罪條例', '商標法', '漁業法', '菸酒管理法', '替代役實施條例', '空氣污染防制法', \
                                '動物傳染病防治條例', '期貨交易法']

        # @ step 3: 增加 article
        if is_article_line and '證據並所犯法條' not in line:
            case_reasons = self.load_case_reasons(f"{self.save_path}charges/charges_count.txt")
            all_law_reasons = list(case_reasons) + default_law_article # = 把所有可能性地 law 都結合起來
            
            line_article_list = self.line_split_article(line, all_law_reasons)
            for article in line_article_list:
                combined_article = f'{article[0]}{article[1]}'
                if combined_article not in original_article_list: # 不重複才加入
                    original_article_list.append(combined_article)
                    case_reason_list += [article]
            
        # - 找是否有符合需要找下一行的條件，尋找 article
        article_charges_begin = [   '所犯法條', '所犯法條:', '所犯法條：', '附錄法條', '附錄本案論罪科刑法條全文：', \
                                    '附錄本案論罪科刑法條：', '附錄本案論罪科刑法條', '參考法條', '參考法條：', \
                                    '附錄所犯法條：', '附錄本件論罪科刑法條：', '附錄本案論罪科刑法條:', '附錄本案所犯法條全文', \
                                    '附錄本判決論罪法條全文：', '附錄論罪科刑法條：', '附錄本案論罪法條全文：', '附錄本判決論罪科刑法條：', \
                                    '附錄論罪科刑法條全文：', '附錄本案論罪科刑所適用之法條：', '附錄本案論罪科刑法條：', '所犯法條全文：', '附錄本案論罪科刑法律條文'] # = charges 的上一句
        
        # @ step 1:  找下一行 - a
        for article_charges_beginning in article_charges_begin:
            if article_charges_beginning == line:
                is_article_line = True
                break
            
        # @ step2: 找下一行 - b 
        temp_pattern = re.compile(r'書\s*記\s*官')
        if temp_pattern.search(line):
            is_article_line = True
                
        total_article = len(case_reason_list)
        return original_article_list, case_reason_list, total_article, is_article_line, 
    
    def load_case_reasons(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return {line.split(',')[0].strip() for line in file}
    
    def line_split_article(self, line, law_list):
        # - 把 line 拆解成 陣列模式獲取 list
        
        parts = re.split('，|。|、', line)
        matches = []
        current_prefix = None
        
        for part in parts:
            for law in law_list:
                if law in part:
                    current_prefix = law
                    article_number = re.search(r'第(\d+)條', part)
                    if article_number:
                        # matches.append(f'{current_prefix}第{article_number.group(1)}條')
                        converted_text = self.fullwidth_to_halfwidth(article_number.group(1))
                        matches.append([f'{current_prefix}', f'第{converted_text}條'])
                    break  
                
            else:  
                if current_prefix:
                    article_number = re.search(r'第(\d+)條', part)
                    if article_number:
                        # matches.append(f'{current_prefix}第{article_number.group(1)}條')
                        converted_text = self.fullwidth_to_halfwidth(article_number.group(1))
                        matches.append([f'{current_prefix}', f'第{converted_text}條'])
                        

        return matches
    
    def re_charges(self, content, pattern=r'案　　由：(.+)'):
        
        content_charge = ""
        is_done = False
        
        for line in content:
            content_charge, is_done = self.process_charges_file(content_charge, line, pattern)
            
            if is_done:
                break
            
        return content_charge
                
    def process_charges_file(self, content_charge, line, pattern):
        
        '''
            charges 預設位置：
                「案　　由：{charges}」
        '''
        
        is_done = False
        match = re.search(pattern, line)
        if match:
            case_reason = match.group(1).strip()
            content_charge = case_reason
            
            is_done = True
            
        return content_charge, is_done
                
    def re_criminals(self, content):
        
        criminals = []
        
        is_criminals_line = False
        for line in content:
            
            line_text = line.strip()
            if line_text == '': continue
            
            temp_pattern = re.compile(r'被\s+告')
            if temp_pattern.search(line_text) and ('偵查終結' not in line_text) and ('緩起訴' not in line_text):
                is_criminals_line = True
                
            if any(substring in line_text for substring in ['上列被告', '偵查終結', '緩起訴', '辯護人', '一、', '共同', '住', '身分證']):
                is_criminals_line = False
            
            # 若是犯罪嫌疑人的行，則提取姓名
            if is_criminals_line:
                # 使用正則表達式直接匹配姓名
                match_ori = re.search(r'被\s+告\s*([\u4e00-\u9fa5]+)', line_text)
                match_non_chinese = re.search(r'被\s+告\s*([A-Z ]+)', line_text)
                
                if match_ori:
                    criminal_name = match_ori.group(1)
                    criminals.append(criminal_name)
                    
                elif match_non_chinese:
                    criminal_name = match_non_chinese.group(1)
                    criminals.append(criminal_name)
                    
                else:
                    criminal_name = line_text
                    criminals.append(criminal_name)
                    
        return criminals
    
    def re_main_text(self, content):
        
        # 擷取判決主文
        result_main_text = ""
        is_main_text = False
        
        for line in content:
            
            # @ 處理資料，若只是空白則跳過
            if line.strip() == '':
                continue
            
            text = line.replace(u'\u3000', u' ').replace(u'\xa0', u' ').strip()

            # 後文到了則停止
            temp_pattern = re.compile(r'^\s*(犯\s*罪\s*事\s*實\s*及\s*理\s*由|犯\s*罪\s*事\s*實|事\s*實\s*及\s*理\s*由|事\s*實|理\s*由|犯\s*罪\s*事\s*實\s*及\s*證\s*據\s*名\s*稱)\s*$')
            if temp_pattern.search(line) or ('犯' in line and '罪' in line and '事' in line and '實' in line) or  ('理' in line and '由' in line and '事' in line and '實' in line):
                is_main_text = False
                break
            
            # @ 擷取 extraction
            if is_main_text:
                result_main_text += text
                
            # 前文找到則開始
            temp_pattern = re.compile(r'^\s*主\s*文\s*$')
            if temp_pattern.search(line):
                is_main_text = True
        
        return result_main_text
    
    def re_amount(self, line):
        pattern = re.compile(r"罰金新臺幣([\u4e00-\u9fff]+)元")
        matches = pattern.findall(line)  # 使用 findall 來找到所有匹配
        
        amount_list = []
        for match in matches:
            regular_match = cn2an.cn2an(match, 'smart')
            amount_list.append(regular_match)  # 將每個匹配的金額添加到列表中

        return amount_list, sum(amount_list)
    
    def re_imprisonment(self, line):
        
        def parse_time(time_str):
            # 解析時間字符串，返回年、月、日的數值
            try:
                return cn2an.cn2an(self.chinese_to_int(time_str) if time_str != '' else 0, 'smart')
            except ValueError as e:
                print(f"轉換錯誤：'{time_str}' 轉換失敗。錯誤訊息：{e}")
                return 0
        
        imprisonments = []
        total_imprisonment = 0
        
        if '年' in line or '月' in line or '日' in line:

            # 有期徒刑的正則表達式
            pattern_imprisonment = re.compile(r'有期徒刑(?:([\u4e00-\u9fff]{1,2})年)?(?:([\u4e00-\u9fff]{1,2})月)?(?:(?:又)([\u4e00-\u9fff]{1,2})日)?')
            matches_imprisonment = pattern_imprisonment.findall(line)
            
            for match in matches_imprisonment:
                years, months, days = match

                if not (years or months or days):
                    continue
                try:
                    years = cn2an.cn2an((self.chinese_to_int(years)) if years != '' else 0, 'smart')
                except ValueError as e:
                    logging.info(f"轉換錯誤：年份 '{years}' 轉換失敗。錯誤訊息：{e} \n{match}: {line}")
                    years = 0  

                try:
                    months = cn2an.cn2an(self.chinese_to_int(months) if months != '' else 0, 'smart')
                except ValueError as e:
                    logging.info(f"轉換錯誤：月份 '{months}' 轉換失敗。錯誤訊息：{e} \n{match}: {line}")
                    months = 0  

                try:
                    days = cn2an.cn2an(self.chinese_to_int(days) if days != '' else 0, 'smart')
                except ValueError as e:
                    logging.info(f"轉換錯誤：日數 '{days}' 轉換失敗。錯誤訊息：{e} \n{match}: {line}")
                    days = 0  

                if years != 0 or months != 0 or days != 0:
                    imprisonment_str = f"有期徒刑{years}年{months}月{days}日" if days else f"有期徒刑{years}年{months}月"
                    imprisonments.append(imprisonment_str)
                    
                total_imprisonment += (years * 12) + months + (days / 30)

            # 處拘役的正則表達式
            pattern_detention = re.compile(r'處拘役(?:([\u4e00-\u9fff]{1,2})年)?(?:([\u4e00-\u9fff]{1,2})月)?(?:([\u4e00-\u9fff]{1,2})日)?')
            matches_detention = pattern_detention.findall(line)

            for match in matches_detention:
                years, months, days = match
                
                if not (years or months or days):
                    continue
                try:
                    years = cn2an.cn2an(self.chinese_to_int(years) if years != '' else 0, 'smart')
                except ValueError as e:
                    print(f"轉換錯誤：年份 '{years}' 轉換失敗。錯誤訊息：{e} \n{match}: {line}")
                    years = 0  

                try:
                    months = cn2an.cn2an(self.chinese_to_int(months) if months != '' else 0, 'smart')
                except ValueError as e:
                    print(f"轉換錯誤：月份 '{months}' 轉換失敗。錯誤訊息：{e} \n{match}: {line}")
                    months = 0  

                try:
                    days = cn2an.cn2an(self.chinese_to_int(days) if days != '' else 0, 'smart')
                except ValueError as e:
                    print(f"轉換錯誤：日數 '{days}' 轉換失敗。錯誤訊息：{e} \n{match}: {line}")
                    days = 0  
                    
                if years != 0 or months != 0 or days != 0:
                    detention_str = f"拘役{years}年{months}月{days}日" if days else f"拘役:{years}年{months}月"
                    imprisonments.append(detention_str)
                    
                total_imprisonment += (years * 12) + months + (days / 30)
                
        return imprisonments, math.ceil(total_imprisonment)
    
    def re_life_imprisonment(self, line):
        
        result = False
        if '無期徒刑' in line:
            result = True
            
        return result
    
    def death_penalty(self, line):
        
        result = False
        if '死刑' in line:
            result = True
            
        return result
    
    def re_amount(self, line):
        pattern = re.compile(r"罰金新臺幣([\u4e00-\u9fff]+)元")
        matches = pattern.findall(line)  # 使用 findall 來找到所有匹配
        
        amount_list = []
        for match in matches:
            regular_match = cn2an.cn2an(self.chinese_to_int(match), 'smart')
            amount_list.append(regular_match)  # 將每個匹配的金額添加到列表中

        return amount_list, sum(amount_list)
    
    def re_reason(self, line, amount_count, imprisonment_count):
        """
            (0) 無罪
            (1) 有罪
            (2) 免刑
            (3) 不受理
        """
        result = -1
        if '無罪' in line:
            result = 0
        if '免刑' in line:
            result = 2
        if '不受理' in line:
            result = 3
        if amount_count != 0 or imprisonment_count != 0:
            result = 1
            
        return result
    
    def re_penalty(self, _amounts=0, _imprisonments=0):
        
        """
            (0) 無
            (1) 刑期
            (2) 罰金
            (3) 刑期＋罰金
        """
        
        if _amounts == 0 and _imprisonments == 0:
            return 0
        elif _amounts == 0 and _imprisonments != 0:
            return 1
        elif _amounts != 0 and _imprisonments == 0:
            return 2
        elif _amounts != 0 and _imprisonments != 0:
            return 3
        
    def punishment(self, reason):
        
        if reason != 1:
            return True
        elif reason == 1:
            return False
        else:
            return None
        
    
    # ---------------------------------------------------------------------------------------------------- 其他程式碼
    
    # -v- 儲存個別結果
    def save_results(self, case_reason_count, file_type, accumulated_total):
        sorted_case_reasons = sorted(case_reason_count.items(), key=lambda x: x[1], reverse=True)

        # 保存計數結果
        save_file_path = f"{self.save_path}{file_type}/{file_type}_count.txt"
        with open(save_file_path, 'w', encoding='utf-8') as writeFile:
            for reason, count in sorted_case_reasons:
                writeFile.write(f"{reason}, {count}\n")

        # 僅保存案由
        save_file_path = f"{self.save_path}{file_type}/{file_type}.txt"
        with open(save_file_path, 'w', encoding='utf-8') as writeFile:
            for reason, _ in sorted_case_reasons:
                writeFile.write(f"{reason}\n")        
        
    # -v- 全行文字轉半形
    def fullwidth_to_halfwidth(self, text):
        result = ""
        for char in text:
            code = ord(char)
            if 0xFF10 <= code <= 0xFF19:  # 全形數字的範圍
                halfwidth_char = chr(code - 0xFEE0)
                result += halfwidth_char
            else:
                result += char
        return result
    
    def save_to_json(self, save_file_path, filename, writeContent, comment=''):
        """
        Save data to a JSON file.

        Args:
            save_file_path (str): The path to the directory where the file will be saved.
            filename (str): The name of the file to save the data in.
            writeContent (list): The content to write to the file.
        """
        
        # 確保保存文件的目錄存在
        if not path.isdir(save_file_path):
            mkdir(save_file_path)

        # 拼接完整的文件路徑
        full_path = path.join(save_file_path, filename)

        # 寫入數據到文件
        with open(full_path, 'w', encoding="utf-8") as writeFile:
            for item in writeContent:
                writeFile.write(json.dumps(item, ensure_ascii=False))
                writeFile.write('\n')
                
        print(f"Save To {full_path}!\n{comment}")
            
    # -v- 將 list 存到 file_path
    def save_to_file(self, file_path, content):
        with open(file_path, 'w', encoding='utf-8') as writeFile:
            writeFile.write(content)
    
    # -v- 防呆資料夾
    def check_and_create_directories(self, save_path, required_dirs_=['charges', 'article', 'criminals', 'log']):
        required_dirs = required_dirs_
        for dir in required_dirs:
            full_path = path.join(save_path, dir)
            if not path.isdir(full_path):
                mkdir(full_path)
                
    # -v- 初始化 logging
    def initialize_logging(self, save_path):
        log_file_path = f'{save_path}log/ProcessAILA.log'
        logging.basicConfig(filename=log_file_path, level=logging.INFO,
                            format='%(asctime)s:%(levelname)s:%(message)s')
        logging.Formatter = TaiwanTimeFormatter
        logging.info(f"-------------------------------------------------------------")
    
    # -v- 新增的 initialize_accumulators 方法
    def initialize_accumulators(self):
        accumulated_charge_dict = defaultdict(int)
        accumulated_article_dict = defaultdict(int)
        accumulated_criminals_dict = defaultdict(int)
        accumulated_total_charges = 0
        accumulated_total_article = 0
        accumulated_total_mult_criminals = 0

        return (accumulated_charge_dict, accumulated_article_dict, accumulated_criminals_dict, 
                accumulated_total_charges, accumulated_total_article, accumulated_total_mult_criminals)
        
        
    def chinese_to_int(self, text):

        num_dict = {
            '零': '0', '０': '0',
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
    

# ---------------------------------------------------------------------------------------------------- Default implementation    

class Mode(Enum):
    FORMAL_EXPECT_PROBLEM = 0
    TEST = 1
    DOING = 2

    @staticmethod
    def from_string(s):
        if s in ["test", "1"]:
            return Mode.TEST
        elif s in ["doing", "2"]:
            return Mode.DOING
        else:
            return Mode.FORMAL_EXPECT_PROBLEM
        
        
class TaiwanTimeFormatter(logging.Formatter):
    converter = time.localtime

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = "%s,%03d" % (t, record.msecs)
        return s
    
