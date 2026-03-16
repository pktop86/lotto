#!/usr/bin/env python3
import urllib.request, json, re, sys, time, ssl, gzip
 
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
 
def get_html(url, headers=None):
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req, timeout=20, context=ctx)
    raw = res.read()
    try:
        return gzip.decompress(raw).decode('utf-8', errors='replace')
    except:
        return raw.decode('utf-8', errors='replace')
 
def fetch_round(r):
    print(f"  시도1: gameResult.do HTML 파싱")
    try:
        url = f"https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={r}"
        html = get_html(url)
        print(f"  HTML 길이: {len(html)}")
        
        # 당첨번호 파싱 - 다양한 패턴
        # 패턴1: 공 이미지 alt 속성
        p1 = re.findall(r'<img[^>]+alt="(\d+)"[^>]+class="[^"]*ball', html)
        print(f"  패턴1(img alt ball): {p1}")
        
        # 패턴2: span ball 클래스
        p2 = re.findall(r'<span[^>]+class="[^"]*ball[^"]*"[^>]*>(\d+)</span>', html)
        print(f"  패턴2(span ball): {p2}")
        
        # 패턴3: 번호 직접 텍스트
        p3 = re.findall(r'class="[^"]*num[^"]*"[^>]*>(\d+)<', html)
        print(f"  패턴3(num class): {p3[:10]}")
        
        # 패턴4: 당첨번호 섹션 찾기
        win_section = re.search(r'당첨번호.{0,2000}', html, re.DOTALL)
        if win_section:
            section = win_section.group()
            nums_in_section = re.findall(r'>(\d+)<', section)
            print(f"  패턴4(당첨번호 섹션): {nums_in_section[:10]}")
        
        # 패턴5: JSON 데이터 임베드
        json_embed = re.search(r'var\s+\w+\s*=\s*(\{[^;]+returnValue[^;]+\})', html)
        if json_embed:
            try:
                d = json.loads(json_embed.group(1))
                if d.get('returnValue') == 'success':
                    print(f"  패턴5(JSON 임베드) 성공!")
                    return {
                        'round': r,
                        'nums': [d[f'drwtNo{i}'] for i in range(1,7)],
                        'bonus': d['bnusNo'],
                        'date': d.get('drwNoDate','')
                    }
            except: pass
        
        # 패턴6: 숫자만 추출 (위치 기반)
        drw_pos = html.find(f'{r}회')
        if drw_pos > 0:
            section2 = html[drw_pos:drw_pos+3000]
            nums6 = re.findall(r'\b([1-9]|[1-3][0-9]|4[0-5])\b', section2)
            print(f"  패턴6(회차 근처 숫자): {nums6[:15]}")
        
        # HTML 일부 저장 (디버깅)
        # 당첨번호 관련 부분 찾기
        for keyword in ['당첨번호', 'winNum', 'drwtNo', 'ball_645', 'numBall']:
            pos = html.find(keyword)
            if pos > 0:
                print(f"  키워드 '{keyword}' 위치: {pos}")
                print(f"  주변: {repr(html[max(0,pos-50):pos+200])}")
                break
                
    except Exception as e:
        print(f"  시도1 오류: {type(e).__name__}: {e}")
    
    # 시도2: 네이버 검색으로 최신 번호 확인
    print(f"\n  시도2: 네이버 검색")
    try:
        url2 = f"https://search.naver.com/search.naver?query=로또+{r}회+당첨번호"
        html2 = get_html(url2, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Referer': 'https://www.naver.com/',
        })
        print(f"  네이버 HTML 길이: {len(html2)}")
        
        # 네이버 로또 결과 파싱
        # 당첨번호 파싱
        lotto_nums = re.findall(r'"winning_num[^"]*"[^>]*>(\d+)<', html2)
        print(f"  네이버 당첨번호: {lotto_nums}")
        
        num_section = re.search(r'로또.{0,100}당첨.{0,1000}', html2, re.DOTALL)
        if num_section:
            s = num_section.group()
            nums_found = re.findall(r'\b([1-9]|[1-3][0-9]|4[0-5])\b', s)
            print(f"  네이버 섹션 숫자: {nums_found[:15]}")
            
    except Exception as e:
        print(f"  시도2 오류: {type(e).__name__}: {e}")
    
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
        print(f"\n새 회차 없음 - 로그 확인 필요")
        return
 
    print(f"\n✅ {r}회차 확보: {d['nums']} 보너스:{d['bonus']}")
    
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
    print(f"✅ index.html 업데이트 완료! latestRound: {d['round']}")
 
if __name__ == '__main__':
    main()
