/**
 * Gestor360 — PDF generator (client-side).
 *
 * Recreates the ReportLab layout used previously on the backend:
 *   - A4 portrait, ~1.5cm margins.
 *   - Header: company logo/name (left) + doc type/number/dates (right).
 *   - Orange separator bar.
 *   - Client info block (2 rows, 4 columns).
 *   - Line-item table with dark header row and zebra body.
 *   - Right-aligned totals table with highlighted final row.
 *   - Optional notes + payment conditions (Boleto shows individual due dates).
 *
 * Uses jsPDF only — no server round-trip, no paid service.
 */
import { jsPDF } from "jspdf";

const ORANGE = "#F05D23";
const DARK = "#09090B";
const GRAY = "#71717A";
const LIGHT = "#F4F4F5";
const HIGHLIGHT = "#FDF0EC";
const BORDER = "#E4E4E7";
const FOOTER = "#A1A1AA";

// ---- helpers ----
const fmtMoney = (v) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(v || 0));

const fmtDate = (iso, includeTime = true) => {
  if (!iso) return "—";
  const d = new Date(iso);
  const opts = includeTime
    ? { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "2-digit", month: "2-digit", year: "numeric" };
  return d.toLocaleString("pt-BR", opts);
};

const addDays = (iso, days) => {
  const d = new Date(iso);
  d.setDate(d.getDate() + Number(days || 0));
  return d;
};

const METHODS = {
  pix: "PIX",
  dinheiro: "Dinheiro",
  credito: "Cartão de Crédito",
  debito: "Cartão de Débito",
  boleto: "Boleto",
  transferencia: "Transferência",
};

/**
 * Load a data-URL image into a promise resolving to { data, w, h } for jsPDF.addImage.
 * Returns null if the URL is invalid / not a data-URL.
 */
function loadLogo(dataUrl) {
  return new Promise((resolve) => {
    if (!dataUrl || !String(dataUrl).startsWith("data:image")) return resolve(null);
    const img = new Image();
    img.onload = () => resolve({ data: dataUrl, w: img.width, h: img.height });
    img.onerror = () => resolve(null);
    img.src = dataUrl;
  });
}

// ---- Layout constants (all mm) ----
const PAGE = { w: 210, h: 297 };
const MARGIN = { l: 15, r: 15, t: 12, b: 15 };

function drawHeader(pdf, company, doc, logo) {
  const y0 = MARGIN.t;

  // ---- left: logo OR company name in bold big ----
  let leftY = y0;
  if (logo) {
    const size = 30; // 30mm ~ 3.5cm
    const ratio = logo.w && logo.h ? Math.min(size / logo.w, size / logo.h) : 1;
    const w = (logo.w || size) * ratio;
    const h = (logo.h || size) * ratio;
    pdf.addImage(logo.data, "PNG", MARGIN.l, leftY, w, h, undefined, "FAST");
    leftY += h + 3;
  } else {
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(18);
    pdf.setTextColor(DARK);
    pdf.text(company.name || "Sua Empresa", MARGIN.l, leftY + 6);
    leftY += 10;
  }
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(9);
  pdf.setTextColor(GRAY);
  pdf.text(`CNPJ: ${company.cnpj || "—"}`, MARGIN.l, leftY); leftY += 4;
  if (company.ie) { pdf.text(`IE: ${company.ie}`, MARGIN.l, leftY); leftY += 4; }
  if (company.address) { pdf.text(String(company.address).slice(0, 90), MARGIN.l, leftY); leftY += 4; }
  const contact = [company.phone, company.email].filter(Boolean).join("   ");
  if (contact) { pdf.text(contact, MARGIN.l, leftY); leftY += 4; }

  // ---- right: doc type / number / dates ----
  const rightX = PAGE.w - MARGIN.r;
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(16);
  pdf.setTextColor(ORANGE);
  const label = doc.doc_type === "orcamento" ? "ORÇAMENTO" : "VENDA";
  pdf.text(label, rightX, y0 + 6, { align: "right" });

  pdf.setFontSize(11);
  pdf.setTextColor(DARK);
  pdf.text(`Nº ${String(doc.number).padStart(6, "0")}`, rightX, y0 + 12, { align: "right" });

  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(9);
  pdf.setTextColor(GRAY);
  pdf.text(`Emissão: ${fmtDate(doc.created_at)}`, rightX, y0 + 18, { align: "right" });
  if (doc.valid_until) {
    pdf.text(`Validade: ${fmtDate(doc.valid_until)}`, rightX, y0 + 23, { align: "right" });
  }

  const bottomY = Math.max(leftY, y0 + 26);

  // ---- orange separator bar ----
  pdf.setFillColor(ORANGE);
  pdf.rect(MARGIN.l, bottomY + 1, PAGE.w - MARGIN.l - MARGIN.r, 1.2, "F");
  return bottomY + 6;
}

