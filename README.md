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

# 計算初始總筆數
# processData.countLength_source()

# 負責處理擷取資訊，以及將資訊儲存到 log
processData.TWLJP_JSON()

# 篩選資料
processData.filter_TWLJP()

# 計算處理後資訊
# processData.counting_status()

# 刪掉多犯罪者
processData.remove_multiple_criminals()

# 隨機抽樣, 預設為 10
processData.random_samples(file_path="/TWLJP/sigleCriminal_allData.json", random_size=10)

# 分割 train test validation
processData.train_test_split(file_path="/TWLJP/sigleCriminal_allData.json")

```

資料夾格式
```

.
├── TWLJP
│   └── all_data.json 
├── article
│   ├── article.txt 
│   └── article_count.txt
├── charge_article
│   ├── charge_article.txt
│   └── charge_article_count.txt
├── charges
│   ├── charges.txt
│   └── charges_count.txt
├── countLength_source.txt
├── criminals
│   ├── criminals.txt
│   └── criminals_count.txt
├── error
│   ├── error.txt
│   └── error_count.txt
├── log
│   └── ProcessAILA.log
├── penalty
│   ├── penalty.txt
│   └── penalty_count.txt
└── reason
    ├── reason.txt
    └── reason_count.txt

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
    
    "reason": reason,   # (0) 無罪  (1) 有罪 (2) 免刑 (3) 不受理  (default = (-1) 未抓取成功 )
    "penalty": penalty, # (0) 無 (1) 只有刑期 (2) 只有罰金 (3) 刑期＋罰金
    "punishment": self.punishment(reason),     # True(有罪)、False(無罪、免刑、不受理)
    
    "ori_indictment_content": content_split[0],
    "ori_judgment_content": content_split[1]
}
```