-- Supabase 대시보드 > SQL Editor 에서 한 번 실행하세요 (여러 번 실행해도 안전합니다)

-- 1. 메모 (기존 기능)
create table if not exists public.notes (
  id bigint generated always as identity primary key,
  content text not null,
  created_at timestamptz not null default now()
);

-- 2. 상품
create table if not exists public.products (
  id bigint generated always as identity primary key,
  name text not null unique,
  description text not null default '',
  category text not null default '기타',
  price integer not null check (price >= 0),
  emoji text not null default '🛍️',
  created_at timestamptz not null default now()
);

-- 3. 장바구니 (로그인 없이 브라우저가 만든 cart_id 로 구분)
create table if not exists public.cart_items (
  id bigint generated always as identity primary key,
  cart_id text not null,
  product_id bigint not null references public.products (id) on delete cascade,
  quantity integer not null check (quantity between 1 and 99),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cart_id, product_id)
);

create index if not exists cart_items_cart_id_idx on public.cart_items (cart_id);

-- 4. 보안: 브라우저가 Supabase 에 직접 접근하지 못하게 RLS 를 켭니다.
--    FastAPI 는 secret key 로 접근하므로 영향이 없습니다.
alter table public.notes enable row level security;
alter table public.products enable row level security;
alter table public.cart_items enable row level security;

-- 5. 샘플 상품 (이미 있으면 건너뜀)
insert into public.products (name, description, category, price, emoji) values
  ('제주 한라봉 2kg',   '새콤달콤 산지직송 한라봉',           '과일', 18900, '🍊'),
  ('감귤 초콜릿',       '제주 감귤 향이 가득한 수제 초콜릿',   '간식', 9800,  '🍫'),
  ('흑돼지 육포',       '쫀득하게 말린 제주 흑돼지 육포',      '간식', 12500, '🥓'),
  ('녹차 라떼 파우더',  '오설록 스타일 진한 말차 라떼',        '음료', 7900,  '🍵'),
  ('유채꿀 300g',       '봄 유채꽃에서 채밀한 꿀',             '식품', 15900, '🍯'),
  ('돌하르방 키링',     '제주 여행 기념 수제 키링',            '기념품', 6500, '🗿'),
  ('해녀 에코백',       '튼튼한 캔버스 장바구니 가방',         '기념품', 14900, '👜'),
  ('한라산 소주잔 세트','한라산 일러스트가 새겨진 잔 2개',     '기념품', 11000, '🥃')
on conflict (name) do nothing;
