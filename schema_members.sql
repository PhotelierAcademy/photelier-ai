-- Photelier Academy 会員テーブル
-- 2026-08 サブスク（Photelierサロン）＋これからの本講座受講生 用
--
-- 既存6名（students.json）はこのテーブルに入れない。今まで通り名前選択で入れる。
-- 2026年11月に全員サポート終了 → そのタイミングで名前選択の入口を閉じる想定。
--
-- パスワードは Supabase Auth（auth.users）が預かる。ここには保存しない。
-- → パスワード再発行メールも Supabase がやってくれる。

create table if not exists members (
  -- Supabase Auth のユーザーIDと 1対1
  id                    uuid primary key references auth.users(id) on delete cascade,

  email                 text not null unique,          -- ログインID。データの保存キーにもなる
  name                  text not null,                 -- 画面に出るお名前

  -- 種別
  tier                  text not null default 'subscription',  -- 'subscription' | 'course'

  -- サブスク（Photelierサロン）用
  subscription_started_at date,                         -- ドリップ開放の起点。入会日
  stripe_customer_id    text,
  stripe_subscription_id text,
  full_unlock           boolean not null default false, -- true なら全部開放（アップセル用）

  -- 本講座用
  support_end           date,                           -- サポート終了日
  course_months         int,

  -- 共通
  active                boolean not null default true,  -- false でログイン不可（解約・停止）
  created_at            timestamptz not null default now()
);

create index if not exists members_email_idx on members (lower(email));

-- 本人だけが自分の行を読める
alter table members enable row level security;

create policy "members_select_own"
  on members for select
  using (auth.uid() = id);

-- 会員自身のデータは email をキーにして既存テーブル（conversations / progress /
-- video_progress / submissions / message_counts）に保存する。
-- 既存6名は今まで通り「名前」がキー。混ざらない。
