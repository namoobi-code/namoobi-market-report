# GOODREPORT 비교 게이트 (v3.6.33)
# 최종 docx 를 연결폴더 GOODREPORT 기준본과 구조 비교한다(섹션/차트/표 누락 검출).
# 사용: python3 gen_goodreport_compare.py <new.docx> [goodreport.docx]
#   goodreport.docx 미지정 시 D:\claudeCowork\GOODREPORT (VM: /sessions/*/mnt/claudeCowork/GOODREPORT) 의 최신 docx 자동 탐색.
# 출력: 이미지/표/용량/섹션헤딩 비교 + 이상부 경고. 이상부가 있으면 사용자에게 보고(조용히 넘기지 말 것).
import sys, zipfile, re, os, glob

def find_good():
    for d in glob.glob('/sessions/*/mnt/claudeCowork/GOODREPORT') + ['/sessions/*/mnt/claudeCowork/GOODREPORT']:
        c = sorted(glob.glob(os.path.join(d, '*.docx')))
        if c: return c[-1]
    return None

def info(p):
    z = zipfile.ZipFile(p)
    media = [n for n in z.namelist() if n.startswith('word/media/')]
    doc = z.read('word/document.xml').decode('utf-8', 'ignore')
    tbl = doc.count('<w:tbl>')
    heads = sorted(set(re.findall(r'[1-9]\d?\.[0-9]\.[0-9][^<]{0,40}', doc)))
    return {'bytes': os.path.getsize(p), 'images': len(media), 'tables': tbl, 'heads': heads}

def main():
    new_p = sys.argv[1]
    good_p = sys.argv[2] if len(sys.argv) > 2 else find_good()
    if not good_p or not os.path.exists(good_p):
        print('⚠️ GOODREPORT 기준본을 찾지 못함 — 비교 생략'); return
    n, g = info(new_p), info(good_p)
    print('항목         NEW        GOOD')
    print('bytes   {:>10} {:>10}'.format(n['bytes'], g['bytes']))
    print('images  {:>10} {:>10}'.format(n['images'], g['images']))
    print('tables  {:>10} {:>10}'.format(n['tables'], g['tables']))
    miss = [h for h in g['heads'] if h not in n['heads']]
    if miss: print('⚠️ NEW 에 없는 GOODREPORT 섹션:', miss)
    warn = []
    if n['images'] < g['images'] * 0.9: warn.append('이미지 {} < 기준 {} (차트 누락 의심)'.format(n['images'], g['images']))
    if n['bytes'] < g['bytes'] * 0.85: warn.append('용량 {} < 기준 {} (내용/차트 부족 의심)'.format(n['bytes'], g['bytes']))
    if n['tables'] < g['tables'] - 3: warn.append('표 {} < 기준 {} (표 누락 의심)'.format(n['tables'], g['tables']))
    if warn or miss:
        print('⚠️ GOODREPORT 대비 이상부 — 사용자 확인 필요:')
        for w in warn: print('  -', w)
        sys.exit(2)
    print('✅ GOODREPORT 대비 구조 정상 (이미지·용량·표·섹션)')

if __name__ == '__main__':
    main()
