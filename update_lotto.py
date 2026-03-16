#!/usr/bin/env python3
"""매주 토요일 추첨 후 index.html의 SEED_HISTORY와 latestRound를 자동 업데이트"""
import urllib.request, json, re, sys, os

def fetch_round(r):
    url = f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={r}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=10)
        d = json.loads(res.read())
        if d.get('returnValue') == 'success':
            return {
                'round': r,
                'nums': [d[f'drwtNo{i}'] for i in range(1,7)],
                'bonus': d['bnusNo'],
                'date': d['drwNoDate']
            }
    except Exception as e:
        print(f"  fetch {r} error: {e}")
    return None

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 현재 latestRound 파싱
    m = re.search(r'let latestRound\s*=\s*(\d+)', content)
    if not m:
        print("latestRound not found"); sys.exit(1)
    current = int(m.group(1))
    print(f"현재 latestRound: {current}")

    # 새 회차 fetch
    new_rounds = []
    r = current + 1
    while True:
        print(f"  {r}회차 조회 중...")
        d = fetch_round(r)
        if not d:
            break
        new_rounds.append(d)
        print(f"  ✅ {r}회차: {d['nums']} 보너스:{d['bonus']}")
        r += 1

    if not new_rounds:
        print("새 회차 없음")
        return

    latest = new_rounds[-1]
    new_latest_round = latest['round']
    print(f"\n{len(new_rounds)}개 새 회차 발견! 최신: {new_latest_round}회차")

    # SEED_HISTORY 업데이트 (마지막 5개 유지)
    # 기존 SEED_HISTORY 파싱
    sh_match = re.search(r'const SEED_HISTORY = \[(.*?)\];', content, re.DOTALL)
    if not sh_match:
        print("SEED_HISTORY not found"); sys.exit(1)

    # 기존 항목 파싱
    existing = []
    for m2 in re.finditer(r'\{round:(\d+),nums:\[([^\]]+)\],bonus:(\d+)\}', sh_match.group(1)):
        existing.append({
            'round': int(m2.group(1)),
            'nums': list(map(int, m2.group(2).split(','))),
            'bonus': int(m2.group(3))
        })

    # 새 회차 추가
    for d in new_rounds:
        existing.append({'round': d['round'], 'nums': d['nums'], 'bonus': d['bonus']})

    # 최신 5개만 유지
    existing = sorted(existing, key=lambda x: x['round'])[-5:]

    # 새 SEED_HISTORY 문자열
    lines = []
    for e in existing:
        nums_str = ','.join(map(str, e['nums']))
        lines.append(f"  {{round:{e['round']},nums:[{nums_str}],bonus:{e['bonus']}}}")
    new_sh = 'const SEED_HISTORY = [\n' + ',\n'.join(lines) + ',\n];'

    # latestRound 업데이트
    content = re.sub(r'const SEED_HISTORY = \[.*?\];', new_sh, content, flags=re.DOTALL)
    content = re.sub(r'let latestRound\s*=\s*\d+', f'let latestRound = {new_latest_round}', content)

    # latestWinNums, latestBonusNum 업데이트
    content = re.sub(
        r'let latestWinNums = \[[^\]]*\]',
        f'let latestWinNums = {json.dumps(latest["nums"])}',
        content
    )
    content = re.sub(
        r'let latestBonusNum = \d+',
        f'let latestBonusNum = {latest["bonus"]}',
        content
    )

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ index.html 업데이트 완료! latestRound: {new_latest_round}")

if __name__ == '__main__':
    main()
