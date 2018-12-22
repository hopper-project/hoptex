#!/bin/bash

# Download article data from remote mount path (UChicago) and demacro the articles
python3 article_service.py -i ~/.ssh/id_rsa
cp /local/hoptex/article_service_test/update_article_service/processed_articles/1812/1812_tex/* /local/hoptex/monthly_test/

# Run enumerate.py on the new articles
python3 enumerate.py /local/hoptex/monthly_test 2

# Copy the article lists to Habanero for monthly processing
scp -r /local/hoptex/sep habanero:~/hoptex
