# Many lines are borrowed from https://github.com/fedebotu/ICLR2022-OpenReviewData
import argparse
import os
import time
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from utils import read_yaml

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_filepath', default='./configs/neurips_2023.yaml')
    #parser.add_argument('--config_filepath', default='./configs/iclr_2024.yaml')
    parser.add_argument('--headless', action="store_true")
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
    config = read_yaml(args.config_filepath)

    conference_name = config["conference"]["name"]
    conference_year = config["conference"]["year"]
    conference_type = config["conference"]["type"][0]

    type_page = config["type_page"][conference_type]

    if args.headless:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
    else:
        options = None

    driver = webdriver.Chrome(options=options)

    driver.get(f'https://openreview.net/group?id={conference_name}.cc/{conference_year}/Conference#tab-accept-{conference_type}')
    print(f"https://openreview.net/group?id={conference_name}.cc/{conference_year}/Conference#tab-accept-{conference_type}")

    cond = EC.presence_of_element_located((By.XPATH, f'//*[@id="accept-{conference_type}"]/div/div/nav/ul/li[{type_page}]/a'))
    WebDriverWait(driver, 60).until(cond)
    time.sleep(10)
    
    # set output file
    save_filename = f'{conference_name}{conference_year}/{conference_type}_{config["save_info"]["save_filename"]}'
    os.makedirs(config["save_info"]["save_dir"], exist_ok=True)
    os.makedirs(f'{config["save_info"]["save_dir"]}/{conference_name}{conference_year}', exist_ok=True)
    save_filename = os.path.join(config["save_info"]["save_dir"], save_filename)

    with open(save_filename, 'w', encoding='utf8') as f:
        f.write('\t'.join(['Authors', 'Paper Title', 'Paper Link', 'Keywords'])+'\n')

    processed_page = 0

    while True:
        with open(save_filename, 'a', encoding='utf8') as f:
            papers = driver.find_elements(By.XPATH, f'//*[@id="accept-{conference_type}"]/div/div/ul/li')
            for idx, paper in enumerate(papers):
                title_link = paper.find_element(By.TAG_NAME, 'a')
                title = title_link.text.strip()
                link = title_link.get_attribute('href').strip()

                # get authors information
                if conference_name == 'NeurIPS':
                    authors = paper.find_element(By.CLASS_NAME, 'note-authors').text.strip()
                else:
                    authors = 'N/A'
                
                # open up the details
                details = paper.find_element(By.CLASS_NAME, 'collapse-widget')
                if idx == 0:
                    details.find_element(By.TAG_NAME, 'a').send_keys(Keys.CONTROL + Keys.HOME)

                page_loaded = False
                while not page_loaded:
                    try:
                        WebDriverWait(driver, 40).until(EC.element_to_be_clickable(details.find_element(By.TAG_NAME, 'a')))
                        page_loaded = True
                    except:
                        time.sleep(1)
                try:
                    show_or_hide_details_button = details.find_element(By.TAG_NAME, 'a')
                    if show_or_hide_details_button.text.strip() == 'Show details':
                        show_or_hide_details_button.click()                
                except:
                    import pdb; pdb.set_trace()
                    show_or_hide_details_button.send_keys(Keys.CONTROL + Keys.HOME)


                time.sleep(2)
                try:
                    keywords = details.find_element(By.XPATH, './/div/div/span').text.strip()
                    print(keywords)
                except:
                    keywords = ' '
                    import pdb; pdb.set_trace()
                f.write('\t'.join([authors, title, link, keywords])+'\n')

            processed_page += 1
            print(f'Finished processing {processed_page}!')
            
            # go to the next page
            try:
                driver.find_element(By.XPATH, f'//*[@id="accept-{conference_type}"]/div/div/nav/ul/li[{TYPE_PAGE[conference_name.lower()][conference_type]}]/a').click()
                time.sleep(30)               

            except:
                print('No next page, exit')
                break

