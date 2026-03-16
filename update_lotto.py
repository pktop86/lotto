#!/usr/bin/env python3
"""매주 토요일 추첨 후 index.html의 SEED_HISTORY와 latestRound를 자동 업데이트"""
import urllib.request, urllib.parse, json, re, sys, time
 
def fetch_round(r):
    """여러 방법으로 로또 회차 데이터 가져오기"""
    
    # 방법1: 동행복권 직접 (인코딩 처리)
    urls = [
        f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={r}",
    ]
    
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/javascript, */*',
                'Accept-Language': 'ko-KR,ko;q=0.9',
                'Referer': 'https://www.dhlottery.co.kr/'
            })
            res = urllib.request.urlopen(req, timeout=15)
            raw = res.read()
            print(f"  raw response ({len(raw)} bytes): {raw[:100]}")
            
            # BOM 및 공백 제거
            text = raw.decode('utf-8-sig').strip()
            if not text:
                continue
                
            d = json.loads(text)
            if d.get('returnValue') == 'success':
                return {
                    'round': r,
                    'nums': [d[f'drwtNo{i}'] for i in range(1,7)],
                    'bonus': d['bnusNo'],
                    'date': d['drwNoDate']
                }
            else:
                print(f"  returnValue: {d.get('returnValue')}")
        except Exception as e:
            print(f"  방법1 오류: {e}")
    
    # 방법2: 동행복권 모바일 API
    try:
        url2 = f"https://m.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={r}"
        req2 = urllib.request.Request(url2, headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
            'Accept': '*/*',
        })
        res2 = urllib.request.urlopen(req2, timeout=15)
        html = res2.read().decode('utf-8', errors='ignore')
        
        # HTML에서 당첨번호 파싱
        nums_match = re.findall(r'<span class="ball_645 lball_(\d+)"[^>]*>(\d+)</span>', html)
        bonus_match = re.search(r'<span class="ball_645 lball_(\d+)"[^>]*>\s*(\d+)\s*</span>\s*</div>\s*</div>', html)
        
        if len(nums_match) >= 6:
            nums = [int(m[1]) for m in nums_match[:6]]
            bonus = int(nums_match[6][1]) if len(nums_match) > 6 else 0
            date_match = re.search(r'(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)', html)
            date_str = date_match.group(1) if date_match else ''
            print(f"  방법2 성공: {nums} 보너스:{bonus}")
            return {'round': r, 'nums': nums, 'bonus': bonus, 'date': date_str}
    except Exception as e:
        print(f"  방법2 오류: {e}")
    
    # 방법3: 공공데이터 스크래핑
    try:
        url3 = f"https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={r}&gameGubn=lotto"
        req3 = urllib.request.Request(url3, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        res3 = urllib.request.urlopen(req3, timeout=15)
        html3 = res3.read().decode('utf-8', errors='ignore')
        
        # 번호 파싱
        win_nums = re.findall(r'<span[^>]+class="[^"]*ball_645[^"]*"[^>]*>(\d+)</span>', html3)
        if len(win_nums) >= 7:
            nums = [int(n) for n in win_nums[:6]]
            bonus = int(win_nums[6])
            date_m = re.search(r'(\d{4}-\d{2}-\d{2})', html3)
            date_str = date_m.group(1) if date_m else ''
            print(f"  방법3 성공: {nums} 보너스:{bonus}")
            return {'round': r, 'nums': nums, 'bonus': bonus, 'date': date_str}
    except Exception as e:
        print(f"  방법3 오류: {e}")
    
    return None
 
def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
 
    m = re.search(r'let latestRound\s*=\s*(\d+)', content)
    if not m:
        print("latestRound not found"); sys.exit(1)
    current = int(m.group(1))
    print(f"현재 latestRound: {current}")
 
    new_rounds = []
    r = current + 1
    while True:
        print(f"\n  {r}회차 조회 중...")
        d = fetch_round(r)
        if not d:
            print(f"  {r}회차 데이터 없음 - 중단")
            break
        new_rounds.append(d)
        print(f"  ✅ {r}회차: {d['nums']} 보너스:{d['bonus']}")
        r += 1
        time.sleep(1)
 
    if not new_rounds:
        print("\n새 회차 없음 - index.html 변경 안 함")
        return
 
    latest = new_rounds[-1]
    new_latest_round = latest['round']
    print(f"\n{len(new_rounds)}개 새 회차 발견! 최신: {new_latest_round}회차")
 
    # SEED_HISTORY 파싱
    sh_match = re.search(r'const SEED_HISTORY = \[(.*?)\];', content, re.DOTALL)
    if not sh_match:
        print("SEED_HISTORY not found"); sys.exit(1)
 
    existing = []
    for m2 in re.finditer(r'\{round:(\d+),nums:\[([^\]]+)\],bonus:(\d+)\}', sh_match.group(1)):
        existing.append({
            'round': int(m2.group(1)),
            'nums': list(map(int, m2.group(2).split(','))),
            'bonus': int(m2.group(3))
        })
 
    for d in new_rounds:
        existing.append({'round': d['round'], 'nums': d['nums'], 'bonus': d['bonus']})
 
    existing = sorted(existing, key=lambda x: x['round'])[-5:]
 
    lines = []
    for e in existing:
        nums_str = ','.join(map(str, e['nums']))
        lines.append(f"  {{round:{e['round']},nums:[{nums_str}],bonus:{e['bonus']}}}")
    new_sh = 'const SEED_HISTORY = [\n' + ',\n'.join(lines) + ',\n];'
 
    content = re.sub(r'const SEED_HISTORY = \[.*?\];', new_sh, content, flags=re.DOTALL)
    content = re.sub(r'let latestRound\s*=\s*\d+', f'let latestRound = {new_latest_round}', content)
    content = re.sub(r'let latestWinNums\s*=\s*\[[^\]]*\]', f'let latestWinNums = {json.dumps(latest["nums"])}', content)
    content = re.sub(r'let latestBonusNum\s*=\s*\d+', f'let latestBonusNum = {latest["bonus"]}', content)
 
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ index.html 업데이트 완료! latestRound: {new_latest_round}")
 
if __name__ == '__main__':
    main()
