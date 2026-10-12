from pathlib import Path
import re, html, textwrap, json, sys
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted, KeepTogether, Flowable
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
OUT=ROOT/'NeuroFusion_Full_Project_Guide.pdf'
for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf'),('Arial-Italic','ariali.ttf')]:
    pdfmetrics.registerFont(TTFont(name, 'C:/Windows/Fonts/'+file))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial-Italic',boldItalic='Arial-Bold')
pdfmetrics.registerFont(TTFont('Consolas', 'C:/Windows/Fonts/consola.ttf'))
navy=colors.HexColor('#142D48'); teal=colors.HexColor('#087E8B'); grey=colors.HexColor('#506074'); light=colors.HexColor('#EAF2F6')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body',fontName='Arial',fontSize=9.4,leading=14,spaceAfter=7,textColor=navy,allowWidows=0,allowOrphans=0))
styles.add(ParagraphStyle(name='Chapter',fontName='Arial-Bold',fontSize=21,leading=26,spaceAfter=16,textColor=navy,keepWithNext=True))
styles.add(ParagraphStyle(name='Sub',fontName='Arial-Bold',fontSize=12,leading=16,spaceBefore=12,spaceAfter=7,textColor=teal,keepWithNext=True))
styles.add(ParagraphStyle(name='BulletNF',parent=styles['Body'],leftIndent=12,firstLineIndent=-9,spaceAfter=5))
styles.add(ParagraphStyle(name='Cell',fontName='Arial',fontSize=8.1,leading=11,textColor=navy,splitLongWords=True))
styles.add(ParagraphStyle(name='CellHead',parent=styles['Cell'],fontName='Arial-Bold',textColor=colors.white))
styles.add(ParagraphStyle(name='CodeNF',fontName='Consolas',fontSize=8.2,leading=10.5,backColor=light,borderPadding=8,spaceBefore=5,spaceAfter=10))
styles.add(ParagraphStyle(name='SmallNF',parent=styles['Body'],fontSize=8,leading=11,textColor=grey))
styles.add(ParagraphStyle(name='CoverTitle',fontName='Arial-Bold',fontSize=42,leading=48,textColor=navy,spaceAfter=20))
styles.add(ParagraphStyle(name='CoverSub',fontName='Arial',fontSize=20,leading=27,textColor=teal,spaceAfter=18))

def inline(s):
    s=html.escape(s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',r'<link href="\2" color="#087E8B">\1</link>',s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',s)
    # Link bare URLs; reference paragraphs contain no other generated links.
    if '<link ' not in s:
        s=re.sub(r'https?://[^\s<>]+',lambda m:'<link href="'+m.group(0)+'" color="#087E8B">'+m.group(0)+'</link>',s)
    return s

class GuideDoc(SimpleDocTemplate):
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and f.style.name=='Chapter':
            title=f.getPlainText(); key='chapter-'+str(self.seq.nextf('chapter'))
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title,key,0,False)
            self.notify('TOCEntry',(0,title,self.page,key))

def furniture(c,d):
    if d.page==1:return
    c.saveState(); w,h=A4
    c.setFont('Arial',8); c.setFillColor(grey)
    c.drawString(44,h-27,'NEUROFUSION  /  FULL PROJECT GUIDE')
    c.drawRightString(w-44,h-27,'Research architecture and build roadmap')
    c.setStrokeColor(colors.HexColor('#D7E1E8')); c.line(44,36,w-44,36)
    c.setFont('Arial',7.5); c.drawString(44,23,'Version 2.0  |  5 October 2026  |  Planned system, not clinically validated')
    c.drawRightString(w-44,23,str(d.page)); c.restoreState()

class Pipeline(Flowable):
    def __init__(self):
        Flowable.__init__(self); self.width=505; self.height=330
    def draw(self):
        c=self.canv
        rows=[('INPUT','MRI / CT / angiography / EEG'),('VALIDATE','Quality, sequence and geometry checks'),('ROUTE','Run only compatible specialist models'),('ANALYZE','Segmentation, detection and task-specific fusion'),('REVIEW','Evidence links, overlays and human corrections'),('REPORT','Structured findings and cited explanations')]
        for i,(label,desc) in enumerate(rows):
            y=285-i*52
            c.setFillColor(light); c.roundRect(0,y,505,42,5,fill=1,stroke=0)
            c.setFillColor(teal); c.setFont('Arial-Bold',9); c.drawString(12,y+25,label)
            c.setFillColor(navy); c.setFont('Arial',9); c.drawString(12,y+10,desc)
            if i<5:
                c.setStrokeColor(teal); c.line(252,y,252,y-10)

base=(ROOT/'NeuroFusion_Project_Manual.md').read_text(encoding='utf-8')
extra=(ROOT/'docs/implementation_supplement.md').read_text(encoding='utf-8')
source=base.replace('Version 1.1 | 5 October 2026','Version 2.0 | 5 October 2026')+'\n\n'+extra
source=source.replace('Version 1.1 adds','The approved expansion adds')
source=source.replace('Good fusion reward but little clinical-task gain','Better fusion loss but little task-metric gain')
# Printable ASCII punctuation and tree guides, preserving all content.
for old,new in [('—',' - '),('–','-'),('→','->'),('’',"'"),('“','"'),('”','"'),('├','+'),('└','+'),('│','|'),('─','-')]: source=source.replace(old,new)
(ROOT/'docs/NeuroFusion_Full_Project_Guide.md').write_text(source,encoding='utf-8')

