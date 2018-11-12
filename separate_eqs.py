import csv
import os
import subprocess

# Separates equations into lists of singular and nonsingular equations
def separate_eqs(**kwargs):
    eqs_file = open(kwargs['eq_tsv_file'], 'r+') # Open 4 column eqs.tsv file
    reader = csv.reader(eqs_file, delimiter='\t')

    PATH = os.path.join(os.getcwd(), kwargs['output_dir']) # Output path
    if not os.path.exists(PATH): # If output_dir doesn't exist
        os.mkdir(PATH)
    sing_file = open(os.path.join(PATH, 'singular_eqs.tsv'), 'w+')
    sing_writer = csv.writer(sing_file, delimiter='\t')
    nonsing_file = open(os.path.join(PATH, 'nonsingular_eqs.tsv'), 'w+')
    nonsing_writer = csv.writer(nonsing_file, delimiter='\t')

    for eq in reader:
        if int(eq[2]) == 1: # articleCount == 1
            sing_writer.writerow(eq)
        else:
            nonsing_writer.writerow(eq)

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
