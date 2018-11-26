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

    article_to_eq = defaultdict(list)
    eq_to_article = defaultdict(list)

    article_id_set = set()

    for eq in reader:
        article_ids = eq[3].split(',')
        eq_id = eq[0]
        eq_freq = int(eq[2])

        for article_id in article_ids:
            article_id_set.add(article_id)
            article_to_eq[article_id].append(eq_id)

        eq_to_article[eq_id] += article_ids

        # if eq_freq > 1:
            # for article_id in article_ids:
                # article_eq_dict[article_id] = 1 # Flag to indicate article is nonsingular

    for aid in article_id_set:
        nonsing_flag = 0
        for eq_id in article_to_eq[aid]:
            if len(eq_to_article[eq_id]) > 1:
                nonsing_flag = 1

        if nonsing_flag:
            nonsing_file.write(aid + '.tex' + '\n')
        else:
            sing_file.write(aid + '.tex' + '\n')

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
