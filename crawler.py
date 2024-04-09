# Many lines are adapted from https://github.com/fedebotu/ICLR2022-OpenReviewData
from collections import defaultdict
from dataclasses import dataclass
from tqdm import tqdm
from typing import Any, Dict
import json
import os
import time

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def get_keywords(web_element: WebElement) -> str:
    sections = web_element.find_elements(By.XPATH, ".//div/div/strong")
    for idx, section in enumerate(sections, start=1):
        if section.text.strip() == "Keywords:":
            keywords = web_element.find_element(By.XPATH, f".//div/div[{idx}]/span").text.strip()
            return keywords
    return " "


@dataclass
class OpenreviewCrawler:
    config: Dict[str, Any]
    web_driver: WebDriver
    max_wait: int

    def get_paper_details(self, web_element: WebElement, index: int) -> Dict[str, Any]:
        data = defaultdict()

        paper_base_info = web_element.find_element(By.TAG_NAME, "a")
        data["title"] = paper_base_info.text.strip()
        data["link"] = paper_base_info.get_attribute("href").strip().replace("forum", "pdf")

        # Get authors info
        data["authors"] = web_element.find_element(By.CLASS_NAME, "note-authors").text.strip()
        
        # Open up the details to get keywords (> Show details)
        paper_detailed_info = web_element.find_element(By.CLASS_NAME, "collapse-widget")
        if index == 0: # to avoid ElementClickInterceptedException
            paper_detailed_info.find_element(By.TAG_NAME, "a").send_keys(Keys.CONTROL + Keys.HOME)

        page_loaded = False
        while not page_loaded:
            try:
                condition = EC.element_to_be_clickable(paper_detailed_info.find_element(By.TAG_NAME, "a"))
                WebDriverWait(self.web_driver, self.max_wait).until(condition)
                page_loaded = True
            except:
                time.sleep(1)

        try:
            show_or_hide_details_button = paper_detailed_info.find_element(By.TAG_NAME, "a")
            if show_or_hide_details_button.text.strip() == "Show details":
                show_or_hide_details_button.click()
                time.sleep(1)
        except:
            data["keywords"] = " "
        else:
            data["keywords"] = get_keywords(paper_detailed_info)

        return data
    
    def crawl(self, selection: str):
        main_url = self.config["navigation_paths"]["base_url"].format(
            selection=selection,
            **self.config["conference"]
        )
        self.web_driver.get(main_url)
        print(main_url)

        # Explicitly wait until the entire page has fully loaded 
        # (indicator: right-arrow (>) located at the bottom)

        next_page_xpath = self.config["navigation_paths"]["next_page"].format(
            selection=selection, 
            page_indicator=self.config["page_indicators"][selection]
        )
        condition = EC.presence_of_element_located((By.XPATH, next_page_xpath))
        WebDriverWait(self.web_driver, self.max_wait).until(condition)

        # Set output configs
        save_dir = self.config["save_info"]["save_dir"].format(**self.config["conference"])
        os.makedirs(save_dir, exist_ok=True)
        save_filename = self.config["save_info"]["save_filename"].format(selection=selection)
        save_filename = os.path.join(save_dir, save_filename)

        with open(save_filename, "a", encoding="utf-8") as f:
            while True:
                papers_xpath = self.config["navigation_paths"]["papers"].format(selection=selection)
                papers = self.web_driver.find_elements(By.XPATH, papers_xpath)
                for index, paper in tqdm(enumerate(papers), total=len(papers)):
                    data = self.get_paper_details(paper, index)
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
                try:
                    self.web_driver.find_element(By.XPATH, next_page_xpath).click()
                    time.sleep(20)               

                except:
                    print("No next page, exit")
                    break


 