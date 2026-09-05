"""Read complete sections of the public handbook without the private corpus."""
import argparse,json,re,sys
from pathlib import Path
BOOK_DIR=Path(__file__).resolve().parents[4]/'book'
BOOKS={'practice':BOOK_DIR/'亲密关系实践手册.md','basic':BOOK_DIR/'从认识到相处.md'}
def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--query');g.add_argument('--chapter');p.add_argument('--book',choices=['all',*BOOKS],default='all');p.add_argument('--limit',type=int,default=3,choices=range(1,6));a=p.parse_args()
    selected=BOOKS if a.book=='all' else {a.book:BOOKS[a.book]};sections=[]
    for book in selected.values():
        text=book.read_text(encoding='utf8');matches=list(re.finditer(r'^## (.+)$',text,re.M))
        for i,m in enumerate(matches):
            end=matches[i+1].start() if i+1<len(matches) else len(text);title=m[1];body=text[m.end():end].strip();score=0
            if a.chapter:score=1 if a.chapter in title else 0
            elif not title.startswith(('开始之前','写在前面','怎样使用','资料与编写','来源')):score=sum(20*title.count(w)+body.count(w) for w in a.query.split())
            if score:sections.append({'book':book.stem,'chapter':title,'line':text.count('\n',0,m.start())+1,'text':body,'score':score,'path':book.as_posix()})
    sections.sort(key=lambda x:x['score'],reverse=True)
    print(json.dumps({'books':[b.as_posix() for b in selected.values()],'results':sections[:a.limit]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
