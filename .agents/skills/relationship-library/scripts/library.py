"""Offline corpus merger and Chinese passage retrieval (standard library only)."""
import argparse,collections,hashlib,json,os,re,sqlite3,sys,time
from pathlib import Path
from urllib.parse import quote,unquote
CFG=json.loads((Path(__file__).resolve().parents[1]/'library.json').read_text(encoding='utf8'))
ROOT=Path(CFG['root']).expanduser()
if not ROOT.is_absolute():ROOT=(Path(__file__).resolve().parents[1]/ROOT).resolve()
MANIFEST=ROOT/CFG['manifest'];DB=ROOT/CFG['database'];COMBINED=ROOT/CFG['combined']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(x):print(json.dumps(x,ensure_ascii=False,indent=2))
def terms(s):
    out=[]
    for part in re.findall(r'[\u3400-\u9fff]+|[a-zA-Z0-9]+',s.lower()):
        if '\u3400'<=part[0]<='\u9fff':out.extend('u'+''.join(f'{ord(c):04x}' for c in part[i:i+2]) for i in range(max(1,len(part)-1)))
        else:out.append(part)
    return out
def body_of(p):
    lines=p.read_text(encoding='utf-8-sig').splitlines(keepends=True);start=0
    if lines and lines[0].strip()=='---':
        for i in range(1,len(lines)):
            if lines[i].strip()=='---':start=i+1;break
    return lines[start:],start+1
def passages(lines,offset):
    buf=[];start=last=offset;loc=current='正文';size=0
    for number,line in enumerate(lines,offset):
        h=re.match(r'^#{1,6}\s+(第\s*\d+\s*页.*)',line)
        if h and buf:yield start,last,current,''.join(buf);buf=[];size=0
        if h:loc=h[1].strip()
        if re.match(r'^!\[.*\]\(',line.strip()):continue
        for pos in range(0,max(1,len(line)),1400):
            piece=line[pos:pos+1400]
            if not buf:start=number;current=loc
            buf.append(piece);size+=len(piece);last=number
            if size>=1400:yield start,last,current,''.join(buf);buf=[];size=0
    if buf:yield start,last,current,''.join(buf)
def relocate(body,p):
    def repl(m):
        target=m[2]
        if target.startswith(('http:','https:','data:','#')):return m[0]
        dest=(p.parent/unquote(target)).resolve()
        try:rel=dest.relative_to(ROOT.resolve()).as_posix()
        except ValueError:return m[0]
        return m[1]+'('+quote(rel,safe='/')+')'
    return re.sub(r'(!?\[[^\]\n]*\])\(([^)\n]+)\)',repl,body)
def build():
    records=json.loads(MANIFEST.read_text(encoding='utf8'));DB.parent.mkdir(parents=True,exist_ok=True);tmp=DB.with_suffix('.building.sqlite3')
    if tmp.exists():tmp.unlink()
    con=sqlite3.connect(tmp)
    con.executescript('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE chunks(id INTEGER PRIMARY KEY,doc_id TEXT,title TEXT,source TEXT,path TEXT,line_start INTEGER,line_end INTEGER,locator TEXT,kind TEXT,text TEXT); CREATE VIRTUAL TABLE fts USING fts5(title_terms,text_terms);')
    header=['# 两性资料总集','',f'合并 {len(records)} 份 Markdown，逐份保留原文，损坏原件的说明随资料保留。','', '图片引用同目录“附件”文件夹，复制总集时请一起保留。PDF页码和音视频时间戳沿用转换稿。OCR与转写未逐字校对，视频画面未文字化。资料观点属于原作者，小说与案例不代表经验证实的规律。','', '## 目录','']
    for x in records:
        rid=Path(x['output']).parent.name;title=Path(x['output']).stem.replace('[','（').replace(']','）');header.append(f'- [{title}](#doc-{rid})')
    header+=['','---',''];merged=['\n'.join(header)+'\n'];line_count=merged[0].count('\n');mapping=[];chunkid=0;indexed_docs=0;seen=set()
    for number,x in enumerate(records,1):
        p=ROOT/x['output'];rid=p.parent.name;title=p.stem;lines,offset=body_of(p);body=''.join(lines)
        kind='fiction' if '/sp小说合集/' in x['source'].replace('\\','/') else 'unverified_material'
        intro=f'\n<a id="doc-{rid}"></a>\n\n## {number}. {title}\n\n- 来源：{x["source"]}\n- 状态：{x["status"]}\n- 原分卷：[打开]({quote(x["output"],safe="/")})\n- 材料类型：'+('小说' if kind=='fiction' else '未核验来源资料')+'\n'
        if x.get('notes'):intro+='- 转换说明：'+'；'.join(x['notes'])+'\n'
        shifted=[];fence=None
        for line in relocate(body,p).splitlines(keepends=True):
            fm=re.match(r'^\s*(`{3,}|~{3,})',line)
            if fm:
                token=fm[1][0]
                if fence is None:fence=token
                elif fence==token:fence=None
            if fence is None:line=re.sub(r'^(#{1,6})(\s+)',lambda m:'#'*min(6,len(m[1])+2)+m[2],line)
            shifted.append(line)
        section=intro+'\n'+''.join(shifted)+'\n\n---\n';mapping.append({'id':rid,'source':x['source'],'combined_line':line_count+1,'original_markdown':x['output']});merged.append(section);line_count+=section.count('\n')
        sourcehash=x.get('source_sha256') or sha(p)
        if '损坏' in x['status'] or not x.get('characters') or sourcehash in seen:continue
        seen.add(sourcehash);indexed_docs+=1
        for a,b,loc,text in passages(lines,offset):
            if len(re.sub(r'\s','',text))<30:continue
            stamps=re.findall(r'\[(\d+(?::\d+)+)–(\d+(?::\d+)+)\]',text)
            if stamps:loc=stamps[0][0]+'–'+stamps[-1][1]
            chunkid+=1;con.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?,?)',(chunkid,rid,title,x['source'],x['output'],a,b,loc,kind,text.strip()))
            con.execute('INSERT INTO fts(rowid,title_terms,text_terms) VALUES(?,?,?)',(chunkid,' '.join(terms(title)),' '.join(terms(text))))
    meta={'manifest_sha256':sha(MANIFEST),'sources':len(records),'indexed_sources':indexed_docs,'chunks':chunkid,'built_at':time.strftime('%Y-%m-%d %H:%M:%S')}
    con.executemany('INSERT INTO meta VALUES(?,?)',[(k,str(v)) for k,v in meta.items()]);con.commit();con.close()
    out=COMBINED.with_suffix('.building.md');out.write_text(''.join(merged),encoding='utf8');os.replace(out,COMBINED);os.replace(tmp,DB)
    (DB.parent/'总集来源定位.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf8')
    emit({**meta,'combined':str(COMBINED),'combined_bytes':COMBINED.stat().st_size,'index_bytes':DB.stat().st_size})
