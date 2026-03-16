#!/usr/bin/env python3
import urllib.request, urllib.parse, json, re, sys, time, ssl, gzip
 
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
 
def get_html(url, headers=None):
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,*/*',
            'Accept-Language': 'ko-KR,ko;q=0.9',
        }
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req, timeout=20, context=ctx)
    raw = res.read()
    try:
        return gzip.decompress(raw).decode('utf-8', errors='replace')
    except:
        return raw.decode('utf-8', errors='replace')
 
def fetch_round(r):
    # gameResult.do 파싱
    try:
        url = f"https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={r}"
        html = get_html(url)
        print(f"  HTML 길이: {len(html)}")
        
        # 번호 관련 키워드 위치 찾기
        for kw in ['ball_645', 'win_num', 'drwtNo', 'bNum', 'num645', 'winning', 'lball', 'nBall']:
            pos = html.find(kw)
            if pos >= 0:
                snippet = html[max(0,pos-30):pos+200]
                print(f"  [{kw}@{pos}]: {repr(snippet)}")
        
        # 1215회 텍스트 찾기
        pos2 = html.find(str(r))
        if pos2 >= 0:
            print(f"  [{r} 위치@{pos2}]: {repr(html[max(0,pos2-20):pos2+300])}")
            
        # 모든 숫자 패턴
        all_nums = re.findall(r'\b(4[0-5]|[1-3][0-9]|[1-9])\b', html[html.find('당첨'):html.find('당첨')+2000] if '당첨' in html else html[:3000])
        print(f"  당첨 근처 숫자들: {all_nums[:20]}")
        
        # HTML 중간 부분 출력 (번호가 있을 만한 곳)
        mid = len(html) // 3
        print(f"  HTML[{mid}:{mid+500}]: {repr(html[mid:mid+500])}")
        
    except Exception as e:
        print(f"  gameResult 오류: {e}")
 
    # 방법2: 로또 결과 RSS/XML
    try:
        url2 = f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={r}"
        req2 = urllib.request.Request(url2, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        })
        res2 = urllib.request.urlopen(req2, timeout=20, context=ctx)
        raw2 = res2.read()
        try:
            text2 = gzip.decompress(raw2).decode('utf-8', errors='replace')
        except:
            text2 = raw2.decode('utf-8', errors='replace')
        print(f"\n  JSON API 응답({len(text2)}자): {repr(text2[:300])}")
        
        if '{' in text2:
            d = json.loads(text2[text2.find('{'):text2.rfind('}')+1])
            if d.get('returnValue') == 'success':
                return {
                    'round': r,
                    'nums': [d[f'drwtNo{i}'] for i in range(1,7)],
                    'bonus': d['bnusNo'],
                    'date': d.get('drwNoDate','')
                }
    except Exception as e:
        print(f"  JSON API 오류: {e}")
 
    # 방법3: 나눔로또 이전 도메인
    try:
        url3 = f"https://ol.dhlottery.co.kr/olotto/result/resultSingle.do"
        data = urllib.parse.urlencode({'method':'getSingle','drwNo':str(r)}).encode()
        req3 = urllib.request.Request(url3, data=data, headers={
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        res3 = urllib.request.urlopen(req3, timeout=20, context=ctx)
        text3 = res3.read().decode('utf-8', errors='replace')
        print(f"\n  ol.dhlottery 응답: {repr(text3[:300])}")
    except Exception as e:
        print(f"  ol.dhlottery 오류: {e}")
        
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
        print(f"\n새 회차 데이터 획득 실패 - 위 로그 확인")
        return
 
    # index.html 업데이트
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
    print(f"\n✅ 완료! latestRound: {d['round']}, nums: {d['nums']}")
 
if __name__ == '__main__':
    main()
