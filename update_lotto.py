#!/usr/bin/env python3
import json, re, sys, time, ssl, gzip, urllib.request, urllib.parse
 
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
 
def fetch_round(r):
    url = "https://www.dhlottery.co.kr/common.do"
    params = urllib.parse.urlencode({'method':'getLottoNumber','drwNo':str(r)})
    full_url = f"{url}?{params}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Accept-Encoding': 'identity',  # gzip 압축 비활성화
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.dhlottery.co.kr/gameResult.do?method=byWin',
        'Connection': 'keep-alive',
    }
    
    req = urllib.request.Request(full_url, headers=headers)
    try:
        res = urllib.request.urlopen(req, timeout=20, context=ctx)
        raw = res.read()
        text = raw.decode('utf-8', errors='replace').strip()
        print(f"  응답({len(text)}자): {repr(text[:200])}")
        
        # JSON 파싱
        d = json.loads(text)
        if d.get('returnValue') == 'success':
            return {
                'round': int(d['drwNo']),
                'nums': [int(d[f'drwtNo{i}']) for i in range(1,7)],
                'bonus': int(d['bnusNo']),
                'date': d.get('drwNoDate','')
            }
        else:
            print(f"  returnValue: {d.get('returnValue')}")
    except Exception as e:
        print(f"  오류: {type(e).__name__}: {e}")
    return None
 
def update_data_json(rounds_data):
    """data.json 업데이트"""
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {'history': [], 'latestRound': 0}
    
    existing = {r['round']: r for r in data.get('history', [])}
    for r in rounds_data:
        existing[r['round']] = r
    
    history = sorted(existing.values(), key=lambda x: x['round'])
    latest = history[-1] if history else None
    
    data = {
        'latestRound': latest['round'] if latest else 0,
        'latestWinNums': latest['nums'] if latest else [],
        'latestBonusNum': latest['bonus'] if latest else 0,
        'history': history[-10:]  # 최근 10회차만 보관
    }
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  data.json 업데이트 완료: {len(history)}개 회차")
    return data
 
def update_index_html(data):
    """index.html의 SEED_HISTORY와 latestRound 업데이트"""
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    history = data['history'][-5:]  # 최근 5개
    latest_round = data['latestRound']
    latest_nums = data['latestWinNums']
    latest_bonus = data['latestBonusNum']
    
    # SEED_HISTORY 업데이트
    lines = []
    for e in history:
        nums_str = ','.join(map(str, e['nums']))
        lines.append(f"  {{round:{e['round']},nums:[{nums_str}],bonus:{e['bonus']}}}")
    new_sh = 'const SEED_HISTORY = [\n' + ',\n'.join(lines) + ',\n];'
    
    content = re.sub(r'const SEED_HISTORY = \[.*?\];', new_sh, content, flags=re.DOTALL)
    content = re.sub(r'let latestRound\s*=\s*\d+', f'let latestRound = {latest_round}', content)
    content = re.sub(r'let latestWinNums\s*=\s*\[[^\]]*\]', f'let latestWinNums = {json.dumps(latest_nums)}', content)
    content = re.sub(r'let latestBonusNum\s*=\s*\d+', f'let latestBonusNum = {latest_bonus}', content)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  index.html 업데이트: latestRound={latest_round}")
 
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
        d = fetch_round(r)
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
    
    print(f"\n{len(new_rounds)}개 새 회차 발견!")
    
    # data.json 업데이트
    print("\ndata.json 업데이트 중...")
    data = update_data_json(new_rounds)
    
    # index.html 업데이트
    print("\nindex.html 업데이트 중...")
    update_index_html(data)
    
    print(f"\n✅ 완료! latestRound: {data['latestRound']}")
    print(f"   당첨번호: {data['latestWinNums']} 보너스: {data['latestBonusNum']}")
 
if __name__ == '__main__':
    main()
 
