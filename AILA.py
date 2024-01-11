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
    isRandomData=False
)

# processData.countLength_source()
processData.TWLJP_JSON()
processData.filter_TWLJP()

# processData.remove_multiple_criminals() # = 刪掉多犯罪者
# processData.random_samples(file_path="/TWLJP/sigleCriminal_allData.json", random_size=10)   # = 隨機抽樣, 預設為 10
# processData.train_test_split(file_path="/TWLJP/sigleCriminal_allData.json")   # = 分割 train test validation


# # - 計算資料
# processData.countLength_souce()
# processData.check_files_existence('TWLJP_30_old')
# processData.final_result_save_excel()

