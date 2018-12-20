# from flask import Flask
import datetime
import subprocess
import argparse
import time
import os
#import config
import demacro_test
import shutil
import tarfile
#import convertlatex
#import proctex
#import enumerate_eqs
#import enumerate_docs
#import striplatex

#Input days between updates here
DAYS_BETWEEN_UPDATES = 30

# application = Flask(__name__)

#LOCAL_ARTICLE_MOUNT_PATH needs to be manually created before starting program (mkdir)
REMOTE_ARTICLE_MOUNT_PATH = 'dpj2108@habanero.rcs.columbia.edu:/rigel/home/dpj2108/remote_mount'
LOCAL_ARTICLE_MOUNT_PATH = '/local/hoptex/article_service_test/update_article_service/updated_articles'
PROCESSED_ARTICLE_FOLDER = '/local/hoptex/article_service_test/update_article_service/processed_articles'
COPY_FOLDER = '/local/hoptex/article_service_test/update_article_service/local_mount_copy'

input_pattern = r'\\input\s*\{\s*([^\s\\]+)\}|\\input(?![A-Za-z@])\s*([^\s\\]+)'

def monthly_update(days, ssh):
    while True:

        #Mounting remote folder
        print('{} | Mounting Remote Article Folder...'.format(str(datetime.datetime.now())))
        mount_remote_folder(ssh, REMOTE_ARTICLE_MOUNT_PATH, LOCAL_ARTICLE_MOUNT_PATH)

        now = datetime.datetime.now()
        print('------------------------------')
        print('{} | Updating articles... '.format(str(now)))

        #old 2.7 service (untars .tar file and .tar.gz files within each .tar file / demacro's each .tex file)
        extractlatex()

        #Equation-portion of service
        #enumerate_eqs.main()
        #enumerate_docs.main()
        #striplatex.main()

        #old 3.4 service (converting .tex files -> .xhtml files / convert .xhtml files -> .json files)
        #convertlatex.main()
        #proctex.main()

        print('------------------------------')
        print('Completed downloading and untarring the articles')

        #Unmounting remote folder
        print('{} | Unmounting Remote Article Folder...'.format(str(datetime.datetime.now())))
        unmount_chicago_hd(REMOTE_ARTICLE_MOUNT_PATH)

        delay = 60 * 60 * 24 * days
        next_update_time = now + datetime.timedelta(0, delay)
        next_update_time = str(next_update_time).split(".")[0]
        print('{} | Next update will be @ {}'.format(str(datetime.datetime.now()), next_update_time))
        print('\n\n\n')
        time.sleep(delay)

def mount_remote_folder(ssh_key_path, remote_path, mount_path):
    cmd = 'sshfs -o StrictHostKeyChecking=no -o IdentityFile={} {} {}'.format(ssh_key_path, remote_path, mount_path)
    subprocess.call(cmd.split())

def extractlatex():
    #Making the initial 3 directories
    print('{} | Making Project Dirs...'.format(str(datetime.datetime.now())))
    article_data_folder = LOCAL_ARTICLE_MOUNT_PATH

    processed_data_folder = PROCESSED_ARTICLE_FOLDER
    if not os.path.isdir(processed_data_folder):
        os.makedirs(processed_data_folder)

    copy_folder = COPY_FOLDER
    if not os.path.isdir(copy_folder):
        os.makedirs(copy_folder)

    print('{} | Find Last Update...'.format(str(datetime.datetime.now())))
    updated_activity_last_date = find_last_article_update(processed_data_folder)
    today = datetime.datetime.now()

    inserted_article_count = 0
    curr_date_list = []
    # Iterates through the number of months between 'today' and 'updated_activity_last_date'
    # Each curr_date == (year, month, 1); article downloaded at the beginning of each month
    for n in range(1, (today.year - updated_activity_last_date.year) * 12 + (today.month - updated_activity_last_date.month)):
        curr_date_list.append(datetime.datetime(updated_activity_last_date.year + int((updated_activity_last_date.month + n) / 12),
                                                max((updated_activity_last_date.month + n) % 12 + 1, 1),
                                                1))
    for curr_date in curr_date_list:
        filename = curr_date.strftime('%y%m') + '.tar'
        # os.walk() generates the file names in a directory tree by walking the tree top-down or bottom-up
        # Untars each .tar file in the article_data_folder (updated_articles)
        for root, dirs, files in os.walk(article_data_folder):
            try:
                # parse file (untars the .tar files)
                if filename in files and '.tar' in filename:
                    # Processes each compressed article folder
                    parsed = parse_article_file(root, curr_date.strftime('%y%m'), processed_data_folder, copy_folder)
                    if not parsed:
                        print('Error reading data for ' + curr_date.strftime('%Y-%m'))
                else:
                    print('Could not find data for ' + curr_date.strftime('%Y-%m'))

            except Exception as e:
                print(e)
                print('failed to insert %s' % filename)

    return {'status': 'success', 'activity_inserted': inserted_article_count}

def find_last_article_update(data_folder): # data_folder == processed_data_folder
    last_date = datetime.datetime.strptime('1801', '%y%m')
    # Go through folders, find the last date on this
    for curr_dir in os.listdir(data_folder):
        if(curr_dir.startswith(".")):
            #print(".DS Store")
            continue
        else:
            time = curr_dir[0:4] # Format of folder name (contains articles from that date) inside processed_data_folder
            curr_dir_date = datetime.datetime.strptime(time, '%y%m')
            if curr_dir_date is not None and curr_dir_date > last_date:
                last_date = curr_dir_date
    return last_date

def parse_article_file(root, foldername, processed_folder, local_folder):
    filename = foldername + '.tar'
    article_filename = os.path.join(root, filename)
    local_filename = os.path.join(local_folder, filename) # local_folder == 'local_mount_copy'
    print("{} | Creating copy of file {} into {}".format(str(datetime.datetime.now()), article_filename,
                                                         local_filename))
    shutil.copy2(article_filename, local_folder) # Copy to 'local_mount_copy'
    f = tarfile.open(local_filename)

    print("{} | Untarring file {}".format(str(datetime.datetime.now()), local_filename))
    output_folder = os.path.join(processed_folder, foldername)
    article_folder = os.path.join(output_folder, filename)
    global untar_directory
    untar_directory = os.path.join(output_folder, foldername)
    f.extractall(output_folder) # Extract all the .tex folders to 'processed_articles'
    f.close()
    print("{} | Deleting local file {}".format(str(datetime.datetime.now()), local_filename))
    os.remove(local_filename)

    try:
        global tex_folder
        # .../processed_articles/1220/1220_tex/<.tex articles>
        tex_folder = os.path.join(output_folder, foldername + '_tex') # USE THIS FORMAT TO PUT IN THE .tex FILES
        print(tex_folder)
        # Extract and demacro
        print("{} | Running demacro script on folder {}".format(str(datetime.datetime.now()), article_folder))
        demacro_untar(untar_directory, tex_folder)
        return True
    except Exception as e:
        print(e)
        return False

def demacro_untar(untar, tex):
    demacro_test.untarballs(untar, tex)
    demacro_test.demacro_folder(tex)

def unmount_chicago_hd(drive_path):
    cmd = 'umount {}'.format(drive_path)
    subprocess.call(cmd.split())

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', help='private key file', required=True)

    ssh_key = parser.parse_args().i
    monthly_update(DAYS_BETWEEN_UPDATES, ssh_key)
