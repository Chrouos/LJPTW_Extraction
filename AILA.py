import argparse

# 建立命令列參數解析器
ap = argparse.ArgumentParser(description="用來處理 AILA  資料擷取的部分")
ap.add_argument("-m", "--mode", required=False, help="設定模式 \n EXPECT_PROBLEM=0, TEST=1='test', DOING=2='doing'. \ne.g. -m 0", default=0)
ap.add_argument("-c", "--count", required=False, help="要 Sample 的筆數 e.g. -c 100")
args = vars(ap.parse_args())

# 確認是否提供了 mode 參數
mode_arg = args["mode"] if "mode" in args and args["mode"] is not None else None
count_arg = args["count"] if "count" in args and args["count"] is not None else None

# ---------------------------------------------------------------------------------------------------- v 

from tools.processAILA import ProcessAILA
processData = ProcessAILA(
    source_path='./data/data_org/',
    save_path='./data/processed/',
    mode=mode_arg,
    limit_counts=count_arg,
    isRandomData=True
)

processData.countLength_source() # @ 計算初始總筆數
processData.TWLJP_JSON() # @ 負責處理擷取資訊，以及將資訊儲存到 log # => 輸出檔案為 all_data.json
processData.counting_status("all_data.json", save_dir="statistics/ori/") # @ 計算處理前資訊
processData.filter_TWLJP([{"name": "article", "number": 30}, {"name": "charges", "number": 30}], "all_data.json", reference_dir="statistics/filter/") # @ 篩選資料 # => 輸出檔案為 filter_data.json
processData.category_data(file_name="filter_data.json", is_filter=True) # @ 分類 TWLJP: 1, 2, 3
processData.category_train_test_split() # @ 分割 train test validation # => 輸出檔案為 TWLJP: 1, 2, 3, 4

# @ 轉換成 pickle


# @ 統計
# processData.statistics_to_excel()

# @ 隨機抽樣, 預設為 10
# processData.random_samples(file_name="filter_data.json", random_size=10)
# => 輸出檔案為 random.json

