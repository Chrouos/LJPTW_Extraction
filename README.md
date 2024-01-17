+ Step 1.
    + `git clone git@github.com:Chrouos/LJPTW_Extraction.git`
+ Step 2.
    + Deal with Permission: `chmod +x ./download.sh`
    + Execute: `./download.sh` or Download the Source File [GOOGLE DRIVE](https://drive.google.com/file/d/1-sBPlmdmkzimdhCu7Aa8Ug1EluNwRBHT/view?usp=drive_link)
+ Step 3.
    + Execute `python AILA.py`


# 說明 AILA
執行:
+ mode (觸發模式)
    + `0` or `default` (所有檔案)
    + `1` or `test` (開發者模式，挑出一些比較特別的案例)
    + `2` or `doing` (開發者模式，單獨選擇一項檔案測試)
+ limit_count (限制筆數)
    + 注意，每次資料都會隨機生成 
```shell
python organise_data.py -m {mode} -c {limit_count} 

# Example:
# m=所有檔案模式, c=只取 100 筆
# python organise_data.py -m 0 -c 100

```

```py
from tools.processAILA import ProcessAILA
processData = ProcessAILA(
    source_path='./data/data_org/',
    save_path='./data/processed/',
    mode=mode_arg,
    limit_counts=count_arg,
    isRandomData=False
)


# @ 計算初始總筆數
processData.countLength_source()

# @ 負責處理擷取資訊，以及將資訊儲存到 log # => 輸出檔案為 all_data.json
processData.TWLJP_JSON()

# @ 計算處理前資訊
processData.counting_status("all_data.json", save_dir="statistics/ori/")

# @ 篩選資料 # => 輸出檔案為 filter_data.json
processData.filter_TWLJP([{"name": "article", "number": 30}, {"name": "charges", "number": 30}], "all_data.json", reference_dir="statistics/filter/")

# @ 分類 TWLJP: 1, 2, 3
processData.category_data(file_name="filter_data.json", is_filter=True)

# @ 分割 train test validation # => 輸出檔案為 TWLJP: 1, 2, 3, 4
processData.category_train_test_split()

# @ 隨機抽樣, 預設為 10
# processData.random_samples(file_name="filter_data.json", random_size=10)
# => 輸出檔案為 random.json
```

TWLJP_JSON 格式:
```
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
    
    "reason": reason,   # (0) 無罪  (1) 有罪 (2) 免刑 (3) 不受理 (4)裁定判決  (default = (-1) 未抓取成功 )
    "penalty": penalty, # (0) 無 (1) 只有刑期 (2) 只有罰金 (3) 刑期＋罰金
    "punishment": self.punishment(reason),     # True(有罪)、False(無罪、免刑、不受理)
    
    "ori_indictment_content": content_split[0],
    "ori_judgment_content": content_split[1]
}
```

### Filter
處理的 function: `filter_TWLJP`
+ article/charge: 統計資料 < 30 筆以下，移除
+ reason: "裁定判決"或"未抓取成功"，移除
+ main_text, fact, charge: 為空，移除 
+ criminals: 多位犯罪者，移除

### TWLJP 
處理的 function: `category_data`
+ TASK_1: (有罪)
+ TASK_2: (刑期：只留下有刑期的部分，有罰金就不要)
+ TASK_3: (罰金：只留下有罰金的部分，有刑期就不要)
+ TASK_4: (罰金 + 刑期)


### 輸出格式: processed
```
├── TWLJP # 處理後的資料存擋
│   ├── all_data.json # 分類後的所有檔案
│   ├── category # 任務分類目標
│   │   ├── TWLJP_1.json
│   │   ├── TWLJP_2.json
│   │   ├── TWLJP_3.json
│   │   └── TWLJP_4.json
│   ├── filter_data.json
│   ├── formal  # 正式訓練資料
│   │   └── TWLJP_1, TWLJP_2, TWLJP_3, TWLJP_4
│   │       ├── count.txt # 統計 test, train, validation 筆數
│   │       ├── test.json
│   │       ├── train.json
│   │       └── validation.json
│   └── random.json # 隨機從某 file 抽取筆數
├── countLength_category.txt
├── countLength_source.txt
statistics
    ├── TWLJP_1, TWLJP_2, TWLJP_3, TWLJP_4
    │   └── article, article_charge, charges, criminals, error, law, penalty, reason
    │       ├── {key}.txt           # 未包含數字的數據，純Key
    │       └── {key}_count.txt     # 統計數據數量
    ├── filter
    │   └── article, article_charge, charges, criminals, error, law, penalty, reason
    │       ├── {key}.txt           # 未包含數字的數據，純Key
    │       └── {key}_count.txt     # 統計數據數量
    └── ori # 原始資料的資料統計
    │   └── article, article_charge, charges, criminals, error, law, penalty, reason
    │       ├── {key}.txt           # 未包含數字的數據，純Key
    │       └── {key}_count.txt     # 統計數據數量
└── log # 處理 log
    ├── ALL_ProcessAILA.log # 過去的所有 log 紀錄
    └── ProcessAILA.log     # 最後一次的 log 紀錄


```
