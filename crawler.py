# Many lines are borrowed from https://github.com/fedebotu/ICLR2022-OpenReviewData
import argparse
import time
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conference', choices=['ICLR', 'NeurIPS'])
    parser.add_argument('--year', choices=[2023, 2424])
    parser.add_argument('--type', choices=['oral', 'spotlight', 'poster'])
    parser.add_argument('--save_filename', default='papers.tsv')
    parser.add_argument('--path', default=None)
    return parser.parse_args()


TYPE_PAGE = {
    "iclr": {
        'oral': 7,
        'spotlight': 13,
        'poster': 13,
    },
    "neurips": {
        'oral': 6,
        'spotlight': 13,
        'poster': 13,
    }
}


if __name__ == '__main__':

    args = get_args()
    driver = webdriver.Chrome(args.path)
    driver.get(f'https://openreview.net/group?id={args.conference}.cc/{args.year}/Conference#tab-accept-{args.type}')

    cond = EC.presence_of_element_located((By.XPATH, f'//*[@id="accept-{args.type}"]/div/div/nav/ul/li[{TYPE_PAGE[args.conference.lower()][args.type]}]/a'))
    WebDriverWait(driver, 60).until(cond)
    time.sleep(10)
    
    # set output file
    save_filename = f'{args.conference}{args.year}_{args.type}_{args.save_filename}'
    with open(save_filename, 'w', encoding='utf8') as f:
        f.write('\t'.join(['Authors', 'Paper Title', 'Paper Link', 'Keywords'])+'\n')

    processed_page = 0

    while True:
        with open(save_filename, 'a', encoding='utf8') as f:
            papers = driver.find_elements(By.XPATH, f'//*[@id="accept-{args.type}"]/div/div/ul/li')
            for paper in papers:
                title_link = paper.find_element(By.TAG_NAME, 'a')
                title = title_link.text.strip()
                link = title_link.get_attribute('href').strip()

                # get authors information
                if args.conference == 'NeurIPS':
                    authors = paper.find_element(By.CLASS_NAME, 'note-authors').text.strip()
                else:
                    authors = 'N/A'
                
                # open up the details
                details = paper.find_element(By.CLASS_NAME, 'collapse-widget')
                time.sleep(0.2)
                try:
                    details.find_element(By.TAG_NAME, 'a').click()
                    keywords = details.find_element(By.XPATH, './/div/div/span').text.strip()
                except:
                    keywords = ' '
                f.write('\t'.join([authors, title, link, keywords])+'\n')

            processed_page += 1
            print(f'Finished processing {processed_page}!')
            
            # go to the next page
            try:
                driver.find_element(By.XPATH, f'//*[@id="accept-{args.type}"]/div/div/nav/ul/li[{TYPE_PAGE[args.conference.lower()][args.type]}]/a').click()
                time.sleep(5)               

            except:
                print('No next page, exit')
                break

