from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

router = APIRouter(prefix="/pautas", tags=["Pautas Estratégicas"])

class PautaPdfIn(BaseModel):
    tema: str
    duracao_total_prevista: int | None = 15
    status: str | None = "gerada"
    gerado_em: str | None = None
    resumo_executivo: list[str] = []
    titulos_sugeridos: list[str] = []
    perguntas_sugeridas: list[str] = []
    artigos: list[dict] = []

@router.post("/pdf")
def gerar_pdf(p: PautaPdfIn):
    try:
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4

        y = h - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, f"Pauta: {p.tema}")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Status: {p.status}   •   Duração: {p.duracao_total_prevista} min   •   Gerado em: {p.gerado_em or ''}")
        y -= 25

        def bloco(titulo, itens):
            nonlocal y
            if not itens: 
                return
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, y, titulo)
            y -= 16
            c.setFont("Helvetica", 10)
            for item in itens:
                for linha in [item[:110], item[110:220], item[220:330]]:  # wrap simples
                    if not linha:
                        break
                    if y < 60:
                        c.showPage(); y = h - 50
                    c.drawString(50, y, f"• {linha}")
                    y -= 14
            y -= 8

        bloco("Resumo Executivo", p.resumo_executivo)
        bloco("Títulos Sugeridos", p.titulos_sugeridos)
        bloco("Perguntas Sugeridas", p.perguntas_sugeridas)

        if p.artigos:
            artigos_fmt = [f"{a.get('titulo','')} — {a.get('fonte','')} ({a.get('data','')})" for a in p.artigos]
            bloco("Artigos de Referência", artigos_fmt)

        c.showPage()
        c.save()

        pdf_bytes = buf.getvalue()
        buf.close()

        headers = {
            "Content-Disposition": f'attachment; filename="pauta-{p.tema}.pdf"'
        }
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")