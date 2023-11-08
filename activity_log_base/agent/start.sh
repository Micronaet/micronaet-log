#!/bin/bash
cd /backup/logger
for OPERATION in "$@"
do
   python ./logger.py $OPERATION # folder name
done
