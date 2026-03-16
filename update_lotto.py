#!/usr/bin/env python3
import requests, json, re, sys, time
 
def fetch_lotto_data(drwNo):
    url = "https://www.dhlottery.co.kr/common.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.dhlottery.co.kr/gameResult.do?method=byWin',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
    }
    params = {'method': 'getLottoNumber', 'drwNo': drwNo}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        content_type = response.headers.get('Content-Type', '').lower()
        print(f"  Content-Type: {content_type}")
        print(f"  응답({len(response.text)}자): {repr(response.text[:200])}")
        if 'html' in content_type:
            print(f"  [경고] HTML 반환 - 차단됨")
            return None
        data = response.json()
        if data.get('returnValue') == 'success':
            return {
                'round': int(data['drwNo']),
                'nums': [int(data[f'drwtNo{i}']) for i in range(1,7)],
                'bonus': int(data['bnusNo']),
                'date': data.get('drwNoDate','')
            }
        print(f"  returnValue: {data.get('returnValue')}")
    except Exception as e:
        print(f"  [오류] {type(e).__name__}: {e}")
    return None
 
def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'let latestRound\s*=\s*(\d+)', content)
    current = int(m.group(1))
    print(f"현재 latestRound: {current}")
 
    new_rounds = []
    r = current + 1
    while True:
        print(f"\n{r}회차 조회 중...")
        d = fetch_lotto_data(r)
        if not d:
            print(f"  {r}회차 없음 - 종료")
            break
        new_rounds.append(d)
        print(f"  ✅ {r}회차: {d['nums']} 보너스:{d['bonus']} ({d['date']})")
        r += 1
        time.sleep(1)
 
    if not new_rounds:
        print("\n새 회차 없음")
        return
 
    latest = new_rounds[-1]
    print(f"\n{len(new_rounds)}개 새 회차! 최신: {latest['round']}회")
 
    # SEED_HISTORY 업데이트
    sh_match = re.search(r'const SEED_HISTORY = \[(.*?)\];', content, re.DOTALL)
    existing = []
    for m2 in re.finditer(r'\{round:(\d+),nums:\[([^\]]+)\],bonus:(\d+)\}', sh_match.group(1)):
        existing.append({'round':int(m2.group(1)),'nums':list(map(int,m2.group(2).split(','))),'bonus':int(m2.group(3))})
    for d in new_rounds:
        existing.append({'round':d['round'],'nums':d['nums'],'bonus':d['bonus']})
    existing = sorted(existing, key=lambda x: x['round'])[-5:]
    lines = [f"  {{round:{e['round']},nums:[{','.join(map(str,e['nums']))}],bonus:{e['bonus']}}}" for e in existing]
    new_sh = 'const SEED_HISTORY = [\n' + ',\n'.join(lines) + ',\n];'
    content = re.sub(r'const SEED_HISTORY = \[.*?\];', new_sh, content, flags=re.DOTALL)
    content = re.sub(r'let latestRound\s*=\s*\d+', f'let latestRound = {latest["round"]}', content)
    content = re.sub(r'let latestWinNums\s*=\s*\[[^\]]*\]', f'let latestWinNums = {json.dumps(latest["nums"])}', content)
    content = re.sub(r'let latestBonusNum\s*=\s*\d+', f'let latestBonusNum = {latest["bonus"]}', content)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ index.html 업데이트 완료! latestRound: {latest['round']}")
 
if __name__ == '__main__':
    main()
