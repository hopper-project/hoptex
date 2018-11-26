import csv
import os
import subprocess
from collections import defaultdict

# Separates equations into lists of singular and nonsingular equations
def separate_eqs(**kwargs):
    eqs_file = open(kwargs['eq_tsv_file'], 'r+') # Open 4 column eqs.tsv file
    reader = csv.reader(eqs_file, delimiter='\t')

    PATH = os.path.join(os.getcwd(), kwargs['output_dir']) # Output path
    if not os.path.exists(PATH): # If output_dir doesn't exist
        os.mkdir(PATH)
    sing_file = open(os.path.join(PATH, 'singular_articles.txt'), 'w+')
    # sing_writer = csv.writer(sing_file, delimiter='\t')
    nonsing_file = open(os.path.join(PATH, 'nonsingular_articles.txt'), 'w+')
    # nonsing_writer = csv.writer(nonsing_file, delimiter='\t')

    article_eq_dict = defaultdict(int)

    for eq in reader:
        article_ids = eq[3].split(',')
        eq_id = eq[0]
        eq_freq = int(eq[2])

        if eq_freq > 1:
            for article_id in article_ids:
                article_eq_dict[article_id] = 1 # Flag to indicate article is nonsingular

    for aid in article_eq_dict.keys():
        print(aid)
        if article_eq_dict[aid] == 0:
            sing_file.write(aid + '\n')
        else:
            nonsing_file.write(aid + '\n')

    eqs_file.close()
    sing_file.close()
    nonsing_file.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Separates 4 column data into two different lists')
    parser.add_argument('eq_tsv_file', help='Path to the generated 4 column tsv file')
    parser.add_argument('output_dir', help='Path at which the file lists will be stored')
    args = parser.parse_args()
    separate_eqs(**vars(args))
