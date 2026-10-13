-- universal-workbench 迁移模板（幂等，schema + 种子合并为单次提交）
-- 定制点：按 server-skeleton.js 的 TABLES 白名单生成业务表；种子数据建议用 gen_seed.js 脚本生成后拼在下方

-- ===== 固定表 =====
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  username VARCHAR(80) UNIQUE,
  password_hash VARCHAR(255),        -- scrypt: salt:hash（用生成脚本算好，勿明文）
  nick VARCHAR(120),
  role VARCHAR(30) DEFAULT 'member', -- admin / member（自定义角色先读 SKILL.md 升级路径）
  status VARCHAR(20) DEFAULT 'approved',
  permissions TEXT DEFAULT '[]',     -- 可授权视图 JSON 数组
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seed_meta (
  k VARCHAR(80) PRIMARY KEY,
  v TEXT
);

-- ===== 业务表（示例：clients，按 TABLES 白名单替换） =====
-- 列类型只用 text / numeric / boolean / date；避开保留字（order→sort_order, usage→usage_notes）
CREATE TABLE IF NOT EXISTS clients (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  owner VARCHAR(80),
  stage VARCHAR(40) DEFAULT 'new',
  amount NUMERIC(12,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS followups (
  id BIGSERIAL PRIMARY KEY,
  client_id INT,
  note TEXT,
  owner VARCHAR(80),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ===== RLS：服务端持钥访问，应用层做权限（每张表都要放行，漏一张=404/空数据） =====
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['users','seed_meta','clients','followups' /* ← 加你的业务表 */]
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = t AND policyname = 'wb_all_' || t) THEN
      EXECUTE format('CREATE POLICY wb_all_%I ON %I FOR ALL USING (true) WITH CHECK (true)', t, t);
    END IF;
  END LOOP;
END $$;

-- ===== 种子数据 =====
-- 密码 hash 必须用 node crypto.scryptSync 预先生成（见 gen_seed.js 模式）
INSERT INTO users (username, password_hash, nick, role, status, permissions) VALUES
  ('admin', '<scrypt-hash>', '管理员', 'admin', 'approved', '[]')
ON CONFLICT (username) DO NOTHING;

-- 演示数据：gen_seed.js 生成后拼接（真实录入用则留空，只留 admin）
INSERT INTO clients (name, owner, stage, amount) VALUES
  ('示例客户 A（演示）', '张三', 'new', 10000);
