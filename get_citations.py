import argparse
import requests
import json
import time
import pandas as pd
from tqdm import trange

API_KEY = ""    # Works without API key but faster with it
URL = f"http://api.semanticscholar.org/graph/v1/paper/search"
HEADERS = {"x-api-key": API_KEY} if API_KEY else None


def get_citation_count(title: str) -> int:
    query_params = {
        "query": title,
        "fields": "title,citationCount",
        "limit": 1,
    }
    response = requests.get(URL, params=query_params, headers=HEADERS)
    max_retries = 5
    retries = 0
    
    while response.status_code != 200 and retries < max_retries:
        response = requests.get(URL, params=query_params, headers=HEADERS)
        retries += 1
        time.sleep(1)

    if response.status_code == 200:
        data = response.json()
        try:
            citation_count = data["data"][0]["citationCount"]
            return citation_count
        except:
            return -1   # No paper found
    else:
        print(f"Failed to get citation count for '{title}'")
        return -1


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_filepath", default="./outputs/EMNLP-2024/main_conference_paper.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    df = pd.read_json(args.config_filepath, lines=True)
    output_file = args.config_filepath.replace(".json", "_with_citation.json")
    output_file_sorted = args.config_filepath.replace(".json", "_with_citation_sorted.json")
    new_data = []

    with open(output_file, "a", encoding="utf-8") as f:
        for i in trange(len(df), desc="Getting citation counts"):
            title = df.loc[i, "title"]
            link = df.loc[i, "link"]
            authors = df.loc[i, "authors"]
            keywords = df.loc[i, "keywords"]
            num_citations = get_citation_count(title)
            new_data.append({
                "title": title, 
                "link": link,
                "authors": authors,
                "keywords": keywords,
                "citation_count": num_citations
            })
            f.write(json.dumps(new_data[-1], ensure_ascii=False) + "\n")
            
            # Sleep for 1 second to avoid rate limiting
            time.sleep(1)

    # Sort by citation count
    new_data = sorted(new_data, key=lambda x: x["citation_count"], reverse=True)
    with open(output_file_sorted, "a", encoding="utf-8") as f:
        for item in new_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
