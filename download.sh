#!/bin/bash

gdown https://drive.google.com/uc?id=11oQYInLoDBU4gj4eQNX3MzH9yp3rZT2E
mkdir -p ./data
unrar x data_org.rar ./data/ || echo "若遭到安全性阻止，請前去開啟設定後輸入：unrar x data_org.rar ./data/ \n「系統設定」→「隱私權與安全性」→「強制允許」"


