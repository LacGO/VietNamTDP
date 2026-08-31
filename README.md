# CSDL Tổ dân phố Việt Nam — Hà Nội & Phú Thọ

Repo: <https://github.com/LacGO/VietNamTDP>

> Cơ sở dữ liệu mở về đơn vị hành chính Việt Nam **3 cấp**: tỉnh/thành → phường/xã → **tổ dân phố / thôn**,
> theo bộ máy sau sắp xếp (cấp tỉnh & cấp xã hiệu lực **01/07/2025**, cấp tổ dân phố/thôn hiệu lực **01/07/2026**).
> Giai đoạn 1 tập trung **Thành phố Hà Nội** và **tỉnh Phú Thọ** (mới — hợp nhất Phú Thọ + Vĩnh Phúc + Hòa Bình).

An open dataset of Vietnam's administrative units at **three levels** — province → ward/commune → residential group
(*tổ dân phố* / *thôn*) — reflecting the 2025–2026 reorganisation. Phase 1 covers **Hà Nội** and the **new Phú Thọ province**.

## Nội dung

| Cấp | Nguồn pháp lý | Số đơn vị | Trạng thái |
|-----|--------------|-----------|-----------|
| Tỉnh/thành | NQ 202/2025/QH15 (34 tỉnh/thành) | 2 (Hà Nội `01`, Phú Thọ `25`) | ✅ đầy đủ, có mã |
| Phường/xã | NQ 1656/NQ-UBTVQH15 (Hà Nội), NQ 1676/NQ-UBTVQH15 (Phú Thọ) | 126 + 148 = **274** | ✅ đầy đủ, có mã chính thức (GSO) |
| Ánh xạ ĐVHC cũ → mới | 2 nghị quyết trên | **1.277** dòng | ✅ trích tự động từ toàn văn |
| Tổ dân phố / thôn — **đúng mốc 01/7/2026** | NĐ 185/2026/NĐ-CP + nghị quyết/đề án HĐND **từng phường/xã** | **Hà Nội: 117/126 phường/xã (~2.500 TDP)** · **Phú Thọ: 22/148 (~500 đơn vị)** | 🚧 xem [docs/STATUS.md](docs/STATUS.md) |
| Tổ dân phố / thôn — hiện trạng **trước 01/7/2026** | Wikipedia tiếng Việt (dẫn nguồn) | Phú Thọ: 117/148 phường/xã (~3.100 đơn vị) · Hà Nội: 5/126 | ⚠️ dữ liệu nền, chưa phải bộ máy mới |
| _(chưa có dữ liệu)_ | — | Hà Nội: 4 · Phú Thọ: 9 | ⛔ chưa công bố công khai |

> ⚠️ **Cấp tổ dân phố chưa đầy đủ và có 2 mốc thời gian.** Danh mục TDP/thôn mới do HĐND **cấp xã** quyết định
> (mỗi phường/xã một nghị quyết, ban hành rải rác 5–9/2026); **chưa cơ quan nào tổng hợp công khai** và nhiều
> phường/xã chưa đăng toàn văn nghị quyết lên mạng.
> - **Hà Nội**: Wikipedia tiếng Việt cập nhật tốt → ~90% bản ghi đã đúng bộ máy **01/7/2026** (`arrangement = 2026_07`).
> - **Phú Thọ**: Wikipedia **chưa cập nhật** đợt sắp xếp thôn 01/7/2026 → phần lớn bản ghi là **hiện trạng trước đó**
>   (`arrangement = truoc_2026_07`). Dữ liệu đúng mốc chỉ có ở các xã đã đăng nghị quyết/thông báo lên cổng
>   `<mã-xã>.phutho.gov.vn` (đã lấy 19 xã, vd xã Võ Miếu — NQ 20/NQ-HĐND ngày 22/6/2026).
>
> **Lọc theo `arrangement` và `verified`** để dùng đúng tập dữ liệu. Cách bổ sung 1 phường/xã: xem mục Đóng góp.

