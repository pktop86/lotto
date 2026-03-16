#!/usr/bin/env python3
import requests, json, re, sys, time
from bs4 import BeautifulSoup
 
def fetch_lotto_naver(drwNo):
    url = f"https://search.naver.com/search.naver?query={drwNo}회+로또"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        print(f"  네이버 응답: {res.status_code}, {len(res.text)}자")
        soup = BeautifulSoup(res.text, 'html.parser')
 
        # 네이버 로또 볼 추출
        balls = soup.select('.ball_645')
        print(f"  .ball_645 개수: {len(balls)}")
 
        if len(balls) >= 7:
            nums = [int(b.text.strip()) for b in balls[:6]]
            bonus = int(balls[6].text.strip())
            print(f"  ✅ 성공: {nums} 보너스:{bonus}")
            return {'round': drwNo, 'nums': nums, 'bonus': bonus, 'date': ''}
 
        # 클래스명이 다를 수 있으므로 다른 패턴도 시도
        balls2 = soup.select('[class*="ball"]')
        print(f"  ball 포함 클래스 개수: {len(balls2)}")
        if balls2:
            for b in balls2[:10]:
                print(f"    클래스:{b.get('class')} 텍스트:{b.text.strip()}")
 
        # 숫자 직접 파싱
        lotto_section = soup.find('div', class_=re.compile('lotto|lottery|winning', re.I))
        if lotto_section:
            print(f"  로또섹션: {lotto_section.get('class')}")
            nums_text = re.findall(r'\b([1-9]|[1-3][0-9]|4[0-5])\b', lotto_section.text)
            print(f"  섹션 숫자: {nums_text[:10]}")
 
        print(f"  [경고] 번호 파싱 실패")
        return None
 
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
        d = fetch_lotto_naver(r)
        if not d:
            print(f"  {r}회차 없음 - 종료")
            break
        new_rounds.append(d)
        print(f"  ✅ {r}회차 확보!")
        r += 1
        time.sleep(1)
 
    if not new_rounds:
        print("\n새 회차 없음")
        return
 
    latest = new_rounds[-1]
 
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
    print(f"\n✅ 완료! latestRound: {latest['round']}, nums: {latest['nums']}")
 
if __name__ == '__main__':
    main()