function drawClient(pdf, client, startY) {
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(8);
  pdf.setTextColor(GRAY);
  pdf.text("CLIENTE", MARGIN.l, startY);

  const rowY = startY + 4;
  const cols = [MARGIN.l, 40, 120, 150];
  const parts = [];
  if (client.street) {
    let s = client.street;
    if (client.number) s += `, ${client.number}`;
    if (client.complement) s += ` — ${client.complement}`;
    parts.push(s);
  }
  if (client.district) parts.push(client.district);
  if (client.city) parts.push(client.state ? `${client.city}/${client.state}` : client.city);
  if (client.cep) parts.push(`CEP ${client.cep}`);
  const address = parts.join(" · ") || client.address || "—";

  const rows = [
    [["Nome", client.name || "—"], ["Documento", client.document || "—"]],
    [["Endereço", address], ["Telefone", client.phone || "—"]],
    [["Email", client.email || "—"], ["IE", client.ie || "—"]],
  ];

  // top border
  pdf.setDrawColor(BORDER);
  pdf.setLineWidth(0.2);
  pdf.line(MARGIN.l, rowY - 2, PAGE.w - MARGIN.r, rowY - 2);

  let y = rowY + 2;
  rows.forEach((row) => {
    row.forEach(([lbl, val], idx) => {
      const baseX = idx === 0 ? cols[0] : cols[2];
      const valX = idx === 0 ? cols[1] : cols[3];
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(8);
      pdf.setTextColor(GRAY);
      pdf.text(lbl, baseX, y);
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(9);
      pdf.setTextColor(DARK);
      const maxW = idx === 0 ? cols[2] - cols[1] - 5 : PAGE.w - MARGIN.r - valX;
      const lines = pdf.splitTextToSize(String(val || "—"), maxW);
      pdf.text(lines, valX, y);
    });
    y += 6;
  });
  pdf.line(MARGIN.l, y - 3, PAGE.w - MARGIN.r, y - 3);
  return y + 3;
}

