#!/bin/bash
cd /backup/logger
for OPERATION in "$@"
do
   python3 ./logger.py $OPERATION # folder name
done
