

import requests


# address = "0x45d26f28196d226497130c4bac709d808fed4029"
address = "0x5b5d51203a0f9079f8aeb098a6523a13f298c060"
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz/info"

coin = "BTC"

def get_positions(address, coin):

        payload = {
            "type": "clearinghouseState",
            "user": address
        }
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(HYPERLIQUID_API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            

            print("==========================")
                  
            for position in data['assetPositions']:

                
                if position.get('position', {}).get('coin') == coin:

                    """
                    # 提取所需字段
                    szi = position['position'].get('szi', 'N/A')
                    entry_px = position['position'].get('entryPx', 'N/A')
                    liquidation_px = position['position'].get('liquidationPx', 'N/A')
                    # 格式化输出
                    print(f"Coin: {coin}, szi: {szi}, entryPx: {entry_px}, liquidationPx: {liquidation_px}")
                    """
                    print(position)
        else:
            print(f"请求失败: {response.status_code}, {response.text}")

get_positions(address, coin)

