# Many lines are adapted from https://github.com/fedebotu/ICLR2022-OpenReviewData
import argparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import yaml

from crawler import OpenreviewCrawler

def read_yaml(fname):
    with open(fname, "r") as f:
        return yaml.full_load(f)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_filepath", default="./configs/iclr_2024.yaml")
    parser.add_argument("--all", action="store_true", help="All selections (oral, spotlight, poster) will be crawled.")
    parser.add_argument("--selection", default="oral")
    parser.add_argument("--max_wait", default=60, type=int, help="Maximum wait time (in seconds) until the page is fully loaded.")
    parser.add_argument("--headless", action="store_true", help="Crawl with headless mode.")
    return parser.parse_args()


if __name__ == "__main__":

    args = get_args()
    config = read_yaml(args.config_filepath)

    # Select a crawling scope among ("all", ["oral", "spotlight", "poster"])
    if args.all:
        crawling_scope = config["conference"]["selections"]
    else:
        crawling_scope = [args.selection]
    
    # Set a webdriver
    if args.headless:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
    else:
        options = None

    web_driver = webdriver.Chrome(
        service=ChromeService(
            ChromeDriverManager().install()
        ), 
        options=options,
    )

    crawler = OpenreviewCrawler(
        config=config, 
        web_driver=web_driver, 
        max_wait=args.max_wait,
    )
    
    for selection in crawling_scope:
        crawler.crawl(selection)

 