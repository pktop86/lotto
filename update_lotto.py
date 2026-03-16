#!/usr/bin/env python3
import urllib.request, json, re, sys, ssl, gzip
 
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
 
def get(url, headers=None):
    h = headers or {'User-Agent':'Mozilla/5.0','Accept':'*/*'}
    req = urllib.request.Request(url, headers=h)
    res = urllib.request.urlopen(req, timeout=20, context=ctx)
    raw = res.read()
    try: return gzip.decompress(raw).decode('utf-8','replace')
    except: return raw.decode('utf-8','replace')
 
def fetch_round(r):
    # 방법1: 올바른 gameResult URL
    urls_to_try = [
        f"https://www.dhlottery.co.kr/gameResult.do?method=byWin&wiselog=C_A_1_1&drwNo={r}",
        f"https://www.dhlottery.co.kr/gameResult.do?method=byWin",
    ]
    
    for url in urls_to_try:
        try:
            html = get(url)
            print(f"  URL: {url[:80]}")
            print(f"  길이: {len(html)}")
            
            # drwNo 파라미터가 POST로 전달되어야 할 수도 있음
            # 번호 관련 텍스트 찾기
            for kw in ['당첨번호','win_result','bWin','num1','645ball','lotto645']:
                pos = html.find(kw)
                if pos >= 0:
                    print(f"  '{kw}'@{pos}: {repr(html[pos:pos+200])}")
        except Exception as e:
            print(f"  오류: {e}")
 
    # 방법2: POST 요청으로 특정 회차 조회
    try:
        import urllib.parse
        url2 = "https://www.dhlottery.co.kr/gameResult.do?method=byWin"
        data = urllib.parse.urlencode({'drwNo': str(r), 'method': 'byWin'}).encode()
        req2 = urllib.request.Request(url2, data=data, headers={
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.dhlottery.co.kr/gameResult.do?method=byWin',
        })
        res2 = urllib.request.urlopen(req2, timeout=20, context=ctx)
        raw2 = res2.read()
        try: html2 = gzip.decompress(raw2).decode('utf-8','replace')
        except: html2 = raw2.decode('utf-8','replace')
        print(f"\n  POST 응답 길이: {len(html2)}")
        
        # 당첨번호 파싱 시도
        for kw in ['당첨번호','drwtNo','ball','win']:
            pos = html2.find(kw)
            if pos >= 0:
                print(f"  POST '{kw}'@{pos}: {repr(html2[pos:pos+300])}")
                break
                
        # 숫자 추출
        nums = re.findall(r'class="[^"]*ball[^"]*"[^>]*>\s*(\d+)\s*<', html2)
        print(f"  POST ball nums: {nums}")
        
        if len(nums) >= 7:
            return {'round':r,'nums':[int(n) for n in nums[:6]],'bonus':int(nums[6]),'date':''}
            
    except Exception as e:
        print(f"  POST 오류: {e}")
 
    # 방법3: 동행복권 당첨결과 API (비공식)
    try:
        url3 = f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={r}"
        req3 = urllib.request.Request(url3, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'https://m.dhlottery.co.kr/gameResult.do?method=byWin&wiselog=C_A_1_1&drwNo={r}',
        })
        res3 = urllib.request.urlopen(req3, timeout=20, context=ctx)
        raw3 = res3.read()
        try: text3 = gzip.decompress(raw3).decode('utf-8','replace')
        except: text3 = raw3.decode('utf-8','replace')
        
        print(f"\n  모바일 API 응답({len(text3)}자): {repr(text3[:200])}")
        
        # JSON 찾기
        json_start = text3.find('{')
        if json_start >= 0:
            try:
                d = json.loads(text3[json_start:])
                print(f"  JSON keys: {list(d.keys())[:8]}")
                if d.get('returnValue') == 'success':
                    return {
                        'round': r,
                        'nums': [d[f'drwtNo{i}'] for i in range(1,7)],
                        'bonus': d['bnusNo'],
                        'date': d.get('drwNoDate','')
                    }
            except Exception as je:
                print(f"  JSON 파싱 오류: {je}")
                # JSON이 여러 개일 수 있음, 마지막 중괄호 찾기
                try:
                    json_end = text3.rfind('}')
                    d2 = json.loads(text3[json_start:json_end+1])
                    if d2.get('returnValue') == 'success':
                        return {
                            'round': r,
                            'nums': [d2[f'drwtNo{i}'] for i in range(1,7)],
                            'bonus': d2['bnusNo'],
                            'date': d2.get('drwNoDate','')
                        }
                except: pass
    except Exception as e:
        print(f"  모바일 API 오류: {e}")
 
    # 방법4: 공공데이터포털 API (인증키 불필요 미리보기)  
    try:
        url4 = f"https://apis.data.go.kr/B551015/API645/allWinNum?serviceKey=test&pageNo=1&numOfRows=1&drwNo={r}&type=json"
        html4 = get(url4)
        print(f"\n  공공데이터 응답: {repr(html4[:200])}")
    except Exception as e:
        print(f"  공공데이터 오류: {e}")
 
    return None
 
def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'let latestRound\s*=\s*(\d+)', content)
    current = int(m.group(1))
    print(f"현재 latestRound: {current}")
    r = current + 1
    print(f"\n{'='*40}\n{r}회차 조회 중...")
    d = fetch_round(r)
    if not d:
        print(f"\n실패 - 위 로그 확인 필요")
        return
    # 업데이트
    sh_match = re.search(r'const SEED_HISTORY = \[(.*?)\];', content, re.DOTALL)
    existing = []
    for m2 in re.finditer(r'\{round:(\d+),nums:\[([^\]]+)\],bonus:(\d+)\}', sh_match.group(1)):
        existing.append({'round':int(m2.group(1)),'nums':list(map(int,m2.group(2).split(','))),'bonus':int(m2.group(3))})
    existing.append({'round':d['round'],'nums':d['nums'],'bonus':d['bonus']})
    existing = sorted(existing, key=lambda x: x['round'])[-5:]
    lines = [f"  {{round:{e['round']},nums:[{','.join(map(str,e['nums']))}],bonus:{e['bonus']}}}" for e in existing]
    new_sh = 'const SEED_HISTORY = [\n' + ',\n'.join(lines) + ',\n];'
    content = re.sub(r'const SEED_HISTORY = \[.*?\];', new_sh, content, flags=re.DOTALL)
    content = re.sub(r'let latestRound\s*=\s*\d+', f'let latestRound = {d["round"]}', content)
    content = re.sub(r'let latestWinNums\s*=\s*\[[^\]]*\]', f'let latestWinNums = {json.dumps(d["nums"])}', content)
    content = re.sub(r'let latestBonusNum\s*=\s*\d+', f'let latestBonusNum = {d["bonus"]}', content)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ 완료! latestRound:{d['round']} nums:{d['nums']} bonus:{d['bonus']}")
 
if __name__ == '__main__':
    main()
