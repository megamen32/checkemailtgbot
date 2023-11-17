import traceback

import redis
import random
import requests
import time
import json

# Настройки Redis
from private_config import SERVER_URL, AUTH

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 5

# Подключение к Redis
redis_conn = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
PROXY_CACHE_KEY = 'proxy_cache'
PROXY_CACHE_TIME = 60  # Время кеширования в секундах


def get_proxy():
    try:
        while True:
            # Проверка кеша и времени последнего запроса
            cached_proxies = redis_conn.get(PROXY_CACHE_KEY)
            proxy_list=None
            if cached_proxies and time.time() - json.loads(cached_proxies)['timestamp'] < PROXY_CACHE_TIME:
                proxy_list = json.loads(cached_proxies)['proxies']
            if not proxy_list:
                if False:
                    with open('data/proxy.txt', 'r') as f:
                        proxies = f.read()
                        _proxy_list = proxies.split('\n')
                        proxy_list=[]
                        for pr in _proxy_list:
                            proxy_list.append({'proxy':pr})
                else:
                    for i in range(2):
                        t = requests.get(f'{SERVER_URL}/proxy/', params={'count': 50, 'priority': i == 0}, auth=AUTH, timeout=15)
                        if t.status_code == 500:
                            break
                        try:
                            proxy_list = t.json()
                        except:
                            proxy_list = [{'proxy': t.text}]
                        if len(proxy_list)>0:
                            break
                    # Сохранение прокси в кеше Redis
                    redis_conn.set(PROXY_CACHE_KEY, json.dumps({'proxies': proxy_list, 'timestamp': time.time()}))

            proxy = random.choice(proxy_list)['proxy']



            return proxy
    except:
        traceback.print_exc()
        return None


if __name__=='__main__':
    proxy=get_proxy()
    print(proxy)