function drawItemsTable(pdf, doc, startY) {
  const cols = [
    { key: "code", label: "Cód.", w: 15, align: "left" },
    { key: "description", label: "Descrição", w: 74, align: "left" },
    { key: "qty", label: "Qtd.", w: 15, align: "right" },
    { key: "price", label: "Valor Unit.", w: 25, align: "right" },
    { key: "gross", label: "Bruto", w: 25, align: "right" },
    { key: "net", label: "Líquido", w: 26, align: "right" },
  ];
  const totalW = cols.reduce((s, c) => s + c.w, 0);
  const x0 = MARGIN.l;
  const rowH = 7;

  // header
  pdf.setFillColor(DARK);
  pdf.rect(x0, startY, totalW, rowH, "F");
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(8.5);
  pdf.setTextColor("#FFFFFF");
  let cx = x0;
  cols.forEach((c) => {
    const tx = c.align === "right" ? cx + c.w - 2 : cx + 2;
    pdf.text(c.label, tx, startY + rowH - 2.2, { align: c.align });
    cx += c.w;
  });
  // orange underline
  pdf.setDrawColor(ORANGE);
  pdf.setLineWidth(0.4);
  pdf.line(x0, startY + rowH, x0 + totalW, startY + rowH);

  // body
  let y = startY + rowH;
  let totalGross = 0, totalNet = 0;
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(9);

  (doc.lines || []).forEach((line, idx) => {
    // page break if needed
    if (y + rowH > PAGE.h - MARGIN.b - 60) {
      pdf.addPage();
      y = MARGIN.t;
    }
    const qty = Number(line.quantity || 0);
    const price = Number(line.unit_price || 0);
    const discPct = Number(line.discount_pct || 0);
    const gross = qty * price;
    const net = gross * (1 - discPct / 100);
    totalGross += gross;
    totalNet += net;

    // zebra
    if (idx % 2 === 1) {
      pdf.setFillColor(LIGHT);
      pdf.rect(x0, y, totalW, rowH, "F");
    }

    pdf.setTextColor(DARK);
    cx = x0;
    const values = {
      code: line.code || "—",
      description: pdf.splitTextToSize(line.description || "", cols[1].w - 4)[0] || "",
      qty: Number.isInteger(qty) ? String(qty) : String(qty),
      price: fmtMoney(price),
      gross: fmtMoney(gross),
      net: fmtMoney(net),
    };
    cols.forEach((c) => {
      const tx = c.align === "right" ? cx + c.w - 2 : cx + 2;
      pdf.text(String(values[c.key] ?? ""), tx, y + rowH - 2.2, { align: c.align });
      cx += c.w;
    });
    y += rowH;
  });

  return { endY: y + 4, totalGross, totalNet };
}

function drawTotals(pdf, doc, startY, totalGross, totalNet) {
  const gpct = Number(doc.global_discount_pct || 0);
  const gamt = Number(doc.global_discount_amount || 0);
  const totalDiscItems = totalGross - totalNet;
  const globalDiscValue = totalNet * (gpct / 100) + gamt;
  const final = Math.max(totalNet - globalDiscValue, 0);

  const boxW = 90;
  const boxX = PAGE.w - MARGIN.r - boxW;
  let y = startY;

  const drawRow = (label, value, opts = {}) => {
    pdf.setFont("helvetica", opts.bold ? "bold" : "normal");
    pdf.setFontSize(opts.big ? 12 : 10);
    pdf.setTextColor(opts.color || (opts.bold ? DARK : GRAY));
    if (opts.bg) {
      pdf.setFillColor(opts.bg);
      pdf.rect(boxX, y - 5, boxW, 8, "F");
      pdf.setDrawColor(ORANGE);
      pdf.setLineWidth(0.6);
      pdf.line(boxX, y - 5, boxX + boxW, y - 5);
    }
    pdf.text(label, boxX + 2, y);
    pdf.text(value, boxX + boxW - 2, y, { align: "right" });
    y += opts.big ? 8 : 6;
  };

  drawRow("Subtotal Bruto", fmtMoney(totalGross));
  drawRow("Desconto nos itens", `- ${fmtMoney(totalDiscItems)}`);
  if (gpct > 0 || gamt > 0) {
    const lbl = gpct > 0 && gamt === 0 ? `Desconto no total (${gpct}%)` : "Desconto no total";
    drawRow(lbl, `- ${fmtMoney(globalDiscValue)}`);
  }
  drawRow("TOTAL LÍQUIDO", fmtMoney(final), { bold: true, big: true, bg: HIGHLIGHT, color: DARK });

  return { endY: y + 2, final };
}

