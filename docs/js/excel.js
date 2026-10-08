// Excel import / export. Same layout as the desktop app: one sheet per theme,
// column A = Question, column B = Réponse, header on row 1.
// Uses SheetJS (global `XLSX`, loaded from lib/xlsx.full.min.js).

const FORBIDDEN = /[\[\]:*?/\\]/g;

/** Read a workbook and return [{ name, pairs: [[question, answer], …] }] for every non-empty sheet. */
export function parseWorkbook(arrayBuffer) {
  const wb = XLSX.read(arrayBuffer, { type: "array" });
  const sheets = [];
  for (const name of wb.SheetNames) {
    const rows = XLSX.utils.sheet_to_json(wb.Sheets[name], { header: 1, defval: "", blankrows: false });
    if (!rows.length) continue;
    let qCol = 0;
    let aCol = 1;
    const head = rows[0].map((v) => String(v).trim().toLowerCase());
    const qi = head.findIndex((v) => v.startsWith("question"));
    const ai = head.findIndex((v) => v.startsWith("réponse") || v.startsWith("reponse"));
    if (qi >= 0 && ai >= 0 && qi !== ai) {
      qCol = qi;
      aCol = ai;
    }
    const pairs = rows
      .slice(1)
      .map((r) => [String(r[qCol] ?? "").trim(), String(r[aCol] ?? "").trim()])
      .filter(([q, a]) => q && a);
    if (pairs.length) sheets.push({ name: name.trim(), pairs });
  }
  return sheets;
}

function sheetTitle(name, used) {
  const base = name.replace(FORBIDDEN, " ").trim().slice(0, 31) || "Thème";
  let title = base;
  let n = 2;
  while (used.has(title.toLowerCase())) {
    const suffix = ` (${n++})`;
    title = base.slice(0, 31 - suffix.length) + suffix;
  }
  used.add(title.toLowerCase());
  return title;
}

/** Build an .xlsx file from the store. Returns { file, themes, questions }. */
export function buildExport(store) {
  const wb = XLSX.utils.book_new();
  const used = new Set();
  let questions = 0;
  const themes = store.listThemes();
  for (const theme of themes) {
    const rows = [["Question", "Réponse"]];
    for (const q of store.listQuestions(theme.id)) {
      rows.push([q.question, q.answer]);
      questions++;
    }
    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws["!cols"] = [{ wch: 80 }, { wch: 38 }];
    XLSX.utils.book_append_sheet(wb, ws, sheetTitle(theme.name, used));
  }
  if (!themes.length) {
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([["Question", "Réponse"]]), "Questions");
  }
  const bytes = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  const file = new File([bytes], "banque_questions.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  return { file, themes: themes.length, questions };
}

export function downloadFile(file) {
  const url = URL.createObjectURL(file);
  const a = document.createElement("a");
  a.href = url;
  a.download = file.name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

export function canShareFile(file) {
  return !!(navigator.canShare && navigator.canShare({ files: [file] }));
}

export async function shareFile(file) {
  try {
    await navigator.share({ files: [file], title: "Banque de questions" });
    return true;
  } catch (e) {
    if (e && e.name === "AbortError") return false;
    throw e;
  }
}
