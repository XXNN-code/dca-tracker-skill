"""Google Sheets CRUD 操作"""
import gspread
from google.oauth2.service_account import Credentials

from dca_tracker.config import CREDENTIALS_PATH, SHEET_NAME, WORKSHEET_NAME, SHEET_COLUMNS


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client() -> gspread.Client:
    """获取 gspread 客户端（Service Account 认证）"""
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def init_sheet() -> str:
    """初始化 Sheet：打开已有的 Sheet，确保 Records 工作表和表头存在。

    Sheet 需要用户在 Google Drive 中手动创建并共享给服务账户。
    返回 Sheet URL。
    """
    gc = get_client()
    try:
        sh = gc.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        raise RuntimeError(
            f"未找到名为 '{SHEET_NAME}' 的 Google Sheet。\n"
            f"请在 Google Drive 中创建此 Sheet，并共享给服务账户。"
        )

    # 确保 Records 工作表存在
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(
            title=WORKSHEET_NAME, rows=1000, cols=len(SHEET_COLUMNS)
        )

    # 检查是否需要写入表头
    first_row = ws.row_values(1)
    if not first_row:
        ws.append_row(SHEET_COLUMNS)

    return sh.url


def _get_worksheet() -> gspread.Worksheet:
    """获取工作表（内部使用）"""
    gc = get_client()
    sh = gc.open(SHEET_NAME)
    return sh.worksheet(WORKSHEET_NAME)


def get_all_records() -> list[dict]:
    """读取所有记录，返回字典列表"""
    ws = _get_worksheet()
    return ws.get_all_records()


def get_unique_tickers() -> list[str]:
    """获取不重复的 Ticker 列表（保持首次出现顺序）"""
    records = get_all_records()
    seen = set()
    tickers = []
    for r in records:
        t = r.get("Ticker", "")
        if t and t not in seen:
            seen.add(t)
            tickers.append(t)
    return tickers


def get_latest_record(ticker: str) -> dict | None:
    """获取某 Ticker 最新一条记录（最后一行）"""
    records = get_all_records()
    matches = [r for r in records if str(r.get("Ticker", "")) == str(ticker)]
    return matches[-1] if matches else None


def append_record(record: dict):
    """追加一行新记录到 Sheet"""
    ws = _get_worksheet()
    row = [str(record.get(col, "")) for col in SHEET_COLUMNS]
    ws.append_row(row, value_input_option="RAW")
