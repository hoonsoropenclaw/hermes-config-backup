-- ============================================
-- School Bulletin - 5 tables + indexes + RLS
-- 完整 schema (2026-06-11 從 school-bulletin 實戰)
--
-- 貼到 Supabase Dashboard → SQL Editor → New query → 貼上 → Run
-- 跑完 SELECT table_name 應該看到 5 個表:
--   announcements / attachments / departments / tags / users
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
  display_name TEXT NOT NULL,
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
  publisher_name TEXT NOT NULL,                    -- 冗餘、避免 join
  publisher_dept TEXT NOT NULL REFERENCES departments(code),
  tag_ids TEXT[] NOT NULL DEFAULT '{}'::TEXT[],    -- 陣列、簡化
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
CREATE INDEX IF NOT EXISTS idx_ann_tags ON announcements USING GIN(tag_ids);  -- OR/AND 標籤篩選關鍵

-- 5. 附件表
CREATE TABLE IF NOT EXISTS attachments (
  id TEXT PRIMARY KEY,                             -- 'f_xxx'
  announcement_id TEXT REFERENCES announcements(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  storage_path TEXT NOT NULL,                      -- Supabase Storage path
  uploaded_by TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_att_ann ON attachments(announcement_id);

-- ============================================
-- Row Level Security (RLS) — 5 個表都開
-- ============================================

ALTER TABLE departments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags          ENABLE ROW LEVEL SECURITY;
ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;
ALTER TABLE attachments  ENABLE ROW LEVEL SECURITY;

-- 公開讀（給未登入的人看 + anon key 從前端讀）
DROP POLICY IF EXISTS "ann_read_public" ON announcements;
CREATE POLICY "ann_read_public" ON announcements FOR SELECT USING (deleted_at IS NULL);

DROP POLICY IF EXISTS "tags_read_public" ON tags;
CREATE POLICY "tags_read_public" ON tags FOR SELECT USING (is_active = TRUE);

DROP POLICY IF EXISTS "dept_read_public" ON departments;
CREATE POLICY "dept_read_public" ON departments FOR SELECT USING (TRUE);

-- users 表完全不建 SELECT policy → anon 讀不到、後端用 service_role 處理
-- 寫入一律走後端 service_role（anon key 沒 INSERT/UPDATE/DELETE policy → 完全不能寫）

-- 完工驗證
SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name IN
    ('departments','users','tags','announcements','attachments')
  ORDER BY table_name;
