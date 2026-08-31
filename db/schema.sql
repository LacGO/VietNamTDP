-- CSDL Tổ dân phố Việt Nam (Hà Nội, Phú Thọ) — hiệu lực 01/07/2025 (tỉnh/xã) & 01/07/2026 (TDP)
-- Sinh tự động từ thư mục data/ bằng scripts/build_sqlite.py

PRAGMA foreign_keys = ON;

CREATE TABLE province (
    province_code   TEXT PRIMARY KEY,      -- mã ĐVHC cấp tỉnh (GSO), vd '01', '25'
    name            TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    name_en         TEXT,
    full_name_en    TEXT,
    code_name       TEXT,
    unit_type       TEXT,                  -- Thành phố trực thuộc trung ương / Tỉnh
    postal_prefix   TEXT
);

CREATE TABLE ward (
    ward_code       TEXT PRIMARY KEY,      -- mã ĐVHC cấp xã (GSO), 5 chữ số
    province_code   TEXT NOT NULL REFERENCES province(province_code),
    name            TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    name_en         TEXT,
    full_name_en    TEXT,
    code_name       TEXT,
    unit_type       TEXT NOT NULL,         -- Phường / Xã
    postal_code     TEXT
);
CREATE INDEX idx_ward_province ON ward(province_code);

CREATE TABLE tdp (
    tdp_code        TEXT PRIMARY KEY,      -- <ward_code>.<seq:03d>, vd '00070.001'
    ward_code       TEXT NOT NULL REFERENCES ward(ward_code),
    province_code   TEXT NOT NULL REFERENCES province(province_code),
    name            TEXT NOT NULL,        -- vd 'Hàng Bạc 1'
    unit_type       TEXT NOT NULL,        -- tổ dân phố / thôn / khu phố / khu / bản / xóm
    code_name       TEXT,
    seq             INTEGER NOT NULL,
    arrangement     TEXT,                 -- 2026_07 (đúng mốc) | truoc_2026_07 | unknown
    verified        TEXT NOT NULL,        -- primary | partial | unverified | pending
    effective_date  TEXT
);
CREATE INDEX idx_tdp_ward ON tdp(ward_code);
CREATE INDEX idx_tdp_province ON tdp(province_code);

-- Metadata thu thập cho từng phường/xã (nghị quyết HĐND cấp xã, mức xác minh)
CREATE TABLE tdp_ward_meta (
    ward_code       TEXT PRIMARY KEY REFERENCES ward(ward_code),
    province_code   TEXT NOT NULL,
    tdp_count       INTEGER NOT NULL,       -- số TDP có tên trong bảng tdp
    approx_count    INTEGER,                -- số TDP ước tính (kể cả khi chưa có tên)
    arrangement     TEXT,
    resolution      TEXT,
    effective_date  TEXT,
    verified        TEXT NOT NULL,
    source_keys     TEXT,
    note            TEXT
);

CREATE TABLE tdp_source (
    source_key      TEXT PRIMARY KEY,
    title           TEXT,
    url             TEXT,
    date            TEXT,
    type            TEXT,                 -- nghi_quyet | cong_bao | bao | wikipedia | cong_ttdt
    via             TEXT
);

-- Ánh xạ đơn vị hành chính cũ -> mới ở cấp xã (NQ 1656 Hà Nội, NQ 1676 Phú Thọ)
CREATE TABLE ward_mapping (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    province_code      TEXT NOT NULL,
    new_ward_code      TEXT REFERENCES ward(ward_code),
    new_ward_name      TEXT NOT NULL,
    new_ward_type      TEXT,
    relation           TEXT NOT NULL,     -- toan_bo | mot_phan | mot_phan_dt | mot_phan_dt_toanbo_ds | phan_con_lai | giu_nguyen
    old_unit_type      TEXT,              -- phường / xã / thị trấn
    old_unit_name      TEXT NOT NULL,
    old_unit_qualifier TEXT,              -- vd 'quận Hai Bà Trưng', 'huyện Đông Anh'
    provision_no       INTEGER,
    source             TEXT
);
CREATE INDEX idx_map_new ON ward_mapping(new_ward_code);
CREATE INDEX idx_map_old ON ward_mapping(old_unit_name);