## Cấu trúc thư mục

```
data/                 # dữ liệu đã build — dạng phẳng, dùng ngay
  provinces.csv/.json
  wards.csv/.json                 # 274 phường/xã + mã + mã bưu chính
  ward_mapping.csv/.json          # đơn vị cũ -> mới (cấp xã)
  tdp.csv/.json                   # tổ dân phố / thôn
  tdp_ward_meta.csv               # nghị quyết & mức xác minh theo từng phường/xã
  tdp_sources.csv                 # danh mục nguồn trích dẫn
json/                 # dạng cây lồng nhau theo tỉnh: ha_noi.json, phu_tho.json
db/
  schema.sql
  vietnam_tdp.sqlite              # build từ data/ (chạy scripts/build_sqlite.py)
sources/
  raw/                            # toàn văn nghị quyết đã trích (txt)
  tdp/<mã tỉnh>/<mã xã>_*.json     # dữ liệu TDP nhập tay theo từng phường/xã
scripts/              # pipeline build (Python 3, không phụ thuộc thư viện ngoài)
docs/
  STATUS.md                       # bảng theo dõi độ phủ TDP (sinh tự động)
  SOURCES.md                      # danh mục văn bản nguồn
```

## Build

```bash
python3 scripts/build_all.py     # build_admin -> build_mapping -> build_tdp -> build_nested -> build_sqlite
python3 scripts/gen_status.py     # cập nhật docs/STATUS.md
```

## Lược đồ mã

- **Tỉnh/thành, phường/xã**: mã ĐVHC chính thức của Cục Thống kê (GSO) — `01` (Hà Nội), `25` (Phú Thọ); phường/xã 5 chữ số.
- **Tổ dân phố**: mã tự sinh `"<mã xã>.<số thứ tự 3 chữ số>"`, ví dụ `00070.001`. Ổn định theo thứ tự trong file nguồn.

## Đóng góp

Thiếu / sai danh mục TDP của một phường/xã?

**Cách nhanh** — nếu có link bài viết hoặc file PDF nghị quyết/đề án của phường/xã:
```bash
python3 scripts/add_ward.py <mã xã> "<url bài viết>" --title "..." --date 2026-06-26
# hoặc chỉ định thẳng: --pdf "<url .pdf>" | --names "Thôn A;Thôn B;..." | --range 50
python3 scripts/scrape_danviet.py <mã xã> "<url bài Báo Dân Việt>"   # bài đăng toàn văn nghị quyết
python3 scripts/scrape_portals.py --codes <mã xã>                     # tự dò cổng TTĐT phường/xã
```
**Cách thủ công** — thêm/sửa `sources/tdp/<mã tỉnh>/<mã xã>_<slug>.json`
(mẫu: `01/00070_hoan_kiem.json`), kèm ít nhất một nguồn trong `sources[]`, đặt `arrangement`
(`2026_07` nếu là danh mục sau 01/7/2026), rồi `python3 scripts/build_all.py && python3 scripts/gen_status.py`.

Ưu tiên nguồn `verified: primary` = toàn văn nghị quyết HĐND phường/xã / công báo tỉnh;
`partial` = đề án UBND / báo chí; `unverified` = trích Wikipedia tự động.
`scripts/gaps.py` in danh sách phường/xã còn thiếu; `sources/portal_hosts.json` có host cổng TTĐT từng đơn vị.

## Giấy phép

- **Dữ liệu**: CC BY 4.0 — xem [LICENSE](LICENSE).
- Dữ liệu gốc là văn bản quy phạm pháp luật của Nhà nước Việt Nam (không thuộc phạm vi bảo hộ quyền tác giả theo Luật SHTT).
- Mã đơn vị & tên tiếng Anh cấp tỉnh/xã tham chiếu bộ dữ liệu công khai của Cục Thống kê Việt Nam.
