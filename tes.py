from quant.fundamental import get_report_list, _normalize_url, DL_HEADERS, _extract_cookies
from curl_cffi import requests as curl_requests

rl = get_report_list(2026, 'tw3')
atts = rl['BBCA']['Attachments']
xurl = atts[0]['File_Path']
url = _normalize_url(xurl)

print("URL:", url)
print("Mencoba download via curl_cffi...")
cookies = _extract_cookies()
r = curl_requests.get(url, headers=DL_HEADERS, cookies=cookies, impersonate="firefox", timeout=90)

print("Status Code:", r.status_code)
print("Content length:", len(r.content))
print("Apakah format Excel (ZIP)?", r.content[:2] == b"PK" if r.content else False)