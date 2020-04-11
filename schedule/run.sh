#!/bin/bash
source /home/tucovid/miniconda/etc/profile.d/conda.sh && \
conda activate covid-19 && \
python /home/tucovid/tucovid19/schedule/pulldata_dump.py

#Make this file executable
#chmod +x run.sh
#Add the following line in crontab -e at the last line
#0 */2 * * * /home/tucovid/tucovid19/schedule/run.sh >> /home/tucovid/cron.log 2>&1
