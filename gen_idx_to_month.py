import os
import yaml
import argparse

def main(**kwargs):
    texpath = kwargs['texpath']
    outpath = kwargs['outpath']

    subfolder_list = []

    folderlist = next(os.walk(texpath))[1]
    for subfolder in folderlist:
        if not subfolder.startswith('.'):
            subfolder_list.append(subfolder)

    with open(outpath, 'w') as fh:
        yaml.dump(subfolder_list, fh, default_flow_style=False)

    print('{} idx_to_month mappings found.'.format(len(subfolder_list)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('texpath', help='Path to the directory containing subfolders of .tex files')
    parser.add_argument('--outpath', help='Path to output the idx_to_month mapping', default='./idx_to_month.yml')
    args = parser.parse_args()

    main(**vars(args))