story=[]
story += [Spacer(1,65),Paragraph('NEUROFUSION',styles['CoverTitle']),Paragraph('Full project guide<br/>and implementation roadmap',styles['CoverSub'])]
story += [Paragraph('A web-based research platform for multimodal brain imaging and EEG analysis',styles['Body']),Spacer(1,20)]
cover=[['PROJECT ROOT','D:\\NeuroFusion'],['PLATFORM','Windows 11 development; browser interface'],['LOCAL GPU','RTX 4070 Laptop GPU / approximately 8 GB VRAM'],['SYSTEM','Intel i7-13700HX / 16 GB RAM class'],['EDITION','Version 2.0 / 5 October 2026']]
t=Table([[Paragraph(a,styles['Cell']),Paragraph(html.escape(b),styles['Cell'])] for a,b in cover],colWidths=[116,389])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),light),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)])); story+=[t,Spacer(1,28)]
story += [Paragraph('From one validated specialist to a broader research platform',styles['Sub']),Paragraph('Datasets and provenance. Specialist models. Fusion experiments. Local GPU training. Web architecture. Human review. Active learning. Robustness testing. Federated-learning simulation.',styles['Body']),Spacer(1,22),Paragraph('Implementation guide, not an implemented product or medical diagnosis system. Capabilities require task-specific validation and qualified review.',styles['SmallNF']),PageBreak()]
story += [Paragraph('Contents',styles['Chapter'])]
toc=TableOfContents(); toc.levelStyles=[ParagraphStyle(name='TOC0',fontName='Arial',fontSize=9,leading=14,leftIndent=0,firstLineIndent=0,spaceBefore=4,textColor=navy)]
story += [toc,PageBreak(),Paragraph('Reading route and delivery status',styles['Chapter'])]
story += [Paragraph('Start with Sections 1-5 for the scope, Sections 8-18 for architecture and evaluation, Section 26 for the approved priority features, and Sections 27-35 for the laptop-specific build plan.',styles['Body']),Paragraph('This document consolidates the prior manual and expands it into 38 numbered sections. The primary sources are in Sections 25 and 38. Proposed code paths and API routes are specifications; no training scripts or models are delivered by this documentation task.',styles['Body']),Paragraph('The first recommended milestone is an ISLES MRI stroke-segmentation baseline and a controlled fusion comparison. Then connect it to a browser viewer and evidence-linked reports. Add further specialists only after their datasets and evaluation gates are ready.',styles['Body']),Pipeline(),PageBreak()]
lines=source.splitlines(); i=0
while i<len(lines):
    line=lines[i].strip()
    if not line: i+=1; continue
    if line.startswith('# '): i+=1; continue
    if line.startswith('Version 2.0') or line.startswith('Status: proposed research'): i+=1; continue
    if line.startswith('## '):
        section_number=int(re.match(r'## (\d+)',line).group(1))
        if section_number in [1,4,8,16,21,25,26,27,28,29,30,31,32,34,38]:
            if not isinstance(story[-1],PageBreak):story.append(PageBreak())
        else: story.append(Spacer(1,18))
        story.append(Paragraph(inline(line[3:]),styles['Chapter']));i+=1;continue
    if line.startswith('### '):story.append(Paragraph(inline(line[4:]),styles['Sub']));i+=1;continue
    if line.startswith('```'):
        lang=line[3:]; block=[];i+=1
        while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
        i+=1
        if lang=='mermaid':story += [Pipeline()];continue
        wrapped=[]
        for b in block:
            wrapped.extend(textwrap.wrap(b,width=104,subsequent_indent='    ',replace_whitespace=False,drop_whitespace=False) or [''])
        # Allow splitting large code blocks across pages.
        code=Preformatted('\n'.join(wrapped),styles['CodeNF'])
        story.append(KeepTogether([code]) if len(wrapped)<=24 else code);continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r'[:\- ]+',c) for c in cells):rows.append(cells)
            i+=1
        n=len(rows[0]);weights={2:[.28,.72],3:[.24,.36,.40],4:[.20,.28,.28,.24],5:[.18,.23,.20,.24,.15]}.get(n,[1/n]*n)
        if rows[0][0]=='Proposed file': weights=[.42,.29,.29]
        data=[[Paragraph(inline(c),styles['CellHead'] if rid==0 else styles['Cell']) for c in row] for rid,row in enumerate(rows)]
        t=Table(data,colWidths=[505*x for x in weights],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,light]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.5,teal)]))
        story += [t,Spacer(1,10)];continue
    if line.startswith('- '):story.append(Paragraph('&#8226; '+inline(line[2:]),styles['BulletNF']));i+=1;continue
    if re.match(r'^\d+\. ',line):story.append(Paragraph(inline(line),styles['Body']));i+=1;continue
    para=[line];i+=1
    while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|- |\d+\. )',lines[i].strip()):para.append(lines[i].strip());i+=1
    story.append(Paragraph(inline(' '.join(para)),styles['Body']))

doc=GuideDoc(str(OUT),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=50,bottomMargin=50,title='NeuroFusion Full Project Guide',author='NeuroFusion project documentation',subject='Architecture, datasets, models, GPU training and implementation roadmap')
doc.multiBuild(story,onFirstPage=furniture,onLaterPages=furniture)
from pypdf import PdfReader
reader=PdfReader(OUT)
print(json.dumps({'pdf':str(OUT),'pages':len(reader.pages),'words':len(source.split()),'bytes':OUT.stat().st_size}))