function drawNotesAndPayments(pdf, doc, startY) {
  let y = startY;

  if (doc.notes) {
    if (y > PAGE.h - MARGIN.b - 40) { pdf.addPage(); y = MARGIN.t; }
    pdf.setFont("helvetica", "normal"); pdf.setFontSize(8); pdf.setTextColor(GRAY);
    pdf.text("OBSERVAÇÕES", MARGIN.l, y);
    y += 4;
    pdf.setFontSize(10); pdf.setTextColor(DARK);
    const lines = pdf.splitTextToSize(String(doc.notes), PAGE.w - MARGIN.l - MARGIN.r);
    pdf.text(lines, MARGIN.l, y);
    y += lines.length * 5 + 4;
  }

  if (doc.payments && doc.payments.length) {
    if (y > PAGE.h - MARGIN.b - 40) { pdf.addPage(); y = MARGIN.t; }
    pdf.setFont("helvetica", "normal"); pdf.setFontSize(8); pdf.setTextColor(GRAY);
    pdf.text("CONDIÇÕES DE PAGAMENTO", MARGIN.l, y);
    y += 4;

    doc.payments.forEach((p) => {
      if (y > PAGE.h - MARGIN.b - 15) { pdf.addPage(); y = MARGIN.t; }
      pdf.setFont("helvetica", "bold"); pdf.setFontSize(10); pdf.setTextColor(DARK);
      pdf.text(METHODS[p.method] || p.method || "—", MARGIN.l, y);

      pdf.setFont("helvetica", "normal");
      let detail = fmtMoney(p.amount);
      if (p.method === "credito" && Number(p.installments) > 1) {
        detail += ` · ${p.installments}x de ${fmtMoney(Number(p.amount) / Number(p.installments))}`;
      }
      pdf.text(detail, PAGE.w - MARGIN.r, y, { align: "right" });
      y += 5;

      if (p.method === "boleto" && Array.isArray(p.boleto_days) && p.boleto_days.length) {
        const days = p.boleto_days.filter((d) => Number(d) > 0);
        const per = Number(p.amount) / days.length;
        pdf.setFontSize(8);
        pdf.setTextColor(GRAY);
        const parcelas = days.map((d, i) => {
          const due = addDays(doc.created_at, d);
          return `${i + 1}ª/${due.toLocaleDateString("pt-BR")} — ${fmtMoney(per)}`;
        });
        const wrapped = pdf.splitTextToSize(parcelas.join("  ·  "), PAGE.w - MARGIN.l - MARGIN.r);
        pdf.text(wrapped, MARGIN.l, y);
        y += wrapped.length * 4 + 2;
      }

      pdf.setDrawColor(BORDER);
      pdf.setLineWidth(0.1);
      pdf.line(MARGIN.l, y, PAGE.w - MARGIN.r, y);
      y += 3;
    });
  }
  return y;
}

function drawFooter(pdf) {
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(8);
  pdf.setTextColor(FOOTER);
  const today = new Date().toLocaleDateString("pt-BR");
  const total = pdf.getNumberOfPages();
  for (let i = 1; i <= total; i++) {
    pdf.setPage(i);
    const txt = `Documento gerado por Gestor360 · ${today} · página ${i}/${total}`;
    pdf.text(txt, MARGIN.l, PAGE.h - 8);
  }
}

/**
 * Build a PDF for a document and open/download it.
 *
 * @param {object} doc     — the document object (from /api/documents/:id)
 * @param {object} company — the company object (from /api/company)
 * @param {object} client  — the client object (from /api/clients)
 * @param {object} options — { openInline: bool, autoDownload: bool, filename?: string }
 */
export async function buildDocumentPdf(doc, company, client, options = {}) {
  const pdf = new jsPDF({ unit: "mm", format: "a4", compress: true });
  const logo = await loadLogo(company?.logo_data_url);

  let y = drawHeader(pdf, company || {}, doc, logo);
  y = drawClient(pdf, client || {}, y + 2);
  const items = drawItemsTable(pdf, doc, y);
  const totals = drawTotals(pdf, doc, items.endY + 4, items.totalGross, items.totalNet);
  drawNotesAndPayments(pdf, doc, totals.endY + 4);
  drawFooter(pdf);

  const filename = options.filename
    || `${doc.doc_type === "orcamento" ? "orcamento" : "venda"}_${String(doc.number).padStart(6, "0")}.pdf`;

  if (options.openInline !== false) {
    const blob = pdf.output("blob");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener";
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } else {
    pdf.save(filename);
  }
  return filename;
}
