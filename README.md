改變權限

```
chown -R 1000 {file_path}
```

# processAILA

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
# 所有檔案，100 筆資料
# python organise_data.py -m 0 -c 100

```

```py
from tools.processAILA import ProcessAILA
processData = ProcessAILA(
    source_path='./data/aila_data_org/',
    save_path='./data/aila_data_process/',
    mode=mode_arg,
    limit_counts=count_arg,
    isRandomData=False # 檔案是否要隨機
)

# 負責處理擷取資訊，以及將資訊儲存到 log
processData.TWLJP_JSON()

# 刪掉多犯罪者
processData.remove_multiple_criminals()

# 隨機抽樣, 預設為 10
processData.random_samples(file_path="/TWLJP/sigleCriminal_allData.json")

# 分割 train test validation
processData.train_test_split(file_path="/TWLJP/sigleCriminal_allData.json")
```