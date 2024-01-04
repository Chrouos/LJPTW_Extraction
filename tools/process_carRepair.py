from datetime import datetime
import math
import configparser
import json

def carDepreciation(manufactureDate, incidentDate, repairFee, vehicle, method='equal-annual-payment'):
    ''' 
    變數輸入
        manufactureDate: 民國 YYY-mm
        incidentDate: 民國 YYY-mm-dd
        repairFee: <list> = { 
            '工資': 0,
            '材料': 0, (!)
            '零件': 0, (!)
            '鈑金': 0,
            '塗裝': 0,
            '烤漆': 0
        }(需要折舊的項目：零件費用、材料費用),
        method:
            平均法: 'equal-annual-payment'
            定率遞減法: 'depreciation-fixed'
        vehicle:
            機車: scooter (3)
            營業用: business_car (4)
            汽車: car (5)
        
        
    耐用年數
        3年：機械腳踏車
        4年：運輸業用客車、貨車 
        5年：非運輸業用客車、貨車 
    '''
    
    # print(f"迄本件車禍發生時即{incidentDate}，出廠日{manufactureDate}")
    
    try:
    
        # ----- 轉換民國年份為西元年份
        manufactureYear_AD = int(manufactureDate.split('-')[0]) + 1911
        manufactureMonth = int(manufactureDate.split('-')[1])
        
        incidentYear_AD = int(incidentDate.split('-')[0]) + 1911
        incidentMonth = int(incidentDate.split('-')[1])
        
        manufacture_date_obj = datetime(manufactureYear_AD, manufactureMonth, 1)
        incident_date_obj = datetime(incidentYear_AD, incidentMonth, 15)
        
        # - 計算日期差距
        betweenMonth = ((incident_date_obj.year - manufacture_date_obj.year) * 12 + incident_date_obj.month - manufacture_date_obj.month)

        # - 若有日期且日期大於5，則以多一個月作為計算
        try: incidentDay = int(incident_date_obj.day)
        except (IndexError, ValueError, TypeError, AttributeError):  incidentDay = 1
        if incidentDay >= 15: betweenMonth += 1
            
        # print(f"中間經過{betweenMonth}月")
        
        # - 轉換耐用年數
        useful_life = 0 # = 預設耐用年數
        if vehicle == 'scooter': useful_life = 3
        elif vehicle == 'business_car': useful_life = 4
        elif vehicle == 'car': useful_life = 5
        else: useful_life = int(vehicle)
        # print(f'{vehicle} - 耐用年數為 {useful_life}')
        
        # ----- 折舊計算
        '''
        計算須知：
            不需要折舊的項目：工資、鈑金、塗裝、烤漆
            需要折舊的項目：零件費用、材料費用
        '''
        depreciation_count = repairFee.get('零件', 0) + repairFee.get('材料', 0) # = 取得成本
        final_amount = 0 # = 最後需要支付總額
        for key, value in repairFee.items(): 
            if key != '零件' and key != '材料':
                final_amount += repairFee.get(key, 0)   # @ 加總除了需折舊項目總額
        # print(f"無需折舊總額 {final_amount}, 需折舊金額為 {depreciation_count}")
        
        # - 平均法
        if method == 'equal-annual-payment': 
            
            # * 殘價 = 取得成本 ÷（ 耐用年數 ＋ 1 ）|【大於耐用年數的只算到這一項】
            residual = round(depreciation_count / ( useful_life + 1 )) # = 殘價
            reduce_amount = 0
            
            if betweenMonth < useful_life * 12: 
                # * 折舊額 ＝（ 取得成本 － 殘價 ）× 1 /（ 耐用年數 ）×（ 使用年數 ）
                depreciation_amount = round((depreciation_count - residual) * 1 / (useful_life) * (betweenMonth / 12)) # = 折舊額

                # * 扣除折舊後價值 ＝ 新品取得成本 － 折舊額
                reduce_amount = depreciation_count - depreciation_amount
            else: 
                # * 實際使用時間 > 耐用年數，為殘值
                reduce_amount = residual
                
            final_amount += reduce_amount
            # print(f"[平均法] 算出的折舊金額 {reduce_amount}")
                
        # - 定率遞減法
        elif method == 'depreciation-fixed': 
            # * 【非運輸業用客車、貨車】之耐用年數為5年，依定率遞減法每年折舊1000分之369
            # * 【運輸業用客車、貨車】之耐用年數為4年，依定率遞減法每年折舊1000分之438
            # * 【機械腳踏車】之耐用年數為3年，依定率遞減法每年折舊1000分之536
            
            # - 率遞減法每年折舊值
            depreciation_division = 1
            if useful_life == 5: depreciation_division = 0.369
            elif useful_life == 4: depreciation_division = 0.438
            elif useful_life == 3: depreciation_division = 0.536
            
            # -----  計算遞減率        
            remainsMonth = betweenMonth # = 計算總共要遞減幾次
            depreciation_amount = depreciation_count # = 折舊後價值
            temp_amount = 0

            # - 每年進行折舊
            for i in range(betweenMonth // 12):
                temp_amount = round(depreciation_amount * depreciation_division)
                depreciation_amount -= temp_amount

            # - 處理剩餘的月份
            temp_amount = round(depreciation_amount * depreciation_division * ((betweenMonth % 12) / 12))
            depreciation_amount -= temp_amount

            # - 最終價格
            depreciation_count_bound = depreciation_count * 0.1 # * 加歷年折舊累積額，總和不得超過該資產成本原額之10分之9
            reduce_amount = 0
            if depreciation_amount > depreciation_count_bound:
                reduce_amount = depreciation_amount
            else: 
                reduce_amount = depreciation_count_bound
                
            final_amount += reduce_amount
            # print(f"[定率遞減法] 算出的折舊金額 {reduce_amount}")
            
        else:
            print("Please input method. 請輸入方法，否則無法計算")
        
        return round(final_amount)
    
    except Exception as e:
        print("！錯誤", manufactureDate, incidentDate)
        print(e)

    
           
# if __name__ == '__main__':
    
    # # 初始化 configparser 對象
    # config = configparser.ConfigParser()

    # # 讀取配置文件
    # config.read('carDepreciation.ini')

    # # 從配置文件中獲取參數
    # manufactureDate = config.get('CarInfo', 'manufactureDate')
    # incidentDate = config.get('CarInfo', 'incidentDate')
    # repairFee = json.loads(config.get('CarInfo', 'repairFee'))  # 將 JSON 字串轉換為字典
    # vehicle = int(config.get('CarInfo', 'vehicle'))  # 轉換為整數
    # method = config.get('CarInfo', 'method')

    # # 呼叫 carDepreciation 函數
    # carDepreciation(
    #     manufactureDate=manufactureDate,
    #     incidentDate=incidentDate,
    #     repairFee=repairFee,
    #     vehicle=vehicle,
    #     method=method
    # )




''' 
範例輸入:
    carDepreciation(
        manufactureDate='107-8',
        incidentDate='108-1',
        repairFee={
            '工資': 8885,
            '材料': 19400,
            '零件': 0,
            '鈑金': 0,
            '塗裝': 0,
            '烤漆': 0
        },
        vehicle=5,
        method='depreciation-fixed'
    )
'''
