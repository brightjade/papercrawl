import os
import argparse
import requests
import json
import yaml
from bs4 import BeautifulSoup


def read_yaml(fname):
    with open(fname, "r") as f:
        return yaml.full_load(f)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_filepath", default="./configs/emnlp_2024.yaml")
    parser.add_argument("--selection", default="main_conference")
    return parser.parse_args()


def scrape(config, selection):
    main_url = config["navigation_paths"]["base_url"].format(
        selection=selection, **config["conference"]
    )
    response = requests.get(main_url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Find all 'strong' tags within 'p' tags and extract the text
    papers = [strong.get_text() for strong in soup.select('p strong')]

    # Set output configs
    save_dir = config["save_info"]["save_dir"].format(
        **config["conference"]
    )
    os.makedirs(save_dir, exist_ok=True)
    save_filename = config["save_info"]["save_filename"].format(
        selection=selection
    )
    save_filename = os.path.join(save_dir, save_filename)

    with open(save_filename, "a", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps({"title": paper}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    args = get_args()
    config = read_yaml(args.config_filepath)

    scrape(config, args.selection)
