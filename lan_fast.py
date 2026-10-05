import os, requests
from concurrent.futures import ThreadPoolExecutor
PROJECT_DIR = r'C:\Users\Table\Documents\GitHub\Hong-Kong-Assetto-Corsa'
ZIP_FOLDER = os.path.join(PROJECT_DIR, 'all_3324_zips')
API_KEY = 'ad5940a63bd344c48b0351ef1c7a905e'
os.makedirs(ZIP_FOLDER, exist_ok=True)
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})
tiles = [f'{m}-{s}-{i}{sub}' for m in range(1, 17) for s in ['NW', 'NE', 'SW', 'SE'] for i in range(1, 26) for sub in ['A', 'B', 'C', 'D']]
print('🚀 啟動 LAN 極速專用版 (32 Threads + Fast Timeout)...')

def download_tile(item):
    idx, tile = item
    zip_name = f'{tile}.zip'
    save_path = os.path.join(ZIP_FOLDER, zip_name)
    if os.path.exists(save_path) and os.path.getsize(save_path) > 5000: return
    url = f'https://data11.map.gov.hk/api/3d-zip/FBX/{zip_name}?&key={API_KEY}'
    try:
        with session.get(url, stream=True, timeout=5) as resp:
            if resp.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=2048*1024):
                        if chunk: f.write(chunk)
                sz_mb = round(os.path.getsize(save_path)/(1024*1024), 2)
                if sz_mb > 0.01:
                    print(f'[{idx}/3324] 🟢 下載成功: {zip_name} ({sz_mb} MB)')
                else:
                    if os.path.exists(save_path): os.remove(save_path)
    except Exception:
        if os.path.exists(save_path): os.remove(save_path)

with ThreadPoolExecutor(max_workers=32) as executor:
    executor.map(download_tile, enumerate(tiles, 1))
print('🎉 LAN 極速下載完成！')
