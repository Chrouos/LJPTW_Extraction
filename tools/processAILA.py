import io
import json
import logging
import math
import random
import re
import shutil
import sys
import time
from collections import defaultdict, Counter
from datetime import datetime
from enum import Enum
from os import listdir, mkdir, path, remove

import pandas as pd
from sklearn.model_selection import train_test_split
from tqdm import tqdm

sys.path.append('./tools')
from processNumber import auto_translate_ch_to_int_number

class ProcessAILA:

    # -v- 初始化
    def __init__(self,  save_path, source_path, expect_folder=['test', 'problem_file', 'doing'], 
                        mode=0, limit_counts=None, isRandomData=False):
        
        # - 預設值
        self.isRandomData = isRandomData
        
        # - 資料路徑
        self.source_path = source_path
        self.save_path = save_path
        
        self.check_and_create_directories(self.save_path)   # = 路徑防呆
        self.initialize_logging(self.save_path) # = 初始化 logging
        
        # - 獲得所有資料夾與之子之資料名稱
        folders = listdir(self.source_path)
        mode = Mode.from_string(mode)
        print("Here is Running by {} mode".format(mode))
        
        # @ 模式
        if mode == Mode.TEST:
            self.source_folderList = [folder for folder in folders if folder == 'test']
        elif mode == Mode.DOING:
            self.source_folderList = [folder for folder in folders if folder == 'doing']
        elif mode == Mode.EXPECT_PROBLEM:
            self.source_folderList = [folder for folder in folders if folder not in expect_folder]
            
        self.limit_counts = -1 if limit_counts == None else round(int(limit_counts) / len(self.source_folderList)) # 預設要取多少
        # - 保存每個資料夾中的檔案名稱
        self.source_fileList= {} 
        for folder in self.source_folderList:
            files = listdir(self.source_path + folder)
            self.source_fileList[folder] = sorted(file for file in files)
           
    # -v- 計算數量
    def countLength_souce(self):
        
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
        
    # --------------------------------------------------  主要 function
                    
    def TWLJP_JSON(self, is_statistic_charge=True, is_statistic_article=True, is_statistic_criminals=True):
        
        writeContent = []
        
        # - 初始化累積的字典和計數器
        (accumulated_charge_dict, accumulated_article_dict, accumulated_criminals_dict, 
         accumulated_total_charges, accumulated_total_article, accumulated_total_mult_criminals) = self.initialize_accumulators()
        
        total_folders = len(self.source_folderList)
        folder_progress = tqdm(self.source_folderList, desc='Processing Folders', total=total_folders)
        
        total_count = 0
        
        # - 動作
        for folder_name in folder_progress: # = outerLoop 資料夾名稱
            folder_progress.set_description(f"Processing {folder_name}")
            temp_fileList = self.source_fileList[folder_name]
            
            limit_count = min(len(temp_fileList), self.limit_counts) if self.limit_counts != -1 else len(temp_fileList)
            
            if self.isRandomData == True: limit_fileList = random.sample(temp_fileList, limit_count)
            else: limit_fileList = temp_fileList[:limit_count]  
            
            total_count += len(limit_fileList)
            logging.info(f"{folder_name} 取 {limit_count} 筆資料")
            for fileName in tqdm(limit_fileList, desc='Processing Files', leave=False):
                
                file_path = f"{self.source_path}{folder_name}/{fileName}"
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.readlines()
                    
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
                
                # @ 最後存檔
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
                            "#_imprisonments": len(imprisonment_list),      # 刑期 數量  
                            "total_imprisonment_month": total_imprisonment, # 總共刑期時間 
                            
                            "amounts" : amount_list,                                         # 罰金 List
                            "#_amounts": len(amount_list),                                   # 罰金數量
                            "total_amount": total_amount,                               # 罰金總額
                        }
                    },
                    
                    # "ori_indictment_content": content_split[0],
                    # "ori_judgment_content": content_split[1]
                }
                
                # - 計數器
                # @ 多人犯罪者
                if is_statistic_criminals:
                    accumulated_criminals_dict[len(criminals_list)] += 1
                    accumulated_total_mult_criminals += 1
                    
                    self.save_results(accumulated_criminals_dict, 'criminals', accumulated_total_mult_criminals)
                
                # @ 起訴書、簡易判決處刑書： 擷取 charge
                if is_statistic_charge:
                    if content_charge_indictment != "":
                        accumulated_total_charges += 1
                        accumulated_charge_dict[content_charge_indictment] += 1
                        
                    self.save_results(accumulated_charge_dict, 'charges', accumulated_total_charges)
                    
                # @ 法條數量
                if is_statistic_article:
                    accumulated_total_article += total_article
                    for key in original_article_list:
                        accumulated_article_dict[key] += 1
                        
                    self.save_results(accumulated_article_dict, 'article', accumulated_total_article)
            
                # @ 存入 JSON
                writeContent.append(content_dict)
            
            
            # - 儲存檔案
            save_file_path = f"{self.save_path}/TWLJP/"
            file_name = "all_data.json"
            json_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in writeContent])
            self.check_and_create_directories(self.save_path, ['TWLJP'])   # = 路徑防呆
            self.save_to_file(f"{save_file_path}{file_name}", json_content)
                
        # - 在文件處理完畢後保存結果
        logging.info(f"這次總共取樣 {total_count} 筆資料")
        if is_statistic_criminals: 
            logging.info(f"re_criminals 總共 {accumulated_total_mult_criminals}, 1個犯罪者: {accumulated_criminals_dict[1]}, 0個犯罪者的: {accumulated_criminals_dict[0]}")
        if is_statistic_charge: 
            logging.info(f"re_article 總共 {accumulated_total_article}")
        if is_statistic_article: 
            logging.info(f"re_charges 總共 {accumulated_total_charges}")
        
    # --------------------------------------------------  擷取 主要 function
        
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
            
    def re_charges(self, content, pattern=r'案　　由：(.+)'):
        
        content_charge = ""
        is_done = False
        
        for line in content:
            content_charge, is_done = self.process_charges_file(content_charge, line, pattern)
            
            if is_done:
                break
            
        return content_charge

    def re_article(self, content):
        
        '''
            return example
                Counter({'刑法第30條': 1, '刑法第339條': 1})
        '''
        
        # case_reason_dict = Counter()
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

    def re_imprisonment(self, line):
        
        imprisonments = []
        total_imprisonment = 0
        
        if '年' in line or '月' in line or '日' in line:

            # 有期徒刑的正則表達式
            pattern_imprisonment = re.compile(r'有期徒刑(?:([\u4e00-\u9fff]+)年)?(?:([\u4e00-\u9fff]+)月)?(?:([\u4e00-\u9fff]+)日)?')
            matches_imprisonment = pattern_imprisonment.findall(line)
            
            for match in matches_imprisonment:
                years, months, days = match
                if not (years or months or days):
                    continue
                
                years = auto_translate_ch_to_int_number(years if years else '零')
                months = auto_translate_ch_to_int_number(months if months else '零')
                days = auto_translate_ch_to_int_number(days if days else '')
                if years != '零' or months != '零' or days:
                    imprisonment_str = f"有期徒刑{years}年{months}月{days}日" if days else f"有期徒刑{years}年{months}月"
                    imprisonments.append(imprisonment_str)
                    
                total_imprisonment += (years * 12) + months + (days / 30)

            # 處拘役的正則表達式
            pattern_detention = re.compile(r'處拘役(?:([\u4e00-\u9fff]+)年)?(?:([\u4e00-\u9fff]+)月)?(?:([\u4e00-\u9fff]+)日)?')
            matches_detention = pattern_detention.findall(line)

            for match in matches_detention:
                years, months, days = match
                if not (years or months or days):
                    continue
                
                years = auto_translate_ch_to_int_number(years if years else '零')
                months = auto_translate_ch_to_int_number(months if months else '零')
                days = auto_translate_ch_to_int_number(days if days else '')
                if years != '零' or months != '零' or days:
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
            regular_match = auto_translate_ch_to_int_number(match)
            amount_list.append(regular_match)  # 將每個匹配的金額添加到列表中

        return amount_list, sum(amount_list)


    # -------------------------------------------------- 內部 function
            
    def process_charges_file(self, content_charge, line, pattenr):
        
        '''
            charges 的擷取位置在
                「案　　由：...」
            之後的位置如
                「案　　由：侵占」
        '''
        
        is_done = False
        match = re.search(pattenr, line)
        if match:
            case_reason = match.group(1).strip()
            content_charge = case_reason
            
            is_done = True
            
        return content_charge, is_done
               
    def load_case_reasons(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return {line.split(',')[0].strip() for line in file}

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
                    
    # -------------------------------------------------- 其他
    
    def save_results(self, case_reason_count, file_type, total_charges):
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
        
    def final_result_save_excel(self):
        output_file = self.save_path + 'result.xlsx'
        if path.exists(output_file):
            remove(output_file)

        # 創建一個新的 Excel 檔案
        pd.DataFrame().to_excel(output_file)

        with pd.ExcelWriter(output_file, engine='openpyxl', mode='a') as writer:
            # 檢查 'charges' 和 'article' 資料夾是否存在
            for folder in ['charges', 'article']:
                folder_path = self.save_path + folder
                if not path.isdir(folder_path):
                    print(f"Directory {folder_path} does not exist.")
                    continue
                
                files = listdir(self.save_path + folder)
                count_files = [file for file in files if 'count' in file]
                
                for file in count_files:
                    data = pd.read_csv(self.save_path + folder + '/' + file, header=None, names=['Key', 'Count'])
                    data.to_excel(writer, sheet_name=file, index=False)
                    
                    
            single_file = [ {'countLength_source.txt': ['Key', "Count"]}, {'notExit_fileName.txt': ['index', "source_file", "unExit"]}]
            for file_dict in single_file:
                for file_name, headers in file_dict.items():
                    data = pd.read_csv(self.save_path + file_name, header=None, names=headers)
                    data.to_excel(writer, sheet_name=file_name, index=False)
                
    # ----- 抽樣 20 筆到 test
    def copy_random_files(self, number_of_files=20):
        
        all_files = []
        for folder in self.source_folderList:
            folder_path = self.source_path + folder
            files_in_folder = [folder_path + "/" + f for f in self.source_fileList[folder]]
            all_files.extend(files_in_folder)

        # 隨機選取檔案
        selected_files = random.sample(all_files, min(len(all_files), number_of_files))

        # 確保目標目錄存在
        test_dir = f"{self.source_path}test/" 
        self.clear_directory(test_dir)
        
        if not path.exists(test_dir):
            mkdir(test_dir)

        # 複製檔案
        for file in selected_files:
            shutil.copy(file, test_dir)
            
    # 起訴書、判決書
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
        
    def check_files_existence(self, check_file_path_folder):
        
        check_file_folder = self.save_path + check_file_path_folder + "/"
        files = listdir(check_file_folder)
        
        writeContent = []
        
        for file_name in files:
            file_path = check_file_folder + file_name
            with open(file_path, 'r', encoding='utf-8') as line_file:
                for index, line in enumerate(line_file):
                    
                    # @ 擷取檔名
                    json_content = json.loads(line)
                    json_file_name = json_content['file']
                    
                    # @ 擷取地區
                    pattern = re.compile(r'(?:臺灣|福建)?(\w+地方檢察署)')
                    match = pattern.search(json_file_name)
                    
                    if match:
                        area = match.group(1)  # 地名
                        list_to_check = self.source_fileList.get(area, self.source_fileList.get('problem_file', []))
                        
                        if json_file_name not in list_to_check:
                            writeContent.append("{:<5}, {:<20}, {:<50}".format(index, file_name, json_file_name))
                                                        
                    else:
                        print("未找到匹配 match 地區 ", json_file_name)
                        
            break
                    
        # @ 儲存檔案
        save_file_path = f"{self.save_path}notExit_fileName.txt"
        with open(save_file_path, 'w', encoding='utf-8') as writeFile:
            writeFile.write("\n".join(writeContent))
        
    def load_data(self, file_path="/TWLJP/all_data.json"):
        
        # 獲取檔案 all_data 拆檔案
        all_data = []
        with open(self.save_path + file_path, 'r', encoding="utf-8") as file:
            for line in file:
                all_data.append(json.loads(line))
                
        return all_data
    
    # 拆檔案 test_size validation_size
    def train_test_split(self, file_path="/TWLJP/all_data.json", test_size=0.2, validation_size=0.1):
        
        # 獲取檔案 all_data 拆檔案
        
        all_data = self.load_data(file_path)
        
        train_data, test_data = train_test_split(all_data, test_size=test_size) # 分割訓練集和測試集
        train_data, validation_data = train_test_split(train_data, test_size=validation_size / (1 - test_size)) # 再從訓練集中分割出驗證集

        # 將分割後的資料儲存為不同的檔案
        for data, suffix in zip([train_data, test_data, validation_data], ['train', 'test', 'validation']):
            with open(f'{self.save_path}TWLJP/{suffix}.json', 'w', encoding='utf-8') as file:
                for item in data:
                    file.write(json.dumps(item, ensure_ascii=False))
                    file.write('\n')
                    
        
    def random_samples(self, random_size = 10, file_path="/TWLJP/all_data.json"):
        
        save_path = f'{self.save_path}TWLJP/random.json'
        print(f"Do the [random_samples] (size={random_size}) from={file_path}, in={save_path}")
        
        all_data = self.load_data(file_path)
        if len(all_data) > random_size:
            random_data = random.sample(all_data, random_size)
        else:
            print(f"random_size({random_size}) < total_size({len(all_data)})")
            random_data = all_data
        
        # 隨機抽取 random_size 筆數據
        with open(save_path, 'w', encoding='utf-8') as file:
            for item in random_data:
                file.write(json.dumps(item, ensure_ascii=False))
                file.write('\n')

    
    def remove_multiple_criminals(self):
        
        print("Do the [remove_multiple_criminals] Now.")
        all_data = self.load_data()
        sigle_data = []
        for data in all_data:
            if data['meta']['#_criminals'] == 1 or data['meta']['#_criminals'] == 0 :
                sigle_data.append(data)
            
        
        with open(f'{self.save_path}TWLJP/sigleCriminal_allData.json', 'w', encoding='utf-8') as file:
            for item in sigle_data:
                file.write(json.dumps(item, ensure_ascii=False))
                file.write('\n')
                
        logging.info(f"刪除多個犯罪者: {len(all_data)} -> {len(sigle_data)} (-{len(all_data) - len(sigle_data)})")
        
        
    # 全行文字轉半形
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
    
    # -v- 初始化 logging
    def initialize_logging(self, save_path):
        log_file_path = f'{save_path}log/ProcessAILA.log'
        logging.basicConfig(filename=log_file_path, level=logging.INFO,
                            format='%(asctime)s:%(levelname)s:%(message)s')
        logging.Formatter = TaiwanTimeFormatter
        logging.info(f"-------------------------------------------------------------")

    # -v- 防呆資料夾
    def check_and_create_directories(self, save_path, required_dirs_=['', 'charges', 'article', 'criminals', 'log']):
        required_dirs = required_dirs_
        for dir in required_dirs:
            full_path = path.join(save_path, dir)
            if not path.isdir(full_path):
                mkdir(full_path)
                
    # -v- 將 list 存到 file_path
    def save_to_file(self, file_path, content):
        with open(file_path, 'w', encoding='utf-8') as writeFile:
            writeFile.write(content)
        
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
    
class Mode(Enum):
    EXPECT_PROBLEM = 0
    TEST = 1
    DOING = 2

    @staticmethod
    def from_string(s):
        if s in ["test", "1"]:
            return Mode.TEST
        elif s in ["doing", "2"]:
            return Mode.DOING
        else:
            return Mode.EXPECT_PROBLEM