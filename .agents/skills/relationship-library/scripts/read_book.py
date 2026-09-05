"""Read complete sections of the public handbook without the private corpus."""
import argparse,json,re,sys
from pathlib import Path
BOOK=Path(__file__).resolve().parents[4]/'book'/'从认识到相处.md'
def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--query');g.add_argument('--chapter');p.add_argument('--limit',type=int,default=3,choices=range(1,6));a=p.parse_args()
    text=BOOK.read_text(encoding='utf8');sections=[];matches=list(re.finditer(r'^## (.+)$',text,re.M))
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(text);title=m[1];body=text[m.end():end].strip();score=0
        if a.chapter:score=1 if a.chapter in title else 0
        else:score=sum(5*title.count(w)+body.count(w) for w in a.query.split())
        if score:sections.append({'chapter':title,'line':text.count('\n',0,m.start())+1,'text':body,'score':score,'path':BOOK.as_posix()})
    sections.sort(key=lambda x:x['score'],reverse=True)
    print(json.dumps({'book':BOOK.as_posix(),'results':sections[:a.limit]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
