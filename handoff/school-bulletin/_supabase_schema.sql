-- ============================================
-- School Bulletin - 5 tables + indexes + RLS
-- 貼到 Supabase Dashboard → SQL Editor → New query → 貼上 → Run
-- ============================================

-- 1. 處室表 (lookup)
CREATE TABLE IF NOT EXISTS departments (
  code TEXT PRIMARY KEY,           -- 'teaching' / 'student' / ...
  name TEXT NOT NULL,              -- '教務處'
  short TEXT NOT NULL,             -- '教'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO departments (code, name, short) VALUES
  ('teaching', '教務處', '教'),
  ('student',  '學務處', '學'),
  ('general',  '總務處', '總'),
  ('counsel',  '輔導處', '輔'),
  ('it',       '資訊組', '資'),
  ('principal','校長室', '校')
ON CONFLICT (code) DO NOTHING;

-- 2. 使用者表
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,                              -- 'u_xxx'
  username TEXT UNIQUE NOT NULL,                   -- 處室 code
  display_name TEXT NOT NULL,                      -- '教務處'
  department_code TEXT NOT NULL REFERENCES departments(code),
  role TEXT NOT NULL DEFAULT 'dept_officer',       -- 'dept_officer' | 'sysadmin'
  password_hash TEXT NOT NULL,                     -- bcrypt
  must_change_password BOOLEAN DEFAULT TRUE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_login_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_users_dept ON users(department_code);

-- 3. 標籤表
CREATE TABLE IF NOT EXISTS tags (
  id TEXT PRIMARY KEY,                             -- 't_xxx'
  type TEXT NOT NULL,                              -- 'grade' | 'class' | 'department' | 'activity' | 'role'
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  color TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tags_type ON tags(type);

-- 4. 公告表
CREATE TABLE IF NOT EXISTS announcements (
  id TEXT PRIMARY KEY,                             -- 'a_xxx'
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  publisher_id TEXT NOT NULL REFERENCES users(id),
  publisher_name TEXT NOT NULL,                    -- 冗餘,避免 join
  publisher_dept TEXT NOT NULL REFERENCES departments(code),
  tag_ids TEXT[] NOT NULL DEFAULT '{}'::TEXT[],    -- 陣列,簡化
  attachment_ids TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
  require_signature BOOLEAN DEFAULT FALSE,
  signature_deadline TIMESTAMPTZ,
  publish_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ann_publish_at ON announcements(publish_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_ann_publisher ON announcements(publisher_id);
CREATE INDEX IF NOT EXISTS idx_ann_dept ON announcements(publisher_dept);
CREATE INDEX IF NOT EXISTS idx_ann_tags ON announcements USING GIN(tag_ids);

-- 5. 附件表 (用 base64 存小檔、>5MB 改走 supabase storage bucket)
CREATE TABLE IF NOT EXISTS attachments (
  id TEXT PRIMARY KEY,                             -- 'f_xxx'
  announcement_id TEXT REFERENCES announcements(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  storage_path TEXT NOT NULL,                      -- 'attachments/u_xxx/123.pdf' (在 Supabase Storage)
  uploaded_by TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_att_ann ON attachments(announcement_id);

-- ============================================
-- 路線 A 補完 (2026-06-11) — 3 張新表,搭配 M-05/M-06/M-07
-- 不動既有 5 張表的 schema;idempotent CREATE TABLE IF NOT EXISTS
-- ============================================

-- 6. user_role_assignments:把 user 對應到既有 tags (type='role') 的多對多表
--   用途:teacher/parent/student/guest 等「受眾身分」(M-06 受眾分流)
--   設計理由:不動 users 表 schema,用 join table 表達「一個 user 可有多個 role 標籤」
CREATE TABLE IF NOT EXISTS user_role_assignments (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, role_tag_id)
);
CREATE INDEX IF NOT EXISTS idx_ura_user ON user_role_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_ura_role_tag ON user_role_assignments(role_tag_id);

-- 7. signature_receipts:使用者對公告的簽收回條 (M-07 簽收追蹤)
--   唯一索引 (announcement_id, user_id) 防止重複簽收
CREATE TABLE IF NOT EXISTS signature_receipts (
  id TEXT PRIMARY KEY,                             -- 'sig_xxx'
  announcement_id TEXT NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ip_address TEXT,
  user_agent TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_signature_unique ON signature_receipts(announcement_id, user_id);
CREATE INDEX IF NOT EXISTS idx_signature_ann ON signature_receipts(announcement_id);
CREATE INDEX IF NOT EXISTS idx_signature_user ON signature_receipts(user_id);

-- 8. read_receipts:使用者進入公告詳情頁的已讀紀錄 (M-07)
--   唯一索引 (announcement_id, user_id) — 同一則同一使用者只記一筆(去重)
CREATE TABLE IF NOT EXISTS read_receipts (
  id TEXT PRIMARY KEY,                             -- 'rd_xxx'
  announcement_id TEXT NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  read_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_read_unique ON read_receipts(announcement_id, user_id);
CREATE INDEX IF NOT EXISTS idx_read_ann ON read_receipts(announcement_id);
CREATE INDEX IF NOT EXISTS idx_read_user ON read_receipts(user_id);

-- ============================================
-- Row Level Security (RLS)
-- anon key 從前端 / API 只能做 RLS 允許的事
-- ============================================

ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE users        ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags         ENABLE ROW LEVEL SECURITY;
ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE attachments ENABLE ROW LEVEL SECURITY;

-- 3 張新表也開 RLS(後端 service_role 繞過;anon 進不來)
ALTER TABLE user_role_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE signature_receipts    ENABLE ROW LEVEL SECURITY;
ALTER TABLE read_receipts         ENABLE ROW LEVEL SECURITY;

-- 公開讀:公告 (給未登入的人看)
DROP POLICY IF EXISTS "ann_read_public" ON announcements;
CREATE POLICY "ann_read_public" ON announcements
  FOR SELECT USING (deleted_at IS NULL);

-- 公開讀:標籤
DROP POLICY IF EXISTS "tags_read_public" ON tags;
CREATE POLICY "tags_read_public" ON tags
  FOR SELECT USING (is_active = TRUE);

-- 公開讀:處室
DROP POLICY IF EXISTS "dept_read_public" ON departments;
CREATE POLICY "dept_read_public" ON departments FOR SELECT USING (TRUE);

-- 公開讀:用戶 (只限顯示名 / 處室 — 密碼 hash 透過 column 限制)
-- (後端 API 不透過 RLS 過 user password,改用 service_role 走後端)
-- 為了 MVP 簡化,users 表的 SELECT 完全擋,前端不直接查 users
DROP POLICY IF EXISTS "users_read_self" ON users;
-- 不創建 SELECT policy → anon 完全讀不到 users,只能透過後端 API

-- 3 張新表:不放 SELECT policy → anon 完全讀不到,只能透過後端 API (service_role)
-- signature_receipts / read_receipts / user_role_assignments 全部走後端

-- 寫入策略:anon 完全不能寫 → 全部後端 API 透過 service_role 處理
-- 這樣 anon key 不會被用來亂 insert

-- 完工!現在跑 SELECT 應該看得到 8 個表
SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name IN
    ('departments','users','tags','announcements','attachments',
     'user_role_assignments','signature_receipts','read_receipts')
  ORDER BY table_name;
