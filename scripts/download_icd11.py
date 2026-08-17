import os
import requests

def download_icd11():
    os.makedirs("data", exist_ok=True)

    ICD11_FILE = {
        "ICD-11.csv": "1MuNfO5hmaF5v8aSGloMGyLSbjDEjPXqs",
    }

    BASE_URL = "https://drive.google.com/uc?export=download&id={file_id}"

    for filename, file_id in ICD11_FILE.items():
        out_path = os.path.join("data", filename)
        if not os.path.exists(out_path):
            url = BASE_URL.format(file_id=file_id)
            print(f"Downloading {filename} from {url} ...")
            try:
                r = requests.get(url)
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    f.write(r.content)
                print(f"Downloaded {filename}")
            except requests.RequestException as e:
                print(f"Failed to download {filename}: {e}")
        else:
            print(f"{filename} already exists, skipping.")
