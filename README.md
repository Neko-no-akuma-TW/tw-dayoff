# Taiwan Day Off API Wrapper (`tw-dayoff`)

Python wrapper for querying Taiwan's natural disaster work and school closure announcements (天然災害停止上班及上課情形, `work_closure`) via the [dashboard.tw](https://dashboard.tw) Open Data API.

> **v0.2.0 重大更新**：因原先使用的非官方 API 已廢棄，本套件已全面重構改為串接 **dashboard.tw API v1**，支援 **OAuth 2.0 Client Credentials** 權杖快取與自動續期、ETag 條件請求（`304 Not Modified` 節省流量配額）、歷史分頁查詢與 CLI 工具。

---

## 安裝方式

```bash
pip install tw-dayoff
```

---

## 取得 API 憑證（OAuth 2.0）

1. 前往 [https://dashboard.tw](https://dashboard.tw) 使用 GitHub 或 Google 帳號登入。
2. 前往 [我的 API 憑證（https://dashboard.tw/me/api-key）](https://dashboard.tw/me/api-key) 建立一組 **Client ID** 與 **Client Secret**。
3. 建議透過環境變數設定憑證（套件會自動讀取）：

```bash
export DASHBOARD_TW_CLIENT_ID="your-client-id"
export DASHBOARD_TW_CLIENT_SECRET="your-client-secret"
```

Windows PowerShell：

```powershell
$env:DASHBOARD_TW_CLIENT_ID="your-client-id"
$env:DASHBOARD_TW_CLIENT_SECRET="your-client-secret"
```

---

## 快速使用

### 1. 高階單一縣市查詢（`TyphoonDayOff`）

支援傳入內政部五位數代碼（如 `"63000"`）、中文縣市名（如 `"臺北市"`、`"台北市"`、`"高雄"`）、英文名稱（如 `"Taipei"`）或舊版簡稱（如 `"tp"`、`"kh"`、`"ntpc"`）：

```python
from tw_dayoff import TyphoonDayOff

with TyphoonDayOff("臺北市") as dayoff:
    print(dayoff.get_dayoff())   # 公告原文（若無公告則為 None）
    print(dayoff.is_dayoff())    # True 代表停班停課 (level == 2)
    record = dayoff.get_record() # 完整 WorkClosureRecord 物件
```

若不想使用環境變數，也可直接傳入憑證：

```python
dayoff = TyphoonDayOff(
    "63000",
    client_id="your-client-id",
    client_secret="your-client-secret",
)
```

### 2. 完整客戶端（`DashboardClient`）

支援查詢全國最新資料、歷史紀錄（單次最長 31 天，支援 `next_cursor` 自動分頁）、ETag 快取與配額標頭追蹤：

```python
from tw_dayoff import DashboardClient

with DashboardClient() as client:
    # 查詢全國最新停班停課公告
    records = client.get_latest()
    for r in records:
        print(r.day, r.county_name, r.level, r.status)

    # 查詢特定縣市歷史紀錄（自動拉取所有分頁）
    history = client.get_history(
        county="高雄市",
        from_time="2026-10-01",
        to_time="2026-10-05",
        fetch_all=True,
    )

    # 查看剩餘每日 API 配額與資料來源
    print(client.last_rate_limit)
    print(client.last_source)
```

---

## CLI 指令

```bash
# 查詢全國
python -m tw_dayoff

# 查詢特定縣市並輸出 JSON
tw-dayoff --county 臺北市 --json
```

---

## 縣市代碼對照（內政部五位數代碼）

* 直轄市：`63000` 臺北市、`65000` 新北市、`68000` 桃園市、`66000` 臺中市、`67000` 臺南市、`64000` 高雄市
* 臺灣省：`10017` 基隆市、`10002` 宜蘭縣、`10004` 新竹縣、`10018` 新竹市、`10005` 苗栗縣、`10007` 彰化縣、`10008` 南投縣、`10009` 雲林縣、`10010` 嘉義縣、`10020` 嘉義市、`10013` 屏東縣、`10014` 臺東縣、`10015` 花蓮縣、`10016` 澎湖縣
* 福建省：`09020` 金門縣、`09007` 連江縣

---

## 資料來源與授權

* **資料來源**：行政院人事行政總處（各縣市政府），經由 [dashboard.tw](https://dashboard.tw/developers/datasets/work_closure) 開放資料 API 提供。
* **本專案授權**：GNU GPLv3（詳見 [LICENSE](LICENSE)）。
