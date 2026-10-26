"""Google Sheets access through a service account (gspread)."""
from __future__ import annotations

import gspread
from gspread.utils import ValueRenderOption

from .importer import REQUIRED_COLUMNS, SheetError, SheetRow, norm_text


class GoogleSheet:
    def __init__(self, sheet_id: str, worksheet: str, credentials_file: str):
        try:
            client = gspread.service_account(filename=credentials_file)
            self.ws = client.open_by_key(sheet_id).worksheet(worksheet)
        except Exception as e:  # noqa: BLE001
            raise SheetError(f"cannot open sheet: {e}") from e

    def _grid(self) -> tuple[list[str], list[list]]:
        # UNFORMATTED so 13-digit timestamps are not turned into 1.76E+12
        grid = self.ws.get_all_values(value_render_option=ValueRenderOption.unformatted)
        if not grid:
            raise SheetError("sheet is empty: row 1 must be the header")
        header = [norm_text(h).lower() for h in grid[0]]
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            raise SheetError("header is missing column(s): " + ", ".join(missing))
        return header, grid[1:]

    def read_rows(self) -> list[SheetRow]:
        header, body = self._grid()
        rows = []
        for i, cells in enumerate(body, start=2):
            if all(norm_text(c) == "" for c in cells):
                continue
            rows.append(SheetRow(i, {h: cells[j] for j, h in enumerate(header) if j < len(cells)}))
        return rows

    def delete_rows_by_uid(self, uids: set[str]) -> int:
        # Re-read right now and match by uid, never by an old row number,
        # so rows added or moved since the import can not be hit by mistake.
        header, body = self._grid()
        u = header.index("uid")
        hit = [i for i, cells in enumerate(body, start=2)
               if u < len(cells) and norm_text(cells[u]) in uids]
        if not hit:
            return 0

        runs: list[tuple[int, int]] = []  # contiguous (first_row, last_row), 1-based inclusive
        for r in hit:
            if runs and r == runs[-1][1] + 1:
                runs[-1] = (runs[-1][0], r)
            else:
                runs.append((r, r))

        # bottom-up, so earlier deletions do not shift the later ones
        requests = [
            {"deleteDimension": {"range": {
                "sheetId": self.ws.id, "dimension": "ROWS",
                "startIndex": first - 1, "endIndex": last}}}
            for first, last in reversed(runs)
        ]
        self.ws.spreadsheet.batch_update({"requests": requests})
        return len(hit)
