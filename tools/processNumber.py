import json
import re
from os import listdir
import traceback

def is_number(input):
  if (
      input == '0' or
      input == '1' or
      input == '2' or
      input == '3' or
      input == '4' or
      input == '5' or
      input == '6' or
      input == '7' or
      input == '8' or
      input == '9'
    ):
      return True

  else:
    return False

def is_chinese_number(input):
  if (
      input == '零' or
      input == '壹' or input == '一' or
      input == '貳' or input == '二' or
      input == '參' or input == '三' or input == '叁' or input == '参' or
      input == '肆' or input == '四' or
      input == '伍' or input == '五' or
      input == '陸' or input == '六' or
      input == '柒' or input == '七' or
      input == '捌' or input == '八' or
      input == '玖' or input == '九' or
      input == '拾' or input == '十' or
      input == '佰' or input == '百' or
      input == '仟' or input == '千' or
      input == '萬'
    ):
      return True

  else:
      return False

def chinese_to_arabic(chinese_num):
    num_dict = {
        '零': 0,
        '壹': 1, '一': 1,
        '貳': 2, '二': 2,
        '參': 3, '三': 3, '叁': 3, '参': 3,
        '肆': 4, '四': 4,
        '伍': 5, '五': 5,
        '陸': 6, '六': 6,
        '柒': 7, '七': 7,
        '捌': 8, '八': 8,
        '玖': 9, '九': 9,
    }

    result = [0,0,0,0,0,0,0,0]

    l = len(chinese_num)
    i = l-1
    cnt = 7
    while i >= 0:
      char = chinese_num[i]

      if char == '萬':
        cnt = 3
        i -= 1
        while i >= 0:
          char_1 = chinese_num[i]

          if char_1 == '萬':
            return ''

          if char_1 == '仟' or char_1 == '千':
            cnt = 0
            i -= 1

          elif char_1 == '佰' or char_1 == '百':
            cnt = 1
            i -= 1

          elif char_1 == '拾' or char_1 == '十':
            cnt = 2
            i -= 1

            if(i == -1): result[cnt] += 1

          else: #if char in num_dict:
            result[cnt] += num_dict[char_1]
            i -= 1

      elif char == '仟' or char == '千':
        cnt = 4
        i -= 1

      elif char == '佰' or char == '百':
        cnt = 5
        i -= 1

      elif char == '拾'  or char == '十':
        cnt = 6
        i -= 1

      else: #if char in num_dict:
        result[cnt] += num_dict[char]
        i -= 1

    money = ''
    start = 0
    L = len(result)

    for i in range(L):
      if result[i] != 0:
          start = i
          break

    while start < L:
      money += str(result[start])
      start += 1

    return money

def translate(input_str) -> str:
  
  try:
    if input_str == "":
      return 0
    
    arabic = 0
    tmp = ''

    for i in input_str:
      if is_number(i): 
        if tmp == '':
          tmp = int(i)
        else:  
          tmp += int(i)

      elif i == ('萬'):
        
        if tmp == '':
          arabic = arabic * 10000
        
        else:
          arabic += int(tmp)*10000
          tmp = ''

      elif i == ('仟') or i == ('千'):
        
        if tmp == '':
          arabic = arabic * 1000
        else:
          arabic += int(tmp)*1000
          tmp = ''

      elif i == ('佰') or i == ('百'):
        
        if tmp == '':
          tmp = 100
        else:
          arabic += int(tmp)*100
          tmp = ''

      elif i == ('拾') or i == ('十'):
        
        if tmp == '':
          tmp = 10
          
        else:
          arabic += int(tmp)*10
          tmp = ''

    if tmp: arabic += int(tmp)
    
  except Exception as e:
    print("發生錯誤，輸入的字符串為:", input_str)
    print("錯誤詳情:", e)
    traceback.print_exc()  # 打印錯誤的堆棧跟蹤
    exit()  # 終止程式

  return int(arabic)


# ---------------------------- 時間
incidentTime_regex_list = [
    "(?:主張：|上訴意旨略以：|原告主張(?:：?)|主張如下：|理由要旨[一二三四五六七八九十]、|本件上訴意旨以：).*?(\d+年\d+月\d+日(?:上午|下午|中午|晚間|晚上)?(?:\d+時)?(?:\d+時)?(?:\d+分)?).*?(?:駕駛(?!椅)|車禍|騎乘|[一二三四五六七八九十]、|，自屬有據。)",
    "((?:原告主張|查被告因|被告於|被告於民國)(?:.*?)(\d+年\d+月\d+日(?:上午|下午|中午|晚間|晚上)?(?:\d+時)?(?:\d+時)?(?:\d+分)?)(?:.*?)(?:駕駛|不當|不慎).*?)。"
]
incidentTime_regex_compiled_list = [re.compile(pattern) for pattern in incidentTime_regex_list]

