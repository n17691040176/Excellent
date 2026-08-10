from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from app.core.exceptions import ConflictError

XML_NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'office': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'package': 'http://schemas.openxmlformats.org/package/2006/relationships',
}
TEXT_ENCODINGS = ('utf-8-sig', 'utf-8', 'gb18030', 'gbk')


def build_xlsx(headers: list[str], rows: list[list[object]], sheet_name: str = 'Sheet1') -> bytes:
    """Build a compact standards-compliant xlsx file without an extra runtime dependency."""

    def column_name(index: int) -> str:
        value = index + 1
        result = ''
        while value:
            value, remainder = divmod(value - 1, 26)
            result = chr(65 + remainder) + result
        return result

    all_rows = [headers, *rows]
    sheet_rows: list[str] = []
    for row_index, row in enumerate(all_rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            ref = f'{column_name(column_index)}{row_index}'
            text_value = escape('' if value is None else str(value))
            style = ' s="1"' if row_index == 1 else ''
            cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{text_value}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    safe_sheet_name = ''.join(char for char in sheet_name if char not in '[]:*?/\\')[:31] or 'Sheet1'
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>' + ''.join(sheet_rows) + '</sheetData></worksheet>'
    )
    files = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>',
        'xl/workbook.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(safe_sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>',
        'xl/styles.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font/><font><b/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="2"><xf xfId="0"/><xf xfId="0" fontId="1" applyFont="1"/></cellXfs></styleSheet>',
        'xl/worksheets/sheet1.xml': sheet_xml,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as workbook:
        for name, content in files.items():
            workbook.writestr(name, content.encode('utf-8'))
    return output.getvalue()


def load_tabular_rows(filename: str, data: bytes) -> list[dict[str, str]]:
    suffix = Path(filename or '').suffix.lower()
    if suffix == '.csv':
        return _rows_to_dicts(_read_csv_rows(data))
    if suffix == '.xlsx':
        return _rows_to_dicts(_read_xlsx_rows(data))
    raise ConflictError('Only .xlsx or .csv files are supported')


def _read_csv_rows(data: bytes) -> list[list[str]]:
    last_error: UnicodeDecodeError | None = None
    text = None
    for encoding in TEXT_ENCODINGS:
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    if text is None:
        raise ConflictError('Unable to decode CSV file') from last_error

    reader = csv.reader(io.StringIO(text))
    return [[_clean_cell(item) for item in row] for row in reader]


def _read_xlsx_rows(data: bytes) -> list[list[str]]:
    try:
        workbook = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ConflictError('Invalid xlsx file') from exc

    with workbook:
        shared_strings = _read_shared_strings(workbook)
        sheet_path = _resolve_first_sheet_path(workbook)
        sheet_root = ET.fromstring(workbook.read(sheet_path))
        parsed_rows: list[dict[int, str]] = []
        max_index = -1

        for row in sheet_root.findall('.//main:sheetData/main:row', XML_NS):
            cells: dict[int, str] = {}
            for cell in row.findall('main:c', XML_NS):
                ref = cell.attrib.get('r', '')
                index = _column_index_from_ref(ref)
                if index < 0:
                    continue
                value = _extract_cell_value(cell, shared_strings)
                cells[index] = _clean_cell(value)
                max_index = max(max_index, index)
            if cells:
                parsed_rows.append(cells)

        if max_index < 0:
            return []

        normalized_rows: list[list[str]] = []
        width = max_index + 1
        for parsed_row in parsed_rows:
            normalized_rows.append([parsed_row.get(index, '') for index in range(width)])
        return normalized_rows


def _rows_to_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    meaningful_rows = [row for row in rows if any(_clean_cell(value) for value in row)]
    if not meaningful_rows:
        return []

    headers = [_clean_cell(value) for value in meaningful_rows[0]]
    if not any(headers):
        raise ConflictError('Import file header row is empty')

    items: list[dict[str, str]] = []
    for row in meaningful_rows[1:]:
        values = row + [''] * max(0, len(headers) - len(row))
        item = {
            headers[index]: _clean_cell(values[index])
            for index in range(len(headers))
            if headers[index]
        }
        if any(item.values()):
            items.append(item)
    return items


def _read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if 'xl/sharedStrings.xml' not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read('xl/sharedStrings.xml'))
    values: list[str] = []
    for item in root.findall('main:si', XML_NS):
        parts = [node.text or '' for node in item.findall('.//main:t', XML_NS)]
        values.append(''.join(parts))
    return values


def _resolve_first_sheet_path(workbook: zipfile.ZipFile) -> str:
    workbook_root = ET.fromstring(workbook.read('xl/workbook.xml'))
    rels_root = ET.fromstring(workbook.read('xl/_rels/workbook.xml.rels'))
    relations = {
        rel.attrib.get('Id'): rel.attrib.get('Target', '')
        for rel in rels_root.findall('package:Relationship', XML_NS)
    }
    first_sheet = workbook_root.find('main:sheets/main:sheet', XML_NS)
    if first_sheet is None:
        raise ConflictError('Workbook does not contain any sheet')
    rel_id = first_sheet.attrib.get(f'{{{XML_NS["office"]}}}id')
    target = relations.get(rel_id)
    if not target:
        raise ConflictError('Workbook sheet relationship is invalid')
    target_path = PurePosixPath('xl') / PurePosixPath(target)
    return str(target_path)


def _extract_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get('t')
    value_node = cell.find('main:v', XML_NS)
    if cell_type == 'inlineStr':
        return ''.join(node.text or '' for node in cell.findall('.//main:t', XML_NS))
    if value_node is None:
        return ''

    raw_value = value_node.text or ''
    if cell_type == 's':
        index = int(raw_value)
        return shared_strings[index] if 0 <= index < len(shared_strings) else ''
    if cell_type == 'b':
        return 'true' if raw_value == '1' else 'false'
    return raw_value


def _column_index_from_ref(ref: str) -> int:
    letters = ''.join(char for char in ref if char.isalpha()).upper()
    if not letters:
        return -1
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1


def _clean_cell(value: object) -> str:
    return str(value or '').strip()
