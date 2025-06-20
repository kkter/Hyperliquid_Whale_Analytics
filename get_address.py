import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

url = "https://www.coinglass.com/zh/hyperliquid"

# 设置 Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    # 等待表格行加载出来
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ant-table-row"))
    )

    # 短暂等待，确保JS渲染更多内容
    time.sleep(3)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # 查找所有的表格行
    rows = soup.find_all('tr', class_='ant-table-row')

    whale_data = []
    # 遍历行，获取前20个地址
    for row in rows:
        # 在每一行中查找所有的单元格
        cells = row.find_all('td')
        
        # 通过检查单元格数量来确保是有效的数据行，需要至少4个单元格
        if len(cells) > 3:
            try:
                # 排名在第2个单元格 (索引为1)
                rank = cells[1].get_text(strip=True)
                
                # 币种在第4个单元格 (索引为3)
                asset = cells[3].get_text(strip=True)

                # 地址在第3个单元格 (索引为2) 的 'a' 标签里
                link_tag = cells[2].find('a')
                if link_tag and link_tag.has_attr('href'):
                    href = link_tag['href']
                    address = href.split('/')[-1]
                    
                    # 确保地址是有效的0x格式
                    if address.startswith('0x'):
                        whale_data.append({'rank': rank, 'asset': asset, 'address': address})

            except (IndexError, AttributeError) as e:
                # 如果某一行结构不同，打印一个提示并跳过
                print(f"跳过一个格式不符的行: {e}")
                continue
        
        # 如果已经找到20个地址，就停止
        if len(whale_data) >= 20:
            break

    # 打印结果
    print(f"成功获取到 {len(whale_data)} 个巨鲸持仓条目：")
    for data in whale_data:
        print(f"排名: {data['rank']}, 币种: {data['asset']}, 地址: {data['address']}")

except Exception as e:
    print(f"发生错误: {e}")

finally:
    if 'driver' in locals():
        driver.quit()