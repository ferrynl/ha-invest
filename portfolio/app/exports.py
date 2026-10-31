"""Read-only transaction exports with explicit currency and account columns."""
import csv
import io
from html import escape
from transactions import ledger

COLUMNS=('day','account_name','broker','type','symbol','exchange','currency','quantity','price','amount')

def export(store,account,format):
    rows=ledger(store,account)['transactions']
    if format=='csv':
        out=io.StringIO(newline='');writer=csv.writer(out);writer.writerow(COLUMNS)
        for row in rows:
            values=[str(row.get(key,'')) for key in COLUMNS]
            writer.writerow(["'"+v if v.lstrip().startswith(('=','+','-','@')) else v for v in values])
        return out.getvalue().encode('utf-8-sig'),'text/csv; charset=utf-8'
    if format!='pdf':raise ValueError('Ongeldig exportformaat.')
    from reportlab.platypus import SimpleDocTemplate,Paragraph,LongTable,TableStyle,Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4,landscape
    out=io.BytesIO();styles=getSampleStyleSheet();style=styles['BodyText'];style.fontSize=7;style.leading=9
    table=[[Paragraph(escape(key),style) for key in COLUMNS]]
    for row in rows:table.append([Paragraph(escape(str(row.get(key,''))),style) for key in COLUMNS])
    t=LongTable(table,colWidths=[60,100,75,68,65,65,45,65,65,65],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5edf5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.5,colors.grey),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    SimpleDocTemplate(out,pagesize=landscape(A4),rightMargin=32,leftMargin=32,topMargin=32,bottomMargin=32).build([Paragraph('Home Invest - Transactions',styles['Title']),Spacer(1,12),t])
    return out.getvalue(),'application/pdf'
