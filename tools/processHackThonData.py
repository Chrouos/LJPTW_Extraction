from os import listdir, path, mkdir
from datetime import datetime
import json
import re
import io
import sys
import random
import os

sys.path.append('./tools')
from processNumber import translate, chinese_to_int, incidentTime_regex_catch
from process_carRepair import carDepreciation


class ProcessHackThonData:

    # @ 初始化
    def __init__(self, save_path="./data/process_v1/", source_path="./data/src/"):
        
        # - 資料路徑
        self.source_path = source_path
        self.save_path = save_path
        
        # - 路徑防呆
        if not path.isdir(self.save_path): mkdir(self.save_path) # * 若沒有該資料夾則創建一個
        
        # - 獲得所有資料夾與之子之資料名稱
        files = listdir(self.source_path)
        self.source_filesList = [f for f in files if f.endswith('.json')]

    # @ 獲得所有資料長度
    def writeTheFilelength(self):
        
        writeLengths = [] # = 資料儲存長度
        
        # - 讀取「來源資料夾」的所有「檔案」
        for fileName in self.source_filesList:
            
            countLength = 0 # = 檔案行數
            with open(f"{self.source_path}{fileName}", 'r', encoding='utf-8') as lineFile:
                
                # - 讀取「檔案」，計算共有幾筆資料 
                for line in lineFile:
                    countLength += 1 # @ 計算次數

            file_info = f"[{fileName}] lengths: {countLength}"
            writeLengths.append(file_info)
            
        # - 儲存檔案
        save_file_path = f"{self.save_path}all_file_lenghts.txt"
        with open(save_file_path, 'w', encoding='utf-8') as writeFile:
            writeFile.write("\n".join(writeLengths))
            
    # @ 把資料處理成乾淨資料
    def writeCleanFile(self, fileName):
        print(f"[writeCleanFile] reading the file: {fileName}.")
        
        # - 讀取要擷取的檔案
        with open(f"{self.source_path}{fileName}", "r", encoding='utf-8') as lineFile:
            
            writeContent = [] # = 要存取的檔案
            for line in lineFile:
                content = json.loads(line) 
                tempContent = {} # {}, content
                
                try:
                    # - 處理資料並預計存擋
                    if 'cleanJudgement' in content: tempContent['cleanJudgement'] = content['cleanJudgement']
                    elif 'judgement' in content: 
                        tempContent['cleanJudgement'] = content['judgement'].replace('\n', '').replace('\r', '').replace('　', '').replace(' ', '')
                        tempContent['judgement'] = content['judgement']
                    
                    if 'opinion' in content:
                        tempContent['cleanOpinion'] = content['opinion'].replace('\n', '').replace('\r', '').replace('　', '').replace(' ', '')
                        tempContent['opinion'] = content['opinion']
                        
                except Exception as e:
                    print(f"error in {fileName}\n", e)
                
                # - 存取每一筆資料    
                writeContent.append(tempContent)
                
        # - 儲存檔案
        save_file_path = f"{self.save_path}/writeCleanFile/"
        if not path.isdir(save_file_path): mkdir(save_file_path) # * 若沒有該資料夾則創建一個
        with open(f"{save_file_path}clean_{fileName}", 'w', encoding="utf-8") as writeFile:
            for item in writeContent:
                writeFile.write(json.dumps(item, ensure_ascii=False))  
                writeFile.write('\n')  
                
    # @ 把所有資料處理成乾淨資料 - writeCleanFile
    def writeCleanFile_all(self):
        for fileName in self.source_filesList:
            self.writeCleanFile(fileName)
            
            
    # @ 正規表示法擷取相關數量
    def re_compensation(self, fileName):
        print(f"[re_compensation] reading the file: {fileName}.")
        
        writeContent = []
        
        # = 獲取賠償的 Regular Expression 的 Pattern.
        compensation_pattern = {
            '精神賠償': ['(?:(?:請求之慰撫金|賠償精神慰撫金|請求慰撫金以|\+慰撫金|請求之精神慰撫金金額.*?應以|被告賠償之非財產上損害為|認原告請求非財產上損害即精神慰撫金|認精神慰撫金數額以|認原告請求.*?元之慰撫|精神慰撫金.*?應以)(?:.*?尚屬過高)?.*?)((\d+萬)?(\d+,\d+|\d+)?(\d+,\d+|\d+)?)(?:元.*?(?:。|適當))'],
            '修車費用': ['(?:耐用年數.*?)(?:合計|共計應為|共計|僅為|僅以|損害額為|修復費用共|除折舊後之餘額為|合計為|修理費(?:用為)?|回復原狀費用應為|必要費用應為|總計為|維修費用應為|賠償之金額為|(?:^零件扣除折舊.*?)修復費用為|必要之費用為|必要費用共|加計.*?共|必要修復費用|車輛修復費用應為|總計.*?|合計為|系爭車輛之必要修理費用為)((\d+萬)?(\d+,\d+|\d+)?(\d+,\d+|\d+)?)(?:元.*?。)'],
            '醫療費用': ['(?:(?:醫療費用)(?:.*?)(?:共計|合計)?)((\d+萬)?(\d+,\d+|\d+)?(\d+,\d+|\d+)?)(?:元.*?(?:。|適當|准許))'],
            '看護費用': ['(?:看護費用.*?)((\d+,\d+|\d+)?(\d+萬)?(\d+,\d+|\d+)?)(?:元.*?。)'],
            '交通費用': ['(?:交通費.*?)((\d+,\d+|\d+)?(\d+萬)?(\d+,\d+|\d+)?)(?:元.*?。)'],
            "財產損失": ['(?:水電及電桿材料.*?)((\d+,\d+|\d+)?(\d+萬)?(\d+,\d+|\d+)?)(?:元.*?。)'],
            "營業損失": ['(?:營業損失.*?)((\d+,\d+|\d+)?(\d+萬)?(\d+,\d+|\d+)?)(?:元.*?。)'], 
            "訴訟費用": ['(?:訴訟費用.*?)((\d+,\d+|\d+)?(\d+萬)?(\d+,\d+|\d+)?)(?:元.*?。)'],
            "工作損失": ["(?:工作損失.*?)((\d+,\d+|\d+)?(\d+萬)?(\d+,\d+|\d+)?)(?:元.*?。)"]
        } 
        
        # - 正規表示法處理字串
        with open(f"{self.save_path}/writeCleanFile/clean_{fileName}", 'r', encoding='utf-8') as lineFile:
            for line in lineFile:
                content = json.loads(line)
                text = content['cleanJudgement']
                tempContent = {}
                
                # - RE ~ 九大分類
                for category, patterns in compensation_pattern.items():
                    for pattern in patterns:
                        match = re.search(pattern, text)       
                    
                        
                        if match:
                            tempContent[category] = translate(chinese_to_int(match.group(1)))
                            break
                        else: tempContent[category] = 0
                        
                # - RE ~ 事故時間
                regexIncident = incidentTime_regex_catch(text)
                if regexIncident != None: tempContent['事故時間'] = incidentTime_regex_catch(text).replace('被告於民國', '')
                else: tempContent['事故時間'] = None
                        
                # - RE ~ 車損分類
                # * 出廠日期
                pattern_car = ["(\d+年(?:（西元\d+年）)?\d+月|西元\d+年\d+月)(?:\d+日)?(?:出廠)", "(?:出廠日.*?)(\d+年(?:（.*?西元\d+年）)??\d+月|西元\d+年\d+月)"]
                for pattern in pattern_car:
                    match_car = re.search(pattern, text)
                    if match_car: 
                        tempContent["出廠日期"] =  match_car.group(1).replace('出廠', '').replace('日', '').replace('為', '').replace('期', '').replace('迄', '').replace('即', '')
                        break
                    else: tempContent["出廠日期"] = None
                    
                # * 耐用年數
                pattern_car = f"(?:耐用年數(?:為)?)([\d一二三四五六七八九十])(?:年)"
                match_car = re.search(pattern_car, text)
                if match_car: tempContent["耐用年數"] = match_car.group(1)
                else: tempContent["耐用年數"] = None
                
                # * 折舊計算方法: 平均或定律
                if '千分之' in text or '/1000' in text or '10分之9' in text or '1,000分之' in text: tempContent['折舊計算方法'] = 'depreciation-fixed'
                elif '平均法' in text or '殘值' in text: tempContent['折舊計算方法'] = 'equal-annual-payment'
                else: tempContent['折舊計算方法'] = None
                            
                # * 車損費用細項
                repairFee = {'零件': 0, '材料': 0, '工資': 0, '鈑金': 0, '塗裝': 0, '烤漆': 0, '噴漆': 0, '鈑噴': 0}
                for key, value in repairFee.items():
                    pattern_car = f"(?:{key}.*?)((\d+,\d+|\d+)?(\d+萬)?(\d+,\d+|\d+)?)(?:[元。」])"
                    match_car = re.search(pattern_car, text)
                    if match_car: repairFee[key] = translate(chinese_to_int(match_car.group(1)))
                tempContent['車損費用細項'] = repairFee
                
                # - 擷取內容
                tempContent['擷取內容'] = text
                writeContent.append(tempContent)
        
        # - 儲存檔案
        save_file_path = f"{self.save_path}re/"
        if not path.isdir(save_file_path): mkdir(save_file_path) # * 若沒有該資料夾則創建一個
        with open(f"{save_file_path}re_{fileName}", 'w', encoding="utf-8") as writeFile:
            for item in writeContent:
                writeFile.write(json.dumps(item, ensure_ascii=False))  
                writeFile.write('\n')  
                
                
    # @ 把所有資料 正規表示法擷取相關數量 - re_compensation
    def re_compensation_all(self):
        for fileName in self.source_filesList:
            self.re_compensation(fileName)
            
            
    # @ 預測車損費用
    def caculate_rePairFee(self, fileName):
        
        print(f"[caculate_rePairFee] reading the file: {fileName}.")
        
        writeContent = []
        with open(f"{self.save_path}re/re_{fileName}", 'r', encoding="utf-8") as lineFile:
            for line in lineFile:
                content = json.loads(line)
                tempContent = { 'predict_money': 0, 'ori_money': 0, '車損費用細項': {},
                                '修車費用': None, '出廠日期': None, '耐用年數': None, '事故時間': None, '折舊計算方法': None }
                
                canPredict = True
                
                # ----- 處理資料格式
                
                # = ori_money
                if '修車費用' in content and content['修車費用'] != None:
                    tempContent['ori_money'] = content['修車費用']
                else: canPredict = False
                    
                # = list
                if '車損費用細項' in content and content['車損費用細項'] != None:
                    temp_repairFee = {}
                    tempContent['車損費用細項'] = content['車損費用細項']
                else: canPredict = False
                    
                # = manufactureDate: 出廠日, YYY-mm
                if '出廠日期' in content and content['出廠日期'] != None:
                    pattern = r"（.*?）"
                    processed_content = re.sub(pattern, "", content['出廠日期'])
                    
                    content_split = processed_content.split('年')
                    
                    # - Year
                    year_match = re.search(r'\d+', content_split[0])
                    if year_match: 
                        content_year = int(year_match.group())
                        if "西元" in content_split[0]: content_year = content_year - 1911
                    else: canPredict = False
                            
                    # - Month
                    month_match = re.search(r'\d+', content_split[1].split('月')[0])
                    if month_match: content_month = int(month_match.group())
                    else: canPredict = False
                    
                    # - 防呆
                    current_year = datetime.now().year - 1911
                    if content_year == 0 or content_month >= 12 or content_month <= 1: canPredict = False # @ 若出現月份或年份為0時代表無法判斷真實日期，計算區間
                    if content_year > current_year: canPredict = False # @ 若事故時間比目前時間的年份還大，代表有錯誤
                    
                    tempContent['出廠日期'] = f"{content_year}-{content_month}"
                else: canPredict = False
                
                # = vehicle
                if '耐用年數' in content and content['耐用年數'] != None:
                    tempContent['耐用年數'] = translate(content['耐用年數'])
                else: canPredict = False
                    
                # = incidentDate
                if '事故時間' in content and content['事故時間'] != None:
                    pattern = r"（.*?）"
                    processed_content = re.sub(pattern, "", content['事故時間'])
                    
                    content_split = processed_content.split('年')
                    
                    # - Year
                    year_match = re.search(r'\d+', content_split[0])
                    if year_match: 
                        content_year = int(year_match.group())
                        if "西元" in content_split[0]: content_year = content_year - 1911
                    else: canPredict = False
                            
                    # - Month
                    month_match = re.search(r'\d+', content_split[1].split('月')[0])
                    if month_match: content_month = int(month_match.group())
                    else: canPredict = False
                    
                    # - 防呆
                    current_year = datetime.now().year - 1911
                    if content_year == 0 or content_month >= 12 or content_month <= 1: canPredict = False # @ 若出現月份或年份為0時代表無法判斷真實日期，計算區間
                    if content_year > current_year: canPredict = False # @ 若事故時間比目前時間的年份還大，代表有錯誤
                    
                    tempContent['事故時間'] = f"{content_year}-{content_month}"
                else: canPredict = False
                
                # = method
                if '折舊計算方法' in content and content['折舊計算方法'] != None:
                    tempContent['折舊計算方法'] = content['折舊計算方法']
                else: canPredict = False
                    
                
                # - 預測車損       
                if canPredict:
                    predict_amount = carDepreciation(
                        manufactureDate=tempContent['出廠日期'],
                        incidentDate=tempContent['事故時間'],
                        repairFee=tempContent['車損費用細項'],
                        vehicle=tempContent['耐用年數'],
                        method=tempContent['折舊計算方法']
                    )         
                    
                    tempContent['predict_money'] = predict_amount
                    
                tempContent['擷取內容'] = content['擷取內容'] # ! 除錯用，若有不符合的資料就調用未擷取內容
                writeContent.append(tempContent)
                
                
                    
        # - 儲存檔案
        save_file_path = f"{self.save_path}carRepair/"
        if not path.isdir(save_file_path): mkdir(save_file_path) # * 若沒有該資料夾則創建一個
        with open(f"{save_file_path}predict_{fileName}", 'w', encoding="utf-8") as writeFile:
            for item in writeContent:
                writeFile.write(json.dumps(item, ensure_ascii=False))  
                writeFile.write('\n')  
                
    # @ 把所有資料 預測車損費用 - caculate_rePairFee
    def caculate_rePairFee_all(self):
        for fileName in self.source_filesList:
            self.caculate_rePairFee(fileName)
    
    # @ 切割資料 train, test, validation
    def separateData_trainTestValidation(self, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1):
        
        assert train_ratio + val_ratio + test_ratio == 1, "Ratios 合起來必為一 1"
        
        all_data = []
        exceptFileName = ['clean_random_100_gpt.json', 'clean_random_100.json']
        
        # - Step 1: 合併檔案
        for fileName in self.source_filesList:
            
            print(f"[separateData_trainTestValidation] mergeFile: {fileName}.")
            
            if fileName in exceptFileName:
                print(f"! {fileName} is except.")
                continue
            
            # @ 選擇要切割的檔案: writeCleanFile
            with open(f"{self.save_path}/writeCleanFile/clean_{fileName}", 'r', encoding='utf-8') as lineFile:
                for line in lineFile:
                    content = json.loads(line) 
                    all_data.append(content)
                    
        # - Step 2: 打亂 data
        random.shuffle(all_data)
        
        # - Step 3: 切割 data
        total_size = len(all_data)
        train_size = int(train_ratio * total_size)
        val_size = int(val_ratio * total_size)

        train_data = all_data[:train_size]
        val_data = all_data[train_size:train_size + val_size]
        test_data = all_data[train_size + val_size:]

        # - 儲存檔案
        save_file_path = f"{self.save_path}/separateData/"
        if not path.isdir(save_file_path): mkdir(save_file_path) # * 若沒有該資料夾則創建一個
        with open(f"{self.save_path}/separateData/train.json", 'w', encoding='utf-8') as f:
            for item in train_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        with open(f"{self.save_path}/separateData/val.json", 'w', encoding='utf-8') as f:
            for item in val_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        with open(f"{self.save_path}/separateData/test.json", 'w', encoding='utf-8') as f:
            for item in test_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                
        # ! 其他存擋
        other_data = all_data[:1000]
        with open(f"{self.save_path}/separateData/random_1000.json", 'w', encoding='utf-8') as f:
            for item in other_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        
            
            
    # ---------------------------------------------------------------------------
    
    # @ jsonList -> jsonLine
    def listToJsonLine(self, filePath):

        with open(filePath, 'r', encoding="utf-8") as jsonFile:
            jsonContent = json.load(jsonFile)

        saveFilePath = filePath.replace('.json', '_line.json')
        with open(saveFilePath, 'w', encoding="utf-8") as outputFile:
            for item in jsonContent:
                outputFile.write(json.dumps(item, ensure_ascii=False) + '\n')
                
    def add_Label_to_files(self, dest_folder, label='opinion'):
        # 創建一個字典來存儲第二個文件夾的數據
        judgements = {}
        src_folder = f"{self.save_path}writeCleanFile/"
        
        # 讀取第二個文件夾的文件
        for filename in os.listdir(src_folder):
            if filename.endswith('.json'):
                with open(os.path.join(src_folder, filename), 'r', encoding='utf-8') as file:
                    for line in file:
                        data = json.loads(line)
                        clean_judgement = data.get('cleanJudgement')
                        judgement = data.get(label)
                        if clean_judgement and judgement:
                            judgements[clean_judgement] = judgement
                        
        # 更新第一個文件夾的文件
        for filename in os.listdir(dest_folder):
            if filename.endswith('.txt'):
                file_path = os.path.join(dest_folder, filename)
                updated_lines = []
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file:
                        data = json.loads(line)
                        clean_judgement = data.get('cleanJudgement')
                        if clean_judgement and clean_judgement in judgements:
                            data[label] = judgements[clean_judgement]
                        updated_lines.append(json.dumps(data, ensure_ascii=False))

                # 寫回更新後的內容
                with open(file_path, 'w', encoding='utf-8') as file:
                    for line in updated_lines:
                        file.write(line + '\n')
                        
        # print(filePath)
        # print(f"{self.save_path}writeCleanFile/")
        
        
                
    # @ Excel -> Json
    # def excelToJson(self, filePath):
    #     data = pd.read_excel(filePath, sheet_name="car")
    #     json_data = data.to_json(force_ascii=False, orient='records') # * forch_ascii=False 不用會亂碼
        
    #     saveFilePath = filePath.replace('.json', '_excel2json.json')
    #     with open(save_file_path, 'w', encoding="utf-8") as writeFile:
    #         writeFile.write(json_data)


        
    

