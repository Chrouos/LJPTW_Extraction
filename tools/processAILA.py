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
from os import listdir, makedirs, path, remove, makedirs
from os.path import isdir, join

import pandas as pd
from sklearn.model_selection import train_test_split
from tqdm import tqdm

import cn2an

sys.path.append('./tools')
from operation import chinese_to_int, convert_fullwidth_to_halfwidth


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
        
        # - 模式
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
            self.source_fileList[folder] = sorted(file for file in files if file != '.DS_Store')
            
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
        writeContent.append(f"總共 {total_count}")

        # @ 儲存檔案
        save_file_path = f"{self.save_path}countLength_source.txt"
        self.save_to_file(save_file_path, "\n".join(writeContent))
        
        
    # -v- TWLJP
    def TWLJP_JSON(self):
        
        writeContent = []
        
        
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
                
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    content = file.readlines()
                    
                    # @ 獲取資料
                    separator = "------------------------------"
                    content_split = self.split_content_by_separator(content, separator) # = [0]第一段：起訴書, 簡易判決  |  [1]第二段：裁判書   
                
                # @ 變數
                fact = self.re_fact(content_split[0], fileName)
                main_text = self.re_main_text(content_split[1], fileName)
                
                # @ article, charge, criminals, accusation
                relevant_articles_org, article_list, total_article,  = self.re_article(content_split[0]) 
                relevant_articles_org_judge, article_list_judge, total_article_judge,  = self.re_article(content_split[1]) 
                criminals_list = self.re_criminals(content_split[0])
                total_criminals = len(criminals_list)
                
                indictment_accusation = self.re_charges(content_split[0]) 
                judgment_accusation = self.re_charges(content_split[1], r'裁判案由：(.+)')
                
                
                imprisonment_list, total_imprisonment = self.re_imprisonment(main_text, fileName)
                amount_list, total_amount = self.re_amount(main_text, fileName)   
                imprisonment_count, amount_count = len(imprisonment_list), len(amount_list)
                
                death_penalty = self.death_penalty(main_text)
                life_imprisonments = self.re_life_imprisonment(main_text)
                
                judgment_number = self.re_charges(content_split[1], r'裁判字號：(.+)')
                reason = self.re_reason(main_text, amount_count, imprisonment_count, fileName, judgment_number)
                penalty = self.re_penalty(amount_count, imprisonment_count)
                
                
                
                # @ 存擋格式
                content_dict = {
                    "file": fileName,
                    "fact": fact, 
                    "main_text": main_text,   # 判決主文
                    "meta": {
                        
                        "#_relevant_articles": total_article,               # article 的數量 (default = 0)
                        "relevant_articles": article_list,                  # articles (default = [])
                        "relevant_articles_org": relevant_articles_org,     # Law + Article (default = [])
                        
                        
                        "#_relevant_articles_judge": total_article_judge,               # article(主文) 的數量 (default = 0)
                        "relevant_articles_judge": article_list_judge,                  # articles(主文) (default = [])
                        "relevant_articles_org_judge": relevant_articles_org_judge,     # Law + Article(主文) (default = [])
                        
                        "#_criminals": total_criminals,     # 犯罪者的數量 (default = 0)
                        "criminals": criminals_list,        # 犯罪者們 (default = [])
                        
                        "indictment_accusation": indictment_accusation, # 起訴書案由 (default = "")
                        "judgment_accusation": judgment_accusation,     # 裁判書案由 (default = "")
                        
                        "term_of_imprisonment": {
                            
                            "death_penalty": death_penalty,             # 死刑 (default = False)
                            "life_imprisonments": life_imprisonments,   # 無期徒刑 (default = False)
                            
                            "#_imprisonments": imprisonment_count,          # 刑期 數量 (default = 0)
                            "imprisonments": imprisonment_list,             # 刑期s (default = [])
                            "total_imprisonment_month": total_imprisonment, # 總共刑期時間(月) (default = 0)
                            
                            "#_amounts": amount_count,      # 罰金 數量 (default = 0)
                            "amounts" : amount_list,        # 罰金s (default = [])
                            "total_amount": total_amount,   # 罰金總額 總共刑期時間 (default = 0)
                        }
                    },
                    
                    "reason": reason,   # (0) 無罪  (1) 有罪 (2) 免刑 (3) 不受理  (default = (-1) 未抓取成功 )
                    "penalty": penalty, # (0) 無 (1) 只有刑期 (2) 只有罰金 (3) 刑期＋罰金
                    "punishment": self.punishment(reason),     # True(有罪)、False(無罪、免刑、不受理)
                    
                    "ori_indictment_content": content_split[0],
                    "ori_judgment_content": content_split[1]
                }
                
                # @ 存入 JSON
                writeContent.append(content_dict)
            
        # - 儲存檔案
        save_file_path = f"{self.save_path}/TWLJP/"
        file_name = "all_data.json"
        json_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in writeContent])
        self.check_and_create_directories(self.save_path, ['TWLJP'])   # = 路徑防呆
        self.save_to_file(f"{save_file_path}{file_name}", json_content)
                

    # -v- 過濾資料
    def filter_TWLJP(self, 
                        threshold = {"name": "article_charge", "number": 30}, 
                        file_name="all_data.json",
                        reference_dir='ori/'
                    ):
        
        filtered_data = []
        filtered_counting = 0
        threshold_data = self.load_status_data(threshold['name'], reference_dir)
        all_data = self.load_data(file_name)
        
        delete_count = {
            "未達 article_charge 標準": 0,
            "Reason 是「未抓取成功」/「裁定判決」": 0,
            "不存在main_text, fact...": 0,
            "多位犯罪者": 0,
            "沒擷取到犯罪者資訊": 0
        }
        for data in tqdm(all_data, desc="filter_TWLJP"):
            
            keep_data = True  # 預設為保留數據
            
            # @ 檢查 article-charge
            for article in data['meta']['relevant_articles_org']:
                if threshold['name'] == 'article_charge':
                    combined_key = f"{article}-{data['meta']['indictment_accusation']}"
                    if int(threshold_data[combined_key]) <= int(threshold['number']): # 如果不符合條件，標記為不保留
                        keep_data = False  
                        delete_count["未達 article_charge 標準"] += 1
                    
            # @ 檢查 reason
            if data['reason'] == 4 or data['reason'] == -1:
                keep_data = False
                delete_count["Reason 是「未抓取成功」/「裁定判決」"] += 1
                
            # @ 檢查不存在項目
            if data['fact'] == "" or data['main_text'] == "" or data['meta']['indictment_accusation'] == "" or data['meta']['judgment_accusation'] == "":
                keep_data = False
                delete_count["不存在main_text, fact..."] += 1
                
            # @ 刪掉多位犯罪者
            if int(data['meta']['#_criminals']) > 1:
                keep_data = False
                delete_count["多位犯罪者"] += 1
                
            # @ 沒截到犯罪者
            if int(data['meta']['#_criminals']) < 1:
                keep_data = False
                delete_count["沒擷取到犯罪者資訊"] += 1
                    
            if keep_data: filtered_data.append(data)  # 只有符合條件的數據才被添加
            else: filtered_counting += 1
                
            
        # - 儲存檔案
        save_file_path = f"{self.save_path}/TWLJP/"
        file_name = "filter_data.json"
        json_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in filtered_data])
        self.check_and_create_directories(self.save_path, ['TWLJP'])   # = 路徑防呆
        self.save_to_file(f"{save_file_path}{file_name}", json_content)
        
        # @ 結果
        final_result = f"[filter_TWLJP] 從 {file_name} 中，過濾資料: {len(all_data)} -> {filtered_counting} ( 刪掉 -{len(all_data) - filtered_counting})"
        logging.info(final_result)
        logging.info(f"\t未達 article_charge 標準: {delete_count['未達 article_charge 標準']}")
        logging.info(f"\tReason 是「未抓取成功」/「裁定判決」: {delete_count['Reason 是「未抓取成功」/「裁定判決」']}")
        logging.info(f"\t不存在main_text, fact...: {delete_count['不存在main_text, fact...']}")
        logging.info(f"\t多位犯罪者: {delete_count['多位犯罪者']}")
        logging.info(f"\t沒擷取到犯罪者資訊: {delete_count['沒擷取到犯罪者資訊']}")
        
        filter_content = [f"{key}, {value}" for key, value in delete_count.items()]
        filter_content.append(final_result)
        save_filter_file_path = f"{self.save_path}filter_result.txt"
        self.save_to_file(save_filter_file_path, "\n".join(filter_content))
        
        
    # -v- 資料內容 filter
    def counting_status(self, file_name="all_data.json", save_dir='ori/'):
        (
            accumulated_charge_dict, accumulated_article_dict, accumulated_combine_article_charge_dict, accumulated_law,
            accumulated_criminals_dict, accumulated_penalty_dict, accumulated_reason_dict,
            accumulated_error_dict,
            
            accumulated_total_charges, accumulated_total_article, accumulated_total_combine_article_charge, accumulated_total_law,
            accumulated_total_multi_criminals, accumulated_total_penalty, accumulated_total_reason,
            accumulated_total_error
            
        ) = self.initialize_accumulators()
        self.check_and_create_files([   'charges', 'article', 'criminals', 
                                        'penalty', 'reason', 'article_charge',
                                        'error' ],
                                    save_dir)
        all_data = self.load_data(file_name)
        for data in tqdm(all_data, desc="counting_status"):
            
            # - 計數器
                
            # @ Reason 狀況
            accumulated_reason_dict[REASON(data['reason']).name] += 1
            accumulated_total_reason += 1
            self.save_results(accumulated_reason_dict, 'reason', accumulated_total_reason, save_dir)
        
            # @ Penalty 狀況
            accumulated_penalty_dict[PENALTY(data['penalty']).name] += 1
            accumulated_total_penalty += 1
            self.save_results(accumulated_penalty_dict, 'penalty', accumulated_total_penalty, save_dir)
        
            # @ 多人犯罪者
            accumulated_criminals_dict[data['meta']['#_criminals']] += 1
            accumulated_total_multi_criminals += 1
            self.save_results(accumulated_criminals_dict, 'criminals', accumulated_total_multi_criminals, save_dir)
        
            # @ 起訴書、簡易判決處刑書： charge
            if data['meta']['indictment_accusation'] != "":
                accumulated_total_charges += 1
                accumulated_charge_dict[data['meta']['indictment_accusation']] += 1
            self.save_results(accumulated_charge_dict, 'charges', accumulated_total_charges, save_dir)
            
            # @ 法條數量: article
            accumulated_total_article += data['meta']['#_relevant_articles']
            for key in data['meta']['relevant_articles_org']:
                accumulated_article_dict[key] += 1
            self.save_results(accumulated_article_dict, 'article', accumulated_total_article, save_dir)
        
            # @ article + charge
            for article in data['meta']['relevant_articles_org']:
                combined_key = f"{article}, {data['meta']['indictment_accusation']}"
                accumulated_combine_article_charge_dict[combined_key] += 1
                accumulated_total_combine_article_charge += 1
            self.save_results(accumulated_combine_article_charge_dict, 'article_charge', accumulated_total_combine_article_charge, save_dir)
        
            # @ law
            for article in data['meta']['relevant_articles']:
                accumulated_law[article[0]] += 1
                accumulated_total_law += 1
            self.save_results(accumulated_law, 'law', accumulated_total_law, save_dir)
                
        
            # @ ERROR
            if data['main_text'] == '':
                accumulated_error_dict['main_text'] += 1
            if data['fact'] == '':
                accumulated_error_dict['fact'] += 1
            if data['reason'] == -1:
                accumulated_error_dict['reason'] += 1
            if data['meta']['indictment_accusation'] == '':
                accumulated_error_dict['indictment_accusation'] += 1
            if data['meta']['judgment_accusation'] == '':
                accumulated_error_dict['judgment_accusation'] += 1
            self.save_results(accumulated_error_dict, 'error', '', save_dir)
            
        # - 在文件處理完畢後保存結果
        logging.info(f"[counting_status] 從 {file_name} 總共取樣 {len(all_data)} 筆資料")
        logging.info(f"\tre_criminals 總共 {accumulated_total_multi_criminals}, 1個犯罪者: {accumulated_criminals_dict[1]}, 0個犯罪者的: {accumulated_criminals_dict[0]}")
        logging.info(f"\tre_article 總共 {accumulated_total_article}")
        logging.info(f"\tre_charges 總共 {accumulated_total_charges}")
        logging.info(f"\tre_reason 總共 {accumulated_total_reason}")
        logging.info(f"\tre_penalty 總共 {accumulated_total_penalty}")
        
    
    # -v- 隨機 Sample
    def random_samples(self, random_size = 10, file_name="all_data.json"):
        
        save_path = f'{self.save_path}TWLJP/random.json'
        all_data = self.load_data(file_name)
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
                
    # -v- 拆檔案 test_size validation_size
    def train_test_split(self, file_name="all_data.json", save_dir='', test_size=0.2, validation_size=0.1):
        
        # 獲取檔案 all_data 拆檔案
        
        all_data = self.load_data(file_name)
        train_data, test_data = train_test_split(all_data, test_size=test_size) # 分割訓練集和測試集
        train_data, validation_data = train_test_split(train_data, test_size=validation_size / (1 - test_size)) # 再從訓練集中分割出驗證集

        # 將分割後的資料儲存為不同的檔案
        folder_path = f'{self.save_path}TWLJP/formal/{save_dir}'
        if not path.exists(folder_path):
            makedirs(folder_path)
            
        # 初始化計數
        counts = {'train': 0, 'test': 0, 'validation': 0}
            
        for data, suffix in zip([train_data, test_data, validation_data], ['train', 'test', 'validation']):
            with open(f'{folder_path}{suffix}.json', 'w', encoding='utf-8') as file:
                for item in data:
                    file.write(json.dumps(item, ensure_ascii=False))
                    file.write('\n')
                    counts[suffix] += 1 
                    
        # 寫入 count.txt
        with open(f'{folder_path}count.txt', 'w', encoding='utf-8') as file:
            for suffix, count in counts.items():
                file.write(f'{suffix}, {count}\n')
    
    
    # -v- TWLJP => 1, 2, 3
    def category_data(self, file_name="/filter_data.json"):
        
        all_data = self.load_data(file_name)    
        
        task_1 = []
        task_2 = []
        task_3 = []
        task_4 = []
        
        for data in tqdm(all_data, desc="category_data"):
            
            # -v- TASK: 1 (有罪)
            if data['punishment'] != False:
                task_1.append(data)
        
            # -v- TASK: 2 (刑期：只留下有刑期的部分，有罰金就不要)
            if data['punishment'] != False and data['penalty'] == 1:
                task_2.append(data)
            
            # -v- TASK: 3 (罰金：只留下有罰金的部分，有刑期就不要)
            if data['punishment'] != False and data['penalty'] == 2:
                task_3.append(data)
                
            # -v- TASK: 4 (罰金 + 刑期)
            if data['punishment'] != False and data['penalty'] == 3:
                task_4.append(data)
                

        # - 存擋
        save_file_path = f"{self.save_path}/TWLJP/category/"
        self.check_and_create_directories(self.save_path, ['TWLJP/category'])   # = 路徑防呆
        
        # @ 存擋： TASK 1
        file_name = "TWLJP_1.json"
        json_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in task_1])
        self.save_to_file(f"{save_file_path}{file_name}", json_content)
        
        # @ 存擋： TASK 2
        file_name = "TWLJP_2.json"
        json_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in task_2])
        self.save_to_file(f"{save_file_path}{file_name}", json_content)
        
        # @ 存擋： TASK 3
        file_name = "TWLJP_3.json"
        json_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in task_3])
        self.save_to_file(f"{save_file_path}{file_name}", json_content)
        
        # @ 存擋： TASK 4
        file_name = "TWLJP_4.json"
        json_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in task_4])
        self.save_to_file(f"{save_file_path}{file_name}", json_content)
        
        # @ 存擋： TEST
        # file_name = "only_amount.json"
        # json_content = "\n".join([json.dumps(item, ensure_ascii=False) for item in task_4])
        # self.save_to_file(f"{save_file_path}{file_name}", json_content)
        
        # - 總結計算
        category_result = [
            f"TASK_1, {len(task_1)}",
            f"TASK_2, {len(task_2)}",
            f"TASK_3, {len(task_3)}",
            f"TASK_4, {len(task_4)}" 
        ]
        save_filter_file_path = f"{self.save_path}countLength_category.txt"
        self.save_to_file(save_filter_file_path, "\n".join(category_result))
        
        logging.info(f"[category_data] 從 {file_name} 總共取樣 {len(all_data)} 筆資料")
        logging.info(f"\t{category_result[0]}")
        logging.info(f"\t{category_result[1]}")
        logging.info(f"\t{category_result[2]}")
        logging.info(f"\t{category_result[3]}")
        
        
    def category_train_test_split(self, test_size=0.2, validation_size=0.1):
        # -v- TWLJP: 1
        self.train_test_split(file_name="category/TWLJP_1.json", save_dir='TWLJP_1/', test_size=test_size, validation_size=validation_size)
        
        # -v- TWLJP: 2
        self.train_test_split(file_name="category/TWLJP_2.json", save_dir='TWLJP_2/', test_size=test_size, validation_size=validation_size)
        
        # -v- TWLJP: 3
        self.train_test_split(file_name="category/TWLJP_3.json", save_dir='TWLJP_3/', test_size=test_size, validation_size=validation_size)
        
        # -v- TWLJP: 4
        self.train_test_split(file_name="category/TWLJP_4.json", save_dir='TWLJP_4/', test_size=test_size, validation_size=validation_size)
    
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
    
    def re_fact(self, content, fileName):
        
        is_fact = False # 是否是擷取位置
        result = ""     # 結果
        
        for line in content:
            
            # @ 處理資料，若只是空白則跳過
            if line.strip() == '':
                continue
            
            text = re.sub(r'\s', '', line).replace(u'\u3000', u' ').replace(u'\xa0', u' ').strip()
            start_index = 0

            # STOP: 後文到了則停止
            stop_list = [
                "證據並所犯法條", "證據", "所犯法條"
            ]
            for stop_term in stop_list:
                if text == stop_term:
                    is_fact = False
                    return result
            
            # START:
            if '犯罪事實：' in text:
                start_index = text.index('犯罪事實：') + 5
                is_fact = True
            elif '一、' in text:
                start_index = text.index('一、') + 2
                is_fact = True
                
            # @ 擷取 extraction
            if is_fact:
                result += text[start_index: ]
                
            # START:
            if '犯罪事實' == text or ('犯罪事實' in text and '如下' in text):
                is_fact = True
                
        if result == "":
            logging.error(f"re_fact => {fileName}")
                
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
            case_reasons = self.load_case_reasons(f"{self.save_path}ori/charges/charges_count.txt")
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
        
        if not path.exists(file_path):
            open(file_path, 'w', encoding='utf-8').close()
        
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
                    article_number = re.search(r'第(\d+條之\d+|\d+條)', part)
                    if article_number:
                        converted_text = convert_fullwidth_to_halfwidth(article_number.group(0))
                        matches.append([f'{current_prefix}', f'{converted_text}'])
                    break  
                
            else:  
                if current_prefix:
                    article_number = re.search(r'第(\d+條之\d+|\d+條)', part)
                    if article_number:
                        # matches.append(f'{current_prefix}第{article_number.group(1)}條')
                        converted_text = convert_fullwidth_to_halfwidth(article_number.group(0))
                        matches.append([f'{current_prefix}', f'{converted_text}'])
                        

        return matches
    
    def re_charges(self, content, pattern=r'案由：(.+)'):
        
        for line in content:
            text = re.sub(r'\s', '', line).replace(u'\u3000', u' ').replace(u'\xa0', u' ').strip()
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        return ""
                
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
    
    def re_main_text(self, content, fileName):
        
        # 擷取判決主文
        result_main_text = ""
        is_main_text = False
        
        for line in content:
            
            # @ 處理資料，若只是空白則跳過
            if line.strip() == '':
                continue
            
            text = re.sub(r'\s', '', line).replace(u'\u3000', u' ').replace(u'\xa0', u' ').strip()
            # print(text)
            
            # @ 後文到了則停止
            stop_list = [
                "理由", "事實",
                "犯罪事實理由", "犯罪事實", "犯罪事實及證據名稱", "事實及理由", "犯罪事實及理由",
                "二、犯罪事實要旨：", "證據並所犯法條"
            ]
            for stop_term in stop_list:
                if text in stop_term:
                    # print("========= 結束")
                    is_main_text = False
                    return result_main_text
            
            start_index = 0
            
            # START:
            if '主文' in text:
                start_index = text.index('主文') + 2
                is_main_text = True
            
            # @ 擷取 extraction
            if is_main_text:
                result_main_text += text[start_index: ]
                
            # @ 前文找到則開始
            if text == '主文' or "主文：" in text:
                # print("=========主文")
                is_main_text = True
                
        if result_main_text == "":
            logging.error(f"main_text => {fileName}")
        
        return result_main_text
    
    def re_imprisonment(self, line, fileName):
        
        def parse_time(time_str, line, fileName):
            # 解析時間字符串，返回年、月、日的數值
            try:
                result = int(cn2an.cn2an(chinese_to_int(time_str) if time_str != '' else 0, 'smart'))
                return result
            except (ValueError, KeyError) as e: 
                logging.error(f"re_imprisonment => {fileName} => main_text => {line} => 錯誤匹配: {time_str}")
                return 0
        
        imprisonments = []
        total_imprisonment = 0  
        
        if '年' in line or '月' in line or '日' in line:
            # 合併正則表達式
            pattern = re.compile(r'(有期徒刑|拘役)(?:([\u4e00-\u9fff\d+]{1,2})年)?(?:([\u4e00-\u9fff\d+]{1,2})月)?(?:([\u4e00-\u9fff\d+]{1,5})日)?')
            filter_char = {
                '(': '', 
                '（': '', 
                ')': '', 
                '）': '', 
                '以': '', 
                '又': '',
                '月月': '月',
                '萬萬': '萬',
                '年年': '年',
            }
            temp_text = line
            for char in filter_char:
                temp_text = temp_text.replace(char, '')
            matches = pattern.findall(temp_text)
            
            for match in matches:
                sentence_type, years, months, days = match

                years_val = parse_time(years, line, fileName)
                months_val = parse_time(months, line, fileName)
                days_val = parse_time(days, line, fileName)

                if years_val != 0 or months_val != 0 or days_val != 0:
                    imprisonment_str = f"{sentence_type}{years_val}年{months_val}月{days_val}日" if days else f"{sentence_type}{years_val}年{months_val}月"
                    imprisonments.append(imprisonment_str)
                    
                total_imprisonment += (years_val * 12) + months_val + (days_val / 30)
                    
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
    
    def re_amount(self, line, fileName):
        
        pattern = re.compile(r"(?<!易科)(?:罰金(?:新(?:臺|台)幣)?)([\u4e00-\u9fff]+)元(?<!折算壹日)[，。、？]")
        matches = pattern.findall(line)  # 使用 findall 來找到所有匹配
        
        amount_list = []
        for match in matches:
            try:
                regular_match = cn2an.cn2an(chinese_to_int(match), 'smart')
                amount_list.append(regular_match)  
            except Exception as e:
                logging.error(f"re_amount => {fileName} => main_text => {line} => 錯誤匹配: {match}")

        return amount_list, sum(amount_list)
    
    def re_reason(self, line, amount_count, imprisonment_count, fileName, judgment_number):
        """
            (0) 無罪
            (1) 有罪
            (2) 免刑
            (3) 不受理
            (4) 裁定判決
            
            (-1) 管轄錯誤、駁回、延長羈押、補正資料
        """
        result = -1
    
        if amount_count != 0 or imprisonment_count != 0:
            result = 1
        if '無罪' in line:
            result = 0
        if  '免刑' in line or '免訴' in line :
            result = 2
        if '不受理' in line:
            result = 3
        if  '裁定' in judgment_number:
            result = 4
            
        if result == -1 and line != '':
            logging.error(f"re_reason => {fileName} => main_text => {line}")
            
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
        
        if reason == 1:
            return True
        elif reason != 1:
            return False
        else:
            return None
        
    
    # ---------------------------------------------------------------------------------------------------- 其他程式碼
    
    def load_data(self, file_name="all_data.json"):
        
        # 獲取檔案 all_data 拆檔案
        all_data = []
        # 首先計算文件的總行數
        total_lines = sum(1 for _ in open(f"{self.save_path}/TWLJP/{file_name}", 'r', encoding="utf-8"))
        
        # 使用 tqdm 包裹文件對象來追蹤進度
        with open(f"{self.save_path}/TWLJP/{file_name}", 'r', encoding="utf-8") as file:
            for line in tqdm(file, total=total_lines, desc=f"Load Data {file_name}"):
                all_data.append(json.loads(line))
                
        return all_data
    
    # -v- 儲存個別結果
    def save_results(self, case_reason_count, file_type, accumulated_total, save_dir):
        sorted_case_reasons = sorted(case_reason_count.items(), key=lambda x: x[1], reverse=True)
        
        self.check_and_create_directories(self.save_path, [f"{save_dir}{file_type}"])   # = 路徑防呆

        # 保存計數結果
        save_file_path = f"{self.save_path}{save_dir}{file_type}/{file_type}_count.txt"
        with open(save_file_path, 'w', encoding='utf-8') as writeFile:
            for reason, count in sorted_case_reasons:
                writeFile.write(f"{reason}, {count}\n")
            writeFile.write(f"TOTAL, {accumulated_total}\n")

        # 僅保存案由
        save_file_path = f"{self.save_path}{save_dir}{file_type}/{file_type}.txt"
        with open(save_file_path, 'w', encoding='utf-8') as writeFile:
            for reason, _ in sorted_case_reasons:
                writeFile.write(f"{reason}\n")   
    
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
            makedirs(save_file_path)

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
            
        logging.info(f"已存擋於 {file_path}")
    
    # -v- 防呆資料夾
    def check_and_create_directories(self, save_path, required_dirs_=['log', 'ori/charges/']):
        required_dirs = required_dirs_
        for dir in required_dirs:
            full_path = path.join(save_path, dir)
            if not path.isdir(full_path):
                makedirs(full_path)
                
    def check_and_create_files(self, 
            required_dirs=['charges', 'article', 'criminals', 'penalty'],
            save_dir='ori/'):
        for dir in required_dirs:
            # 檢查目錄是否存在，若不存在則創建
            directory_path = path.join(self.save_path, f"{save_dir}{dir}")
            if not path.exists(directory_path):
                makedirs(directory_path)

            # 為每個目錄創建兩個檔案
            for file_name in [f"{dir}.txt", f"{dir}_count.txt"]:
                print(directory_path, file_name)
                file_path = path.join(directory_path, file_name)
                with open(file_path, 'w', encoding='utf-8') as writeFile:
                    pass 
                
    # -v- 初始化 logging
    # def initialize_logging(self, save_path):
    #     log_file_path = f'{save_path}log/ProcessAILA.log'
    #     logging.basicConfig(filename=log_file_path, level=logging.INFO,
    #                         format='%(asctime)s:%(levelname)s:%(message)s')
    #     logging.Formatter = TaiwanTimeFormatter
    #     logging.info(f"-------------------------------------------------------------")
    
    def append_to_all_log(self, current_log_path, all_log_path):
        with open(current_log_path, 'r') as current_log, open(all_log_path, 'a') as all_log:
            all_log.write(current_log.read())

    def clear_file(self, file_path):
        with open(file_path, 'w'):
            pass
        
    def initialize_logging(self, save_path):
        all_log_file_path = f'{save_path}log/ALL_ProcessAILA.log'
        current_log_file_path = f'{save_path}log/ProcessAILA.log'

        # 如果 ProcessAILA.log 存在，將其內容附加到 ALL_ProcessAILA.log
        if path.exists(current_log_file_path):
            self.append_to_all_log(current_log_file_path, all_log_file_path)
            self.clear_file(current_log_file_path)

        # 設置通用的日誌格式
        log_format = '%(asctime)s:%(levelname)s:%(message)s'

        # 設置 ProcessAILA.log 的 logger
        logging.basicConfig(filename=current_log_file_path, level=logging.INFO, format=log_format)
        logging.Formatter = TaiwanTimeFormatter
        logging.info("-------------------------------------------------------------")

    
    # -v- 新增的 initialize_accumulators 方法
    def initialize_accumulators(self):
        
        # - 字典
        accumulated_charge_dict = defaultdict(int)
        accumulated_article_dict = defaultdict(int)
        accumulated_criminals_dict = defaultdict(int)
        accumulated_penalty_dict = defaultdict(int)
        accumulated_reason_dict = defaultdict(int)
        accumulated_combine_article_charge_dict = defaultdict(int)
        accumulated_law = defaultdict(int)
        
        accumulated_error_dict  = defaultdict(int)
        
        # - 數量
        accumulated_total_charges = 0
        accumulated_total_article = 0
        accumulated_total_multi_criminals = 0
        accumulated_total_penalty = 0
        accumulated_total_reason = 0
        accumulated_total_combine_article_charge = 0
        accumulated_total_law = 0
        
        accumulated_total_error = 0

        return (
            accumulated_charge_dict, accumulated_article_dict, accumulated_combine_article_charge_dict, accumulated_law,
            accumulated_criminals_dict, accumulated_penalty_dict, accumulated_reason_dict,
            accumulated_error_dict,
            
            accumulated_total_charges, accumulated_total_article, accumulated_total_combine_article_charge, accumulated_total_law,
            accumulated_total_multi_criminals, accumulated_total_penalty, accumulated_total_reason,
            accumulated_total_error
        )
        
    def load_status_data(self, file_name="article_charge", load_dir='ori/'):
        
        status_count = dict()
        with open(f"{self.save_path}{load_dir}{file_name}/{file_name}_count.txt", 'r', encoding='utf-8') as file:
            for line in file:
                
                # 移除換行符號並分割每一行
                parts = line.strip().split(', ')
                
                if len(parts) > 2:
                    combined = '-'.join(parts[:-1])  # 連接除了最後一個元素以外的所有元素
                    status_count[combined] = parts[-1]  # 使用連接後的字串作為鍵，最後一個元素作為值
                    
                else:
                    status_count[parts[0]] = parts[1]
                
        return status_count

    

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
        

class REASON(Enum):
    
    未抓取成功 = -1
    無罪 = 0
    有罪 = 1
    免刑 = 2
    不受理 = 3
    裁定判決 = 4
    
class PENALTY(Enum):
    
    無 = 0
    只有刑期 = 1
    只有罰金 = 2
    刑期與罰金 = 3
        
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
    
