#!/usr/bin/env python3
import urllib.request, json, re, sys, time, ssl
 
# SSL 검증 무시 (GitHub Actions 환경)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
 
def fetch_round(r):
    # 동행복권 JSON API - 다양한 헤더로 시도
    url = f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={r}"
    
    headers_list = [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.dhlottery.co.kr/gameResult.do?method=byWin',
            'Origin': 'https://www.dhlottery.co.kr',
            'Connection': 'keep-alive',
        },
        {
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11)',
            'Accept': '*/*',
        }
    ]
    
    for i, headers in enumerate(headers_list):
        try:
            req = urllib.request.Request(url, headers=headers)
            res = urllib.request.urlopen(req, timeout=20, context=ctx)
            
            # gzip 디코딩 처리
            import io
            raw_bytes = res.read()
            
            # gzip 여부 확인
            try:
                import gzip
                raw = gzip.decompress(raw_bytes)
            except:
                raw = raw_bytes
            
            text = raw.decode('utf-8', errors='replace').strip()
            print(f"  헤더{i+1} 응답 ({len(text)}자): {repr(text[:150])}")
            
            if not text or text[0] not in ['{', '[']:
                print(f"  JSON 아님, 건너뜀")
                continue
                
            d = json.loads(text)
            if d.get('returnValue') == 'success':
                return {
                    'round': r,
                    'nums': [d[f'drwtNo{i}'] for i in range(1,7)],
                    'bonus': d['bnusNo'],
                    'date': d['drwNoDate']
                }
            print(f"  returnValue: {d.get('returnValue')}, 전체: {list(d.keys())[:5]}")
        except Exception as e:
            print(f"  헤더{i+1} 오류: {type(e).__name__}: {e}")
        time.sleep(0.5)
    
    # HTML 파싱 방법
    try:
        url2 = f"https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={r}"
        req2 = urllib.request.Request(url2, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        })
        res2 = urllib.request.urlopen(req2, timeout=20, context=ctx)
        raw2 = res2.read()
        try:
            import gzip
            html = gzip.decompress(raw2).decode('utf-8', errors='replace')
        except:
            html = raw2.decode('utf-8', errors='replace')
        
        print(f"  HTML 응답 ({len(html)}자)")
        
        # 번호 파싱 - 여러 패턴 시도
        patterns = [
            r'class="ball_645[^"]*"[^>]*>\s*(\d+)\s*<',
            r'<span[^>]+ball[^>]+>\s*(\d+)\s*</span>',
            r'"drwtNo\d+":(\d+)',
        ]
        
        for pat in patterns:
            nums_found = re.findall(pat, html)
            if len(nums_found) >= 7:
                nums = [int(n) for n in nums_found[:6]]
                bonus = int(nums_found[6])
                date_m = re.search(r'(\d{4}-\d{2}-\d{2})', html)
                date_str = date_m.group(1) if date_m else ''
                print(f"  HTML 파싱 성공(패턴): {nums} 보너스:{bonus}")
                return {'round': r, 'nums': nums, 'bonus': bonus, 'date': date_str}
        
        # JSON 데이터 추출 시도
        json_match = re.search(r'drwNo["\s:]+(\d+)[^}]+drwtNo1["\s:]+(\d+)[^}]+drwtNo2["\s:]+(\d+)[^}]+drwtNo3["\s:]+(\d+)[^}]+drwtNo4["\s:]+(\d+)[^}]+drwtNo5["\s:]+(\d+)[^}]+drwtNo6["\s:]+(\d+)[^}]+bnusNo["\s:]+(\d+)', html)
        if json_match:
            g = json_match.groups()
            nums = [int(g[i]) for i in range(1,7)]
            bonus = int(g[7])
            print(f"  HTML JSON 추출 성공: {nums} 보너스:{bonus}")
            return {'round': r, 'nums': nums, 'bonus': bonus, 'date': ''}
            
        print(f"  HTML에서 번호 파싱 실패")
        print(f"  HTML 샘플: {html[1000:1500]}")
        
    except Exception as e:
        print(f"  HTML 방법 오류: {type(e).__name__}: {e}")
    
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
        print(f"\n{'='*40}\n{r}회차 조회 중...")
        d = fetch_round(r)
        if not d:
            print(f"{r}회차 데이터 없음 - 종료")
            break
        new_rounds.append(d)
        print(f"✅ {r}회차 확보: {d['nums']} 보너스:{d['bonus']}")
        r += 1
        time.sleep(1)
 
    if not new_rounds:
        print("\n새 회차 없음")
        return
 
    latest = new_rounds[-1]
    new_latest_round = latest['round']
    print(f"\n{len(new_rounds)}개 새 회차! 최신: {new_latest_round}회")
 
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
    content = re.sub(r'let latestRound\s*=\s*\d+', f'let latestRound = {new_latest_round}', content)
    content = re.sub(r'let latestWinNums\s*=\s*\[[^\]]*\]', f'let latestWinNums = {json.dumps(latest["nums"])}', content)
    content = re.sub(r'let latestBonusNum\s*=\s*\d+', f'let latestBonusNum = {latest["bonus"]}', content)
 
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ 완료! latestRound: {new_latest_round}")
 
if __name__ == '__main__':
    main()