# ---------------------------- 事發
happened_regex_list = [
    "(?:實體部分|事實及理由|實體方面|原告聲明)(?:.*?)(?:主張略以：|主張：|[^被]上訴人方面：|上訴意旨略以：|原告主張(?:：?)|主張如下：|理由要旨[一二三四五六七八九十]、|本件上訴意旨以：)([一二三四五六七八九十]?.*?)(?=[一二三四五六七八九十]、|，自屬有據。)",
    "(?:主張：|上訴意旨略以：|上訴人起訴主張|原告主張(?:：?)|主張如下：|理由要旨[一二三四五六七八九十]、|本件上訴意旨以：|本件上訴人於原審起訴主張略以：|上訴人於原審起訴主張略以：)(.*?(?:駕駛(?!椅)|車禍|騎乘).*?)(?:[一二三四五六七八九十]、|，自屬有據。|(?:，為此)?，爰依)",
    "(?:經查，)(.*?)(?=[一二三四五六七八九十]、)",
    "((原告主張|查被告[因自]|被告於).*?(駕駛|不當|不慎|駛出).*?)(?:。|等情)",
    "(?:查本件車禍之發生，)(.*?)。",
    "(?:查被告駕車)((.*?肇事主因)(.*?肇事次因)?)",
    "認定上訴人於(.*?)。",
    "均陳稱(.*?)。"
]
happened_regex_compiled_list = [re.compile(pattern) for pattern in happened_regex_list]

# !預先執行 re.compile 會讓後續程式碼較快

# --------------------------------------------------------------------------------------------------------------------

def incidentTime_regex_catch(text):
    for regex in incidentTime_regex_compiled_list:
        matches = list(regex.finditer(text, re.MULTILINE))
        if matches and matches[0].group(1) != None:
            return matches[0].group(1)

    return None

def happened_regex_catch(text):
    for regex in happened_regex_compiled_list:
        matches = list(regex.finditer(text, re.MULTILINE))
        if matches:
            return matches[0].group(1)

    return None


def money_regex_catch(text):
    mainText = ''
    mainText = re.search(r'主文(.*?)(事實|理由|書記官)', text)

    if(mainText):
        text = re.search(r'給付(.*?)原告(.*?)(新臺幣|新台幣)(.*?)元', str(mainText.group(0)))
        text = str(text)

        start_keyword = '新臺幣'
        end_keyword = '元'

        start_index = text.find(start_keyword)
        end_index = text.find(end_keyword)

        compensation = text[start_index : end_index]
        money = ''

        if(len(compensation) <= 50):
            arabic_num = ''
            chinese_num = ''
            total_num = ''

            for i in compensation:
                if is_number(i) or is_chinese_number(i): total_num += i
                if is_number(i): arabic_num += i
                if is_chinese_number(i): chinese_num += i

            if chinese_num and arabic_num:
                money = translate(total_num)

            elif arabic_num:
                money = arabic_num

            elif chinese_num:
                money = chinese_to_arabic(chinese_num)

            if money: return int(money)

    return None
  
def chinese_to_int(text):
  
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
  
  
def auto_translate_ch_to_int_number(text):
  return translate(chinese_to_int(text)) 
            

# if __name__ == '__main__':
#   print(auto_translate_ch_to_int_number('十四'))
#   print(auto_translate_ch_to_int_number('四十'))
#   print(auto_translate_ch_to_int_number('6拾'))
#   print(auto_translate_ch_to_int_number('6拾萬'))
  
#   print(auto_translate_ch_to_int_number('拾萬'))
#   print(auto_translate_ch_to_int_number('10萬'))
  
#   print(auto_translate_ch_to_int_number('百萬'))
#   print(auto_translate_ch_to_int_number('一百萬'))
#   print(auto_translate_ch_to_int_number('1百萬'))
#   print(auto_translate_ch_to_int_number('100萬'))
#   print(auto_translate_ch_to_int_number('拾1'))
  
  
