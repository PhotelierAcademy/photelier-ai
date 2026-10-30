-- 発信ネタ出しツール（本講座の受講生だけ）用テーブル
-- 2026-10-29
--
-- 使い方: Supabase の SQL Editor にこのファイルを貼って Run するだけ。
-- 既存テーブルには一切触らない（新しいテーブルを2つ足すだけ）。
--
-- キーは members と同じく email。
-- サロン会員（tier='subscription'）はアプリ側（app.py）で弾くので、ここには入らない。

-- ① カルテ（1回だけ登録。ペルソナ／悩み／解決策／きっかけ／行き先 など全部まとめて1つのJSONで持つ）
create table if not exists hasshin_karte (
  email       text primary key,
  karte       jsonb not null,
  updated_at  timestamptz not null default now()
);

-- ② 毎週のネタ出し結果（一言テーマ＋7本）。
--    「先週の反応→カルテ更新」のループのために履歴で残す。
create table if not exists hasshin_weeks (
  id          bigint generated always as identity primary key,
  email       text not null,
  theme       text not null,
  items       jsonb not null,
  created_at  timestamptz not null default now()
);

create index if not exists hasshin_weeks_email_idx on hasshin_weeks (email, created_at desc);