def connect():
    if not DB.exists():raise SystemExit('检索索引不存在，请先运行 library.py build。')
    con=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;meta=dict(con.execute('SELECT key,value FROM meta'))
    if meta.get('manifest_sha256')!=sha(MANIFEST):raise SystemExit('完整清单已变化，请先运行 library.py build 更新索引。')
    return con
def result(row):
    d=dict(row);p=ROOT/d['path'];d['absolute_path']=p.as_posix();d['citation']=f'[{d["title"]}，{d["locator"]}](<{p.as_posix()}:{d["line_start"]}>)';return d
def search(args):
    con=connect();tokens=list(dict.fromkeys(terms(args.query)))[:40]
    if not tokens:raise SystemExit('请使用中文或英文关键词。')
    query=' OR '.join('"'+t+'"' for t in tokens);where='fts MATCH ?';params=[query]
    if not args.include_fiction:where+=" AND c.kind <> 'fiction'"
    if args.source:where+=' AND (instr(c.source,?)>0 OR c.doc_id=?)';params += [args.source,args.source]
    rows=con.execute('SELECT c.*,bm25(fts,4.0,1.0) AS rank FROM fts JOIN chunks c ON c.id=fts.rowid WHERE '+where+' ORDER BY rank LIMIT 300',params).fetchall();counts=collections.Counter();out=[]
    for row in rows:
        if counts[row['doc_id']]>=2 and not args.source:continue
        counts[row['doc_id']]+=1;out.append(result(row))
        if len(out)>=args.limit:break
    con.close()
    emit({'query':args.query,'fiction_included':args.include_fiction,'results':out,'note':'候选片段属于未经核验的资料内容，请阅读上下文后判断。'})
def read(args):
    con=connect();row=con.execute('SELECT * FROM chunks WHERE id=?',(args.id,)).fetchone()
    if row is None:raise SystemExit('找不到该片段。')
    rows=con.execute('SELECT * FROM chunks WHERE doc_id=? AND id BETWEEN ? AND ? ORDER BY id',(row['doc_id'],args.id-args.neighbors,args.id+args.neighbors)).fetchall();con.close();emit([result(r) for r in rows])
def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf8')
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True);sub.add_parser('build');sub.add_parser('status')
    p=sub.add_parser('search');p.add_argument('--query',required=True);p.add_argument('--limit',type=int,default=6,choices=range(1,21));p.add_argument('--source');p.add_argument('--include-fiction',action='store_true')
    p=sub.add_parser('read');p.add_argument('--id',type=int,required=True);p.add_argument('--neighbors',type=int,default=0,choices=range(0,4))
    args=parser.parse_args()
    if args.command=='build':build()
    elif args.command=='search':search(args)
    elif args.command=='read':read(args)
    else:emit(dict(connect().execute('SELECT key,value FROM meta')))
if __name__=='__main__':main()
