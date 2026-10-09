import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load('outputs/acta-excel/acta-34.xlsx'));
for (const [sheetName, range] of [['Resumen','A1:B26'], ['Actas','A1:M5'], ['Coladas','A1:F6'], ['Rollos','A1:P8'], ['Composición','A1:J10'], ['Clasificación','A1:V8'], ['Evidencia','A1:N8'], ['Auditoría','A1:K8']]) {
  const preview = await wb.render({sheetName, range, scale: 1, format:'png'});
  await fs.writeFile(`outputs/acta-excel/${sheetName}.png`,new Uint8Array(await preview.arrayBuffer()));
}
console.log((await wb.inspect({kind:'table',range:'Clasificación!Q3:T8',tableMaxRows:6,tableMaxCols:4,maxChars:1800})).ndjson);
