#!/bin/bash

gdown "https://drive.usercontent.google.com/download?id=1-sBPlmdmkzimdhCu7Aa8Ug1EluNwRBHT&export=download&authuser=3&confirm=t&uuid=7ac4e7c2-385f-479e-bb15-c8d039ae79e3&at=APZUnTUJ_WkTmoK-AKQ6XtH1iuRZ:1705146866592" -O "data_org.zip"
mkdir -p ./data
unzip -n ./data_org.zip -d ./data/

# docker run -it --gpus all --name LJPTW_Extraction -v "$PWD":/usr/src/app -w /usr/src/app python:3.10
docker build -t ljptw_extraction .
docker run -it --gpus all --name LJPTW_Extraction -v "$PWD":/usr/src/app ljptw_extraction

